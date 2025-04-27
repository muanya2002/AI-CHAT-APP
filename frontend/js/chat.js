// Global variables
let currentUser = null;
let userCredits = 0;
let stripe = null;
let cardElement = null;
let selectedPackage = null;
let notifications = [];
let unreadNotifications = 0;
let sidebarCollapsed = false;

// API base URL - update this to your actual backend URL
const API_BASE_URL = "http://localhost:8080";

// Get current user from localStorage
function getCurrentUser() {
  try {
    const user = JSON.parse(localStorage.getItem("currentUser"));
    console.log("Loaded user from localStorage:", user);
    return user;
  } catch {
    return null;
  }
}

// Display notifications using a toast-like approach
function showNotification(message, type) {
  const notification = document.createElement("div");
  notification.className = `notification-toast ${type}`;
  notification.textContent = message;
  
  document.body.appendChild(notification);
  
  // Show the notification
  setTimeout(() => {
    notification.classList.add("show");
  }, 10);
  
  // Hide and remove after 3 seconds
  setTimeout(() => {
    notification.classList.remove("show");
    setTimeout(() => notification.remove(), 300);
  }, 3000);
}

// Format date for display
function formatDate(dateString) {
  const date = new Date(dateString);
  const options = { year: "numeric", month: "long", day: "numeric", hour: "2-digit", minute: "2-digit" };
  return date.toLocaleDateString(undefined, options);
}

// DOM Elements
const sidebar = document.getElementById("sidebar");
const sidebarToggleBtn = document.getElementById("sidebar-toggle-btn");
const mobileSidebarToggle = document.getElementById("mobile-sidebar-toggle");
const mainContent = document.querySelector(".main-content");
const chatMessages = document.getElementById("chat-messages");
const chatInput = document.getElementById("chat-input");
const sendBtn = document.getElementById("send-btn");
const creditsDisplay = document.getElementById("credits-display");
const sidebarCredits = document.getElementById("sidebar-credits");
const sidebarUsername = document.getElementById("sidebar-username");
const sidebarEmail = document.getElementById("sidebar-email");
const logoutBtn = document.getElementById("sidebar-logout-btn");
const buyCreditsBtn = document.getElementById("buy-credits-btn");
const paymentModal = document.getElementById("payment-modal");
const closeBtn = document.querySelector(".close-btn");
const selectPackageBtns = document.querySelectorAll(".select-package-btn");
const paymentFormContainer = document.getElementById("payment-form-container");
const paymentForm = document.getElementById("payment-form");
const notificationBadge = document.getElementById("notification-badge");
const notificationsBtn = document.getElementById("notifications-btn");
const notificationsContainer = document.getElementById("notifications-container");
const notificationsList = document.getElementById("notifications-list");

// Validate user data in localStorage
function validateStoredUserData() {
  try {
    const storedUser = localStorage.getItem("currentUser");
    if (!storedUser) {
      console.error("No user data found in localStorage");
      return false;
    }
    
    const userData = JSON.parse(storedUser);
    
    // Check required fields
    if (!userData.id) {
      console.error("Missing user ID in stored user data");
      return false;
    }
    
    if (!userData.token) {
      console.error("Missing auth token in stored user data");
      return false;
    }
    
    // Check token expiration if using JWT
    if (userData.token.split('.').length === 3) {
      try {
        // Extract payload from JWT (middle part)
        const payload = JSON.parse(atob(userData.token.split('.')[1]));
        const expiration = payload.exp * 1000; // Convert to milliseconds
        
        if (Date.now() > expiration) {
          console.error("Authentication token has expired");
          return false;
        }
      } catch (e) {
        console.warn("Could not parse JWT token:", e);
        // Continue if token isn't a valid JWT format
      }
    }
    
    console.log("User data in localStorage is valid");
    return true;
  } catch (error) {
    console.error("Error validating stored user data:", error);
    return false;
  }
}

