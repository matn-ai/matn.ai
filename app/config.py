import os
from dotenv import load_dotenv

load_dotenv(override=True)

basedir = os.path.abspath(os.path.dirname(__file__))

# Your App secret key
SECRET_KEY = os.environ.get('SECRET_KEY') or "MBqRysyAhUUETgFTc5XOTPrKYKZTJ0oi"

SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
    'mysql+pymysql://{username}:{password}@{hostname}/{databasename}'.format(
        username=os.environ.get('DB_USERNAME', 'root'),
        password=os.environ.get('DB_PASSWORD', '123qwer'),
        hostname=os.environ.get('DB_HOSTNAME', 'localhost'),
        databasename=os.environ.get('DB_NAME', 'app')
    )

APP_POSTS_PER_PAGE = 20
APP_FOLLOWERS_PER_PAGE = 50
APP_COMMENTS_PER_PAGE = 30
APP_SLOW_DB_QUERY_TIME = 0.5
WTF_CSRF_ENABLED = False

MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.googlemail.com')
MAIL_PORT = int(os.environ.get('MAIL_PORT', '587'))
MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
APP_MAIL_SUBJECT_PREFIX = '[هوش مصنوعی به‌نویس]'
APP_MAIL_SENDER = os.environ.get('MAIL_SENDER')
APP_ADMIN = os.environ.get('APP_ADMIN')
MAIL_TOKEN_EXPIER_AGE = 3600
UPLOAD_FOLDER = '/home/saman/Projects/BEHNEVIS/app/app/static/uploads'
ALLOWED_EXTENSIONS = {'pdf'}