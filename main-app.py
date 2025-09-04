import os
import psycopg
from dotenv import load_dotenv, find_dotenv
from flask import Flask, jsonify, render_template, redirect, request, session, url_for
from flask_socketio import SocketIO, join_room, leave_room, send, emit
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

if load_dotenv():
    db_exists = True

    # POSTGRESQL Database configuration
    DB_HOST = os.environ.get("DB_HOST")
    DB_NAME = os.environ.get("DB_NAME")
    DB_USER = os.environ.get("DB_USER")
    DB_PASS = os.environ.get("DB_PASS")
else:
    db_exists = False

# NOTE : These files are loaded from .env file, which will not be on github
# You can use your own DB for storing data, or run the app locally without storage functionality

app = Flask(__name__)
#app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY")
app.config["SECRET_KEY"] = "mysecret"
socketio = SocketIO(app)

def getdbcon():
    conn = psycopg.connect(host=DB_HOST, dbname=DB_NAME, user=DB_USER, password=DB_PASS)
    return conn

@app.route('/', methods=["GET", "POST"])
def home():
    session.clear()
    session['room'] = "room0"
    if request.method == "POST":
        uname = request.form.get('uname')
        if not uname:
            return render_template('home.html', error="Name is required")
        session['uname'] = uname
        #session['uname'] = "guest0"
        return redirect(url_for('chatroom'))
    else:
        return render_template("index.html")

@app.route('/room')
def chatroom():
    room = session.get('room')
    uname = session.get('uname')
    if db_exists:
        conn = getdbcon()
        cur = conn.cursor()

        cur.close()
        conn.close()
        return render_template("chatpage.html",user=uname,nodb=False)
    else:
        # Working without DB
        return render_template("chatpage.html",user=uname,nodb=True)

# Socket handlers
@socketio.on('connect')
def handle_connect():
    uname = session.get('uname')
    room = session.get('room')
    if uname is None or room is None:
        return
    join_room(room)
    #send({
    #    "sender": "",
    #    "message": f"{uname} has entered the chat"
    #}, to=room)
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

if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", debug=True)
    #socketio.run(app, debug=True)
    #app.run(debug=True)