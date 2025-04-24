from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi import HTTPException
import os
from contextlib import asynccontextmanager
from database.mongodb import get_database
from dotenv import load_dotenv
load_dotenv()

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



# Import all routers
from routes.auth_router import router as auth_router
from routes.chat_router import router as chat_router
from routes.notification_router import router as notification_router
from routes.payment_router import router as payment_router
from routes.user_router import router as user_router

# Celery setup
from celery import Celery
celery_app = Celery(
    'ai_chat',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/0'
)

# Database setup
from database.mongodb import close_db_connection, connect_to_db

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Connect to database on startup
    await connect_to_db()
    await setup_indexes()
    await check_db_setup()
    yield
    # Close database connection on shutdown
    await close_db_connection()

# Initialize FastAPI
app = FastAPI(title="AI Chat API", lifespan=lifespan)

@app.get("/health")
async def health_check():
    try:
        db = get_database()
        await db.command("ping")
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        return {"status": "error", "detail": str(e)}

async def check_db_setup():
    try:
        db = get_database()
        collections = await db.list_collection_names()
        print(f"Available collections: {collections}")
        if "users" not in collections:
            print("Users collection doesn't exist yet - it will be created on first insert")
    except Exception as e:
        print(f"Error checking database setup: {str(e)}")
        
    async def test_db_insert():
        try:
            db = get_database()
            result = await db.test_collection.insert_one({"test": "data"})
            print(f"Test document inserted with ID: {result.inserted_id}")
            
            # Verify it was inserted
            doc = await db.test_collection.find_one({"_id": result.inserted_id})
            print(f"Retrieved test document: {doc}")
        except Exception as e:
            print(f"Error in test insert: {str(e)}")

# Ensure unique indexes are set up
async def setup_indexes():
    db = get_database()
    await db.users.create_index("email", unique=True)
    await db.users.create_index("username", unique=True)
    print("Database indexes set up")

# Frontend paths
frontend_path = os.path.join(os.path.dirname(__file__), "..", "frontend")

# Mount static files
app.mount("/js", StaticFiles(directory=os.path.join(frontend_path, "js")), name="js")
app.mount("/css", StaticFiles(directory=os.path.join(frontend_path, "css")), name="css")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routers
app.include_router(auth_router, prefix="/api/auth", tags=["authentication"])
app.include_router(chat_router, prefix="/api/chat", tags=["chat"])
app.include_router(notification_router, prefix="/api/notifications", tags=["notifications"])
app.include_router(payment_router, prefix="/api/payments", tags=["payments"])
app.include_router(user_router, prefix="/api/users", tags=["users"])

# Serve frontend HTML pages
@app.get("/{filename:path}")
async def serve_pages(filename: str):
    # Check if it's a HTML page
    if filename.endswith(".html") or not filename:
        if not filename:
            file_path = os.path.join(frontend_path, "index.html")
        else:
            file_path = os.path.join(frontend_path, filename)
            
        if os.path.exists(file_path):
            return FileResponse(file_path)
        else:
            raise HTTPException(status_code=404, detail="Page not found")

# Run the app with uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)