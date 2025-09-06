import os
import psycopg
import random
from string import ascii_letters
from dotenv import load_dotenv, find_dotenv
from flask import Flask, jsonify, render_template, redirect, request, session, url_for
from flask_socketio import SocketIO, join_room, leave_room, send, emit
from flask_sqlalchemy import SQLAlchemy
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
    db = None

# NOTE : These variables are loaded from .env file, which will not be on github
# You can use your own DB for storing data.

guests = []

if db:
    class chat_msg(db.Model):
        id = db.Column(db.Integer, primary_key=True)
        sender = db.Column(db.String(100), nullable=False)
        message = db.Column(db.String(1000), nullable=False)
        timestamp = db.Column(db.DateTime, default=datetime.utcnow)

def db_chat_store(sender,message):
    pass

@app.before_request
def checkdb():
    if request.path.startswith('/static/'):
        return
    if not db:
        return render_template('nodb.html')

@app.route('/', methods=["GET", "POST"])
def home():
    uname = session.get('uname')
    if request.method == "POST":
        #uname = request.form.get('uname')
        #if not uname:
        #    return render_template('home.html', error="Name is required")
        #session['uname'] = uname
        session['room'] = "room0"
        return redirect(url_for('chatroom'))
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
                    break
        return render_template('index.html',user=uname)    

@app.route('/room')
def chatroom():
    room = session.get('room')
    uname = session.get('uname')
    chatlog = chat_msg.query.all()
    return render_template("chatpage.html",user=uname,chats=chatlog)

# Socket handlers
@socketio.on('connect')
def handle_connect():
    uname = session.get('uname')
    room = session.get('room')
    if uname is None or room is None:
        return
    join_room(room)
    emit('sendmsg',
        {
            "sender": "",
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
    #db_chat_store(uname,payload["message"])

if __name__ == "__main__":
    if db:
        with app.app_context():
            db.create_all()
    socketio.run(app, host="0.0.0.0", debug=True)
    #socketio.run(app, debug=True)
    #app.run(debug=True)