import os
import psycopg
import random

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

class connect4Game():
    def __init__(self, g_id, host, peer):
        self.gameid = g_id
        self.game = "connect4"
        self.player1 = host
        self.player2 = peer
        self.started = False
    def game_setup(self):
        self.board = [[0]*7 for _ in range(6)]
        self.current_turn = self.player1
    def get_peer(self):
        return self.player2
    def get_game(self):
        return self.game

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
#   Main URL Routes
# ------------------------------

@app.before_request
def pre_processor():
    # VERY IMPORTANT that this statement exists, messes up css and js references otherwise
    if request.path.startswith('/static/'):
        return
    g_id = session.get('game')
    if g_id and not request.path.startswith('/game/'):
        game = games[g_id].get_game()
        return redirect(url_for(game+'_page'))

@app.route('/', methods=["GET", "POST"])
def home():
    uname = session.get('uname')
    utype = session.get('utype')
    lgn = login_form()
    if request.method == "POST":
        if 'room-btn' in request.form:
            return redirect(url_for('chatroom'))
        if lgn.validate_on_submit():
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
                # online_users.append(uname)
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
    game = session.get('game')
    if (not game):
        return redirect(url_for('home'))
    return render_template("connect4.html",user=uname)

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
    game = session.get('game')
    if game:
        join_room(game)
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
    newroom = payload["new_room"]
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
    newmsg = chat_msg(sender=uname,message=payload["message"],timestamp=ts,room=room)
    session['chatcount'][room] += 1
    db.session.add(newmsg)
    db.session.commit()
    msg = {
        "sender": uname,
        "message": payload["message"],
        "timestamp": ts.isoformat(),
        "id": newmsg.id
    }
    emit('sendmsg', msg, to=room)

# Connect4 game sockets
# ------------------------------
@socketio.on('invite-c4')
def handle_c4_inv_init(payload):
    uname = session.get('uname')
    peer = payload["peer"]
    print(uname," has invited ",peer," to play connect4")
    gameid = uuid4()
    while gameid in games.keys():
        gameid = uuid4()
    games[gameid] = connect4Game(gameid,uname,peer)
    session['game'] = gameid
    join_room(gameid)
    emit('invite-c4-incoming', { "peer": uname, "gameid" : str(gameid) }, room=online_users.get(peer))
    return {'status':True, 'gameid':str(gameid) }

@socketio.on('invite-c4-canceled')
def handle_c4_inv_canceled(payload):
    join_room(session.get('room'))
    g_id = session.get('game')
    del session['game']
    if games.get(g_id):
        emit('invite-c4-remove', { "rejected": False }, room=online_users.get(games.get(g_id).get_peer()))
        del games[g_id]

@socketio.on('invite-c4-rejected')
def handle_c4_inv_rejected(payload):
    g_id = UUID(payload["gameid"])
    uname = session.get('uname')
    if games.get(g_id):
        emit('invite-c4-remove', { "rejected": True, "peer": uname }, room=g_id)
        del games[g_id]

@socketio.on('invite-c4-reject-ack')
def handle_c4_inv_reject_ack():
    join_room(session.get('room'))

@socketio.on('invite-c4-accepted')
def handle_c4_inv_accept(payload):
    g_id = UUID(payload["gameid"])
    join_room(g_id)
    session['game'] = g_id
    games[g_id].game_setup()
    emit('c4-start-game', {}, room=g_id)

@socketio.on('quit-game')
def handle_quit_game():
    g_id = session.get('game')
    uname = session.get('uname')
    del games[g_id]
    emit('quit-game-server', { "who_quit": uname }, room=g_id)

@socketio.on('quit-game-ack')
def handle_quit_game_ack():
    del session['game']

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