// Updated init function to check localStorage integrity
function init() {
  // Validate localStorage data first
  if (!validateStoredUserData()) {
    console.error("Invalid user data in localStorage, redirecting to login");
    logout();
    return;
  }
  
  // Get current user
  currentUser = getCurrentUser();
  if (!currentUser || !currentUser.token) {
    window.location.href = "login.html";
    return;
  }

  userCredits = currentUser.credits || 0;

  try {
    // Initialize Stripe - replace with your actual Stripe public key
    if (typeof stripe !== 'undefined') {
      stripe = stripe("pk_live_your_actual_stripe_public_key");
    } else {
      console.warn("Stripe library not loaded");
    }
  } catch (error) {
    console.error("Failed to initialize Stripe:", error);
  }

  // Update UI with cached user data first
  updateUIWithUserData();

  // Then fetch fresh data from server
  fetchUserData().catch(err => {
    console.error("Error in initial data fetch:", err);
  });

  // Add event listeners
  setupEventListeners();
}

// Set up all event listeners
function setupEventListeners() {
  // Sidebar toggle
  sidebarToggleBtn.addEventListener("click", toggleSidebar);
  mobileSidebarToggle.addEventListener("click", toggleMobileSidebar);

  // Chat functionality
  chatInput.addEventListener("keypress", (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  });
  sendBtn.addEventListener("click", sendMessage);

  // Logout
  logoutBtn.addEventListener("click", logout);

  // Payment modal
  buyCreditsBtn.addEventListener("click", openPaymentModal);
  closeBtn.addEventListener("click", closePaymentModal);

  // Close modal when clicking outside
  window.addEventListener("click", (e) => {
    if (e.target === paymentModal) {
      closePaymentModal();
    }
  });

  // Package selection
  selectPackageBtns.forEach((btn) => {
    btn.addEventListener("click", (e) => {
        console.log("Check if selectPackage() is actually being called when buttons are clicked");
      const packageElement = e.target.closest(".credit-package");
      const packageId = packageElement.dataset.packageId;
      console.log("Package selected:", packageId);
      selectPackage(packageId);
    });
  });

  // Notifications toggle
  notificationsBtn.addEventListener("click", () => {
    notificationsContainer.classList.toggle("show");
    if (notificationsContainer.classList.contains("show")) {
      markNotificationsAsRead();
    }
  });

  // Close notifications when clicking outside
  document.addEventListener("click", (e) => {
    if (!notificationsBtn.contains(e.target) && !notificationsContainer.contains(e.target)) {
      notificationsContainer.classList.remove("show");
    }
  });

  // Auto-resize textarea
  chatInput.addEventListener("input", () => {
    chatInput.style.height = "auto";
    chatInput.style.height = chatInput.scrollHeight + "px";
  });
}
function logout() {
  localStorage.removeItem("currentUser");
  window.location.href = "login.html";
}

// Update UI with user data
function updateUIWithUserData() {
  // Update sidebar
  sidebarUsername.textContent = currentUser.username;
  sidebarEmail.textContent = currentUser.email;
  sidebarCredits.textContent = `Credits: ${userCredits}`;

  // Update header
  creditsDisplay.textContent = `Credits: ${userCredits}`;

  // Enable chat
  chatInput.disabled = false;
  sendBtn.disabled = false;
}

// Toggle sidebar (desktop)
function toggleSidebar() {
  sidebarCollapsed = !sidebarCollapsed;
  sidebar.classList.toggle("collapsed", sidebarCollapsed);
  mainContent.classList.toggle("expanded", sidebarCollapsed);
}

// Toggle sidebar (mobile)
function toggleMobileSidebar() {
  sidebar.classList.toggle("mobile-open");
}

// Check for Stripe return when page load
window.addEventListener("DOMContentLoaded", function () {
  init();
  //fetchNotifications();
  if (window.location.search.includes("package_id")) {
    handleStripeReturn();
  }
});

