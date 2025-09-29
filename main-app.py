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
from marshmallow_sqlalchemy import SQLAlchemyAutoSchema
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_wtf import FlaskForm
from sqlalchemy import select,func
from wtforms import StringField, SubmitField, PasswordField
from wtforms.validators import DataRequired, EqualTo, Length, ValidationError

from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta

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
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class user_list(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(500), nullable=False)

class login_form(FlaskForm):
    username = StringField('Username:',validators=[DataRequired()])
    password = PasswordField('Password:',validators=[DataRequired()])
    login_submit = SubmitField('Login')
    def validate_username(self,username):
        u = db.session.execute(select(user_list).filter_by(username=username.data)).scalar_one()
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

# Check chat cooldown for guest users
def cdcheck():
    last_ts = session.get('last_msg_ts')
    if session.get('utype') != 'guest':
        return -1
    if last_ts:
        return 10-(datetime.now() - last_ts).seconds
    else:
        return -1

""" Keeping in case you need to check anything before processing request.
@app.before_request
def pre_processor():
    if request.path.startswith('/static/'):
        return
    if request.path.startswith('api'):
        return "Access denied" # This is a bit pointless as it will block fetch request from js as well
    if not db:
        return render_template('nodb.html')
"""

# ------------------------------
#   Main URL Routes
# ------------------------------

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
    return render_template("chatpage.html",user=uname,usertype=utype,room=room,chats=chatlog,online=online_users,cooldown=cdcheck(),loginform=lgn)

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
    

# ------------------------------
#   Socket handlers
# ------------------------------

@socketio.on('connect')
def handle_connect():
    uname = session.get('uname')
    room = session.get('room')
    if uname is None or room is None or uname in online_users or room not in ROOM_LIST:
        return
    online_users.append(uname)
    emit('user_connect',{ 'user': uname },broadcast=True)
    join_room(room)

@socketio.on('disconnect')
def handle_disconnect():
    uname = session.get('uname')
    if uname in online_users:
        online_users.remove(uname)
        emit('user_disconnect',{ 'user': uname },broadcast=True)

@socketio.on('changeroom')
def handle_changeroom(payload):
    newroom = payload["newroom"]
    utype = session['utype']
    if newroom not in ROOM_LIST:
        return
    if newroom != 'general' and utype == 'guest':
        # Prevent guests from accessing rooms other than 'general'
        return
    join_room(newroom)
    session['room'] = newroom
    if not session.get('chatcount').get(newroom):
        session['chatcount'][newroom] = 50

@socketio.on('message')
def handle_message(payload):
    room = session.get('room')
    uname = session.get('uname')
    utype = session.get('utype')
    ts = datetime.now()
    if room not in ROOM_LIST:
        return
    if utype == 'guest':
        if room != 'general':
            return
        if session.get('last_msg_ts'):
            if cdcheck() > 0:
                return
            else:
                session['last_msg_ts'] = ts
        else:
            session['last_msg_ts'] = ts
    elif session.get('last_msg_ts'):
        del session['last_msg_ts']
    msg = {
        "sender": uname,
        "message": payload["message"],
        "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%S")
    }
    emit('sendmsg', msg, to=room)
    newmsg = chat_msg(sender=uname,message=payload["message"],timestamp=ts,room=room)
    session['chatcount'][room] += 1
    db.session.add(newmsg)
    db.session.commit()

# ------------------------------
#   Run app
# ------------------------------

if __name__ == "__main__":
    with app.app_context():
        try:
            db.create_all()
            guests = []
            online_users = []
            USERNAME_LIST = db.session.scalars(select(user_list.username)).all()
            ROOM_LIST = ['general','weebchat','music','politics']
        except Exception as e:
            print(e)
            exit("Error: DB missing - Either postgres has not started, or DB path is wrong.")
    socketio.run(app, host="0.0.0.0", debug=True)