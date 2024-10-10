from flask import render_template, redirect, request, url_for, flash
from flask_login import login_user, logout_user, login_required, \
    current_user
from . import finance
from .. import db
from .models import Receipt, Bank, Charge
from .forms import CreatePayForm
from flask_login import login_required, current_user

import os

from persian_tools import digits, separator

import logging
logger = logging.getLogger()

import zibal.zibal as zibal

merchant_id = os.environ.get('ZIBAL_MERCHAND_ID', 'zibal') # zibal for test mode
callback_url = os.environ.get('ZIBAL_CALLBACK_URL', 'http://127.0.0.1:5000/finance/webhook/zibal')
START_PAYMENT_URL = 'https://gateway.zibal.ir/start/'
MAIN_URL = os.environ.get('MAIN_URL', 'http://127.0.0.1:5000')


def create_pay_service(user, amount) -> dict:
    logger.info('Requested amount for user {} is {}'.format(user.id, amount))
    
    bank = Bank.get_bank_by_slug('zibal')
    receipt = Receipt.create_receipt(user_id=user.id, amount=amount, bank_id=bank.id)
    
    zb = zibal.zibal(merchant_id, callback_url)
    description = 'خرید شارژ به میزان {} ریال'.format(amount * 10)  # Amount is in RIAL !!!!!
    
    request_to_zibal = zb.request(amount=amount * 10, 
                                  description=description, 
                                  order_id=receipt.number)
    logger.info('Zibal request data {}'.format(request_to_zibal))
    
    if request_to_zibal.get('message') != 'success':
        return jsonify({'error': 'Zibal request is not successful'}), 500
    
    receipt.update_additional_data({'request_to_zibal': request_to_zibal})
    receipt.set_tracker_id(str(request_to_zibal.get('trackId')))
    redirect_url = START_PAYMENT_URL + str(request_to_zibal.get('trackId'))
    logger.info(redirect_url)
    
    return {'redirect_url': redirect_url, 'receipt': receipt}



@finance.route('/finance/create_pay', methods=['GET', 'POST'])
@login_required
def create_pay():
    form = CreatePayForm()
    if request.method == 'POST' and form.validate_on_submit():
        user = current_user
        amount = float(form.amount.data)
        redirect_dict = create_pay_service(user=user, amount=amount)
        return redirect(redirect_dict['redirect_url'])
                
    return render_template('finance/create_pay.html', form=form)


@finance.route('/finance/webhook/zibal', methods=['GET'])
# @login_required
def zibal_webhook():
    track_id = request.args.get('trackId')
    success = request.args.get('success')
    status = request.args.get('status')
    order_id = request.args.get('orderId')
    
    if not track_id or not success or not status:
        flash('Invalid callback parameters', 'danger')
        return render_template('finance/status_page.html')
    
    # Check receipt be pending and exists
    logger.info('Incoming track id ' + str(track_id))
    receipt = Receipt.query.filter_by(tracker_id=str(track_id)).first()
    logger.info('Found receipt : {}'.format(receipt))
    if not receipt or receipt.status != 'pending':
        flash('Receipt not found or has not been pending', 'danger')
        return render_template('finance/status_page.html')
    
    if status == '1':
        receipt.set_status('failed')
        flash('پرداخت شما قبلا داخل سیستم نشسته است', 'danger')
        return render_template('finance/status_page.html')
    
    # Check status be success 1: success, 0: failed
    if status != '2':
        receipt.set_status('failed')
        flash('پرداخت شما موفقیت امیز نبود', 'danger')
        return render_template('finance/status_page.html')
    
    logger.info('Adding the additional data')
    # Check receipt
    receipt.update_additional_data({'call_back_data': request.args.to_dict()})
    receipt.add_transaction(bank_slug='zibal', description='Success')
    receipt.set_status('success')
    
    logger.info(f'Charge user {receipt.user_id} -> {receipt.amount}')
    # Add user charge (see finance.business about charge business and rules)
    user_new_charge = Charge.add_user_charge(user_id=receipt.user_id, toman_amount=receipt.amount)
    
    logger.info(f'Going to verify the payment {track_id} -> {receipt.user_id}')
    # Verify it
    zb = zibal.zibal(merchant_id, callback_url)
    verify_zibal = zb.verify(track_id)
    verify_result = verify_zibal['result']
    logger.info('Verify result {}'.format(verify_result))
    receipt.update_additional_data({'verify_result': verify_result})
    if receipt.additional_data.get('redirect_url'):
        return redirect(receipt.additional_data.get('redirect_url'))
    
    return redirect(MAIN_URL + '/finance/status?receipt_number={}&user_charge={}'.format(receipt.number, user_new_charge.word_count))


@finance.route('/finance/status', methods=['GET'])
@login_required
def payment_status():
    receipt_number = request.args.get('receipt_number')
    receipt_number = digits.convert_to_fa(receipt_number)
    charge = request.args.get('user_charge')
    charge = digits.convert_to_fa(charge)
    charge = separator.add(charge)
    flash('اکانت شما به شماره تراکنش {} در سیستم ثبت شد. تعداد {} کلمه اکانت شما شارژ شد'.format(receipt_number, charge), 'success')
    return render_template('finance/status_page.html')