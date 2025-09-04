var socketio = io();
socketio.on("sendmsg", function (message) { createChatItem(message.message, message.sender) });

document.addEventListener('keydown', function (event) {
    if (event.key === "Enter" && document.getElementById('userchat') === document.activeElement) {
        sendMessage();
    }
});

function createChatItem(message, sender) {
    var chat_list = document.getElementById("chat-list");
    if (sender === "") {
        content = `<p class="member-activity">${message}</p>`;
    } else {
        var usersend = uname === sender;
        var content = `
        <div class="message-item ${usersend ? "self-message-item" : "peer-message-item"}">
        <small class="${usersend ? "user-text" : "peer-text"}">${sender}</small>
        <div>${message}</div>
        <small class="${usersend ? "muted-text" : "muted-text-white"}">${new Date().toLocaleString()}</small>
        </div>`
    ;}
    chat_list.innerHTML += content;
    chat_list.scrollIntoView({ behavior: 'smooth', block: 'end' })
}
function sendMessage() {
    var userchat = document.getElementById("userchat");
    if (userchat.value === "") return;
    var msg = userchat.value;
    socketio.emit("message", { message: msg });
    userchat.value = "";
}