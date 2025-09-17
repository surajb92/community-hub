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
from wtforms import StringField, SubmitField, PasswordField
from wtforms.validators import DataRequired, ValidationError

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

class chatSchema(ms.SQLAlchemyAutoSchema):
    class Meta:
        model = chat_msg
        load_instance = True

class user_list(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(500), nullable=False)

guests = []

class login_form(FlaskForm):
    username = StringField('Username:',validators=[DataRequired()])
    password = PasswordField('Password:',validators=[DataRequired()])
    login_submit = SubmitField('Login')
    def validate_username(self,username):
        u = db.session.query(user_list).filter_by(username=username.data).first()
        if not u:
            raise ValidationError("Invalid credentials")
        p = u.password
        if not check_password_hash(p, self.password.data):
            raise ValidationError("Invalid credentials")

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
#   Flask Routes
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
                utype = 'guest'
                break
    return render_template('index.html',user=uname,usertype=utype,loginform=lgn)

@app.route('/register', methods=["GET", "POST"])
def register():
    if request.method == "POST":
        user = request.form.get('username')
        pwd = request.form.get('password')
        phash = generate_password_hash(pwd)
        newuser = user_list(username=user,password=phash)
        db.session.add(newuser)
        db.session.commit()
        session['uname'] = user
        session['utype'] = 'registered'
        return redirect(url_for('home'))
    return render_template('register.html')

@app.route('/logout')
def logout():
    del session['uname']
    del session['utype']
    return redirect(url_for('home'))

@app.route('/room', methods=["GET", "POST"])
def chatroom():
    CHAT_LIMIT = 70
    uname = session.get('uname')
    utype = session.get('utype')
    if not uname:
        return redirect(url_for('home'))
    lgn = login_form()
    room = session.get('room')
    history = session.get('history')
    if not history:
        history = 50
        session['history'] = 50
    elif history > CHAT_LIMIT:
        history = CHAT_LIMIT
        session['history'] = CHAT_LIMIT
    #c = chat_msg.query.filter_by(room=room).order_by(chat_msg.id.desc()).all()
    c = chat_msg.query.filter_by(room=room).order_by(chat_msg.id.desc()).limit(history).all()
    chschema = chatSchema(many=True)
    chatlog = chschema.dump(c)
    if request.method == "POST":
        if lgn.validate_on_submit():
            session['uname'] = lgn.username.data
            session['utype'] = 'registered'
            return redirect(url_for('chatroom'))
    return render_template("chatpage.html",user=uname,usertype=utype,room=room,chats=chatlog,cooldown=cdcheck(),loginform=lgn)

@app.route('/api/getchat')
def changeroom():
    c = chat_msg.query.filter_by(room=session['room']).order_by(chat_msg.id.desc()).limit(session['history']).all()
    chschema = chatSchema(many=True)
    chatlog = chschema.dump(c)
    return jsonify(chatlog)

def cdcheck():
    last_ts = session.get('last_msg_ts')
    if session.get('utype') != 'guest':
        return -1
    if last_ts:
        return 10-(datetime.now() - last_ts).seconds
    else:
        return -1

def cd___check():
    last_ts = session.get('last_msg_ts')
    utype = session.get('utype')
    if not last_ts:
        print("last timestamp does not exist")
        return -1
    elif utype != 'guest':
        del session['last_msg_ts']
        return -1
    cdleft = (datetime.now() - last_ts).seconds
    print("Last ts : ", last_ts, "Time now : ", datetime.now())
    print("COOLDOWN CHECK : ",10-cdleft)
    if cdleft < 10:
        return 10-cdleft
    else:
        del session['last_msg_ts']
        return -1

# ------------------------------
#   Socket handlers
# ------------------------------

@socketio.on('connect')
def handle_connect():
    uname = session.get('uname')
    room = session.get('room')
    if uname is None or room is None:
        return
    join_room(room)
    # emit() # push online members from here
    # rooms[room]["members"] += 1

@socketio.on('changeroom')
def handle_changeroom(payload):
    newroom = payload["newroom"]
    utype = session['utype']
    if newroom != 'general' and utype == 'guest': # Disallow guests from accessing rooms other than 'general'
        return
    join_room(newroom)
    session['room'] = newroom

@socketio.on('message')
def handle_message(payload):
    room = session.get('room')
    uname = session.get('uname')
    utype = session.get('utype')
    ts = datetime.now()
    if utype == 'guest':
        if session.get('last_msg_ts'):
            if cdcheck() >= 0:
                return
            else:
                session['last_msg_ts'] = ts
        else:
            session['last_msg_ts'] = ts
    elif session.get('last_msg_ts'):
        del session['last_msg_ts']
    """
        if utype == 'guest':
        if cd_ts: # if -1, no cd or cdover
            print('cd_ts exists')
            if cdcheck(cd_ts) >= 0:
                #print('deleting old cooldown ts')
                #del session['last_msg_ts']
            #else:
                #print('cd is not over, disallow msg sending')
                return
        else:
            print('cooldown does not exist, set new one')
            session['last_msg_ts'] = ts
    """
    msg = {
        "sender": uname,
        "message": payload["message"],
        "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%S")
    }
    emit('sendmsg', msg, to=room)
    newmsg = chat_msg(sender=uname,message=payload["message"],timestamp=ts,room=room)
    session['history'] += 1
    db.session.add(newmsg)
    db.session.commit()

if __name__ == "__main__":
    with app.app_context():
        try:
            db.create_all()
        except:
            exit("Error: DB missing - Either postgres has not started, or DB path is wrong.")
    socketio.run(app, host="0.0.0.0", debug=True)