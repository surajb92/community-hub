# Community Hub
Community hub page for chatting & other group activities.  
Implemented using flask & socketio backend with html+javascript frontend.  
[Site hosted here](https://www.surajb.in).

## Features
### Main Hub
- Multiple chat rooms for various topics.
- Chat history stored in postgresql database.
- Guest user feature (longer chat cooldown, access restricted to only 'general' room).
- User registration functionality for full access & much shorter chat cooldown.
- Can edit sent messages for 2 minutes after sending.
- Displays online users in hub.
- Invite users to play games (just 1 for now).

## Connect 4
- Multiplayer connect4 game implemented, processing handled serverside.

## For deployment
Set up a python virtual environment and install the packages stored in "requirements.txt" (pip install -r requirements.txt).  
A .env file as well as your own database is required if you want to host this site yourself.  
Contents of .env file -  
- SECRET_KEY = "<your_secret_key>"
  - Required for secure socket & session info communication between client & server.
- 'DATABASE_URL' = "postgresql://\<db_username\>:\<db_password\>@localhost:5432/\<database\>"
  - This assumes that your database is stored locally in the default location.
  - Change 'localhost' and other URL contents depending on where your database is stored.
  - SQLAlchemy is being used to abstract database access within flask, so you should be able to use non-PSQL databases as well by adjusting the DB URL as per your needs.

On your server, use gunicorn to deploy the flask-socketio server and bind it to a .sock file.  
Then use nginx or apache to point port 80 requests to that .sock file.
