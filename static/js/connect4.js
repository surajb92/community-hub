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

document.addEventListener('DOMContentLoaded', function() {
    if (my_turn) {
        document.getElementById('your_turn').classList.toggle("hidden");
    } else {
        document.getElementById('opp_turn').classList.toggle("hidden");
    }
    const gameboard = document.getElementById('gameboard');
    for (let row = 0; row < 6; row++) {
        for (let col = 0; col < 7; col++) {
            const cell = document.createElement('div');
            cell.classList.add('cell');
            cell.dataset.fill = board[row][col];
            if (cell.dataset.fill == 1) {
                cell.classList.add('yellow');
            } else if (cell.dataset.fill == 2) {
                cell.classList.add('red');
            }
            gameboard.appendChild(cell);
        }
    }
    gameboard.addEventListener('click', (e) => {
        if (e.target.classList.contains('cell') && my_turn) {
            const col = parseInt(e.target.dataset.col);
            const row = getNextRow(col);
            if (row !== -1) {
                socketio.emit("c4-move", { column: col } )
            }
        }
    })
})

// Get next available row in column
function getNextRow(col) {
    for (let row = 5; row >= 0; row--) {
        if (board[row][col] === 0) return row;
    }
    return -1;
}

function quit_game() {
    socketio.emit("quit-game");
}