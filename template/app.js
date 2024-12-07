document.addEventListener('DOMContentLoaded', () => {
    const loginBtn = document.getElementById('loginBtn');
    const logoutBtn = document.getElementById('logoutBtn');
    const loginModal = document.getElementById('loginModal');
    const overlay = document.getElementById('overlay');
    const loginForm = document.getElementById('loginForm');
    const bookingForm = document.getElementById('bookingForm');
    const responseMessage = document.getElementById('responseMessage');

    // Toggle Login Modal
    function toggleLoginModal() {
        loginModal.style.display = loginModal.style.display === 'block' ? 'none' : 'block';
        overlay.style.display = loginModal.style.display;
    }

    loginBtn.addEventListener('click', toggleLoginModal);
    overlay.addEventListener('click', toggleLoginModal);

    // Login Form Submission
    loginForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;

        // Simulated login (replace with actual authentication)
        if (username && password) {
            showMessage('Login successful!', 'success');
            toggleLoginModal();
            updateAuthState(true);
        } else {
            showMessage('Invalid username or password', 'error');
        }
    });

    // Logout functionality
    logoutBtn.addEventListener('click', () => {
        showMessage('Logged out successfully', 'success');
        updateAuthState(false);
    });

    // Booking Form Submission
    bookingForm.addEventListener('submit', (e) => {
        e.preventDefault();
        const unitId = document.getElementById('unitId').value;
        const duration = document.getElementById('duration').value;
        const billingOption = document.getElementById('billingOption').value;
        const startDate = document.getElementById('startDate').value;

        // Simulated booking (replace with actual booking logic)
        if (unitId && duration && billingOption && startDate) {
            showMessage('Storage unit booked successfully!', 'success');
        } else {
            showMessage('Please fill in all required fields', 'error');
        }
    });

    // Helper function to show messages
    function showMessage(message, type) {
        responseMessage.textContent = message;
        responseMessage.className = `message ${type}`;
        responseMessage.style.display = 'block';

        // Auto-hide message after 3 seconds
        setTimeout(() => {
            responseMessage.style.display = 'none';
        }, 3000);
    }

    // Update authentication state
    function updateAuthState(isLoggedIn) {
        loginBtn.style.display = isLoggedIn ? 'none' : 'inline-block';
        logoutBtn.style.display = isLoggedIn ? 'inline-block' : 'none';
        bookingForm.style.display = isLoggedIn ? 'block' : 'none';
    }

    // Initial state
    updateAuthState(false);
});