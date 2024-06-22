celery -A app.tasks worker

export FLASK_ENV_FILE=.env.local