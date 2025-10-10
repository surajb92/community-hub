var observer = new IntersectionObserver( (entries,observer) => {
    entries.forEach(entry => {
        if (entry.isIntersecting && entry.intersectionRatio >= 0.5) {
            loadMoreChats();
        }
    });
}, {root:null, rootMargin:'0px', threshold:0.5});

// localStorage.clear();
if (localStorage.getItem('peer_colors') === null) {
    localStorage.setItem('peer_colors', JSON.stringify({}));
}
var peer_colors = JSON.parse(localStorage.getItem('peer_colors'));

socketio.on("sendmsg", function (chat) {
    var chat_list = document.getElementById(room);
    newchat = createChatElement(chat, uname===chat.sender);
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
    document.getElementById('btn-'+room).classList.toggle('current');
    //loadbar = document.getElementById(room+'-load');
    //setTimeout(() => { observer.observe(loadbar) }, 1000);
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
    var loadbar = document.getElementById(room+'-load');
    if (!loadbar) {
        loadbar = document.createElement('div');
        loadbar.innerHTML = `<div class="message-item" style="text-align: center; margin: auto;">Loading...</div>`;
        loadbar.id = room+'-load';
        setTimeout(() => { observer.observe(loadbar) }, 300);
    } else
        chat_list.removeChild(loadbar);
    p = chat_list.scrollHeight - chat_list.scrollTop;
    for (let c of chats) {
        t = createChatElement(c);
        chat_list.prepend(t);
    }
    // This auto smooth scrolls to the last chat, if 2nd argument is not given
    if (scrolldown && chat_list.hasChildNodes())
        chat_list.lastChild.scrollIntoView( { behavior:'smooth' })
    else {
        chat_list.scrollTop = chat_list.scrollHeight - p;
    }
    if (chats.length !== 0)
        chat_list.prepend(loadbar);
}

function removeEdit(editref) {
    editref.remove();
}

function createChatElement(chat,justnow=false) {
    var sent_by_me = uname === chat.sender;
    const newchat = document.createElement('div');
    newchat.className = 'message-item ';
    newchat.className += sent_by_me ? 'self-message-item' : 'peer-message-item';
    const sender_box = document.createElement('div');
    const sname = document.createElement('small');
    sender_box.style.display = 'flex';
    sender_box.appendChild(sname);
    sname.textContent = chat.sender;
    sname.style.fontWeight = 'bold';
    if (sent_by_me) {
        sname.style.color = 'rgb(13, 150, 255)';
    } else {
        if (peer_colors && peer_colors[chat.sender] !== undefined) {
            sname.style.color = peer_colors[chat.sender];
        } else {
            newcolor = generatePeerColor();
            peer_colors[chat.sender] = newcolor;
            localStorage.setItem('peer_colors', JSON.stringify(peer_colors));
            sname.style.color = newcolor;
        }
    }
    const msg = document.createElement('div');
    msg.textContent = chat.message;
    const ts = document.createElement('small');
    ts.className = sent_by_me ? 'muted-text' : 'muted-text-white';
    timestamp = new Date(chat.timestamp)
    ts.textContent = timestamp.toLocaleString('en-GB', {hour12: true}).replace(/am/i, "AM").replace(/pm/i, "PM");
    dt_diff = new Date() - timestamp;
    const EDIT_TIME = 10000;

    if (justnow || (sent_by_me && dt_diff < EDIT_TIME)) {
        editbutton = document.createElement('button');
        editbutton.className = 'edit-button';
        editbutton.innerHTML = '<i class="fas fa-edit"></i>';
        sender_box.appendChild(editbutton);
        // settimeout to delete edit button after dt_diff ms
        setTimeout(removeEdit, justnow ? EDIT_TIME : EDIT_TIME-dt_diff, editbutton);
    }

    newchat.appendChild(sender_box);
    newchat.appendChild(msg);
    newchat.appendChild(ts);

    return newchat;
}

function generatePeerColor() {
    var hue = Math.floor(Math.random() * 361);
    const saturation = 100;
    const lightness = 60;
    let newcolor;
    if (peer_colors)
        looper = true;
    else {
        hue = Math.floor(Math.random() * 361);
        newcolor = `hsl(${hue}, ${saturation}%, ${lightness}%)`;
        looper = false;
    }
    while (looper) { // Loop to check if new user's colors are similar to already stored ones
        looper = false;
        hue = Math.floor(Math.random() * 361);
        newcolor = `hsl(${hue}, ${saturation}%, ${lightness}%)`;
        for(c of Object.values(peer_colors)) {
            comma = c.indexOf(',');
            h = parseInt(c.substring(4,comma),10);
            too_similar = Math.abs(hue - h) < 5;
            if (too_similar) {
                looper = true;
                break;
            }
        }
    }
    return newcolor;
}

function sendMessage() {
    var userchat = document.getElementById("userchat");
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
    document.getElementById('btn-'+room).classList.toggle('current');
    document.getElementById('btn-'+roomid).classList.toggle('current');
    
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