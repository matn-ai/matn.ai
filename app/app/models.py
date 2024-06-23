from datetime import datetime
import hashlib
from werkzeug.security import generate_password_hash, check_password_hash
from itsdangerous import URLSafeTimedSerializer
from sqlalchemy.dialects.mysql import LONGTEXT
from flask import current_app, url_for
from flask_login import UserMixin, AnonymousUserMixin
from app.exceptions import ValidationError
from . import db, mdb, login_manager, contents_collection
from markdown import markdown
from bson import ObjectId


class Permission:
    WRITE = 4
    MODERATE = 8
    ADMIN = 16


class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    default = db.Column(db.Boolean, default=False, index=True)
    permissions = db.Column(db.Integer)
    users = db.relationship('User', backref='role', lazy='dynamic')

    def __init__(self, **kwargs):
        super(Role, self).__init__(**kwargs)
        if self.permissions is None:
            self.permissions = 0

    @staticmethod
    def insert_roles():
        roles = {
            'User': [Permission.WRITE],
            'Moderator': [Permission.WRITE, Permission.MODERATE],
            'Administrator': [Permission.WRITE, Permission.MODERATE,
                              Permission.ADMIN],
        }
        default_role = 'User'
        for r in roles:
            role = Role.query.filter_by(name=r).first()
            if role is None:
                role = Role(name=r)
            role.reset_permissions()
            for perm in roles[r]:
                role.add_permission(perm)
            role.default = (role.name == default_role)
            db.session.add(role)
        db.session.commit()

    def add_permission(self, perm):
        if not self.has_permission(perm):
            self.permissions += perm

    def remove_permission(self, perm):
        if self.has_permission(perm):
            self.permissions -= perm

    def reset_permissions(self):
        self.permissions = 0

    def has_permission(self, perm):
        return self.permissions & perm == perm

    def __repr__(self):
        return '<Role %r>' % self.name


class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(64), unique=True, index=True)
    username = db.Column(db.String(64), unique=True, index=True)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'))
    password_hash = db.Column(db.String(256))
    confirmed = db.Column(db.Boolean, default=False)
    name = db.Column(db.String(64))
    location = db.Column(db.String(64))
    about_me = db.Column(db.Text())
    member_since = db.Column(db.DateTime(), default=datetime.utcnow)
    last_seen = db.Column(db.DateTime(), default=datetime.utcnow)
    avatar_hash = db.Column(db.String(32))
    contents = db.relationship('Content', backref='author', lazy='dynamic')

    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        if self.role is None:
            if self.email == current_app.config['APP_ADMIN']:
                self.role = Role.query.filter_by(name='Administrator').first()
            if self.role is None:
                self.role = Role.query.filter_by(default=True).first()
        if self.email is not None and self.avatar_hash is None:
            self.avatar_hash = self.gravatar_hash()

    @property
    def password(self):
        raise AttributeError('password is not a readable attribute')

    @password.setter
    def password(self, password):
        self.password_hash = generate_password_hash(password)

    def verify_password(self, password):
        return check_password_hash(self.password_hash, password)

    def generate_confirmation_token(self):
        s = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
        return s.dumps({'confirm': self.id})

    def confirm(self, token):
        s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token.encode('utf-8'), max_age=current_app.config['MAIL_TOKEN_EXPIER_AGE'])
        except:
            return False
        if data.get('confirm') != self.id:
            return False
        self.confirmed = True
        db.session.add(self)
        return True

    def generate_reset_token(self, expiration=3600):
        s = URLSafeTimedSerializer(current_app.config["SECRET_KEY"])
        return s.dumps({'confirm': self.id})
        # s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'], expiration)
        # return s.dumps({'reset': self.id}).decode('utf-8')

    @staticmethod
    def reset_password(token, new_password):
        s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        try:
            # data = s.loads(token.encode('utf-8'))
            data = s.loads(token.encode('utf-8'), max_age=current_app.config['MAIL_TOKEN_EXPIER_AGE'])
        except:
            return False
        user = User.query.get(data.get('confirm'))
        if user is None:
            return False
        user.password = new_password
        db.session.add(user)
        return True

    def generate_email_change_token(self, new_email, expiration=3600):
        s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        return s.dumps(
            {'change_email': self.id, 'new_email': new_email})

    def change_email(self, token):
        s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token.encode('utf-8'), max_age=current_app.config['MAIL_TOKEN_EXPIER_AGE'])
        except:
            return False
        if data.get('change_email') != self.id:
            return False
        new_email = data.get('new_email')
        if new_email is None:
            return False
        if self.query.filter_by(email=new_email).first() is not None:
            return False
        self.email = new_email
        self.avatar_hash = self.gravatar_hash()
        db.session.add(self)
        return True

    def can(self, perm):
        return self.role is not None and self.role.has_permission(perm)

    def is_administrator(self):
        return self.can(Permission.ADMIN)

    def ping(self):
        self.last_seen = datetime.utcnow()
        db.session.add(self)

    def gravatar_hash(self):
        return hashlib.md5(self.email.lower().encode('utf-8')).hexdigest()

    def gravatar(self, size=100, default='identicon', rating='g'):
        url = 'https://secure.gravatar.com/avatar'
        hash = self.avatar_hash or self.gravatar_hash()
        return '{url}/{hash}?s={size}&d={default}&r={rating}'.format(
            url=url, hash=hash, size=size, default=default, rating=rating)

    def to_json(self):
        json_user = {
            'url': url_for('api.get_user', id=self.id),
            'username': self.username,
            'member_since': self.member_since,
            'last_seen': self.last_seen,
            'contents_url': url_for('api.get_user_contents', id=self.id),
            'content_count': self.contents.count()
        }
        return json_user

    def generate_auth_token(self):
        s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        return s.dumps({'id': self.id})

    @staticmethod
    def verify_auth_token(token):
        s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
        try:
            data = s.loads(token.encode('utf-8'), max_age=current_app.config['MAIL_TOKEN_EXPIER_AGE'])
        except:
            return None
        return User.query.get(data['id'])

    def __repr__(self):
        return '<User %r>' % self.username


