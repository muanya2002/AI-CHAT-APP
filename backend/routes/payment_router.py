import os
import stripe
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
import uuid
from datetime import datetime
from typing import Dict, Any
import logging
from models.user import UserInDB
from models.payment import PaymentIntent, CreditPackage
from config.oauth import get_current_user
from database.mongodb import get_database

router = APIRouter()

# Initialize Stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://127.0.0.1:8000")

# Define available credit packages
CREDIT_PACKAGES = {
    "basic": {"credits": 100, "price": 5_00},  # $5.00 for 100 credits
    "standard": {"credits": 300, "price": 12_00},  # $12.00 for 300 credits
    "premium": {"credits": 1000, "price": 30_00},  # $30.00 for 1000 credits
}

@router.get("/packages")
async def get_credit_packages():
    """Get available credit packages."""
    return {"packages": CREDIT_PACKAGES}

@router.post("/create-intent")
async def create_payment_intent(payment_data: PaymentIntent, current_user: UserInDB = Depends(get_current_user)):
    """Create payment intent."""
    db = get_database()
    
    try:
        # Create a payment intent with Stripe
        intent = stripe.PaymentIntent.create(
            amount=payment_data.amount,
            currency="usd",
            metadata={
                "user_id": current_user.id,
                "credits": str(payment_data.credits)
            }
        )
        
        # Save payment intent to database
        payment_id = str(uuid.uuid4())
        payment = {
            "_id": payment_id,
            "user_id": current_user.id,
            "payment_intent_id": intent.id,
            "amount": payment_data.amount,
            "credits": payment_data.credits,
            "status": "created",
            "created_at": datetime.utcnow(),
        }
        
        await db.payments.insert_one(payment)
        
        return {"clientSecret": intent.client_secret}
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

@router.post("/create-checkout-session")
async def create_checkout_session(package_data: Dict[str, Any], current_user: UserInDB = Depends(get_current_user)):
    logging.info("Router path: /create-checkout-session")
    """Create Stripe Checkout Session for a credit package."""
    package_id = package_data.get("package_id")
    
    if package_id not in CREDIT_PACKAGES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid package ID",
        )
    
    package = CREDIT_PACKAGES[package_id]
    db = get_database()
    
    try:
        # Create a Stripe Checkout Session
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[
                {
                    "price_data": {
                        "currency": "usd",
                        "product_data": {
                            "name": f"{package_id.capitalize()} Credit Package",
                            "description": f"{package['credits']} Credits",
                        },
                        "unit_amount": package["price"],
                    },
                    "quantity": 1,
                },
            ],
            mode="payment",
            success_url=f"{FRONTEND_URL}/chat.html?payment_success=true",
            cancel_url=f"{FRONTEND_URL}/chat.html?payment_cancelled=true",
            metadata={
                "user_id": current_user.id,
                "credits": str(package["credits"]),
                "package_id": package_id,
            },
        )
        
        # Save checkout session to database
        payment_id = str(uuid.uuid4())
        payment = {
            "_id": payment_id,
            "user_id": current_user.id,
            "checkout_session_id": checkout_session.id,
            "amount": package["price"],
            "credits": package["credits"],
            "package_id": package_id,
            "status": "created",
            "created_at": datetime.utcnow(),
        }
        
        await db.payments.insert_one(payment)
        
        return {"checkout_url": checkout_session.url}
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

@router.post("/webhook")
async def stripe_webhook(request: Request):
    """Handle Stripe webhook."""
    db = get_database()
    
    # Get the webhook signature
    signature = request.headers.get("stripe-signature")
    
    # Get the request body
    payload = await request.body()
    
    try:
        # Verify the webhook signature
        event = stripe.Webhook.construct_event(
            payload, signature, STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid payload",
        )
    except stripe.error.SignatureVerificationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid signature",
        )
    
    # Handle the event
    if event["type"] == "payment_intent.succeeded":
        payment_intent = event["data"]["object"]
        user_id = payment_intent["metadata"]["user_id"]
        credits = int(payment_intent["metadata"]["credits"])
        
        # Update payment status
        await db.payments.update_one(
            {"payment_intent_id": payment_intent.id},
            {"$set": {"status": "succeeded"}}
        )
        
        # Add credits to user
        await db.users.update_one(
            {"_id": user_id},
            {"$inc": {"credits": credits}}
        )
        
        # Create notification
        notification_id = str(uuid.uuid4())
        notification = {
            "_id": notification_id,
            "user_id": user_id,
            "message": f"Payment successful! {credits} credits added to your account.",
            "read": False,
            "created_at": datetime.utcnow(),
        }
        
        await db.notifications.insert_one(notification)
    
    elif event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        user_id = session["metadata"]["user_id"]
        credits = int(session["metadata"]["credits"])
        
        # Update payment status
        await db.payments.update_one(
            {"checkout_session_id": session.id},
            {"$set": {"status": "succeeded"}}
        )
        
        # Add credits to user
        await db.users.update_one(
            {"_id": user_id},
            {"$inc": {"credits": credits}}
        )
        
        # Create notification
        notification_id = str(uuid.uuid4())
        notification = {
            "_id": notification_id,
            "user_id": user_id,
            "message": f"Payment successful! {credits} credits added to your account.",
            "read": False,
            "created_at": datetime.utcnow(),
        }
        
        await db.notifications.insert_one(notification)
    
    return {"received": True}

@router.get("/transaction-history")
async def get_transaction_history(current_user: UserInDB = Depends(get_current_user)):
    """Get user's transaction history."""
    db = get_database()
    
    transactions = await db.payments.find(
        {"user_id": current_user.id}
    ).sort("created_at", -1).to_list(length=50)
    
    # Format transactions for frontend
    formatted_transactions = []
    for transaction in transactions:
        formatted_transactions.append({
            "id": transaction["_id"],
            "amount": transaction["amount"] / 100,  # Convert cents to dollars
            "credits": transaction["credits"],
            "status": transaction["status"],
            "date": transaction["created_at"].strftime("%Y-%m-%d %H:%M:%S"),
        })
    
    return {"transactions": formatted_transactions}
