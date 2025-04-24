// Import necessary modules or declare variables
const API_BASE_URL = "http://localhost:8080" // Replace with your actual API base URL

// Show notification to user
function showNotification(message, type = "info") {
  const notification = document.createElement("div");
  notification.className = `notification-toast ${type}`;
  notification.textContent = message;

  document.body.appendChild(notification);

  // Add show class after a short delay to trigger animation
  setTimeout(() => {
    notification.classList.add("show");
  }, 10);

  // Remove notification after 3 seconds
  setTimeout(() => {
    notification.classList.remove("show");
    setTimeout(() => {
      document.body.removeChild(notification);
    }, 300);
  }, 3000);
}

// Login and Registration functionality
document.addEventListener("DOMContentLoaded", () => {
  // Login form submission
  const loginForm = document.getElementById("login-form")
  if (loginForm) {
    loginForm.addEventListener("submit", handleLogin)
  }

  // Register form submission
  const registerForm = document.getElementById("register-form")
  if (registerForm) {
    registerForm.addEventListener("submit", handleRegister)
  }
  checkAuth();
})

async function handleLogin(e) {
  e.preventDefault()

  const email = document.getElementById("login-email").value
  const password = document.getElementById("login-password").value

  try {
    const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ email, password }),
    })

    if (!response.ok) {
      throw new Error("Login failed")
    }

    const data = await response.json()
    const currentUser = {
      id: data.user.id,
      username: data.user.username,
      email: data.user.email,
      token: data.token,
      credits: data.user.credits,
    }

    // Save to localStorage
    localStorage.setItem("currentUser", JSON.stringify(currentUser))

    // Redirect to chat page
    window.location.href = "chat.html"
  } catch (error) {
    console.error("Login error:", error)
    showNotification("Login failed. Please check your credentials and try again.", "error")
  }
}

async function handleRegister(e) {
  e.preventDefault()

  const username = document.getElementById("register-username").value
  const email = document.getElementById("register-email").value
  const password = document.getElementById("register-password").value

  try {
    const response = await fetch(`${API_BASE_URL}/api/auth/register`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ username, email, password }),
    })
    

    if (!response.ok) {
      const errorData = await response.json();
      throw new Error(errorData.detail || "Registration failed");
    }
    

    const data = await response.json()
    const currentUser = {
      id: data.user.id,
      username: data.user.username,
      email: data.user.email,
      token: data.token,
      credits: data.user.credits || 5, // Usually new users get some free credits
    }
  

    // Redirect to login page
    window.location.href = "login.html"
  } catch (error) {
    console.error("Registration error:", error)
    showNotification("Registration failed. Please try again with a different email or username.", "error")
  }
}

// Check if a token exists in the URL (from OAuth redirects)
function checkOAuthReturn() {
  const urlParams = new URLSearchParams(window.location.search);
  const token = urlParams.get("token");

  if (token) {
    fetch(`${API_BASE_URL}/api/users/profile`, {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    })
      .then((response) => {
        if (!response.ok) {
          throw new Error("Authentication failed");
        }
        return response.json();
      })
      .then((userData) => {
        // Store user data and token in localStorage
        const user = {
          id: userData.id,
          username: userData.username,
          email: userData.email,
          credits: userData.credits,
          token: token,
          avatar: userData.avatar,
        };

        localStorage.setItem("currentUser", JSON.stringify(user));
        
        // Redirect to chat page after successful OAuth login
        window.location.href = "chat.html";
      })
      .catch((error) => {
        console.error("OAuth authentication error:", error);
        showNotification("Authentication failed. Please try logging in again.", "error");
        window.location.href = "login.html";
      });
  }
}


// Check if user is logged in
function checkAuth() {
  const currentUser = getCurrentUser()

  // If on auth page but already logged in, redirect to chat
  if (
    (window.location.pathname.includes("login.html") ||
      window.location.pathname.includes("register.html") ||
      window.location.pathname === "/" ||
      window.location.pathname === "/index.html") &&
    currentUser
  ) {
    window.location.href = "chat.html"
    return
  }

  // If on protected page but not logged in, redirect to login
  if (
    (window.location.pathname.includes("chat.html") || window.location.pathname.includes("profile.html")) &&
    !currentUser
  ) {
    window.location.href = "login.html"
    return
  }
}

// Get current user from localStorage
function getCurrentUser() {
  const savedUser = localStorage.getItem("currentUser")
  if (savedUser) {
    try {
      return JSON.parse(savedUser)
    } catch (error) {
      console.error("Error parsing saved user:", error)
      localStorage.removeItem("currentUser")
      return null
    }
  }
  return null
}

// Format date
function formatDate(dateString) {
  const date = new Date(dateString)
  return date.toLocaleString()
}
