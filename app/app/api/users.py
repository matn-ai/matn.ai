from flask import jsonify, request, current_app, url_for
from werkzeug.security import generate_password_hash
from datetime import datetime
import hashlib
from . import api
from ..models import User, Content, db, Role
from .decorators import token_required
from flask_login import login_required
from app.finance.models import Charge


@api.route('/users/<int:id>')
@login_required
def get_user(id):
    user = User.query.get_or_404(id)
    return jsonify(user.to_json())


@api.route('/users/register', methods=['POST'])
@token_required
def register_external_user():
    data = request.get_json()

    # Check if all required fields are present
    required_fields = ['email', 'username', 'password', 'name']
    for field in required_fields:
        if field not in data:
            return jsonify({'message': f'Missing required field: {field}'}), 400

    # Check if email or username already exists
    user = User.query.filter_by(email=data['email']).first()
    if user:
        return jsonify({'message': 'Email already registered', 'user': {
            'id': user.id,
            'email': user.email,
            'username': user.username,
            'name': user.name
        }}), 400
    user = User.query.filter_by(username=data['username']).first()
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'message': 'Username already taken','user': {
            'id': user.id,
            'email': user.email,
            'username': user.username,
            'name': user.name
        }}), 400

    # Create new user
    new_user = User(
        email=data['email'],
        username=data['username'],
        password_hash=generate_password_hash(data['password']),
        name=data['name'],
        member_since=datetime.utcnow(),
        last_seen=datetime.utcnow(),
        avatar_hash=hashlib.md5(data['email'].lower().encode('utf-8')).hexdigest()
    )
    if data.get('init_charge'):
        Charge.add_user_charge(user_id=new_user.id, toman_amount=data.get('init_charge'))

    # Set role (you might want to set a default role for external users)
    default_role = Role.query.filter_by(name='User').first()
    if default_role:
        new_user.role_id = default_role.id

    # Add user to database
    try:
        db.session.add(new_user)
        db.session.commit()
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': 'An error occurred while registering the user', 'error': str(e)}), 500

    return jsonify({
        'message': 'User registered successfully',
        'user': {
            'id': new_user.id,
            'email': new_user.email,
            'username': new_user.username,
            'name': new_user.name
        }
    }), 201


@api.route('/users/<int:id>/contents/')
@login_required
def get_user_contents(id):
    user = User.query.get_or_404(id)
    page = request.args.get('page', 1, type=int)
    pagination = user.contents.order_by(Content.timestamp.desc()).paginate(
        page=page, per_page=current_app.config['APP_POSTS_PER_PAGE'],
        error_out=False)
    contents = pagination.items
    prev = None
    if pagination.has_prev:
        prev = url_for('api.get_user_contents', id=id, page=page-1)
    next = None
    if pagination.has_next:
        next = url_for('api.get_user_contents', id=id, page=page+1)
    return jsonify({
        'contents': [post.to_json() for post in contents],
        'prev': prev,
        'next': next,
        'count': pagination.total
    })
