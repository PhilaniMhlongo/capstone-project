 // Handle login
 document.getElementById('loginForm').addEventListener('submit', async (event) => {
    event.preventDefault();

    const username = document.getElementById('username').value;
    const password = document.getElementById('password').value;

    const clientId = '1560lns5rp8b2rvh3srh6icllb'; // Replace with your Cognito App Client ID
    const region = 'eu-west-1'; // Replace with your AWS region

    const requestPayload = {
        AuthFlow: 'USER_PASSWORD_AUTH',
        ClientId: clientId,
        AuthParameters: {
            USERNAME: username,
            PASSWORD: password
        }
    };

    try {
        const response = await fetch(`https://cognito-idp.${region}.amazonaws.com/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-amz-json-1.1',
                'X-Amz-Target': 'AWSCognitoIdentityProviderService.InitiateAuth'
            },
            body: JSON.stringify(requestPayload)
        });

        if (response.ok) {
            const data = await response.json();
            const idToken = data.AuthenticationResult.IdToken;
            sessionStorage.setItem('idToken', idToken);
            loginModal.style.display = 'none';
            overlay.style.display = 'none';
            loginButton.style.display = 'none';
            logoutButton.style.display = 'block';
            bookingForm.style.display = 'block';

            // Fetch available units after login
            fetchAvailableUnits(idToken);
        } else {
            alert('Login failed. Please try again.');
        }
    } catch (error) {
        alert('Network error. Please try again.');
    }
});