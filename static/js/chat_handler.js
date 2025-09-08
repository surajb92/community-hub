var socketio = io();
socketio.on("sendmsg", function (message) { createChatItem(message.message, message.sender) });

document.addEventListener('keydown', function (event) {
    if (event.key === "Enter" && document.getElementById('userchat') === document.activeElement) {
        sendMessage();
    }
});

document.addEventListener('DOMContentLoaded', function(event) {
    chat_list = document.getElementById('chat-list');
    chat_list.scrollTop = chat_list.scrollHeight;
});

function createChatItem(message, sender) {
    var chat_list = document.getElementById("chat-list");
    var usersend = uname === sender;
    if (sender === "") {
        content = `<p class="member-activity">${message}</p>`;
    } else {
        var content = `
        <div class="message-item ${usersend ? "self-message-item" : "peer-message-item"}">
        <small class="${usersend ? "user-text" : "peer-text"}">${sender}</small>
        <div>${message}</div>
        <small class="${usersend ? "muted-text" : "muted-text-white"}">${new Date().toLocaleString('en-GB', {hour12: true}).replace(/am/i, "AM").replace(/pm/i, "PM")}</small>
        </div>`
    ;}
    chat_list.innerHTML += content;
    if (usersend) {
        chat_list.scrollTop = chat_list.scrollHeight;
    }
}
function sendMessage() {
    var userchat = document.getElementById("userchat");
    if (userchat.value === "") return;
    var msg = userchat.value;
    socketio.emit("message", { message: msg });
    userchat.value = "";
}