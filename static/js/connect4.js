var socketio=io();
var board_elements = [];
var gameover = false;
var touchinput = false;
var hovercell = null;

socketio.on("quit-game-server", function(data) {
    socketio.emit("quit-game-ack");
    if (uname !== data.who_quit) {
        dbox = createDialogBox(data.who_quit+" has quit the game, you win!");
        dbox.ok.addEventListener('click', () => {
            window.location.href = '/room';
        })
    } else {
        window.location.href = '/room';
    }
})

socketio.on("c4-gameover", function(data) {
    gameover = true;
    const col = data.column;
    const row = getNextRow(col);
    const cell = board_elements[row][col];
    const wincolor = data.color === 1 ? 'yellow' : 'red';
    cell.classList.add(wincolor);
    board[row][col]=data.color;
    if(data.state == "win") {
        win_glow(data.winline, data.winstart);
        if (wincolor === my_color) {
            document.getElementById('your_turn').innerHTML="<h2>You win!</h2>";
            createDialogBox("You win !");
        } else {
            document.getElementById('opp_turn').innerHTML="<h2>Opponent wins..</h2>";
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
    data.color === 1 ? cell.classList.add('yellow') : cell.classList.add('red');
    toggle_turn();
})

function toggle_turn() {
    my_turn = !my_turn
    document.getElementById('your_turn').classList.toggle("hidden");
    document.getElementById('opp_turn').classList.toggle("hidden");
}

function win_glow(wline,wstart) {
    row = wstart[0];
    col = wstart[1];
    for (i=0;i<4;i++) {
        const cell = board_elements[row][col];
        cell.classList.add('cell-glow');
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
            const cellwall = document.createElement('div');
            cellwall.classList.add('cellwall');
            cellwall.dataset.row = row;
            cellwall.dataset.col = col;
            const cell = document.createElement('div');
            cell.classList.add('cell');
            cell.dataset.row = row;
            cell.dataset.col = col;
            if (board[row][col] == 1) {
                cell.classList.add('yellow');
            } else if (board[row][col] == 2) {
                cell.classList.add('red');
            }
            cellwall.appendChild(cell);
            rowset.push(cell);
            gameboard.appendChild(cellwall);
        }
        board_elements.push(rowset);
    }
    
    // Mouse listeners
    gameboard.addEventListener('click', () => {
        if (my_turn)
            move_make();
    });

    gameboard.addEventListener('mousemove', (e) => {
        if ((e.target.classList.contains('cellwall') || e.target.classList.contains('cell')) && my_turn) {
           move_hover(e.target);
        } else {
            move_unhover();
        }
    });
    gameboard.addEventListener('mouseleave', move_unhover);

    // Adding listeners for touch (mobile, tablets etc.)
    if ('ontouchstart' in window || navigator.maxTouchPoints > 0 || window.navigator.msMaxTouchPoints > 0) {
        gameboard.addEventListener('touchstart', (e) => {
            e.preventDefault();
            const touch = e.touches[0];
            const cell = document.elementFromPoint(touch.clientX,touch.clientY);
            if (my_turn && cell && (cell.classList.contains('cellwall') || cell.classList.contains('cell'))) {
                move_hover(cell);
                touchinput = true;
            }
        });
        gameboard.addEventListener('touchmove', (e) => {
            e.preventDefault();
            const touch = e.touches[0];
            const cell = document.elementFromPoint(touch.clientX,touch.clientY);
            if (cell && (cell.classList.contains('cellwall') || cell.classList.contains('cell'))) {
                touchinput = true;
            } else {
                touchinput = false;
            }
            if (my_turn && touchinput)
                move_hover(cell);
            else
                move_unhover();
        });
        gameboard.addEventListener('touchend', (e) => {
            e.preventDefault();
            if (my_turn && touchinput) {
                move_make();
                touchinput = false;
            }
        });
    }
})

function move_make() {
    if (hovercell) {
        const col = parseInt(hovercell.dataset.col);
        move_unhover();
        socketio.emit("c4-move", { column: col } )
    }
}

function move_hover(cell) {
    const col = parseInt(cell.dataset.col);
    const row = getNextRow(col);
    if (row !== -1) {
        if (hovercell && hovercell.dataset.col !== col)
            move_unhover();
        hovercell = board_elements[row][col];
        hovercell.classList.add(my_color+'-sample');
    } else {
        move_unhover();
    }
}

function move_unhover() {
    if (hovercell) {
        hovercell.classList.remove(my_color+'-sample')
        hovercell = null;
    }
}

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