document.addEventListener("DOMContentLoaded", () => {
  const activitiesList = document.getElementById("activities-list");
  const activitySelect = document.getElementById("activity");
  const signupForm = document.getElementById("signup-form");
  const signupButton = document.getElementById("signup-submit");
  const messageDiv = document.getElementById("message");
  const loginForm = document.getElementById("login-form");
  const registerForm = document.getElementById("register-form");
  const profileForm = document.getElementById("profile-form");
  const profilePanel = document.getElementById("profile-panel");
  const authMessage = document.getElementById("auth-message");
  let accessToken = sessionStorage.getItem("accessToken");
  let currentUser = null;

  function apiFetch(url, options = {}) {
    const headers = { ...options.headers };
    if (accessToken) {
      headers.Authorization = `Bearer ${accessToken}`;
    }
    if (options.body) {
      headers["Content-Type"] = "application/json";
    }
    return fetch(url, { ...options, headers });
  }

  function showAuthMessage(text, isError = false) {
    authMessage.textContent = text;
    authMessage.className = isError ? "error" : "success";
  }

  function setAuthenticatedUser(user) {
    currentUser = user;
    loginForm.classList.add("hidden");
    registerForm.classList.add("hidden");
    document.getElementById("auth-switch").classList.add("hidden");
    profilePanel.classList.remove("hidden");
    document.getElementById("account-summary").textContent =
      `${user.name} · ${user.role.replaceAll("_", " ")}`;
    document.getElementById("profile-name").value = user.name;
    document.getElementById("profile-grade").value = user.grade || "";
    signupButton.disabled = false;
  }

  function clearAuthentication() {
    accessToken = null;
    currentUser = null;
    sessionStorage.removeItem("accessToken");
    profilePanel.classList.add("hidden");
    document.getElementById("auth-switch").classList.remove("hidden");
    document.getElementById("show-login").click();
    signupButton.disabled = true;
  }

  async function completeAuthentication(response) {
    const result = await response.json();
    if (!response.ok) {
      showAuthMessage(result.detail || "Unable to sign in.", true);
      return;
    }
    accessToken = result.access_token;
    sessionStorage.setItem("accessToken", accessToken);
    setAuthenticatedUser(result.user);
    authMessage.className = "hidden";
    fetchActivities();
  }

  document.getElementById("show-login").addEventListener("click", () => {
    loginForm.classList.remove("hidden");
    registerForm.classList.add("hidden");
    document.getElementById("show-login").setAttribute("aria-pressed", "true");
    document.getElementById("show-register").setAttribute("aria-pressed", "false");
  });

  document.getElementById("show-register").addEventListener("click", () => {
    loginForm.classList.add("hidden");
    registerForm.classList.remove("hidden");
    document.getElementById("show-login").setAttribute("aria-pressed", "false");
    document.getElementById("show-register").setAttribute("aria-pressed", "true");
  });

  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    await completeAuthentication(apiFetch("/auth/login", {
      method: "POST",
      body: JSON.stringify({
        email: document.getElementById("login-email").value,
        password: document.getElementById("login-password").value,
      }),
    }));
  });

  registerForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    await completeAuthentication(apiFetch("/auth/register", {
      method: "POST",
      body: JSON.stringify({
        email: document.getElementById("register-email").value,
        name: document.getElementById("register-name").value,
        grade: document.getElementById("register-grade").value || null,
        password: document.getElementById("register-password").value,
        invite_code: document.getElementById("register-invite").value,
      }),
    }));
  });

  profileForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const response = await apiFetch(`/users/${encodeURIComponent(currentUser.email)}`, {
      method: "PATCH",
      body: JSON.stringify({
        name: document.getElementById("profile-name").value,
        grade: document.getElementById("profile-grade").value || null,
      }),
    });
    const result = await response.json();
    if (!response.ok) {
      showAuthMessage(result.detail || "Unable to update profile.", true);
      return;
    }
    setAuthenticatedUser(result);
    showAuthMessage("Profile saved.");
  });

  document.getElementById("sign-out").addEventListener("click", async () => {
    await apiFetch("/auth/logout", { method: "POST" });
    clearAuthentication();
    showAuthMessage("Signed out.");
    fetchActivities();
  });

  // Function to fetch activities from API
  async function fetchActivities() {
    try {
      const response = await fetch("/activities");
      const activities = await response.json();

      // Clear loading message
      activitiesList.innerHTML = "";
      activitySelect.innerHTML = '<option value="">-- Select an activity --</option>';

      // Populate activities list
      Object.entries(activities).forEach(([name, details]) => {
        const activityCard = document.createElement("div");
        activityCard.className = "activity-card";

        const spotsLeft =
          details.max_participants - details.participants.length;

        // Create participants HTML with delete icons instead of bullet points
        const canManageOthers = currentUser &&
          ["activity_manager", "administrator"].includes(currentUser.role);
        const participantsHTML =
          details.participants.length > 0
            ? `<div class="participants-section">
              <h5>Participants:</h5>
              <ul class="participants-list">
                ${details.participants
                  .map(
                    (email) =>
                      `<li><span class="participant-email">${email}</span>${currentUser && (currentUser.email === email || canManageOthers) ? `<button class="delete-btn" aria-label="Unregister ${email}" data-activity="${name}" data-email="${email}">Remove</button>` : ""}</li>`
                  )
                  .join("")}
              </ul>
            </div>`
            : `<p><em>No participants yet</em></p>`;

        activityCard.innerHTML = `
          <h4>${name}</h4>
          <p>${details.description}</p>
          <p><strong>Schedule:</strong> ${details.schedule}</p>
          <p><strong>Availability:</strong> ${spotsLeft} spots left</p>
          <div class="participants-container">
            ${participantsHTML}
          </div>
        `;

        activitiesList.appendChild(activityCard);

        // Add option to select dropdown
        const option = document.createElement("option");
        option.value = name;
        option.textContent = name;
        activitySelect.appendChild(option);
      });

      // Add event listeners to delete buttons
      document.querySelectorAll(".delete-btn").forEach((button) => {
        button.addEventListener("click", handleUnregister);
      });
    } catch (error) {
      activitiesList.innerHTML =
        "<p>Failed to load activities. Please try again later.</p>";
      console.error("Error fetching activities:", error);
    }
  }

  // Handle unregister functionality
  async function handleUnregister(event) {
    const button = event.target;
    const activity = button.getAttribute("data-activity");
    const email = button.getAttribute("data-email");

    try {
      const response = await apiFetch(
        `/activities/${encodeURIComponent(
          activity
        )}/unregister?email=${encodeURIComponent(email)}`,
        {
          method: "DELETE",
        }
      );

      const result = await response.json();

      if (response.ok) {
        messageDiv.textContent = result.message;
        messageDiv.className = "success";

        // Refresh activities list to show updated participants
        fetchActivities();
      } else {
        messageDiv.textContent = result.detail || "An error occurred";
        messageDiv.className = "error";
      }

      messageDiv.classList.remove("hidden");

      // Hide message after 5 seconds
      setTimeout(() => {
        messageDiv.classList.add("hidden");
      }, 5000);
    } catch (error) {
      messageDiv.textContent = "Failed to unregister. Please try again.";
      messageDiv.className = "error";
      messageDiv.classList.remove("hidden");
      console.error("Error unregistering:", error);
    }
  }

  // Handle form submission
  signupForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const activity = document.getElementById("activity").value;

    try {
      const response = await apiFetch(
        `/activities/${encodeURIComponent(
          activity
        )}/signup`,
        {
          method: "POST",
        }
      );

      const result = await response.json();

      if (response.ok) {
        messageDiv.textContent = result.message;
        messageDiv.className = "success";
        signupForm.reset();

        // Refresh activities list to show updated participants
        fetchActivities();
      } else {
        messageDiv.textContent = result.detail || "An error occurred";
        messageDiv.className = "error";
      }

      messageDiv.classList.remove("hidden");

      // Hide message after 5 seconds
      setTimeout(() => {
        messageDiv.classList.add("hidden");
      }, 5000);
    } catch (error) {
      messageDiv.textContent = "Failed to sign up. Please try again.";
      messageDiv.className = "error";
      messageDiv.classList.remove("hidden");
      console.error("Error signing up:", error);
    }
  });

  // Initialize app
  document.getElementById("show-login").click();
  if (accessToken) {
    apiFetch("/auth/me").then(async (response) => {
      if (response.ok) {
        setAuthenticatedUser(await response.json());
      } else {
        clearAuthentication();
      }
      fetchActivities();
    });
  }
  fetchActivities();
});
