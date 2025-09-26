var duplicate_user = false;
var user_timeout = null;
var pass_timeout = null;
var pass2_timeout = null;
var valid_user = false;
var valid_pass = false;
const uname = document.getElementById('username');
const pass = document.getElementById('password');
const pass2 = document.getElementById('password2');
const eye = document.getElementById('pass-eye')

document.addEventListener('DOMContentLoaded',() => {
    checkUser();
})

// Internal functions to show/hide required username/password check elements
function userCheckDisplay(element=null) {
    document.getElementById('user_load').classList.add('hidden');
    document.getElementById('user_yes').classList.add('hidden');
    document.getElementById('user_no').classList.add('hidden');
    document.getElementById('user_guest').classList.add('hidden');
    if (element)
        document.getElementById(element).classList.remove('hidden');
}

function pass2CheckDisplay(element=null) {
    document.getElementById('pass2_short').classList.add('hidden');
    document.getElementById('pass2_yes').classList.add('hidden');
    document.getElementById('pass2_no').classList.add('hidden');
    if (element)
        document.getElementById(element).classList.remove('hidden');
}

// Check if username already exists
function checkUser() {
    valid_user = false;
    clearTimeout(user_timeout);
    userCheckDisplay('user_load');
    const username = uname.value;
    user_timeout = setTimeout(() => {
        if (username==="") {
            userCheckDisplay();
            return;
        } else if (username.startsWith('guest-')) {
            userCheckDisplay('user_guest');
            return;
        }
        fetch('/api/unamecheck', {
            method: 'POST',
            headers: {
                'Content-Type' : 'application/json'
            },
            body: JSON.stringify( { username: username} )
        })
        .then(response => response.json())
        .then(result => {
            // update UI here
            if (result['user_exists']) {
                userCheckDisplay('user_no');
            } else {
                userCheckDisplay('user_yes');
                valid_user = true;
            }
        })
        .catch(error => {
            console.error('Error checking username: ', error);
        });
    }, 300);
}
uname.addEventListener('input', checkUser);

// Show password strength
function passwordStrength() {
    const password = pass.value;
    pass_timeout = setTimeout(() => {
        // add password strength check here later
    }, 300);
}
// pass.addEventListener('input', passwordStrength);

// Check if passwords match
function passwordsMatch() {
    valid_pass = false;
    const password = pass.value;
    const password2 = pass2.value;
    if (password === "") {
        pass2CheckDisplay();
        return;
    } else if (password.length < 5) {
        pass2CheckDisplay('pass2_short');
        return;
    } else if (password !== password2) {
        pass2CheckDisplay('pass2_no');
        return;
    }
    pass2CheckDisplay('pass2_yes');
    valid_pass = true;
    return;
}
pass.addEventListener('input', passwordsMatch);
pass2.addEventListener('input', passwordsMatch);

// Toggle password visibility
eye.addEventListener('click', function() {
    if (pass.type === "text")
        pass.type = "password";
    else
        pass.type = "text";
    this.classList.toggle('fa-eye');
    this.classList.toggle('fa-eye-slash');
})

/*function togglePass() {
    const showpass = document.getElementById('showpass');
    const pass = document.getElementById('password');
    if (showpass.checked) {
        pass.type = "text";
  } else {
        pass.type = "password";
  }
}*/

function checkRegisterData() {
    u = document.forms["registrar"]["username"];
    p1 = document.forms["registrar"]["password"];
    p2 = document.forms["registrar"]["password2"];
    if (p1.value.length < 5) {
        return false;
    } else if (p1.value != p2.value) {
        return false;
    } else if (u.value.startsWith('guest-')) {
        return false;
    }
    if (valid_pass && valid_user)
        return true;
    else
        return false;
}