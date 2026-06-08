# Community Hub
Community hub page for chatting, gaming & other group activities.  
Implemented using flask & socketio backend with html+javascript frontend.  
[Site hosted here](https://www.surajb.in).

# Features
- Multiple chat rooms for various topics.
- Chat history stored in postgresql database.
- Guest user feature (longer chat cooldown, access restricted to only 'general' room).
- User registration functionality for full access & much shorter chat cooldown.
- Can edit sent messages for 2 minutes after sending.
- Displays online users in hub.
- Invite other users to play games like connect4 & typ wars.
- Singleplayer typ wars also available.

# Deployment Instructions (Linux)

## Setting up Postgresql locally

> [!NOTE]
> If you have your own DB set up in another location, you can ignore this section.

1. Install postgresql.
2. Initialize DB cluster with command "sudo -u postgres initdb --locale=C.UTF-8 --encoding=UTF8 -D /var/lib/postgres/data".
3. Enter psql interface with "sudo -u postgres psql".
4. Set a new role "db_username" with "db_password" with command : CREATE ROLE db_username WITH LOGIN PASSWORD db_password; (replace with your own username & password).
5. Create database & assign to your user with command : CREATE DATABASE "mydb.db" OWNER db_username; (replace with your own DB name)

## Setting up Python virtual environment
1. Clone the project on to your server : git clone https://github.com/surajb92/community-hub.git, then enter directory with : cd community-hub
2. Install python on your server if it's not already installed.
3. Set up a python virtual environment (python -m venv .venv)
4. Activate the venv with : source .venv/bin/activate.
5. Install the packages stored in "requirements.txt" : pip install -r requirements.txt.
6. Create .env file with contents -
- SECRET_KEY = "\<your_secret_key\>"
  - Required for secure socket & session info communication between client & server.
- 'DATABASE_URL' = "postgresql://\<db_username>:\<db_password>@localhost:5432/\<mydb.db>"
  - This assumes that your database is stored locally in the default location.
  - Change URL to point to wherever your database is stored, if it's not local.
  - SQLAlchemy is being used to abstract database access within flask, so you should be able to use non-PSQL databases as well by adjusting the DB URL as per your needs (untested).

## Set up nginx reverse proxy
1. Install nginx.
2. Create nginx config file for commhub : sudo nano /etc/nginx/sites-available/commhub
3. Add the following to the file (Replace \<user> with your server's local username) -
```
server {
    listen 80;
    server_name <your_domain>;

    # Redirect HTTP traffic to HTTPS
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name <your_domain>;

    # Certbot cert paths
    ssl_certificate /etc/letsencrypt/live/<your_domain>/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/<your_domain>/privkey.pem;

    # Recommended SSL Settings (from Certbot)
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

    location / {
        proxy_pass http://unix:/<path>/community-hub/mysock.sock;
        # proxy_pass <ip_and_port_forwarding_to_gunicorn>;
        # ^ Use this instead, if your nginx server is on a different machine than your python deployment
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location /socket.io {
        proxy_pass http://unix:/<user>/community-hub/mysock.sock;
        # proxy_pass <ip_and_port_forwarding_to_gunicorn>;
        # ^ Use this instead, if your nginx server is on a different machine than your python deployment
        proxy_redirect off;
        proxy_buffering off; # Important for real-time interactions

        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        # proxy_read_timeout 86400; # Keep connection open

        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```
4. Create symlink to sites-enabled folder : sudo ln -s /etc/nginx/sites-available/commhub /etc/nginx/sites-enabled/
5. Test for errors & restart : sudo nginx -t --> sudo systemctl restart nginx
6. Allow nginx over local firewall : sudo ufw allow 'Nginx Full'

### For https access
1. Install certbot & 'python3-certbot-nginx' package.
2. Use certbot to install certificates for nginx, follow instructions after typing command : sudo certbot --nginx

## Setting up gunicorn WSGI 
1. Create file : sudo nano /etc/systemd/system/commhub.service
2. Add the following to the file (Replace \<user> with your server's local username) -
```
[Unit]
Description=Gunicorn instance for community hub
After=network.target

[Service]
User=<user>
Group=www-data
UMask=0007
WorkingDirectory=/<user>/community-hub
Environment="PATH=/<user>/community-hub/.venv/bin"
ExecStart=/<user>/community-hub/.venv/bin/gunicorn --worker-class gthread --threads 100 --workers 1 --bind unix:mysock.sock wsgi:app
# ExecStart=/<user>/community-hub/.venv/bin/gunicorn --worker-class gthread --threads 100 --workers 1  --bind <ip_and_port_listening_to_nginx> wsgi:app
# ^ Use this instead, if your nginx server is on a different machine than your python deployment

[Install]
WantedBy=multi-user.target

```
3. Set up exec permissions for your home directory : chmod +x /\<path> and chmod +x /\<path>\/community-hub\/
4. Run systemctl enable commhub.service and then systemctl start commhub.service.
5. The server should be deployed now. Test it by accessing your domain.
