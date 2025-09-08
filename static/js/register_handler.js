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
    } else {
        return true;
    }
}