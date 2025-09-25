var duplicate_user = false;
var server_timeout = null;
var valid_user = false;
var valid_pass = false;
const uname = document.getElementById('username');

document.addEventListener('DOMContentLoaded',() => {
    checkUser();
})

function userCheckDisplay(element=null) {
    document.getElementById('load').classList.add('hidden');
    document.getElementById('useryes').classList.add('hidden');
    document.getElementById('userno').classList.add('hidden');
    if (element)
        document.getElementById(element).classList.remove('hidden');
}

// Check if username already exists
function checkUser() {
    valid_user = false;
    clearTimeout(server_timeout);
    userCheckDisplay('load');
    const username = uname.value;
    server_timeout = setTimeout(() => {
        if (username==="") {
            userCheckDisplay();
            return
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
                userCheckDisplay('userno');
                console.log("Username already exists!");
            } else {
                userCheckDisplay('useryes');
                console.log("Username is free for use.");
                valid_user = true;
            }
        })
        .catch(error => {
            console.error('Error checking username: ', error);
        });
    }, 300);
}
uname.addEventListener('input', checkUser);

function togglePass() {
    const showpass = document.getElementById('showpass');
    const pass = document.getElementById('password');
    if (showpass.checked) {
        pass.type = "text";
  } else {
        pass.type = "password";
  }
}

function checkRegisterData() {
    u = document.forms["registrar"]["username"];
    p1 = document.forms["registrar"]["password"];
    p2 = document.forms["registrar"]["password2"];
    if (p1.value.length < 6) {
        alert("Password must have at least 6 characters!")
    } else if (p1.value != p2.value) {
        alert("Passwords don't match!")
        return false;
    } else if (u.value.startsWith('guest-')) {
        alert("Cannot use 'guest-' at the start of your username!");
        return false;
    } else {
        return true;
    }
}