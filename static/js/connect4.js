var socketio=io();
var board_elements = [];
var gameover = false;

socketio.on("quit-game-server", function(data) {
    socketio.emit("quit-game-ack");
    if (uname !== data.who_quit) {
        createDialogBox(data.who_quit+" has quit the game, you win!");
    }
    window.location.href = '/room';
})

socketio.on("c4-gameover", function(data) {
    gameover = true;
    if(data.state == "win") {
        win_glow(data.winline, data.winstart, data.wincolor);
        if (data.winner == uname) {
            createDialogBox("You win !");
        } else {
            createDialogBox("You lose !");
        }
    } else {
        createDialogBox("Game tied !");
    }
    socketio.emit("quit-game-ack");
    document.getElementById('goback').classList.remove('hidden');
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

function win_glow(wline,wstart,wcolor) {
    row = wstart[0];
    col = wstart[1];
    for (i=0;i<4;i++) {
        const cell = board_elements[row][col];
        cell.classList.add('cell-glow');
        if (wcolor == 1)
            cell.classList.add('yellow');
        else
            cell.classList.add('red');
        if (wline==="ROW") {
            row+=1;
        } else if (wline==="COL") {
            col+=1;
        } else if (wline=="RDIAG") {
            row+=1;
            col+=1;
        } else {
            row+=1;
            col-=1;
        }
    }
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
    if (gameover)
        window.location.href='/room';
    else
        socketio.emit("quit-game");
}