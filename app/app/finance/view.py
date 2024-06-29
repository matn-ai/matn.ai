from flask import render_template, redirect, request, url_for, flash
from flask_login import login_user, logout_user, login_required, \
    current_user
from . import auth
from .. import db
from ..models import User
from .models import Receipt, Bank, Charge
from ..email import send_email
from .forms import CreatePayForm
from flask_login import login_required, current_user

import zibal.zibal as zibal

merchant_id = 'zibal'
callback_url = 'https://novahub.ir/finance/webhook'
START_PAYMENT_URL = 'https://gateway.zibal.ir/start/3653515082'


@auth.route('/create_pay', methods=['POST'])
@login_required
def create_pay():
    form = CreatePayForm()
    if form.validate_on_submit():
        user = current_user
        amount = form.amount
        bank = Bank.get_bank_by_slug('zibal')
        receipt = Receipt.create_receipt(user_id=user.id, amount=amount, bank_id=bank.id)
        
        zb = zibal.zibal(merchant_id, callback_url)
        description = 'خرید شارژ به میزان {} ریال'.format(amount) # Amount is in RIAL !!!!!
        
        request_to_zibal = zb.request(amount=amount, 
                                      description=description, 
                                      order_id=receipt.number)
        
        if request_to_zibal.get('message') != 'success':
            raise Exception('Zibal request is not successful')
        
        receipt.update_additional_data({'request_to_zibal': request_to_zibal})

        redirect_url = START_PAYMENT_URL + request_to_zibal.get('trackId')
        
        return redirect(redirect_url)
        
        
        
    return render_template('finance/status_page.html')


@auth.route('/webhook', methods=['GET'])
@login_required
def webhook():
    track_id = request.args.get('trackId')
    success = request.args.get('success')
    status = request.args.get('status')
    order_id = request.args.get('orderId')
    
    if not track_id or not success or not status:
        flash('Invalid callback parameters', 'danger')
        return render_template('finance/status_page.html')
    
    # Check receipt be pending and exists
    receipt = Receipt.query.filter_by(track_id=track_id).first()
    if not receipt or receipt.status != 'pending':
        flash('Receipt not found', 'danger')
        return render_template('finance/status_page.html')
    
    # Check status be success 1: success, 0: failed
    if status != '1':
        receipt.set_status('failed')
        flash('Payment not success', 'danger')
        return render_template('finance/status_page.html')
    
    # Check receipt
    receipt.update_additional_data({'call_back_data': request.args.to_dict()})
    receipt.set_status('success')
    receipt.add_transaction(bank_slug='zibal', description='Success')
    
    # Add user charge (see finance.business about charge business and rules)
    Charge.add_user_charge(user_id=receipt.user_id, amount=receipt.amount)
    
    # Verify it
    zb = zibal.zibal(merchant_id, callback_url)
    verify_zibal = zb.verify(track_id)
    verify_result = verify_zibal['result']
    receipt.update_additional_data({'verify_result': verify_result})
    
    
    return redirect(url_for('finance/status_page.html'))