// Chat Functions
async function sendMessage() {
  const message = chatInput.value.trim();
  if (!message) return;

  if (userCredits <= 0) {
    showNotification("You don't have enough credits. Please purchase more.", "error");
    return;
  }

  const thinkingId = "thinking-" + Date.now();
  addStatusMessage("AI is thinking...", thinkingId);

  try {
    console.log("Sending message to AI:", message);
    const response = await fetch(`${API_BASE_URL}/api/chat/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${currentUser.token}`,
      },
      body: JSON.stringify({ message }),
    });

    const thinkingElement = document.getElementById(thinkingId);
    if (thinkingElement) thinkingElement.remove();

    if (!response.ok) {
      // Handle error responses with status codes
      const errorData = await response.text();
      console.error("Server error:", response.status, errorData);
      throw new Error(`Server error: ${response.status} - ${errorData}`);
    }
    

    if (response.headers.get("Content-Type")?.includes("text/event-stream")) {
      const reader = response.body.getReader();
      let aiMessage = "";
      const messageElement = document.createElement("div");
      messageElement.className = "message ai-message";
      chatMessages.appendChild(messageElement);

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        const chunk = new TextDecoder().decode(value);
        aiMessage += chunk;
        messageElement.textContent = aiMessage;
        chatMessages.scrollTop = chatMessages.scrollHeight;
      }
      // After stream is complete
  addMessageToChat("ai", aiMessage);
  userCredits--;
  updateCreditsDisplay();
    
    } else {
      const data = await response.json();
      console.log("AI response received:", data);

    }

    if (data.response) {
      addMessageToChat("ai", data.response);
      // Credits were successfully deducted on the server
      userCredits--; // Only update client-side credits on success
      updateCreditsDisplay();
    } else {
      throw new Error("Response missing expected data");
    }

    fetchUserData(); // update credits
  } catch (error) {
    console.error("Chat error:", error);

    const thinkingElement = document.getElementById(thinkingId);
    if (thinkingElement) thinkingElement.remove();

    addStatusMessage("Failed to get AI response. Please try again.", "error-" + Date.now());
}
}

