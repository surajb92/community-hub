import os
import psycopg
import random

from sys import exit
from string import ascii_letters
from dotenv import load_dotenv, find_dotenv

from flask import Flask, jsonify, render_template, redirect, request, session, url_for
from flask_socketio import SocketIO, join_room, leave_room, send, emit
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField
from wtforms.validators import DataRequired

from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

app = Flask(__name__)
socketio = SocketIO(app)

if load_dotenv():
    # POSTGRESQL Database configuration
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db = SQLAlchemy(app)
else:
    exit("Error: Local environment variables have not been set up properly. Check github manual.")

# NOTE : These variables are loaded from .env file, which will not be on github.
# You can use your own DB for storing data.

class chat_msg(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sender = db.Column(db.String(100), nullable=False)
    message = db.Column(db.String(1000), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

class user_list(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    password = db.Column(db.String(500), nullable=False)

guests = []

class login_form(FlaskForm):
    username = StringField('Username:',validators=[DataRequired()])
    password = PasswordField('Password:',validators=[DataRequired()])
    login_submit = SubmitField('Login')
    #def validate_username(self,username):
        #u = session.query(user_list).filter_by(username=username).first()
        #if not u:
        #    raise ValidationError("User does not exist")
        #elif generate_password_hash(password) != u.password:
        #    raise ValidationError("Wrong password")

""" Keeping in case you need to check anything before processing request.
@app.before_request
def checkdb():
    if request.path.startswith('/static/'):
        return
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
    session['room'] = "room0"
    lgn = login_form()
    if request.method == "POST":
        if 'room-btn' in request.form:
            return redirect(url_for('chatroom'))
        elif lgn.validate_on_submit():
            session['uname'] = lgn.username.data
            session['utype'] = 'registered'
            return redirect(url_for('home'))
    else:
        if not uname:
            while True:
                r = [random.choice(ascii_letters) for _ in range(5)]
                rs = ''.join(r)
                gname = 'guest-'+rs
                print(gname)
                if gname not in guests:
                    uname = gname
                    session['uname'] = uname
                    session['utype'] = 'guest'
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

@app.route('/room')
def chatroom():
    room = session.get('room')
    uname = session.get('uname')
    utype = session.get('utype')
    if not uname:
        return redirect(url_for('home'))
    chatlog = chat_msg.query.all()
    return render_template("chatpage.html",user=uname,usertype=utype,room=room,chats=chatlog)

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
    emit('sendmsg',
        {   "sender": "",
            "message": f"{uname} has entered the chat"
        },
        to=room
    )
    # rooms[room]["members"] += 1

@socketio.on('message')
def handle_message(payload):
    room = session.get('room')
    uname = session.get('uname')
    msg = {
        "sender": uname,
        "message": payload["message"]
    }
    emit('sendmsg', msg, to=room)
    if db:
        newmsg = chat_msg(sender=uname,message=payload["message"],timestamp=datetime.now())
        db.session.add(newmsg)
        db.session.commit()

if __name__ == "__main__":
    with app.app_context():
        try:
            db.create_all()
        except:
            exit("Error: DB missing - Either postgres has not started, or DB path is wrong.")
    socketio.run(app, host="0.0.0.0", debug=True)