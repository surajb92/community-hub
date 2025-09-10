function showLogin(){
    const loginPopup = document.getElementById('login-popup');
    const overlay = document.getElementById('login-overlay');
    loginPopup.style.display = 'block';
    overlay.style.display = 'block';
    overlay.addEventListener('click', hideLogin);
}

function hideLogin() {
    const loginPopup = document.getElementById('login-popup');
    const overlay = document.getElementById('login-overlay');
    loginPopup.style.display = 'none';
    overlay.style.display = 'none';
    if (typeof lgn_errors !== 'undefined') {
        d = document.getElementById('lerrors')
        d.style.display = 'none'
    }
}

if (typeof lgn_errors !== 'undefined') {
    showLogin();
} 