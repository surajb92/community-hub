var looper;

document.addEventListener('DOMContentLoaded', () => {
    looper = setInterval(game_loop,(11-field['speed'])*100);
    const garea = document.getElementById('gamefield');
    console.log(field);
    words = field['words'];
    for (word in words) {
        const c = document.createElement('div');
        c.classList = 'word';
        c.innerHTML = word;
        var h = (45-words[word][0])
        c.style.top = String(h*10)+'px';
        c.style.left = String(words[word][1]*100)+'px';
        c.dataset.height = h;
        console.log(words[word][0],' ',words[word][1]);
        garea.appendChild(c);
    }
});

function game_loop() {
    const gkids = Array.from(document.getElementById('gamefield').children);
    console.log("ticking ");
    if (!gkids) // temp loop exit when all words disappear from screen
        return
    for (w of gkids) {
        var height = parseInt(w.dataset.height);
        height+=1;
        w.style.top = String((height)*10)+'px';
        w.dataset.height = height;
    }
}