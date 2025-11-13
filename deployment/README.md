# MyFin Deployment (nginx + systemd + gunicorn)

This folder contains deployment templates and commands to run MyFin on a Linux server behind nginx and gunicorn, using a unix socket and systemd.

Assumptions
- User: `jaoga`
- Repo path: `/home/jaoga/repositories/myfin`
- Subdomain: `myfin.example.com`
- Python venv: `/home/jaoga/repositories/myfin/venv`
- Socket: `/run/myfin/flask_app.sock` (created via systemd RuntimeDirectory)

Adjust names as needed.

## 0) Prepare server
```
sudo apt update && sudo apt install -y python3-venv python3-pip nginx
```

## 1) Fetch code
```
mkdir -p /home/jaoga/repositories
cd /home/jaoga/repositories
git clone <your_git_remote> myfin
cd myfin
```

## 2) Create venv and install deps
```
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

## 3) Configure environment
Copy the example env and edit.
```
cp deployment/.env.example .env
nano .env
```
Set at least `SECRET_KEY` to a strong random value. Leave SQLite as default or set a `DATABASE_URL` and adjust `config.py` if you switch databases.

## 4) Initialize the database and views
Run the one-time initialization commands.
```
source venv/bin/activate
flask --app app init-db
flask --app app create-admin
python init_views.py
python migrate_patterns.py
```

## 5) Install systemd service
Edit the service file paths and domain if needed, then install and start it.
```
sudo cp deployment/myfin.service /etc/systemd/system/myfin.service
sudo systemctl daemon-reload
sudo systemctl enable myfin
sudo systemctl start myfin
sudo systemctl status myfin --no-pager -l
```
If it fails, check logs:
```
sudo journalctl -u myfin -e
```

## 6) Configure nginx for subdomain
Edit the nginx server block with your real domain, then enable and reload.
```
sudo cp deployment/nginx-myfin.conf /etc/nginx/sites-available/myfin
sudo sed -i 's/myfin.example.com/myfin.yourdomain.tld/g' /etc/nginx/sites-available/myfin
sudo ln -s /etc/nginx/sites-available/myfin /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

Optional: serve TLS via certbot
```
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d myfin.yourdomain.tld
```

## 7) Directory permissions
Ensure the service user (`jaoga`) can write the working dir and that nginx (group `www-data`) can access the socket created under `/run/myfin`.
```
sudo usermod -aG www-data jaoga
# log out/in or restart the service to apply group membership
```
`gunicorn.conf.py` sets `umask = 007` so the socket is group-readable.

## 8) Service management
```
sudo systemctl restart myfin
sudo systemctl status myfin --no-pager -l
sudo journalctl -u myfin -f
```

## 9) Updating the app
```
cd /home/jaoga/repositories/myfin
git pull
source venv/bin/activate
pip install -r requirements.txt
python migrate_patterns.py  # if schema changed
python init_views.py        # if views changed
sudo systemctl restart myfin
```

## Gunicorn target
Gunicorn starts `app:app` where `app.py` contains `app = Flask(__name__)`.

## Files in this folder
- `.env.example` – env vars template (copy to `.env` on server)
- `gunicorn.conf.py` – gunicorn configuration (binds a unix socket under `/run/myfin`)
- `myfin.service` – systemd unit (adjust paths before installing)
- `nginx-myfin.conf` – nginx server block for subdomain proxying to the socket