function addMessageToChat(role, content) {
  const messageElement = document.createElement("div");
  messageElement.className = `message ${role}-message`;
  messageElement.textContent = content;
  chatMessages.appendChild(messageElement);

  // Scroll to bottom
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function addStatusMessage(message, id) {
  const statusElement = document.createElement("div");
  statusElement.className = "message-status";
  statusElement.textContent = message;
  statusElement.id = id;
  chatMessages.appendChild(statusElement);

  // Scroll to bottom
  chatMessages.scrollTop = chatMessages.scrollHeight;
}

function showBrowserNotification(title, body) {
  if (!("Notification" in window)) return;

  if (Notification.permission === "granted") {
    new Notification(title, { body });
  } else if (Notification.permission !== "denied") {
    Notification.requestPermission().then(permission => {
      if (permission === "granted") {
        new Notification(title, { body });
      }
    });
  }
}
showBrowserNotification("New notification", "You're low on credits.");


// Payment Functions
function openPaymentModal() {
  paymentModal.classList.remove("hidden");
  paymentFormContainer.classList.add("hidden");
  selectedPackage = null;
  console.log("Opening payment modal");
}

function closePaymentModal() {
  paymentModal.classList.add("hidden");
  paymentFormContainer.classList.add("hidden");
}

async function selectPackage(packageId) {
    console.log(`Selecting package: ${packageId}`);
  try {
    // Create checkout session on server
    console.log("Frontend fetch path: /payments/create-checkout-session");
    console.log("-> The frontend is adding 'payments/' to the path which might be incorrect");
    const response = await fetch(`${API_BASE_URL}/api/payments/create-checkout-session`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${currentUser.token}`,
      },
      body: JSON.stringify({
        package_id: packageId
      }),
    });
  

    if (!response.ok) {
        const errorText = await response.text();
      console.error("Server response error:", errorText);
      throw new Error("Failed to create checkout session");
    }

    const data = await response.json();
    console.log("Checkout session created:", data);

    // Redirect to Stripe Checkout
    if (data.checkout_url) {
        console.log("Redirecting to:", data.checkout_url);
        window.location.href = data.checkout_url;
      } else {
        throw new Error("No checkout URL returned from server");
      }
    } catch (error) {
      console.error("Error creating checkout session:", error);
      showNotification("Payment failed. Please try again later.", "error");
    }
  }

// This function should be called when returning from Stripe
function handleStripeReturn() {
  const urlParams = new URLSearchParams(window.location.search);
  const paymentSuccess = urlParams.get('payment_success');
  const paymentCancelled = urlParams.get('payment_cancelled');
  
  if (paymentSuccess === 'true') {
    showNotification("Payment successful! Your credits have been updated.", "success");
    fetchUserData(); // Refresh user data including credits
  } else if (paymentCancelled === 'true') {
    showNotification("Payment was cancelled.", "warning");
  }
  
  // Clear the URL parameters
  if (history.pushState) {
    const newUrl = window.location.protocol + "//" + window.location.host + window.location.pathname;
    window.history.pushState({path: newUrl}, '', newUrl);
  }
}

// Update package selection event listeners
function setupPackageSelectionListeners() {
  selectPackageBtns.forEach((btn) => {
    btn.addEventListener("click", (e) => {
      const packageId = e.target.closest(".credit-package").dataset.packageId;
      selectPackage(packageId);
    });
  });
}

async function verifyPayment(packageId) {
  try {
    const response = await fetch(`${API_BASE_URL}/api/payments/verify-payment`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${currentUser.token}`,
      },
      body: JSON.stringify({ sessionId }),
    });
    
    if (!response.ok) {
      throw new Error("Failed to verify payment");
    }
    
    const { success, credits } = await response.json();
    
    if (success) {
      // Update credits
      userCredits = credits;
      updateCreditsDisplay();
      
      // Update localStorage
      currentUser.credits = credits;
      localStorage.setItem("currentUser", JSON.stringify(currentUser));
      
      showNotification("Payment successful! Your credits have been updated.", "success");
    }
  } catch (error) {
    console.error("Payment verification error:", error);
    showNotification("Failed to verify payment. Please contact support.", "error");
  }
}

