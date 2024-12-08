from functools import wraps
from flask import g
from .errors import forbidden
from flask import request, jsonify



def permission_required(permission):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not g.current_user.can(permission):
                return forbidden('Insufficient permissions')
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = None
        
        # Check if the Authorization header is present
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                # Extract the token from the "Bearer <token>" format
                token = auth_header.split()[1]
            except IndexError:
                return jsonify({'message': 'Token is missing or invalid'}), 401
        
        if not token:
            return jsonify({'message': 'Token is missing'}), 401
        
        # Hard-coded token (replace this with your desired token)
        valid_token = 'xT4B0v9n5EGJV2fEIsy3xT4B-0v9n5EGJV2fEIsy3xT4B0v-9n5EGJV2fEIsy3'
        
        if token != valid_token:
            return jsonify({'message': 'Token is invalid'}), 401
        
        return f(*args, **kwargs)
    
    return decorated