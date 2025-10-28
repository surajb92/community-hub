var socketio=io();
var observer = new IntersectionObserver( (entries,observer) => {
    entries.forEach(entry => {
        if (entry.isIntersecting && entry.intersectionRatio >= 0.5) {
            loadMoreChats();
        }
    });
}, {root:null, rootMargin:'0px', threshold:0.5});

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
    for (u of user_list.children) {
        if (u.id == data.user)
            return;
    }
    createUserElement(data.user);
})

socketio.on("user_disconnect", function(data) {
    user_list = document.getElementById('user-list');
    for (u of user_list.children) {
        if (u.id == 'user-ele-'+data.user)
            user_list.removeChild(u);
    }
})

socketio.on("invite-c4-incoming", function(data) {
    dbox = createDialogBox(`${data.peer} has invited you to play Connect4!<br>Accept?`,'yesno');
    dbox.overlay.id = "peer_invite";
    dbox.no.addEventListener('click', function () {
        dbox.overlay.remove();
        socketio.emit("invite-c4-rejected", { gameid : data.gameid });
    })
    dbox.yes.addEventListener('click', function () {
        dbox.overlay.remove();
        socketio.emit("invite-c4-accepted", { gameid : data.gameid });
    })
})

socketio.on("invite-c4-remove", function(data) {
    myinv = document.getElementById('my_invite');
    if (myinv)
        myinv.remove();
    peerinv = document.getElementById('peer_invite');
    if (peerinv)
        peerinv.remove();
    if (data.rejected) {
        socketio.emit("invite-c4-reject-ack");
        dbox = createDialogBox("Your invite was rejected by "+data.peer, 'ok');
        dbox.ok.addEventListener('click', function() {
            dbox.overlay.remove();
        })
    }
})

socketio.on("c4-start-game", function() {
    window.location.href = "/game/connect4";
})

document.addEventListener('DOMContentLoaded', function(event) {
    var chat_list = document.getElementById(room);
    chat_list.style.display = "block";
    populateChat(init_chat);
    populateUsers(online_users);
    document.getElementById('btn-'+room).classList.toggle('current');
    startCooldown(cd);
});