// Notification Functions
function addNotification(notification) {
  notifications.unshift(notification);
  unreadNotifications++;
  updateNotificationBadge();
  renderNotifications();

  // Also send to server
  if (currentUser) {
    fetch(`${API_BASE_URL}/api/notifications/`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${currentUser.token}`,
      },
      body: JSON.stringify(notification),
    }).catch((err) => console.error("Error saving notification:", err));
  }
}

function updateNotificationBadge() {
  const badge = document.getElementById("notification-badge");
  const unreadCount = notifications.filter(n => !n.read).length;

  if (unreadCount > 0) {
    badge.textContent = unreadCount;
    badge.classList.remove("hidden");
  } else {
    badge.classList.add("hidden");
  }
}


function renderNotifications() {
  notificationsList.innerHTML = "";

  if (notifications.length === 0) {
    const emptyElement = document.createElement("div");
    emptyElement.className = "notification";
    emptyElement.textContent = "No notifications yet.";
    notificationsList.appendChild(emptyElement);
    return;
  }

  notifications.forEach((notification) => {
    const notificationElement = document.createElement("div");
    notificationElement.className = `notification notification-item ${notification.read ? "read" : "unread"}`;

    const messageElement = document.createElement("div");
    messageElement.textContent = notification.message;

    const timeElement = document.createElement("div");
    timeElement.className = "notification-time";
    timeElement.textContent = formatDate(notification.createdAt);

    notificationElement.appendChild(messageElement);
    notificationElement.appendChild(timeElement);

    // ✅ Mark as read on click
    notificationElement.onclick = () => {
      markNotificationAsRead(notification._id); // Backend call
      notification.read = true; // Update local state
      notificationElement.classList.add("read");
      notificationElement.classList.remove("unread");
      updateNotificationBadge(); // Optional: update count
    };

    notificationsList.appendChild(notificationElement);
  });

  // Update the badge count after rendering
  updateNotificationBadge();
}

async function fetchNotifications() {
  if (!currentUser) return;

  try {
    const response = await fetch(`${API_BASE_URL}/api/notifications/${currentUser.id}/`, {
      headers: {
        "Authorization": `Bearer ${currentUser.token}`,
      },
    })
    .then((res) => {
      if (!res.ok) throw new Error("Failed to fetch notifications")
      return res.json()
    })
    .then((data) => {
      if (!data || !Array.isArray(data.notifications)) {
        console.error("Invalid notifications response:", data)
        return
      }

      const unread = data.notifications.filter(n => !n.read)
      displayNotifications(unread)
    })
    .catch((err) => {
      console.error("Error fetching notifications:", err)
    })
  
    renderNotifications();
  } catch (error) {
    console.error("Error fetching notifications:", error);
    showNotification("Failed to fetch notifications", "warning");
  }
}

function markNotificationsAsRead() {
  if (unreadNotifications === 0) return;

  notifications = notifications.map((notification) => ({
    ...notification,
    read: true,
  }));

  unreadNotifications = 0;
  updateNotificationBadge();
  renderNotifications();

  // Update on server
  if (currentUser) {
    fetch(`${API_BASE_URL}/api/notifications/mark-read`, {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${currentUser.token}`,
      },
      body: JSON.stringify({ userId: currentUser.id }),
    }).catch((err) => console.error("Error marking notifications as read:", err));
  }
}

// Utility Functions


async function fetchUserData() {
  if (!currentUser) 
    { console.error("No current user found");
      return;
    }
    console.log("Fetching user data for ID:", currentUser.id);
    console.log("Using token:", currentUser.token ? "Token exists" : "No token");
  try {
    const url = `${API_BASE_URL}/api/users/${currentUser.id}`;
      console.log("Making request to:", url);
    
    const response = await fetch(url, {
      headers: {
        "Authorization": `Bearer ${currentUser.token}`,
        "Content-Type": "application/json"
      },
    });
    console.log("Response status:", response.status);

    if (!response.ok) {
      if (response.status === 401) {
        console.error("Unauthorized: Your session may have expired");
        showNotification("Your session has expired. Please log in again.", "warning");
        logout(); // Redirect to login page
        return;
      }

      const errorText = await response.text();
      console.error("Error response body:", errorText);
      throw new Error(`Failed to fetch user data: ${response.status} ${response.statusText}`);
    }

    const userData = await response.json();
    console.log("User data received:", userData);

    if (!userData) {
      console.error("Server returned null data with 200 status. Possible API issue.");
      showNotification("Unable to fetch your latest data. Using stored data instead.", "warning");
      
      // Continue using existing data from localStorage
      console.log("Using existing data:", currentUser);
      updateUIWithUserData();
      return;
    }
    // Verify required fields exist
    if (typeof userData.credits !== "number") {
      console.error("Missing or invalid credits in user data:", userData);
      
      // Continue using existing credits value
      console.log("Using existing credits value:", userCredits);
      updateUIWithUserData();
      return;
    }

    userCredits = userData.credits;

   // Update other fields if they exist
   if (userData.username) currentUser.username = userData.username;
   if (userData.email) currentUser.email = userData.email;
    
    localStorage.setItem("currentUser", JSON.stringify(currentUser));
    
    updateUIWithUserData();
    updateCreditsDisplay();
  } catch (error) {
    console.error("Error fetching user data:", error);
    showNotification("Failed to update user data", "error");
  }
}

function updateCreditsDisplay() {
  creditsDisplay.textContent = `Credits: ${userCredits}`;
  sidebarCredits.textContent = `Credits: ${userCredits}`;
}

