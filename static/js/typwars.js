var division=6;
var tick=10;

socketio.on('tw-opp-word', function(data) {
    if (data.user === uname)
        return;
    score_up(2,true);
});

socketio.on('tw-life-lost', function(data) {
    if (data.user === uname){
        const lives = document.getElementById('your_lives');
        var mylives = parseInt(lives.innerHTML);
        mylives-=data.lives;
        lives.innerHTML = mylives;
    } else {
        const lives = document.getElementById('opp_lives');
        var opplives = parseInt(lives.innerHTML);
        opplives-=data.lives;
        lives.innerHTML = opplives;
    }
});

socketio.on('tw-word-get', function(data) {
    if (data.user !== uname)
        return;
    field['words'][data.word] = data.vals;
    spawn_word(data.word,data.vals);
    score_up(10,true);
});

socketio.on('tw-speed-change', function(data) {
    field['speed'] = data.speed;
});

socketio.on('tw-gameover', function(data) {
    gameover=true;
    if (data.state === "tie")
        createDialogBox("Game tied, wow!");
    else if (data.winner === uname)
        createDialogBox("You win!");
    else
        createDialogBox("You lose!");
    socketio.emit("quit-game-ack");
    document.getElementById('goback').classList.remove('hidden');
});

function set_params() {
    const width = window.screen.width;
    tick = document.getElementById('gamefield').offsetHeight/45;
    if (width/8 >= 150)
        division = 6;
    else if (width/8 >= 130)
        division = 5;
    else if (width/8 >= 100)
        division = 4;
    else
        division = 3;
}

function calc_gap(col) {
    var dis=col; 
    if (col > division)
        dis = col-division;
    switch (division) {
        case 6:
            return (dis*150);
        case 5:
            return (dis*130);
        case 4:
            return (dis*100);
        case 3:
            return (dis*75);
    }
}

document.addEventListener('DOMContentLoaded', () => {
    set_params(); // Set movement & spawn parameters according to screen size
    document.getElementById('your_lives').innerHTML = field['lives'];
    document.getElementById('your_score').innerHTML = field['score'];
    document.getElementById('opp_lives').innerHTML = field['opplives'];
    document.getElementById('opp_score').innerHTML = field['oppscore'];
    for (word in field['words']) {
        spawn_word(word,field['words'][word]);
    }
    const wordfield = document.getElementById('wordfield');
    wordfield.focus();
    wordfield.addEventListener('keyup', function (event) {
        if (event.key === "Enter") {
            word_typed(this);
        } else {
            word_highlight(this);
        }
    });
    game_loop();
});

function spawn_word(word,wordvals) {
    const garea = document.getElementById('gamefield');
    const c = document.createElement('div');
    c.classList = 'word';
    c.id = 'scr-'+word.toLowerCase();
    c.innerHTML = word.toLowerCase();
    var h = (45-wordvals[0]);
    c.style.top = `${h*tick}+px`;
    c.style.left = `${calc_gap(wordvals[1])}px`;
    c.dataset.height = h;
    c.dataset.word = word.toLowerCase();
    garea.appendChild(c);
}

function word_highlight(wfield) {
    const word = wfield.value.toLowerCase();
    const gkids = Array.from(document.getElementById('gamefield').children);
    for (w of gkids) {
        const subs = w.dataset.word.slice(0,word.length);
        const rest = w.dataset.word.slice(word.length);
        if (subs === word) {
            w.innerHTML = `<span class="highlight">${subs}</span>${rest}`;
        } else {
            w.innerHTML = w.dataset.word;
        }
    }
}

function word_typed(wfield) {
    word = wfield.value;
    socketio.emit('tw-word-typed', { 'word':word }, (response) => {
        if (response.status) {
            wfield.value = '';
            if (document.getElementById('scr-'+word.toLowerCase())) {
                document.getElementById('scr-'+word.toLowerCase()).remove();
                score_up(2);
            } else {
                score_up(10);
            }
        }
    });
}

function score_up(score,opp=false) {
    const ys = document.getElementById('your_score');
    const os = document.getElementById('opp_score');
    if (opp)
        os.innerHTML = parseInt(os.innerHTML)+score;
    else
        ys.innerHTML = parseInt(ys.innerHTML)+score;
}

function game_loop() {
    const gkids = Array.from(document.getElementById('gamefield').children);
    for (w of gkids) {
        var height = parseInt(w.dataset.height);
        height+=1;
        w.dataset.height = height;
        w.style.top = `${height*tick}px`;
        var word = w.dataset.word;
        field['words'][word][0]-=1;
        if ((45-height) <= 0) { // word reached bottom
            w.remove();
        }
    }
    if (!gameover) {
        setTimeout(game_loop, (10-field['speed'])*100);
    }
}