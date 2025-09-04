var socketio = io();
socketio.on("sendmsg", function (message) { createChatItem(message.message, message.sender) });

document.addEventListener('keydown', function (event) {
    if (event.key === "Enter" && document.getElementById('userchat') === document.activeElement) {
        sendMessage();
    }
});

function createChatItem(message, sender) {
    var chat_list = document.getElementById("chat-list");
    console.log("entered")
    if (sender === "") {
        content = `<p class="member-activity">${message}</p>`;
        console.log("sender empty")
    } else {
        console.log("sender start")
        var usersend = uname === sender;
        var content = `
        <li class="message-item ${usersend ? "self-message-item" : "peer-message-item"}">
        <p>${message}</p>
        <small class="${usersend ? "muted-text" : "muted-text-white"}">${new Date().toLocaleString()}</small>
        </li>`
        console.log("sender end")
    ;}
    chat_list.innerHTML += content;
}
function sendMessage() {
    var userchat = document.getElementById("userchat");
    if (userchat.value === "") return;
    var msg = userchat.value;
    socketio.emit("message", { message: msg });
    userchat.value = "";
}