class AnonymousUser(AnonymousUserMixin):
    def can(self, permissions):
        return False

    def is_administrator(self):
        return False

login_manager.anonymous_user = AnonymousUser



class Content(db.Model):
    __tablename__ = 'contents'
    id = db.Column(db.Integer, primary_key=True)
    # body = db.Column(LONGTEXT)
    mongo_id = db.Column(db.String(24))
    user_input = db.Column(db.Text)
    system_title = db.Column(db.Text)
    outlines = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    flow_id = db.Column(db.Integer, db.ForeignKey('flows.id'))
    job = db.relationship('Job', backref='content', uselist=False)
    content_type = db.Column(db.Integer, nullable=True)
    word_count = db.Column(db.Integer, nullable=True)
    
    def body(self):
        return self.get_body_from_mongo()

    def to_json(self):
        json_content = {
            'url': url_for('api.get_content', id=self.id),
            'body': self.get_body_from_mongo(),
            'outlines': self.outlines,
            'timestamp': self.timestamp,
            'author_url': url_for('api.get_user', id=self.author_id),
            'job_url': url_for('api.get_content_job', id=self.id),
            'flow_url': url_for('api.get_flow', id=self.flow_id)
        }
        return json_content

    def get_body_from_mongo(self):
        if self.mongo_id:
            document = contents_collection.find_one({'_id': ObjectId(self.mongo_id)})
            return document['body'] if document else None
        return None

    @staticmethod
    def from_json(json_content):
        body = json_content.get('body')
        if body is None or body == '':
            raise ValidationError('content does not have a body')
        return Content(body=body)


# db.event.listen(Content.body, 'set', Content.on_changed_body)


class Flow(db.Model):
    __tablename__ = 'flows'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    prompt_type = db.Column(db.String(64))
    prompt_body = db.Column(db.Text)
    prompt_args = db.Column(db.Text)
    contents = db.relationship('Content', backref='flow', lazy='dynamic')

    def create_flow(name, prompt_type, prompt_body, prompt_args):
        flow = Flow(name=name, prompt_type=prompt_type, prompt_body=prompt_body, prompt_args=prompt_args)
        db.session.add(flow)
        db.session.commit()
        return flow

    @staticmethod
    def get_flow(id):
        return Flow.query.get(id)

    @staticmethod
    def update_flow(id, **kwargs):
        flow = Flow.query.get(id)
        for key, value in kwargs.items():
            if hasattr(flow, key):
                setattr(flow, key, value)
        db.session.commit()
        return flow

    @staticmethod
    def delete_flow(id):
        flow = Flow.query.get(id)
        if flow:
            db.session.delete(flow)
            db.session.commit()

    def __repr__(self):
        return '<Flow %r>' % self.name


class Job(db.Model):
    __tablename__ = 'jobs'
    id = db.Column(db.Integer, primary_key=True)
    job_status = db.Column(db.String(64))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    running_duration = db.Column(db.Integer)
    job_id = db.Column(db.String(64))
    content_id = db.Column(db.Integer, db.ForeignKey('contents.id'))

    def create_job(job_status, running_duration, job_id, content_id):
        job = Job(job_status=job_status, running_duration=running_duration, job_id=job_id, content_id=content_id)
        db.session.add(job)
        db.session.commit()
        return job

    @staticmethod
    def get_job(id):
        return Job.query.get(id)

    @staticmethod
    def update_job(id, **kwargs):
        job = Job.query.get(id)
        for key, value in kwargs.items():
            if hasattr(job, key):
                setattr(job, key, value)
        db.session.commit()
        return job

    @staticmethod
    def delete_job(id):
        job = Job.query.get(id)
        if job:
            db.session.delete(job)
            db.session.commit()

    def __repr__(self):
        return '<Job %r>' % self.id
    
    
    