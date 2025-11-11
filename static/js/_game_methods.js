var socketio=io();
var gameover = false;

socketio.on("quit-game-server", function(data) {
    socketio.emit("quit-game-ack");
    gameover = true;
    if (uname !== data.who_quit) {
        dbox = createDialogBox(data.who_quit+" has quit the game, you win!");
        dbox.ok.addEventListener('click', () => {
            window.location.href = '/room';
        })
    } else {
        window.location.href = '/room';
    }
})

function quit_game() {
    if (gameover)
        window.location.href='/room';
    else {
        dbox = createDialogBox("Are you sure you want to quit the game?",'yesno');
        dbox.yes.addEventListener('click', () => {
            socketio.emit("quit-game");
        })
        dbox.no.addEventListener('click', () => {
            dbox.overlay.remove();
        })
    }
}