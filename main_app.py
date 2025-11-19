import os
import random
import threading

from sys import exit
from string import ascii_letters
from dotenv import load_dotenv, find_dotenv

from flask import Flask, flash, jsonify, make_response, render_template, redirect, request, session, url_for
from flask_socketio import SocketIO, join_room, leave_room, send, emit
from flask_session import Session
from flask_sqlalchemy import SQLAlchemy
from flask_marshmallow import Marshmallow
from marshmallow import fields
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf import FlaskForm
from sqlalchemy import select,func
from uuid import UUID, uuid1, uuid4
from wtforms import StringField, SubmitField, PasswordField
from wtforms.validators import DataRequired, EqualTo, Length, ValidationError

from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta, timezone

app = Flask(__name__)
app.config['SESSION_TYPE'] = 'filesystem'
Session(app)
socketio = SocketIO(app, manage_session=False)
limiter = Limiter(key_func=get_remote_address, app=app, default_limits=['120 per minute'])

if load_dotenv():
    # POSTGRESQL Database configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db = SQLAlchemy(app)
    ms = Marshmallow(app)
else:
    exit("Error: Local environment variables have not been set up properly. Check github manual.")

# NOTE : These variables are loaded from .env file, which will not be on github.
# You can use your own DB for storing data.

class chat_msg(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender = db.Column(db.String(100), nullable=False)
    message = db.Column(db.String(1000), nullable=False)
    room = db.Column(db.String(100), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    edited = db.Column(db.Boolean, default=False)

class user_list(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(500), nullable=False)

class login_form(FlaskForm):
    username = StringField('Username:',validators=[DataRequired()])
    password = PasswordField('Password:',validators=[DataRequired()])
    login_submit = SubmitField('Login')
    def validate_username(self,username):
        u = db.session.execute(select(user_list).filter_by(username=username.data)).scalar()
        if not u:
            raise ValidationError("Invalid credentials")
        p = u.password
        if not check_password_hash(p, self.password.data):
            raise ValidationError("Invalid credentials")

class register_form(FlaskForm):
    username = StringField(
        'Username:',
        render_kw={"placeholder": "Enter your username.."},
        validators=[DataRequired(),Length(min=5,max=50, message="Username must be between 5 and 50 characters.")],
        )
    password = PasswordField(
        'Password:',
        render_kw={"placeholder": "Enter your password.."},
        validators=[DataRequired(), Length(min=5,max=50, message="Password must be between 5 and 50 characters.")]
        )
    password2 = PasswordField(
        'Repeat Password:',
        render_kw={"placeholder": "Repeat your password.."},
        validators=[DataRequired(),EqualTo('password', message="Passwords must match")]
        )
    reg_submit = SubmitField('Register')
    def validate_username(self,username):
        u = db.session.scalar(select(user_list).filter_by(username=username.data))
        if u:
            raise ValidationError("User already exists")

# Schema for serializing objects retrieved from database
class chatSchema(ms.SQLAlchemyAutoSchema):
    class Meta:
        model = chat_msg
        load_instance = True
    timestamp = fields.Method("timezone_aware")
    def timezone_aware(self,chatobj):
        return chatobj.timestamp.astimezone()

# Check chat cooldown for guest users
def cdcheck():
    USER_CHAT_COOLDOWN = 5
    GUEST_CHAT_COOLDOWN = 30
    last_ts = session.get('last_msg_ts')
    if last_ts:
        if session.get('utype') == 'guest':
            return GUEST_CHAT_COOLDOWN-(datetime.now(timezone.utc) - last_ts).seconds
        else:
            return USER_CHAT_COOLDOWN-(datetime.now(timezone.utc) - last_ts).seconds
    else:
        return -1

# ------------------------------
#   Game classes
# ------------------------------

class baseGame():
    def __init__(self, g_id, game, host, peer=None):
        self.gameid = g_id
        self.game = game
        self.player1 = host
        self.player2 = peer
    def get_game(self):
        return self.game
    def get_peer(self):
        return self.player2
    def get_id(self):
        return self.gameid

class connect4Game(baseGame):
    def game_start(self):
        self.movecount = 0
        self.MAXROW = 6
        self.MAXCOL = 7
        self.board = [[0]*self.MAXCOL for _ in range(self.MAXROW)]
        self.current_turn = self.player1
    
    def my_turn(self,username):
        return username == self.current_turn
    def my_color(self,username):
        return 1 if self.player1 == username else 2
    def get_board(self):
        return self.board
    def get_win(self):        
        return self.win if hasattr(self,'win') else None
    def valid_col(self,col):
        return True if self.board[0][col] == 0 else False
    def switch_turn(self):
        if self.player1 == self.current_turn:
            self.current_turn = self.player2
        else:
            self.current_turn = self.player1
    
    def calc_win(self,row,col,color):
        # Check if column connects 4
        c4=1
        start=None
        for i in range(self.MAXROW-1):
            if self.board[i][col] == self.board[i+1][col] == color:
                c4+=1
                if not start:
                    start = [i,col]
                if c4 >= 4:
                    return { 'result': True, 'line': "ROW", 'start': start }
            else:
                c4=1
                start=None
        
        # Check if row connects 4
        c4=1
        start=None
        for i in range(self.MAXCOL-1):
            if self.board[row][i] == self.board[row][i+1] == color:
                c4+=1
                if not start:
                    start = [row,i]
                if c4 >= 4:
                    return { 'result': True, 'line': "COL", 'start': start }
            else:
                c4=1
                start=None
        
        # Check if diagonal \ connects 4
        c4=1
        start=None
        if col > row:
            r,c = 0,col-row
        elif row > col:
            r,c = row-col,0
        else:
            r,c = 0,0
        while r < (self.MAXROW-1) and c < (self.MAXCOL-1):
            if self.board[r][c] == self.board[r+1][c+1] == color:
                c4+=1
                if not start:
                    start = [r,c]
                if c4 >= 4:
                    return { 'result': True, 'line': "RDIAG", 'start': start }
            else:
                c4=1
                start=None
            r+=1
            c+=1
        
        #  Check if diagonal / connects 4
        c4=1
        start=None
        max_col = self.MAXCOL-1
        if row+col > max_col:
            r,c = (row+col)-max_col,max_col
        elif row+col < max_col:
            r,c = 0,(row+col)
        else:
            r,c = 0,max_col

        while r < (self.MAXROW-1) and c > 0:
            if self.board[r][c] == self.board[r+1][c-1] == color:
                c4+=1
                if not start:
                    start = [r,c]
                if c4 >= 4:
                    return { 'result': True, 'line': "LDIAG", 'start': start }
            else:
                c4=1
                start=None
            r+=1
            c-=1
        
        # No connect4 yet
        return { 'result': False }
    
    def make_move(self, col):
        for i in range(self.MAXROW):
            if self.board[i][col] != 0:
                i-=1
                break
        self.board[i][col] = 1 if self.my_turn(self.player1) else 2
        self.movecount+=1
        w = self.calc_win(i,col,self.my_color(self.current_turn))
        if w.get('result'):
            state = 'win'
            self.win = w
        elif self.movecount >= self.MAXROW*self.MAXCOL:
            state = 'draw'
        else:
            state = 'continue'
        return state

class typwarsState():
    def __init__(self):
        self.screen_words = {}
        self._tcount = 1
        self.speed = 1
        self.score = 0
        self.lives = 3
        self.dead = False
        self.set_new_row()
        self.i=0
    def get_screen_words(self):
        return self.screen_words
    def get_score(self):
        return self.score
    def get_speed(self):
        return self.speed
    def get_lives(self):
        return self.lives
    def set_new_row(self):
        self.cols = [_ for _ in range(1,6+1)]
        random.shuffle(self.cols)
    def new_word(self,word,opp=False):
        wdata = [45,self.cols.pop(),opp]
        self.screen_words[word.lower()] = wdata
        if not self.cols:
            self.set_new_row()
        return wdata
    def clear_word(self,word):
        self.score+=2
        del self.screen_words[word]
    def clear_word_sp(self,word):
        self.score+=10
        del self.screen_words[word]
    def sent_word(self):
        self.score+=10
    def speed_up(self):
        if self.speed <= 10:
            self.speed+=1
    def isdead(self):
        return self.dead
    def tick(self):
        self._tcount+=1
        if self._tcount > 10:
            self._tcount = 1
        if (self._tcount % (11-self.speed) == 0):
            self.tick_words()
    def tick_words(self):
        delwords = []
        for word in self.screen_words:
            self.screen_words[word][0]-=1
            if self.screen_words[word][0] <= 0:
                # word reached bottom !
                delwords.append(word)
        if delwords:
            self.life_lost = len(delwords)
        for w in delwords:
            self.lives-=1
            del self.screen_words[w]
        if self.lives <= 0:
            self.lives = 0
            self.dead = True
    def get_state(self):
        return { 'words': self.screen_words, 'speed': self.speed, 'score': self.score, 'lives': self.lives }

class wordTicker():
    def __init__(self,maxtick=300):
        self.wordlist = {}
        self.maxtick = maxtick
    def add(self,word):
        self.wordlist[word]=self.maxtick
    def check(self,word):
        return True if word in self.wordlist else False
    def tick(self):
        delwords = []
        for word in self.wordlist:
            self.wordlist[word]-=1
            if self.wordlist[word] <= 0:
                delwords.append(word)
        for w in delwords:
            del self.wordlist[w]

class typwarsGameSP(baseGame):
    def game_start(self):
        self.dictwords = []
        self.maxwordlen = 5
        self.difficulty = 0
        self.milestones = [100,200,300,500,750,1000,1500,2000,2500,3000]
        self.twstate = typwarsState()
        self.usedwords = wordTicker()
        self.stopgame = threading.Event()
        with open("static/data/words.txt","r") as f:
            for i in f:
                self.dictwords.append(i[:-1].lower())
        while len(self.twstate.get_screen_words()) < 4:
            self.spawn_word()
        self.loopthread = socketio.start_background_task(target=self.run_loop) # Required to send emits from loopthread
    def get_state(self):
        return self.twstate.get_state()
    def spawn_word(self):
        word = random.choice(self.dictwords)
        while self.usedwords.check(word) or len(word) > self.maxwordlen:
            word = random.choice(self.dictwords)
        self.usedwords.add(word)
        vals = self.twstate.new_word(word)
        return [word,vals]
    def adjust_diff(self):
        score = self.twstate.get_score()
        if score >= 100 and score%100 == 0:
            self.maxwordlen = 5 + score/100
        if self.difficulty < 10 and score >= self.milestones[self.difficulty]:
            self.difficulty+=1
            self.twstate.speed_up()
            socketio.emit('tw-speed-change', { 'speed':self.twstate.get_speed() }, room=self.get_id()) 
    def run_loop(self):
        # Serverside game loop
        while not self.stopgame.is_set():
            self.twstate.tick()
            self.usedwords.tick()
            if (hasattr(self.twstate,'life_lost')):
                self.life_lost(self.twstate.life_lost)
                del self.twstate.life_lost
            if (self.twstate.isdead()):
                self.endstate = { 'state':'gameover', 'score': self.twstate.get_score() }
                break
            elif len(self.twstate.get_screen_words()) < 4:
                w = self.spawn_word()
                self.send_word(w[0],w[1])
            self.adjust_diff()
            socketio.sleep(0.1)
        # Game loop ends = game over
        if self.endstate.get('state') != 'quit':
            socketio.emit('tw-gameover', self.endstate, room=self.get_id())
    def word_typed(self,user,word):
        words = self.twstate.get_screen_words()
        if word in words:
            self.twstate.clear_word_sp(word)
            return True
        else:
            return False
    def send_word(self,word,vals):
        socketio.emit('tw-word-get', { 'word':word, 'vals':vals }, room=self.get_id())
    def life_lost(self,lives):
        socketio.emit('tw-life-lost', { 'lives':lives }, room=self.get_id())
    def quit_game(self):
        self.endstate = {'state':'quit'}
        self.stopgame.set()
        self.loopthread.join()

class typwarsGame(baseGame):
    def game_start(self):
        self.dictwords = []
        self.p1 = typwarsState()
        self.p2 = typwarsState()
        self.stopgame = threading.Event()
        with open("static/data/words.txt","r") as f:
            for i in f:
                self.dictwords.append(i[:-1].lower())
        self.loopthread = socketio.start_background_task(target=self.run_loop) # Required to send emits from loopthread
    def get_state(self,user):
        if self.player1 == user:
            state = self.p1.get_state()
            state['oppscore'] = self.p2.get_score()
            state['opplives'] = self.p2.get_lives()
        else:
            state = self.p2.get_state()
            state['oppscore'] = self.p1.get_score()
            state['opplives'] = self.p1.get_lives()
        return state
    def run_loop(self):
        # Serverside game loop
        while not self.stopgame.is_set():
            self.p1.tick()
            self.p2.tick()
            if (hasattr(self.p1,'life_lost')):
                self.life_lost(self.player1, self.p1.life_lost)
                del self.p1.life_lost
            elif (hasattr(self.p2,'life_lost')):
                self.life_lost(self.player2, self.p2.life_lost)
                del self.p2.life_lost
            if (self.p1.isdead() and self.p2.isdead()):
                # tied!
                self.endstate = {'state':'tie'}
                break
            elif self.p1.isdead():
                self.endstate = {'state':'win', 'winner':self.player2}
                break
            elif self.p2.isdead():
                self.endstate = {'state':'win', 'winner':self.player1}
                break
            socketio.sleep(0.1)
        # Game loop ends = game over
        if self.endstate.get('state') != 'quit':
            socketio.emit('tw-gameover', self.endstate, room=self.get_id())
    def word_typed(self,user,word):
        if self.player1 == user:
            words = self.p1.get_screen_words()
            if word in words:
                self.p1.clear_word(word)
                socketio.emit('tw-opp-word', {'user':self.player1}, room=self.get_id())
                return True
            elif word in self.dictwords:
                self.p1.sent_word()
                vals = self.p2.new_word(word,True)
                self.send_word(self.player2,word,vals) # send dict word clientside to p2
                return True
            else:
                return False
        else:
            words = self.p2.get_screen_words()
            if word in words:
                self.p2.clear_word(word)
                socketio.emit('tw-opp-word', {'user':self.player2}, room=self.get_id())
                return True
            elif word in self.dictwords:
                self.p2.sent_word()
                vals = self.p1.new_word(word,True)
                self.send_word(self.player1,word,vals) # send dict word clientside to p1
                return True
            else:
                return False
    def send_word(self,user,word,vals):
        socketio.emit('tw-word-get', { 'user':user, 'word':word, 'vals':vals }, room=self.get_id())
    def life_lost(self,user,lives):
        socketio.emit('tw-life-lost', { 'user':user, 'lives':lives }, room=self.get_id())
    def quit_game(self):
        self.endstate = {'state':'quit'}
        self.stopgame.set()
        self.loopthread.join()

# ------------------------------
#   Main URL Routes
# ------------------------------

@app.before_request
def pre_processor():
    # VERY IMPORTANT that this statement exists, messes up css and js references otherwise
    if request.path.startswith('/static/'):
        return
    if request.path.startswith('/gameapi/'): # In case it's needed in the future
        return
    g_id = session.get('game')
    game = games.get(g_id)
    if g_id and game and not request.path.startswith('/game/'):
        return redirect(url_for(game.get_game()+'_page'))

@app.route('/', methods=["GET", "POST"])
def home():
    uname = session.get('uname')
    utype = session.get('utype')
    lgn = login_form()
    if request.method == "POST" and lgn.validate_on_submit():
        session['uname'] = lgn.username.data
        session['utype'] = 'registered'
        return redirect(url_for('home'))
    if not uname:
        while True:
            r = [random.choice(ascii_letters) for _ in range(5)]
            rs = ''.join(r)
            gname = 'guest-'+rs
            if gname not in guests:
                uname = gname
                session['uname'] = uname
                session['utype'] = 'guest'
                session['room'] = 'general'
                guests.append(uname)
                utype = 'guest'
                break
    return render_template('index.html',user=uname,usertype=utype,loginform=lgn)

@app.route('/register', methods=["GET", "POST"])
def register():
    reg = register_form()
    if request.method == "POST":
        if reg.validate_on_submit():
            user = request.form.get('username')
            pwd = request.form.get('password')
            phash = generate_password_hash(pwd)
            newuser = user_list(username=user,password=phash)
            db.session.add(newuser)
            db.session.commit()
            USERNAME_LIST.append(user)
            session['uname'] = user
            session['utype'] = 'registered'
            return redirect(url_for('home'))
    return render_template('register.html', regform=reg)

@app.route('/logout')
def logout():
    del session['uname']
    del session['utype']
    return redirect(url_for('home'))

@app.route('/room', methods=["GET", "POST"])
def chatroom():
    uname = session.get('uname')
    utype = session.get('utype')
    if not uname:
        return redirect(url_for('home'))
    lgn = login_form()
    room = session.get('room')
    chatcount = session.get('chatcount')
    if not chatcount:
        session['chatcount'] = { room: 50 }
        chatcount = session.get('chatcount')    
    c = db.session.scalars(select(chat_msg).filter_by(room=room).order_by(chat_msg.id.desc()).limit(chatcount.get(room)))
    chschema = chatSchema(many=True)
    chatlog = chschema.dump(c)
    if request.method == "POST":
        if lgn.validate_on_submit():
            session['uname'] = lgn.username.data
            session['utype'] = 'registered'
            return redirect(url_for('chatroom'))
    return render_template("chatpage.html",user=uname,usertype=utype,room=room,chats=chatlog,online=list(online_users.keys()),cooldown=cdcheck(),loginform=lgn)

@app.route('/game/connect4', methods=["GET", "POST"])
def connect4_page():
    uname = session.get('uname')
    g_id = session.get('game')
    game = games.get(g_id)
    if not g_id:
        return redirect(url_for('home'))
    elif not game:
        del session['game']
        return redirect(url_for('home'))
    return render_template("connect4.html",user=uname,board=game.get_board(), myturn=game.my_turn(uname),mycolor=game.my_color(uname))

@app.route('/game/typwars', methods=["GET", "POST"])
def typwars_page():
    uname = session.get('uname')
    g_id = session.get('game')
    game = games.get(g_id)
    if not g_id:
        return redirect(url_for('home'))
    elif not game:
        del session['game']
        return redirect(url_for('home'))
    return render_template("typwars.html",user=uname,twoplayer=True,field=game.get_state(uname))

@app.route('/game/typwars_sp', methods=["GET", "POST"])
def typwars_sp_page():
    uname = session.get('uname')
    g_id = session.get('game')
    game = games.get(g_id)
    if not g_id:
        gameid = uuid4()
        while gameid in games.keys():
            gameid = uuid4()
        games[gameid] = typwarsGameSP(gameid,"typwars_sp",uname)
        session['game'] = gameid
        game = games.get(gameid)
        game.game_start()
    elif not game:
        del session['game']
        return redirect(url_for('home'))
    return render_template("typwars.html",user=uname,twoplayer=False,field=game.get_state())

# ------------------------------
#   API-only Routes
# ------------------------------

@app.route('/api/getchat')
def getchat_roomchange():
    room = session.get('room')
    if room not in ROOM_LIST:
        return
    c = db.session.scalars(select(chat_msg).filter_by(room=room).order_by(chat_msg.id.desc()).limit(session.get('chatcount').get(room)))
    chschema = chatSchema(many=True)
    chatlog = chschema.dump(c)
    return jsonify(chatlog)

@app.route('/api/morechats')
def getchat_scroll():
    room = session.get('room')
    chatcount = session.get('chatcount').get(room)
    maxchats = db.session.execute(select(func.count(chat_msg.id)).filter(chat_msg.room==room)).scalar_one()
    if chatcount >= maxchats:
        return jsonify([])
    sendchats = 25 if maxchats-chatcount>=25 else maxchats-chatcount
    # c = chat_msg.query.filter_by(room=room).order_by(chat_msg.id.desc()).offset(chatcount).limit(sendchats).all()
    c = db.session.scalars(select(chat_msg).filter_by(room=room).order_by(chat_msg.id.desc()).offset(chatcount).limit(sendchats))
    chschema = chatSchema(many=True)
    chatlog = chschema.dump(c)
    session['chatcount'][room] += sendchats
    return jsonify(chatlog)

@app.route('/api/unamecheck', methods=['POST'])
def check_username_exists():
    if request.is_json:
        uname = request.get_json().get('username')
        u_exists = False
        if uname in USERNAME_LIST:
            u_exists = True
        return jsonify({"user_exists": u_exists}), 200
    else:
        return jsonify({"error": "Request must be JSON"}), 400

@app.route('/api/editmessage', methods=['POST'])
def edit_message():
    if request.is_json:
        chatid = request.get_json().get('id')
        msg = request.get_json().get('newmessage')
    chat = db.session.scalars(select(chat_msg).filter_by(id=chatid)).first()
    if ((datetime.now() - chat.timestamp).seconds > 300):
        return jsonify({msg: "Edit cooldown exceeded"}), 400
    else:
        chat.message = msg
        chat.edited = True
        db.session.commit()
        return jsonify({msg: "Success!"}), 200

# ------------------------------
#   Socket handlers
# ------------------------------

@socketio.on('connect')
def handle_connect():
    g_id = session.get('game')
    game = games.get(g_id)
    if g_id and game:
        join_room(g_id)
        return
    
    uname = session.get('uname')
    room = session.get('room')
    if uname is None or room is None or uname in online_users.keys() or room not in ROOM_LIST:
        return
    
    online_users[uname] = request.sid
    join_room(room)
    emit('user_connect',{ 'user': uname },broadcast=True)

@socketio.on('disconnect')
def handle_disconnect():
    uname = session.get('uname')
    if uname in online_users.keys():
        del online_users[uname]
        emit('user_disconnect',{ 'user': uname },broadcast=True)

@socketio.on('changeroom')
def handle_changeroom(payload):
    newroom = payload.get("new_room")
    utype = session.get('utype')
    if newroom not in ROOM_LIST:
        return {'status':False}
    if newroom != 'general' and utype == 'guest':
        # Prevent guests from accessing rooms other than 'general'
        return {'status':False}
    join_room(newroom)
    session['room'] = newroom
    if not session.get('chatcount').get(newroom):
        session['chatcount'][newroom] = 50
    return {'status':True}

@socketio.on('message')
def handle_message(payload):
    room = session.get('room')
    uname = session.get('uname')
    utype = session.get('utype')
    ts = datetime.now(timezone.utc)
    if room not in ROOM_LIST:
        return
    if utype == 'guest' and room != 'general':
        return
    if session.get('last_msg_ts'):
        if cdcheck() > 0:
            return
        else:
            del session['last_msg_ts']
    else:
        session['last_msg_ts'] = ts
    newmsg = chat_msg(sender=uname,message=payload.get("message"),timestamp=ts,room=room)
    session['chatcount'][room] += 1
    db.session.add(newmsg)
    db.session.commit()
    msg = {
        "sender": uname,
        "message": payload.get("message"),
        "timestamp": ts.isoformat(),
        "id": newmsg.id
    }
    emit('sendmsg', msg, to=room)

# Game socket events
# ------------------------------
@socketio.on('game-invite')
def handle_inv_init(payload):
    uname = session.get('uname')
    peer = payload.get("peer")
    game = payload.get("game")
    gameid = uuid4()
    while gameid in games.keys():
        gameid = uuid4()
    if game == 'connect4':
        games[gameid] = connect4Game(gameid,game,uname,peer)
    elif game == 'typwars':
        games[gameid] = typwarsGame(gameid,game,uname,peer)
    session['game'] = gameid
    join_room(gameid)
    emit('invite-incoming', { "peer": uname, "game": game, "gameid" : str(gameid) }, room=online_users.get(peer))
    return {'status':True, 'gameid':str(gameid) }

@socketio.on('invite-canceled')
def handle_inv_canceled(payload):
    join_room(session.get('room'))
    g_id = session.get('game')
    del session['game']
    if games.get(g_id):
        emit('invite-remove', { "rejected": False }, room=online_users.get(games.get(g_id).get_peer()))
        del games[g_id]

@socketio.on('invite-rejected')
def handle_inv_rejected(payload):
    g_id = UUID(payload.get("gameid"))
    uname = session.get('uname')
    if games.get(g_id):
        emit('invite-remove', { "rejected": True, "peer": uname }, room=g_id)
        del games[g_id]

@socketio.on('invite-reject-ack')
def handle_inv_reject_ack():
    del session['game']
    join_room(session.get('room'))

@socketio.on('invite-accepted')
def handle_inv_accept(payload):
    g_id = UUID(payload.get("gameid"))
    join_room(g_id)
    session['game'] = g_id
    game = games.get(g_id)
    game.game_start()
    emit('start-game', { "game": game.get_game() }, room=g_id )

@socketio.on('quit-game')
def handle_quit_game():
    g_id = session.get('game')
    uname = session.get('uname')
    game = games.get(g_id)
    if game.get_game() == 'typwars': # Stop the gameloop before deleting
        game.quit_game()
    del games[g_id]
    emit('quit-game-server', { "who_quit": uname }, room=g_id)

@socketio.on('quit-game-ack')
def handle_quit_game_ack():
    join_room(session.get('room'))
    del session['game']

# Connect4 game socket events
# ------------------------------
@socketio.on('c4-move')
def handle_c4_move(payload):
    uname = session.get('uname')
    g_id = session.get('game')
    game = games.get(g_id)
    col = payload.get("column")
    if game.get_game() == "connect4" and game.my_turn(uname) and game.valid_col(col):
        state = game.make_move(col)
        if state == 'win':
            win = game.get_win()
            color = game.my_color(uname)
            del games[g_id]
            emit('c4-gameover', { "state": state, "column": col, "color": color, "winline": win.get('line'), "winstart": win.get('start') }, room=g_id )
        elif state == 'draw':
            del games[g_id]
            emit('c4-gameover', { "state": state, "column": col, "color": color }, room=g_id )
        else:
            color = game.my_color(uname)
            game.switch_turn()
            emit('move-made', { "column": col, "color": color }, room=g_id)

# Typwars game socket events
# ------------------------------
@socketio.on('tw-word-typed')
def handle_tw_typed(payload):
    uname = session.get('uname')
    game = games.get(session.get('game'))
    valid_word = game.word_typed(uname,payload.get('word').lower())
    if valid_word:
        return {'status':True}
    else:
        return {'status':False}

online_users = {}
guests = []
games = {}
USERNAME_LIST = []
ROOM_LIST = ['general','weebchat','music','politics']

with app.app_context():
    try:
        db.create_all()
        USERNAME_LIST += db.session.scalars(select(user_list.username)).all()
    except Exception as e:
        print(e)
        exit("Error: DB missing - Either postgres has not started, or DB path is wrong.")

# ------------------------------
#   Run app
# ------------------------------

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", debug=True)