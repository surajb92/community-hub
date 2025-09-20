var observer = new IntersectionObserver( (entries,observer) => {
    entries.forEach(entry => {
        if (entry.isIntersecting && entry.intersectionRatio >= 0.5) {
            loadMoreChats();
        }
    });
}, {root:null, rootMargin:'0px', threshold:0.5});
var loadbar = document.createElement('div');
    loadbar.innerHTML = `
        <div class="message-item" style="text-align: center; margin: auto;">Loading...</div>
    `;

socketio.on("sendmsg", function (chat) {
    var chat_list = document.getElementById(room);
    newchat = createChatElement(chat);
    chat_list.appendChild(newchat);
    if (uname === chat.sender) {
        chat_list.scrollTop = chat_list.scrollHeight;
    }
});

socketio.on("user_connect", function(data) {
    user_list = document.getElementById('user-list');
    if (online_users.includes(data.user))
        return;
    var u = document.createElement('div');
    u.innerHTML = data.user;
    user_list.appendChild(u);
})

socketio.on("user_disconnect", function(data) {
    user_list = document.getElementById('user-list');
    for (u of user_list.children) {
        if (u.innerHTML == data.user)
            user_list.removeChild(u);
    }
})

document.addEventListener('DOMContentLoaded', function(event) {
    var chat_list = document.getElementById(room);
    if (!(uname in online_users))
        online_users.push(uname);
    chat_list.style.display = "block";
    populateChat(init_chat);
    populateUsers(online_users);
    setTimeout(() => { observer.observe(loadbar) }, 1000);
    startCooldown(cd);
});

document.addEventListener('keydown', function (event) {
    userchat = document.getElementById('userchat');
    button = document.getElementById('send-btn');
    if (event.key === "Enter" &&  userchat === document.activeElement && !button.disabled) {
        sendMessage();
    }
});

function startCooldown(cooldown) {
    button = document.getElementById('send-btn');
    if (cooldown <= 0) {
        button.disabled = false;
        button.innerHTML = "Send";
        cd = -1;
        return;
    } else {
        button.innerHTML = cooldown;
        if (!button.disabled) {
            button.disabled = true;
        }
        cooldown -= 1;
        setTimeout(() => {
            startCooldown(cooldown);
        }, 1000);
    }
}

function populateUsers(users) {
    user_list = document.getElementById('user-list');
    for (const i of users) {
        var u = document.createElement('div');
        u.innerHTML = i;
        user_list.appendChild(u);
    }
}

function addUser(user) {
}

function removeUser(user) {
}

function loadMoreChats() {
    fetch('/api/morechats')
        .then(response=> {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .then(newchats => {
            populateChat(newchats,false);
        })
        .catch(error => {
            console.error('Error fetching data:', error);
        });
}

function populateChat(chats, scrolldown=true) {
    var chat_list = document.getElementById(room);
    if (loadbar.parentNode == chat_list)
        chat_list.removeChild(loadbar);
    h = chat_list.scrollHeight
    for (let c in chats) {
        t = createChatElement(chats[c]);
        chat_list.prepend(t);
    }
    // This auto smooth scrolls to the last chat, if 2nd argument is not given
    if (scrolldown)
        chat_list.lastChild.scrollIntoView( { behavior:'smooth' })
    else {
        chat_list.scrollTop = chat_list.scrollHeight - h
    }
    if (chats.length !== 0)
        chat_list.prepend(loadbar);
}

function createChatElement(chat) {
    var sent_by_me = uname === chat.sender;
    
    const newchat = document.createElement('div');
    newchat.className = 'message-item ';
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
}

function sendMessage() {
    var userchat = document.getElementById("userchat");
    var chat_list = document.getElementById(room);
    if (userchat.value === "") return;
    var msg = userchat.value;
    socketio.emit("message", { message: msg });
    userchat.value = "";
    if (utype == 'guest')
        startCooldown(10);
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
    room = roomid;
    if (!new_chat.hasChildNodes())
        fetch('/api/getchat')
            .then(response=> {
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                return response.json();
            })
            .then(newchats => {
                populateChat(newchats);
            })
            .catch(error => {
                console.error('Error fetching data:', error);
            });
}