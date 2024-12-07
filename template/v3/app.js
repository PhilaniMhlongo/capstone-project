document.addEventListener('DOMContentLoaded', () => {
    const loginBtn = document.getElementById('loginBtn');
    const logoutBtn = document.getElementById('logoutBtn');
    const loginModal = document.getElementById('loginModal');
    const overlay = document.getElementById('overlay');
    const loginForm = document.getElementById('loginForm');
    const bookingForm = document.getElementById('bookingForm');
    const unitSelect = document.getElementById('unitSelect');
    const unitImagePreview = document.getElementById('unitImagePreview');
    const responseMessage = document.getElementById('responseMessage');
    const unitCards = document.getElementById('unitCards');
    const API_BASE_URL = 'https://yh2imbp562.execute-api.eu-west-1.amazonaws.com/prod';
    let idToken = null; // Stores user authentication token

    // Login functionality
    loginBtn.addEventListener('click', () => {
        loginModal.style.display = 'flex';
        overlay.style.display = 'block';
    });

    overlay.addEventListener('click', () => {
        loginModal.style.display = 'none';
        overlay.style.display = 'none';
    });

    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;

        try {
            const response = await fetch('https://cognito-idp.eu-west-1.amazonaws.com/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-amz-json-1.1',
                    'X-Amz-Target': 'AWSCognitoIdentityProviderService.InitiateAuth',
                },
                body: JSON.stringify({
                    AuthFlow: 'USER_PASSWORD_AUTH',
                    ClientId: '1560lns5rp8b2rvh3srh6icllb',
                    AuthParameters: {
                        USERNAME: username,
                        PASSWORD: password,
                    },
                }),
            });

            if (response.ok) {
                const data = await response.json();
                idToken = data.AuthenticationResult.IdToken; // Save token
                sessionStorage.setItem('idToken', idToken);

                loginModal.style.display = 'none';
                overlay.style.display = 'none';
                loginBtn.style.display = 'none';
                logoutBtn.style.display = 'block';
                loadAvailableUnits(); // Fetch units after login
                showMessage(`Welcome, ${username}!`, 'success');
            } else {
                showMessage('Login failed. Please check your credentials.', 'error');
            }
        } catch (error) {
            console.error('Login error:', error);
            showMessage('Network error during login. Please try again.', 'error');
        }
    });

    // Logout functionality
    logoutBtn.addEventListener('click', () => {
        idToken = null;
        sessionStorage.removeItem('idToken');
        loginBtn.style.display = 'block';
        logoutBtn.style.display = 'none';
        unitCardsContainer.innerHTML = '';
        showMessage('Logged out successfully', 'success');
    });

    // Load available units from the API
    async function loadAvailableUnits() {
        if (!idToken) {
            alert('Please log in first');
            return;
        }

        try {
            const response = await fetch(`https://yh2imbp562.execute-api.eu-west-1.amazonaws.com/prod/units?status=Available&page=1&limit=10`, {
                method: 'GET',
                mode: 'cors',
                headers: {
                    'Authorization': `Bearer ${idToken}`
                }
            });

            const data = await response.json();
            unitCards.innerHTML = ''; // Clear previous units

            if (data.units && data.units.length > 0) {
                data.units.forEach(unit => {
                    const card = document.createElement('div');
                    card.classList.add('unit-card');
                    card.innerHTML = `
                        <h3>Unit ${unit.unit_id.slice(0, 8)}</h3>
                        <p>Size: ${unit.size}</p>
                        <p>Location: ${unit.location}</p>
                        ${unit.imgUrl ? `<img src="${unit.imgUrl}" alt="Unit Image" style="max-width:100%; height:200px; object-fit:cover;">` : ''}
                    `;
                    card.dataset.unitId = unit.unit_id;
                    card.addEventListener('click', () => selectUnit(unit));
                    unitCards.appendChild(card);
                });

                // Populate unit select dropdown
                const unitOptions = data.units.map(unit => 
                    `<option value="${unit.unit_id}">Unit ${unit.unit_id.slice(0, 8)} - ${unit.size}</option>`
                ).join('');
                unitSelect.innerHTML = '<option value="">Choose a Unit</option>' + unitOptions;
            } else {
                unitCards.innerHTML = '<p>No available units found.</p>';
            }
        } catch (error) {
            console.error('Error loading units:', error);
            unitCards.innerHTML = '<p>Error loading units. Please try again.</p>';
        }
    }

    // Unit selection
    function selectUnit(unit) {
        // Set the selected unit in the dropdown
        unitSelect.value = unit.unit_id;

        // Show unit image if available
        if (unit.imgUrl) {
            unitImagePreview.src = unit.imgUrl;
            unitImagePreview.style.display = 'block';
        } else {
            unitImagePreview.style.display = 'none';
        }
    }

    // Booking submission
    bookingForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        if (!ID_TOKEN) {
            alert('Please log in first');
            return;
        }

        const selectedUnitId = unitSelect.value;
        const duration = document.querySelector('input[name="duration"]:checked').value;
        const billingOption = document.getElementById('billingOption').value;
        const startDate = document.getElementById('startDate').value;

        // Validate form
        if (!selectedUnitId || !duration || !billingOption || !startDate) {
            showMessage('Please fill out all fields', 'error');
            return;
        }

        try {
            // Simulate booking API call
            const response = await fetch(`${API_BASE_URL}/book-unit'`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${idToken}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    unit_id: selectedUnitId,
                    duration: parseInt(duration),
                    billing_option: billingOption,
                    start_date: startDate
                })
            });

            const data = await response.json();

            if (data.booking_id) {
                showMessage('Booking confirmed successfully!', 'success');
                bookingForm.reset();
                unitImagePreview.style.display = 'none';
            } else {
                throw new Error('Booking failed');
            }
        } catch (error) {
            console.error('Booking error:', error);
            showMessage('Failed to book unit. Please try again.', 'error');
        }
    });

    // Message display
    function showMessage(message, type) {
        responseMessage.textContent = message;
        responseMessage.className = `message ${type}`;
        responseMessage.style.display = 'block';

        // Hide message after 5 seconds
        setTimeout(() => {
            responseMessage.style.display = 'none';
        }, 5000);
    }
});