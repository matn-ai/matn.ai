celery -A app.tasks worker --loglevel=info
flask run --debugger --reload

export FLASK_ENV_FILE=.env.local

postgres=# createdb behnevis
postgres-# sudo adduser admin
postgres=# CREATE USER postgres WITH PASSWORD 'admin';
postgres=# CREATE USER admin WITH PASSWORD 'admin';
postgres=# CREATE DATABASE behnevis;
postgres=# GRANT ALL PRIVILEGES ON DATABASE behnevis TO admin;
