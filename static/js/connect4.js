var socketio=io();
var board_elements = [];

/*window.addEventListener('beforeunload', function () {

})*/

socketio.on("quit-game-server", function(data) {
    socketio.emit("quit-game-ack");
    if (uname !== data.who_quit) {
        alert(data.who_quit+" has quit the game, you win!");
    }
    window.location.href = '/room';
})

socketio.on("c4-gameover", function(data) {
    if(data.state == "win") {
        if (data.winner == uname) {
            alert("You win !");
        } else {
            alert("You lose !");
        }
    } else {
        alert("Game tied !");
    }
    socketio.emit("quit-game-ack");
    window.location.href = '/room';
})

socketio.on("move-made", function(data) {
    col = data.column;
    row = getNextRow(data.column);
    const cell = board_elements[row][col];
    board[row][col] = data.color;
    cell.dataset.fill = data.color;
    data.color === 1 ? cell.classList.add('yellow') : cell.classList.add('red');
    toggle_turn();
})

function toggle_turn() {
    my_turn = !my_turn
    document.getElementById('your_turn').classList.toggle("hidden");
    document.getElementById('opp_turn').classList.toggle("hidden");
}

document.addEventListener('DOMContentLoaded', function() {
    if(my_turn) {
        document.getElementById('your_turn').classList.toggle("hidden");
    } else {
        document.getElementById('opp_turn').classList.toggle("hidden");
    }
    const gameboard = document.getElementById('gameboard');
    for (let row = 0; row < 6; row++) {
        rowset = []
        for (let col = 0; col < 7; col++) {
            const cell = document.createElement('div');
            cell.classList.add('cell');
            cell.dataset.row = row;
            cell.dataset.col = col;
            cell.dataset.fill = board[row][col];
            if (cell.dataset.fill == 1) {
                cell.classList.add('yellow');
            } else if (cell.dataset.fill == 2) {
                cell.classList.add('red');
            }
            rowset.push(cell);
            gameboard.appendChild(cell);
        }
        board_elements.push(rowset);
    }
    gameboard.addEventListener('click', (e) => {
        if (e.target.classList.contains('cell') && my_turn) {
            const col = parseInt(e.target.dataset.col);
            const row = getNextRow(col);
            if (row !== -1) {
                document.querySelectorAll('.'+my_color+'-sample').forEach(cell => {
                    cell.classList.remove(my_color+'-sample');
                });
                socketio.emit("c4-move", { column: col } )
            }
        }
    })
    for (i=0;i<7;i++) {

    }

    //board_elements[0][0]
    gameboard.addEventListener('mouseover', (e) => {
        if (e.target.classList.contains('cell') && my_turn) {
            const col = parseInt(e.target.dataset.col);
            const row = getNextRow(col);
            if (row !== -1) {
                board_elements[row][col].classList.add(my_color+'-sample')
            }
        } else {
            document.querySelectorAll('.'+my_color+'-sample').forEach(cell => {
                cell.classList.remove(my_color+'-sample');
            });
        }
    });

    //board_elements[0][0].
    gameboard.addEventListener('mouseleave', (e) => {
        document.querySelectorAll('.'+my_color+'-sample').forEach(cell => {
            cell.classList.remove(my_color+'-sample');
        });
    });
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