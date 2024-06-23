from flask import render_template, redirect, request, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from . import auth
from .. import db
from ..models import User
from ..email import send_email
from .forms import LoginForm, RegistrationForm, ChangePasswordForm, PasswordResetRequestForm, PasswordResetForm, ChangeEmailForm


@auth.before_app_request
def before_request():
    if current_user.is_authenticated:
        print(request.full_path)
        current_user.ping()
        if not current_user.confirmed \
                and request.endpoint \
                and request.blueprint != 'auth' \
                and request.endpoint != 'static':
                    return redirect(url_for('auth.unconfirmed'))


@auth.route('/unconfirmed')
def unconfirmed():
    if current_user.is_anonymous or current_user.confirmed:
        return redirect(url_for('main.index'))
    return render_template('auth/unconfirmed.html')


@auth.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    next = request.args.get('next')
    if next is not None:
        form.next_url.data = next
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        if user is not None and user.verify_password(form.password.data):
            login_user(user, remember=True)
            next = form.next_url.data
            if next is None or not next.startswith('/'):
                next = url_for('dashboard.index')
            return redirect(next)
        flash('ایمیل یا رمزعبور صحیح نیست.')
    return render_template('auth/login.html', form=form)


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash('شما خارج شدید.')
    return redirect(url_for('main.index'))


@auth.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(email=form.email.data.lower(),
                    username=form.username.data,
                    password=form.password.data)
        db.session.add(user)
        db.session.commit()
        token = user.generate_confirmation_token()
        send_email(user.email, 'حساب خود را تایید کنید',
                   'auth/email/confirm', user=user, token=token)
        flash('یک ایمیل تایید حساب برای شما ارسال شده است، Inbox یا Spam ایمیل خود را چک کنید')
    return render_template('auth/register.html', form=form)


@auth.route('/confirm/<token>')
@login_required
def confirm(token):
    if current_user.confirmed:
        flash('حساب شما تایید شده است.')
        return redirect(url_for('main.index'))
    if current_user.confirm(token):
        db.session.commit()
        flash('حساب شما تایید شد. با تشکر!')
    else:
        flash('لینک تایید نامعتبر یا منقضی شده است.')
    return redirect(url_for('main.index'))


@auth.route('/confirm')
@login_required
def resend_confirmation():
    token = current_user.generate_confirmation_token()
    send_email(current_user.email, 'حساب خود را تایید کنید',
               'auth/email/confirm', user=current_user, token=token)
    flash('یک ایمیل تایید جدید برای شما ارسال شده است.')
    return redirect(url_for('main.index'))


@auth.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if current_user.verify_password(form.old_password.data):
            current_user.password = form.password.data
            db.session.add(current_user)
            db.session.commit()
            flash('رمز عبور شما بروز رسانی شد.')
            return redirect(url_for('main.index'))
        else:
            flash('رمز عبور نامعتبر است.')
    return render_template("auth/change_password.html", form=form)


@auth.route('/reset', methods=['GET', 'POST'])
def password_reset_request():
    if not current_user.is_anonymous:
        return redirect(url_for('main.index'))
    form = PasswordResetRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        if user:
            token = user.generate_reset_token()
            send_email(user.email, 'بازیابی رمز عبور',
                       'auth/email/reset_password',
                       user=user, token=token)
        flash('یک ایمیل با دستورالعمل‌های بازیابی رمز عبور برای شما ارسال شده است.')
        return redirect(url_for('auth.login'))
    return render_template('auth/reset_password.html', form=form)


@auth.route('/reset/<token>', methods=['GET', 'POST'])
def password_reset(token):
    if not current_user.is_anonymous:
        return redirect(url_for('main.index'))
    form = PasswordResetForm()
    if form.validate_on_submit():
        if User.reset_password(token, form.password.data):
            db.session.commit()
            flash('رمز عبور شما بروز رسانی شد.')
            return redirect(url_for('auth.login'))
        else:
            flash('درخواست نامعتبر است.')
            return redirect(url_for('main.index'))
    return render_template('auth/reset_password.html', form=form)


@auth.route('/change_email', methods=['GET', 'POST'])
@login_required
def change_email_request():
    form = ChangeEmailForm()
    if form.validate_on_submit():
        if current_user.verify_password(form.password.data):
            new_email = form.email.data.lower()
            token = current_user.generate_email_change_token(new_email)
            send_email(new_email, 'آدرس ایمیل خود را تایید کنید',
                       'auth/email/change_email',
                       user=current_user, token=token)
            flash('یک ایمیل با دستورالعمل‌های تایید آدرس ایمیل جدید برای شما ارسال شده است.')
            return redirect(url_for('main.index'))
        else:
            flash('ایمیل یا رمزعبور نامعتبر است.')
    return render_template("auth/change_email.html", form=form)


@auth.route('/change_email/<token>')
@login_required
def change_email(token):
    if current_user.change_email(token):
        db.session.commit()
        flash('آدرس ایمیل شما بروز رسانی شد.')
    else:
        flash('درخواست نامعتبر است.')
    return redirect(url_for('main.index'))