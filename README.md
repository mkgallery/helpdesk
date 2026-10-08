# IT Helpdesk (Django + MySQL)

Employees report IT problems (region, district, office, GPS location, title, details, attachments).
IT staff pick up and solve tickets. The supervisor oversees everything.

## Roles
- **Employee** - registers at `/register/`, creates and tracks own tickets.
- **IT Staff** - created in `/admin/` (set role = IT Staff), sees all tickets, takes them, updates status, comments.
- **Supervisor** - the superuser created with `createsuperuser`; dashboard, assigns/reassigns tickets.

## Option A: Run with Docker (recommended)
```bash
sudo apt update
sudo apt install -y docker.io docker-compose-v2
sudo usermod -aG docker $USER
newgrp docker

docker compose up --build
```
In a second terminal, in the same folder:
```bash
docker compose exec web python manage.py createsuperuser
```
Open http://127.0.0.1:8000/

Useful commands:
```bash
docker compose up -d          # start in the background
docker compose logs -f web    # watch the app logs
docker compose down           # stop (data is kept)
docker compose down -v        # stop AND delete the database
docker compose exec web python manage.py shell
```
If files created by the container are owned by root: `sudo chown -R $USER:$USER .`

## Option B: Run without Docker (Ubuntu)
```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip python3-dev build-essential pkg-config default-libmysqlclient-dev mysql-server git
sudo systemctl enable --now mysql

sudo mysql < setup_mysql.sql

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

python manage.py makemigrations tickets
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

## Database settings
Defaults are in `config/settings.py` and can be overridden with environment variables:
`DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, `DB_PORT`.
Change the default passwords (settings.py and docker-compose.yml) before using this anywhere public.
