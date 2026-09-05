document.addEventListener("DOMContentLoaded", () => {
  const activitiesList = document.getElementById("activities-list");
  const activitySelect = document.getElementById("activity");
  const emailInput = document.getElementById("email");
  const loginForm = document.getElementById("login-form");
  const logoutButton = document.getElementById("logout-button");
  const managedStudentSelect = document.getElementById("managed-student");
  const messageDiv = document.getElementById("message");
  const signupContainer = document.getElementById("signup-container");
  const signupForm = document.getElementById("signup-form");
  const userPanel = document.getElementById("user-panel");
  const userStatus = document.getElementById("user-status");

  let token = sessionStorage.getItem("accessToken");
  let currentUser = null;

  function showMessage(text, type) {
    messageDiv.textContent = text;
    messageDiv.className = type;
    setTimeout(() => messageDiv.classList.add("hidden"), 5000);
  }

  function authHeaders() {
    return token ? { Authorization: `Bearer ${token}` } : {};
  }

  function canManage(email) {
    if (!currentUser) return false;
    if (["provider", "admin"].includes(currentUser.role)) return true;
    if (currentUser.role === "student") return currentUser.email === email;
    return currentUser.managed_students.includes(email);
  }

  function requestedEmail() {
    if (currentUser.role === "student") return null;
    if (currentUser.role === "parent") return managedStudentSelect.value;
    return emailInput.value;
  }

  function updateAccountView() {
    const signedIn = currentUser !== null;
    loginForm.classList.toggle("hidden", signedIn);
    userPanel.classList.toggle("hidden", !signedIn);
    signupContainer.classList.toggle("hidden", !signedIn);

    if (!signedIn) return;

    userStatus.textContent = `${currentUser.email} (${currentUser.role})`;
    managedStudentSelect.classList.toggle("hidden", currentUser.role !== "parent");
    emailInput.classList.toggle("hidden", currentUser.role === "parent");

    if (currentUser.role === "student") {
      emailInput.value = currentUser.email;
      emailInput.readOnly = true;
    } else {
      emailInput.value = "";
      emailInput.readOnly = false;
    }

    managedStudentSelect.innerHTML = "";
    currentUser.managed_students.forEach((email) => {
      const option = document.createElement("option");
      option.value = email;
      option.textContent = email;
      managedStudentSelect.appendChild(option);
    });
  }

  async function fetchActivities() {
    try {
      const response = await fetch("/activities");
      if (!response.ok) throw new Error("Unable to load activities");
      const activities = await response.json();

      activitiesList.innerHTML = "";
      activitySelect.innerHTML = '<option value="">-- Select an activity --</option>';

      Object.entries(activities).forEach(([name, details]) => {
        const activityCard = document.createElement("div");
        activityCard.className = "activity-card";
        const spotsLeft = details.max_participants - details.participants.length;
        const participantsHTML = details.participants.length
          ? `<div class="participants-section">
              <h5>Participants:</h5>
              <ul class="participants-list">
                ${details.participants
                  .map(
                    (email) =>
                      `<li><span class="participant-email">${email}</span>${
                        canManage(email)
                          ? `<button class="delete-btn" data-activity="${name}" data-email="${email}" aria-label="Unregister ${email}" title="Unregister">&times;</button>`
                          : ""
                      }</li>`
                  )
                  .join("")}
              </ul>
            </div>`
          : "<p><em>No participants yet</em></p>";

        activityCard.innerHTML = `
          <h4>${name}</h4>
          <p>${details.description}</p>
          <p><strong>Schedule:</strong> ${details.schedule}</p>
          <p><strong>Availability:</strong> ${spotsLeft} spots left</p>
          <div class="participants-container">${participantsHTML}</div>
        `;
        activitiesList.appendChild(activityCard);

        const option = document.createElement("option");
        option.value = name;
        option.textContent = name;
        activitySelect.appendChild(option);
      });

      document.querySelectorAll(".delete-btn").forEach((button) => {
        button.addEventListener("click", handleUnregister);
      });
    } catch (error) {
      activitiesList.innerHTML =
        "<p>Failed to load activities. Please try again later.</p>";
      console.error("Error fetching activities:", error);
    }
  }

  async function handleUnregister(event) {
    const button = event.currentTarget;
    const activity = button.dataset.activity;
    const email = button.dataset.email;

    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(activity)}/unregister?email=${encodeURIComponent(email)}`,
        { method: "DELETE", headers: authHeaders() }
      );
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || "Unable to unregister student");
      showMessage(result.message, "success");
      await fetchActivities();
    } catch (error) {
      showMessage(error.message, "error");
    }
  }

  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    try {
      const response = await fetch("/auth/login", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          email: document.getElementById("login-email").value,
          password: document.getElementById("login-password").value,
        }),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || "Unable to sign in");

      token = result.access_token;
      currentUser = result.user;
      sessionStorage.setItem("accessToken", token);
      loginForm.reset();
      updateAccountView();
      await fetchActivities();
    } catch (error) {
      showMessage(error.message, "error");
    }
  });

  logoutButton.addEventListener("click", async () => {
    if (token) {
      await fetch("/auth/logout", { method: "POST", headers: authHeaders() });
    }
    token = null;
    currentUser = null;
    sessionStorage.removeItem("accessToken");
    updateAccountView();
    await fetchActivities();
  });

  signupForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const activity = activitySelect.value;
    const email = requestedEmail();
    const query = email ? `?email=${encodeURIComponent(email)}` : "";

    try {
      const response = await fetch(
        `/activities/${encodeURIComponent(activity)}/signup${query}`,
        { method: "POST", headers: authHeaders() }
      );
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || "Unable to sign up");
      showMessage(result.message, "success");
      activitySelect.value = "";
      await fetchActivities();
    } catch (error) {
      showMessage(error.message, "error");
    }
  });

  async function initialize() {
    if (token) {
      const response = await fetch("/auth/me", { headers: authHeaders() });
      if (response.ok) {
        currentUser = await response.json();
      } else {
        token = null;
        sessionStorage.removeItem("accessToken");
      }
    }
    updateAccountView();
    await fetchActivities();
  }

  initialize();
});