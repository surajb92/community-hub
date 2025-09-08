function showLogin(){
    const loginHtml = `
        <div id="login-overlay" class="login-overlay"></div>
        <div id="login-popup" class="login-popup">
            <form id="login-form">
                <label for="username">Username:</label><br>
                <input type="text" id="username" name="username"><br>
                <label for="password">Password:</label><br>
                <input type="password" id="password" name="password"><br>
                <br>
                <button type="submit">Login</button>
                <button type="button" id="register" onclick="window.location.href='/register';">Register</button>
            </form>
        </div>
    `;
    // <div id="login-overlay" style="display:none; position:fixed; top:0; left:0; width:100%; height:100%; background-color:rgba(0,0,0,0.5); z-index:999;"></div>
    document.getElementById('topbar').insertAdjacentHTML('afterend', loginHtml);
    // topbar = document.getElementById('topbar');
    // topbar.innerHTML += loginHtml;
    // insertAdjacentHTML('beforeend', loginHtml);

    const loginPopup = document.getElementById('login-popup');
    const overlay = document.getElementById('login-overlay');
    // const closeButton = document.getElementById('close-popup');

    loginPopup.style.display = 'block';
    overlay.style.display = 'block';

    // closeButton.addEventListener('click', hideLogin);
    overlay.addEventListener('click', hideLogin);

}

function hideLogin() {
        const loginPopup = document.getElementById('login-popup');
        const overlay = document.getElementById('login-overlay');
        if (loginPopup) {
            loginPopup.remove(); // Remove the element from the DOM
        }
        if (overlay) {
            overlay.remove(); // Remove the overlay
        }
    }