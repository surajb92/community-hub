function showLogin(){
    const loginPopup = document.getElementById('login1-popup');
    const overlay = document.getElementById('login1-overlay');
    loginPopup.style.display = 'block';
    overlay.style.display = 'block';
    overlay.addEventListener('click', hideLogin);
}

function hideLogin() {
    const loginPopup = document.getElementById('login1-popup');
    const overlay = document.getElementById('login1-overlay');
    loginPopup.style.display = 'none';
    overlay.style.display = 'none';
}