document.addEventListener('keydown', function (event) {
    if (event.key === "Enter") {
        userchat = document.getElementById('userchat');
        button = document.getElementById('send-btn');
        if (userchat === document.activeElement && !button.disabled)
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

function inviteMenu(userbtn,invpeer){
    const overlay = document.createElement('div');
    overlay.className = "basic-overlay";
    overlay.style.display = "block";
    const rect = userbtn.getBoundingClientRect();
    overlay.addEventListener('click', function clickme () {
        this.remove();
    })
    const mbox = document.createElement('div');
    mbox.style.position = 'absolute';
    mbox.style.left = `${rect.left - 120}px`;
    mbox.style.top = `${rect.bottom}px`;
    mbox.style.color = "black";

    const inv1 = document.createElement('button');
    inv1.innerHTML = 'Invite to Connect4';
    inv1.addEventListener('click', function () {
        socketio.emit("invite-c4", { peer : invpeer }, (response) => {
            if (response.status) {
                inviteWaiting('connect4', invpeer, response.gameid);
            }
        } );
        
    })
    mbox.appendChild(inv1);
    overlay.appendChild(mbox);
    document.body.appendChild(overlay);
}

function createUserElement(user) {
    const is_this_me = user === uname;
    user_list = document.getElementById('user-list');
    var bbox = document.createElement('div');
    var ubox = document.createElement('span');
    bbox.id = 'user-ele-'+user;
    bbox.style.display = 'flex';
    ubox.innerHTML = user;
    ubox.style.marginRight = "5px";
    bbox.appendChild(ubox);
    if (is_this_me===true) {
        bbox.style.backgroundColor = "hsla(210, 100%, 30%, 1.00)";
        user_list.prepend(bbox);
    } else {
        var btn = document.createElement('button');
        btn.style.marginLeft = "auto";
        btn.style.backgroundColor = "hsla(120, 100%, 15%, 1.00)";
        btn.style.color = "white";
        btn.innerHTML = `<i class="fas fa-ellipsis-vertical"></i>`;
        btn.onclick = () => inviteMenu(btn, user);
        bbox.appendChild(btn);
        user_list.appendChild(bbox);
    }
}

function populateUsers(users) {
    for (const i of users) {
        createUserElement(i);
    }
}

function loadMoreChats() {
    fetch('/api/morechats')
        .then(response=> {
            if (!response.ok)
                throw new Error(`HTTP error! status: ${response.status}`);
            return response.json();
        })
        .then(newchats => {
            populateChat(newchats,false);
        })
        .catch(error => {
            console.error('Error fetching data: ', error);
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
        chat_list.lastChild.scrollIntoView( { behavior:'smooth' });
    else {
        chat_list.scrollTop = chat_list.scrollHeight - p;
    }
    if (chats.length !== 0)
        chat_list.prepend(loadbar);
}

function createChatElement(chat,justnow=false) {
    var sent_by_me = uname === chat.sender;
    const newchat = document.createElement('div');
    newchat.className = 'message-item ';
    newchat.className += sent_by_me ? 'self-message-item' : 'peer-message-item';
    const sender_box = document.createElement('div');
    sender_box.style.display = 'flex';

    const sname = document.createElement('small');
    sname.textContent = chat.sender;
    sname.style.fontWeight = 'bold';
    sname.style.marginRight = 'auto';
    sender_box.appendChild(sname);

    const edited = document.createElement('small');
    edited.className = 'edit-button';
    edited.textContent = '(edited)';
    edited.id = chat.id+'-edited';
    edited.style.marginRight = '2px';
    edited.hidden = !chat.edited;
    sender_box.appendChild(edited);

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
    timestamp = new Date(chat.timestamp);
    ts.textContent = timestamp.toLocaleString(undefined, {hour12: true});
    dt_diff = new Date() - timestamp;
    const EDIT_TIME = 120000;

    if (justnow || (sent_by_me && dt_diff < EDIT_TIME)) {
        editbutton = document.createElement('button');
        editbutton.className = 'edit-button';
        editbutton.innerHTML = '<i class="fas fa-edit"></i>';
        msg.id = 'edit-'+chat.id;
        editbutton.addEventListener('click', function () { editMessage(this, chat.id) });
        sender_box.appendChild(editbutton);
        // settimeout to delete edit button after dt_diff ms
        setTimeout(removeEdit, justnow ? EDIT_TIME : EDIT_TIME-dt_diff, editbutton, chat.id);
    }

    newchat.appendChild(sender_box);
    newchat.appendChild(msg);
    newchat.appendChild(ts);

    return newchat;
}

function removeEdit(editref,chatid) {
    msg = document.getElementById('edit-'+chatid)
    msg.removeAttribute('id');
    editref.remove();
}

function editMessage(editb, chatid) {
    editb.hidden = true;
    const chat = document.getElementById('edit-'+chatid);
    const oldmsg = chat.innerHTML;
    const form = document.createElement('form');
    const editbox = document.createElement('input');
    const subm = document.createElement('input');
    subm.type = 'submit';
    subm.hidden = true;
    editbox.name = 'newmsg';
    editbox.value = oldmsg;
    editbox.size = oldmsg.length > 60 ? 60 : oldmsg.length;
    form.appendChild(editbox);
    form.appendChild(subm);
    chat.innerHTML = "";
    chat.appendChild(form);
    editbox.focus();
    editbox.addEventListener('focusout', () => {
        form.remove();
        chat.innerHTML = oldmsg;
        if (editb)
            editb.hidden = false;
    })
    form.addEventListener('submit', function (event) {
        event.preventDefault();
        fdata = new FormData(this);
        const newmsg = fdata.get('newmsg');
        fetch('/api/editmessage', {
            method: 'POST',
            headers: { 'Content-Type' : 'application/json'},
            body: JSON.stringify( {id: chatid, newmessage: newmsg} )
        })
        .then(response => {
            if (!response.ok) {
                chat.innerHTML = oldmsg;
                throw new Error(`HTTP error from server, status : ${response.status}`);
            }
            if (editb)
                editb.hidden = false;
            document.getElementById(chatid+'-edited').hidden = false;
            chat.innerHTML = newmsg;
        })
        .catch(error => {
            chat.innerHTML = oldmsg;
            console.error('Error editing message with id ',chatid,': ', error);
        });
        form.remove();
    })
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
        startCooldown(30);
    else
        startCooldown(5);
}

function changeRoom(newroom) {
    if (room == newroom) {
        return;
    }
    var old_chat = document.getElementById(room);
    var new_chat = document.getElementById(newroom);
    socketio.emit("changeroom", { new_room: newroom} , (response) => {
        if (response.status) {
            old_chat.style.display = "none";
            new_chat.style.display = "block";
            document.getElementById('btn-'+room).classList.toggle('current');
            document.getElementById('btn-'+newroom).classList.toggle('current');
            room = newroom;
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
                        console.error('Error fetching messages from room ',room,': ', error);
                    });
        } else
            console.error("Error! Failed to change room to ", newroom);
    });
}

function inviteWaiting(game, peer, g_id) {
    dbox = createDialogBox(`Invited ${peer} to ${game}...<br>Awaiting response...<br><i class="fas fa-spinner fa-spin"></i>`,'cancel')
    dbox.overlay.id = "my_invite";
    dbox.cancel.addEventListener('click', function () {
        dbox.overlay.remove();
        socketio.emit("invite-c4-canceled", { gameid: g_id });
    })
}

function createDialogBox(msg,format) {
    var dbox = {};

    const overlay = document.createElement('div');
    const mbox = document.createElement('div');
    const bbox = document.createElement('div');
    const message = document.createElement('div');

    message.style.textAlign = "center";
    message.innerHTML = msg;
    mbox.appendChild(message);
    overlay.classList.add('basic-overlay','message-overlay','message-centered');
    bbox.classList.add('message-centered');
    mbox.appendChild(bbox);
    overlay.appendChild(mbox);
    document.body.appendChild(overlay);
    dbox.overlay = overlay;
    
    if (format == "yesno") {
        const yes = document.createElement('button');
        const no = document.createElement('button');
        yes.style.marginRight = "5px";
        yes.innerHTML = "Yes";
        no.innerHTML = "No";
        bbox.appendChild(yes);
        bbox.appendChild(no);
        dbox.yes = yes;
        dbox.no = no;
    } else if (format == "cancel") {
        const cancel = document.createElement('button');
        cancel.innerHTML = "Cancel";
        bbox.appendChild(cancel);
        dbox.cancel = cancel;
    } else if (format == "ok") {
        const ok = document.createElement('button');
        ok.innerHTML = "Ok";
        bbox.appendChild(ok);
        dbox.ok = ok;
    }
    return dbox;
}