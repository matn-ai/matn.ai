from flask import jsonify, request, current_app, url_for
from . import api
from ..models import User, Content



@api.get("/get_user_charge/<string:chat_user_id>")
async def get_user_charge(chat_user_id):
    print(chat_user_id)
    import requests
    import json
    print ("TEST\n\n"*10)

    url = "http://localhost:5050/dashboard/get_chatuser_charge/" +chat_user_id

    payload = json.dumps({
    "chat_user_id": chat_user_id
    })
    headers = {
    'Content-Type': 'application/json'
    }

    response = requests.request("GET", url, headers=headers, data=payload)
    return response
    # print(response.text)

@api.route('/users/<int:id>')
def get_user(id):
    user = User.query.get_or_404(id)
    return jsonify(user.to_json())


@api.route('/users/<int:id>/contents/')
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
