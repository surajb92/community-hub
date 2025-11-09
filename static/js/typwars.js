var looper;

socketio.on('tw-opp-word', function(data) {
    if (data.user === uname)
        return;
    score_up(2,true);
});

socketio.on('tw-word-get', function(data) {
    if (data.user !== uname)
        return;
    field['words'][data.word] = data.vals;
    spawn_word(data.word,data.vals);
    score_up(10,true);
});

document.addEventListener('DOMContentLoaded', () => {
    document.getElementById('your_lives').innerHTML = field['lives'];
    document.getElementById('your_score').innerHTML = field['score'];
    document.getElementById('opp_lives').innerHTML = field['opplives'];
    document.getElementById('opp_score').innerHTML = field['oppscore'];
    looper = setInterval(game_loop,(11-field['speed'])*100);
    for (word in field['words']) {
        spawn_word(word,field['words'][word]);
    }
    const wfield = document.getElementById('wordfield');
    wfield.addEventListener('keydown', function (event) {
        if (event.key === "Enter") {
            word_typed(this);
        } else {
            word_highlight(this);
        }
    });
});

function spawn_word(word,wordvals) {
    const garea = document.getElementById('gamefield');
    const c = document.createElement('div');
    c.classList = 'word';
    c.id = 'scr-'+word;
    c.innerHTML = word;
    var h = (45-wordvals[0]);
    c.style.top = String(h*10)+'px';
    c.style.left = String(wordvals[1]*100)+'px';
    c.dataset.height = h;
    c.dataset.word = word;
    console.log(wordvals[0],' ',wordvals[1]);
    garea.appendChild(c);
}

function word_highlight(wfield,word) {
    word = wfield.value;
}

function word_typed(wfield) {
    word = wfield.value;
    socketio.emit('tw-word-typed', { 'word':word }, (response) => {
        if (response.status) {
            wfield.value = '';
            if (document.getElementById('scr-'+word)) {
                document.getElementById('scr-'+word).remove();
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
        w.style.top = String((height)*10)+'px';
        var word = w.dataset.word;
        field['words'][word][0]-=1;
        if ((45-height) <= 0) {
            // word reached bottom
            w.remove();
            const lives = document.getElementById('your_lives');
            var mylives = parseInt(lives.innerHTML);
            mylives-=1;
            lives.innerHTML = mylives;
            if (mylives <= 0)
                console.log('gameover');
        }
    }
}