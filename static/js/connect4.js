var socketio=io();

/*window.addEventListener('beforeunload', function () {

})*/

socketio.on("quit-game-server", function(data) {
    socketio.emit("quit-game-ack");
    if (uname !== data.who_quit) {
        alert(data.who_quit+" has quit the game!");
    }
    window.location.href = '/room';
})

function quit_game() {
    socketio.emit("quit-game");
}