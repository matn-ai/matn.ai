from flask import jsonify, request, g, url_for, current_app
from .. import db
from ..models import Content, Permission
from . import api
from .decorators import permission_required
from .errors import forbidden


@api.route('/contents/')
def get_contents():
    page = request.args.get('page', 1, type=int)
    pagination = Content.query.paginate(
        page=page, per_page=current_app.config['APP_POSTS_PER_PAGE'],
        error_out=False)
    contents = pagination.items
    prev = None
    if pagination.has_prev:
        prev = url_for('api.get_contents', page=page-1)
    next = None
    if pagination.has_next:
        next = url_for('api.get_contents', page=page+1)
    return jsonify({
        'contents': [post.to_json() for post in contents],
        'prev': prev,
        'next': next,
        'count': pagination.total
    })


@api.route('/contents/<int:id>')
def get_post(id):
    post = Content.query.get_or_404(id)
    return jsonify(post.to_json())


@api.route('/contents/', methods=['POST'])
@permission_required(Permission.WRITE)
def new_post():
    post = Content.from_json(request.json)
    post.author = g.current_user
    db.session.add(post)
    db.session.commit()
    return jsonify(post.to_json()), 201, \
        {'Location': url_for('api.get_post', id=post.id)}


@api.route('/contents/<int:id>', methods=['PUT'])
@permission_required(Permission.WRITE)
def edit_post(id):
    post = Content.query.get_or_404(id)
    if g.current_user != post.author and \
            not g.current_user.can(Permission.ADMIN):
        return forbidden('Insufficient permissions')
    post.body = request.json.get('body', post.body)
    db.session.add(post)
    db.session.commit()
    return jsonify(post.to_json())
