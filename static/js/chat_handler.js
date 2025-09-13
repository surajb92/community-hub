var socketio = io();
socketio.on("sendmsg", function (message) { createChatItem(message.message, message.sender) });
//socketio.on("roomchg", function (message) { createChatItem(message.message, message.sender) });

document.addEventListener('DOMContentLoaded', function(event) {
    // Populate chat here?
    var chat_list = document.getElementById(room);
    chat_list.style.display = "block";
    populateChat(init_chat);
});

document.addEventListener('keydown', function (event) {
    if (event.key === "Enter" && document.getElementById('userchat') === document.activeElement) {
        sendMessage();
    }
});

function populateChat(chats) {
    var chat_list = document.getElementById(room);
    for (let c in chats) {
        t = createChatElement(chats[c]);
        chat_list.prepend(t);
    }
    // This auto scrolls to front, can add functionality later if needed
    chat_list.scrollTop = chat_list.scrollHeight;
}

function createChatElement(chat) {
    var sent_by_me = uname === chat.sender;
    
    const newchat = document.createElement('div');
    newchat.className = 'message-item '
    newchat.className += sent_by_me ? 'self-message-item' : 'peer-message-item';
    const sndr = document.createElement('small');
    sndr.className = sent_by_me ? 'user-text' : 'peer-text';
    sndr.textContent = chat.sender;
    const msg = document.createElement('div');
    msg.textContent = chat.message;
    const ts = document.createElement('small');
    ts.className = sent_by_me ? 'muted-text' : 'muted-text-white';
    ts.textContent = new Date(chat.timestamp).toLocaleString('en-GB', {hour12: true}).replace(/am/i, "AM").replace(/pm/i, "PM");

    newchat.appendChild(sndr);
    newchat.appendChild(msg);
    newchat.appendChild(ts);

    return newchat;

    /*
    var content = `
    <div class="message-item ${sent_by_me ? "self-message-item" : "peer-message-item"}">
    <small class="${sent_by_me ? "user-text" : "peer-text"}">${sender}</small>
    <div>${message}</div>
    <small class="${sent_by_me ? "muted-text" : "muted-text-white"}">${new Date().toLocaleString('en-GB', {hour12: true}).replace(/am/i, "AM").replace(/pm/i, "PM")}</small>
    </div>`
    return content;
    */
}

function createChatItem(message, sender) {
    var chat_list = document.getElementById(room);
    var usersend = uname === sender;
    if (sender !== "") {
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

function changeRoom(roomid) {
    if (room == roomid) {
        return;
    }
    var old_chat = document.getElementById(room);
    var new_chat = document.getElementById(roomid);
    old_chat.style.display = "none";
    new_chat.style.display = "block";
    socketio.emit("changeroom", { newroom: roomid} );
    fetch('/api/getchat')
        .then(response=> {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(newchats => {
            room = roomid;
            populateChat(newchats);
        })
        .catch(error => {
            console.error('Error fetching data:', error);
        });
}