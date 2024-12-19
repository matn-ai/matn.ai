from flask import jsonify, request, current_app, url_for
from . import api
from ..models import User, Content
from .decorators import token_required
from flask import request, jsonify
from app.finance.views import create_pay_service
from app.finance.models import Charge

@api.route('/finance/reduce_charge', methods=['POST'])
@token_required
def reduce_charge():
    data = request.get_json()
    user_id = data.get('user_id')
    word_count = data.get('word_count')
    model = data.get('model', 'gpt-3.5')

    if not user_id or not word_count:
        return jsonify({'error': 'User ID and word count are required'}), 400

    try:
        user_id = int(user_id)
        word_count = int(word_count)
    except ValueError:
        return jsonify({'error': 'Invalid user ID or word count'}), 400

    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    charge = Charge.reduce_user_charge(user_id, word_count, model=model)
    
    return jsonify({
        'message': 'Charge reduced successfully',
        'user_id': user_id,
        'reduced_words': abs(charge.word_count),
        'remaining_words': Charge.get_user_charge(user_id)
    }), 200
    
@api.route('/finance/increase_charge', methods=['POST'])
@token_required
def increase_charge():
    data = request.get_json()
    user_id = data.get('user_id')
    charge_toman = data.get('charge_toman')

    if not user_id or not charge_toman:
        return jsonify({'error': 'User ID and word count are required'}), 400

    try:
        user_id = int(user_id)
        charge_toman = int(charge_toman)
    except ValueError:
        return jsonify({'error': 'Invalid user ID or word count'}), 400

    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    charge = Charge.add_user_charge(user_id, charge_toman)
    
    return jsonify({
        'message': 'Charge reduced successfully',
        'user_id': user_id,
        'increased_charge': abs(charge.word_count),
        'remaining_words': Charge.get_user_charge(user_id)
    }), 200



@api.route('/finance/view_charge', methods=['POST'])
@token_required
def view_charge():
    data = request.get_json()
    user_id = data.get('user_id')

    if not user_id:
        return jsonify({'error': 'User ID is required'}), 400

    try:
        user_id = int(user_id)
    except ValueError:
        return jsonify({'error': 'Invalid user ID'}), 400

    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    total_word_count = Charge.get_user_charge(user_id)
    
    return jsonify({
        'user_id': user_id,
        'total_word_count': total_word_count
    }), 200


@api.route('/finance/create_pay', methods=['POST'])
@token_required
def create_pay():
    """
    Create a payment request for a user.

    This service is designed for back-to-back communication and expects a JSON body
    with 'user_id' and 'amount' fields.

    JSON Body:
    - user_id: int, the ID of the user making the payment
    - amount: float, the amount to be paid

    Returns:
    - JSON object with 'redirect_url' on success
    - JSON object with 'error' message on failure
    """
    data = request.get_json()
    
    if not data or 'user_id' not in data or 'amount' not in data or 'redirect_url' not in data:
        return jsonify({'error': 'Invalid request. User ID and amount and redirect_url are required.'}), 400

    user_id = data['user_id']
    amount = float(data['amount'])
    main_redirect_url = data['redirect_url']
    # Retrieve user from database
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found.'}), 404

    redirect_dict = create_pay_service(user=user, amount=amount)
    redirect_dict['receipt'].update_additional_data({'redirect_url': main_redirect_url})
    
    return jsonify({'redirect_url': redirect_dict['redirect_url']}), 200

