// Elements
const modal = document.querySelector(".modal");
const modalUnitText = document.getElementById("modal-unit-text");
const loginModal = document.getElementById("loginModal"); // Modal for login
const overlay = document.getElementById("overlay"); // Overlay element
const loginForm = document.getElementById("loginForm"); // Login form element
const loginBtn = document.getElementById("loginBtn"); // Login button
const logoutBtn = document.getElementById("logoutBtn"); // Logout button
const storageContainer = document.querySelector(".grid");

// Simulated storage units data
const storageUnits = [
  { id: 1, size: "1m x 1m", description: "Ideal for small items and boxes." },
  { id: 2, size: "2m x 3m", description: "Perfect for furniture and equipment." },
  { id: 3, size: "3m x 4m", description: "For multiple large items." },
  { id: 4, size: "4m x 6m", description: "Great for full house storage." },
];

// Display storage units dynamically
const displayStorageUnits = (units) => {
  storageContainer.innerHTML = ""; // Clear existing units
  units.forEach((unit) => {
    const unitCard = `
      <div class="bg-white p-6 rounded-lg shadow-md">
        <h3 class="text-xl font-medium">${unit.size}</h3>
        <p>${unit.description}</p>
        <button class="mt-4 bg-orange-500 text-white px-4 py-2 rounded-lg book-now" data-unit="${unit.size}">Book Now</button>
      </div>
    `;
    storageContainer.insertAdjacentHTML("beforeend", unitCard);
  });
};

// Load storage units on page load
document.addEventListener("DOMContentLoaded", () => {
  displayStorageUnits(storageUnits);

  // Attach modal actions dynamically
  document.querySelectorAll(".book-now").forEach((button) => {
    button.addEventListener("click", () => {
      const unit = button.getAttribute("data-unit");
      modalUnitText.querySelector("span").textContent = unit;
      modal.classList.add("active");
    });
  });

  // Close modal on clicking close button
  document.querySelectorAll(".close-modal").forEach((button) => {
    button.addEventListener("click", () => {
      modal.classList.remove("active");
    });
  });

  // Close modal when clicking outside
  modal.addEventListener("click", (e) => {
    if (e.target === modal) {
      modal.classList.remove("active");
    }
  });
});

// Open login modal
loginBtn.addEventListener("click", () => {
  loginModal.style.display = "flex";
  overlay.style.display = "block";
});

// Close login modal on overlay click
overlay.addEventListener("click", () => {
  loginModal.style.display = "none";
  overlay.style.display = "none";
});

// Handle login form submission
loginForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const username = document.getElementById("username").value;
  const password = document.getElementById("password").value;

  try {
    const response = await fetch("https://cognito-idp.eu-west-1.amazonaws.com/", {
      method: "POST",
      headers: {
        "Content-Type": "application/x-amz-json-1.1",
        "X-Amz-Target": "AWSCognitoIdentityProviderService.InitiateAuth",
      },
      body: JSON.stringify({
        AuthFlow: "USER_PASSWORD_AUTH",
        ClientId: "1560lns5rp8b2rvh3srh6icllb",
        AuthParameters: {
          USERNAME: username,
          PASSWORD: password,
        },
      }),
    });

    if (response.ok) {
      const data = await response.json();
      const idToken = data.AuthenticationResult.IdToken;
      sessionStorage.setItem("idToken", idToken);

      loginModal.style.display = "none";
      overlay.style.display = "none";
      loginBtn.style.display = "none";
      logoutBtn.style.display = "block";

      alert(`Welcome, ${username}!`);
    } else {
      alert("Login failed. Please check your credentials.");
    }
  } catch (error) {
    console.error("Login error:", error);
    alert("Network error during login. Please try again.");
  }
});

// Logout action
logoutBtn.addEventListener("click", () => {
  sessionStorage.removeItem("idToken");
  loginBtn.style.display = "block";
  logoutBtn.style.display = "none";
  alert("You have been logged out.");
});
