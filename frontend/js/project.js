// Global variables
let currentUser = null;
let userCredits = 0;
let sidebarCollapsed = false;

// API base URL
const API_BASE_URL = "http://localhost:8080"; // Replace with your actual API base URL

// Initialize the application
function init() {
  // Check if user is logged in
  currentUser = getCurrentUser();
  
  if (!currentUser) {
    window.location.href = "login.html";
    return;
  }
  
  // Update UI with user data
  updateUIWithUserData();
  
  // Fetch fresh data from server
  fetchUserData();
  
  // Set up event listeners
  setupEventListeners();
}

// Helper function to get current user from localStorage
function getCurrentUser() {
  try {
    return JSON.parse(localStorage.getItem("currentUser"));
  } catch (error) {
    console.error("Error getting current user:", error);
    return null;
  }
}

// Update UI with user data
function updateUIWithUserData() {
  if (!currentUser) return;
  
  // Update sidebar
  const sidebarUsername = document.getElementById("sidebar-username");
  const sidebarEmail = document.getElementById("sidebar-email");
  
  if (sidebarUsername) sidebarUsername.textContent = currentUser.username;
  if (sidebarEmail) sidebarEmail.textContent = currentUser.email;
  
  // Update profile
  const profileUsername = document.getElementById("profile-username");
  const profileEmail = document.getElementById("profile-email");
  const profileUsernameInput = document.getElementById("profile-username-input");
  const profileEmailInput = document.getElementById("profile-email-input");
  
  if (profileUsername) profileUsername.textContent = currentUser.username;
  if (profileEmail) profileEmail.textContent = currentUser.email;
  if (profileUsernameInput) profileUsernameInput.value = currentUser.username;
  if (profileEmailInput) profileEmailInput.value = currentUser.email;
}

// Set up all event listeners
function setupEventListeners() {
  // Sidebar toggle (desktop)
  const sidebarToggleBtn = document.getElementById("sidebar-toggle-btn");
  if (sidebarToggleBtn) {
    sidebarToggleBtn.addEventListener("click", toggleSidebar);
  }
  
  // Sidebar toggle (mobile)
  const mobileSidebarToggle = document.getElementById("mobile-sidebar-toggle");
  if (mobileSidebarToggle) {
    mobileSidebarToggle.addEventListener("click", toggleMobileSidebar);
  }
  
  // Logout
  const logoutBtn = document.getElementById("sidebar-logout-btn");
  if (logoutBtn) {
    logoutBtn.addEventListener("click", logout);
  }
  
  // Profile form submission
  const profileForm = document.getElementById("profile-form");
  if (profileForm) {
    profileForm.addEventListener("submit", updateProfile);
  }
}

// Toggle sidebar (desktop)
function toggleSidebar() {
  const sidebar = document.getElementById("sidebar");
  const mainContent = document.querySelector(".main-content");
  
  sidebarCollapsed = !sidebarCollapsed;
  sidebar.classList.toggle("collapsed", sidebarCollapsed);
  if (mainContent) {
    mainContent.classList.toggle("expanded", sidebarCollapsed);
  }
}

// Toggle sidebar (mobile)
function toggleMobileSidebar() {
  const sidebar = document.getElementById("sidebar");
  sidebar.classList.toggle("mobile-open");
}

// Logout function
function logout() {
  localStorage.removeItem("currentUser");
  window.location.href = "login.html";
}

// Update profile
async function updateProfile(e) {
  e.preventDefault();
  
  const profileUsernameInput = document.getElementById("profile-username-input");
  const newUsername = profileUsernameInput.value.trim();
  
  if (!newUsername) {
    showNotification("Username cannot be empty", "error");
    return;
  }
  
  if (newUsername === currentUser.username) {
    showNotification("No changes to save", "info");
    return;
  }
  
  try {
    const response = await fetch(`${API_BASE_URL}/api/users/update-profile`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${currentUser.token}`,
      },
      body: JSON.stringify({
        username: newUsername,
      }),
    });
    
    if (!response.ok) {
      throw new Error("Failed to update profile");
    }
    
    // Update current user
    currentUser.username = newUsername;
    localStorage.setItem("currentUser", JSON.stringify(currentUser));
    
    // Update UI
    updateUIWithUserData();
    
    showNotification("Profile updated successfully", "success");
  } catch (error) {
    console.error("Error updating profile:", error);
    showNotification("Failed to update profile", "error");
  }
}

// Fetch user data from the server
async function fetchUserData() {
  if (!currentUser) return;
  
  try {
    const response = await fetch(`${API_BASE_URL}/api/users/${currentUser.id}`, {
      headers: {
        Authorization: `Bearer ${currentUser.token}`,
      },
    });
    
    if (!response.ok) {
      throw new Error("Failed to fetch user data");
    }
    
    const userData = await response.json();
    
    // Update current user with fresh data
    currentUser = { ...currentUser, ...userData };
    localStorage.setItem("currentUser", JSON.stringify(currentUser));
    
    // Update UI
    updateUIWithUserData();
  } catch (error) {
    console.error("Error fetching user data:", error);
  }
}

async function loadProfileChatHistory() {
  if (!currentUser) return;

  try {
    const response = await fetch(`${API_BASE_URL}/api/chat/`, {
      headers: {
        "Authorization": `Bearer ${currentUser.token}`,
        "Content-Type": "application/json",
      },
    });

    if (!response.ok) {
      throw new Error("Failed to fetch chat history");
    }

    const history = await response.json();
    
    const chatHistoryContainer = document.getElementById("chat-history");
    chatHistoryContainer.innerHTML = ""; // Clear any placeholder

    if (!Array.isArray(history) || history.length === 0) {
      chatHistoryContainer.innerHTML = `<p class="empty-state">No chat history available.</p>`;
      return;
    }

    history.reverse().forEach((entry) => {
      console.log("User:", entry.message, "\nAI:", entry.response);
      const chatEntry = document.createElement("div");
      chatEntry.className = "chat-history-entry";
      chatEntry.innerHTML = `
      <div><strong>You:</strong> ${entry.message}</div>
        <div><strong>AI:</strong> ${entry.response || "(No response)"}</div>
        <div><em>${new Date(entry.created_at).toLocaleString()}</em></div>
        <hr/>
      `;
      chatHistoryContainer.appendChild(chatEntry);
    });
  } catch (error) {
    console.error("Error loading profile chat history:", error);
  }
}


// Simple notification function
function showNotification(message, type = "info") {
  // You can implement a proper notification system here
  // For now, let's use console.log
  console.log(`[${type}] ${message}`);
  
  // If you want to show a visual notification, you could use something like:
  alert(message);
}

// Initialize the app when the DOM is loaded
document.addEventListener("DOMContentLoaded", () => {
  init();
  loadProfileChatHistory();
});