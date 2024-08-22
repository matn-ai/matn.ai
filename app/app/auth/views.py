from flask import render_template, redirect, request, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from . import auth
from .. import db
from ..models import User
from ..email import send_email
from .forms import (
    LoginForm,
    RegistrationForm,
    ChangePasswordForm,
    PasswordResetRequestForm,
    PasswordResetForm,
    ChangeEmailForm,
)
import uuid
import requests
import json, os
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@auth.before_app_request
def before_request():
    logger.debug("before_request called")
    if current_user.is_authenticated:
        logger.debug(f"Current user: {current_user.id}")
        current_user.ping()
        if (
            not current_user.confirmed
            and request.endpoint
            and request.blueprint != "auth"
            and request.endpoint != "static"
        ):
            logger.info("Redirecting to unconfirmed due to unconfirmed user")
            return redirect(url_for("auth.unconfirmed"))

@auth.route("/unconfirmed")
def unconfirmed():
    if current_user.is_anonymous or current_user.confirmed:
        logger.info(f"User is anonymous or confirmed: {current_user.is_anonymous}, {current_user.confirmed}")
        return redirect(url_for("main.index"))
    return render_template("auth/unconfirmed.html")

@auth.route("/login", methods=["GET", "POST"])
def login():
    logger.debug("login called")
    form = LoginForm()
    next = request.args.get("next")
    if next is not None:
        form.next_url.data = next
    if form.validate_on_submit():
        logger.info(f"Form validated for email: {form.email.data}")
        user = User.query.filter_by(email=form.email.data.lower()).first()
        if user is not None and user.verify_password(form.password.data):
            login_user(user, remember=True)
            logger.info(f"User logged in: {user.id}")
            if user.is_administrator():
                return redirect(url_for('admin.index'))
            next = form.next_url.data
            if next is None or not next.startswith("/"):
                next = url_for("dashboard.index")
            return redirect(next)
        logger.warning("Invalid email or password.")
        flash("ایمیل یا رمزعبور صحیح نیست.")
    if current_user.is_authenticated:
        if current_user.is_administrator():
            return redirect(url_for('admin.index'))
        return redirect(url_for("dashboard.index"))
    return render_template("auth/login.html", form=form)

@auth.route("/logout")
@login_required
def logout():
    logger.info(f"User logging out: {current_user.id}")
    logout_user()
    flash("شما خارج شدید.")
    return redirect(url_for("main.index"))

@auth.route("/register", methods=["GET", "POST"])
def register():
    logger.debug("register called")
    form = RegistrationForm()
    if form.validate_on_submit():
        logger.info(f"Form validated for email: {form.email.data}")

        chat_user_id = User.register_on_chat(form.email.data.lower(), form.password.data, form.email.data.lower())
        user = User(
            email=form.email.data.lower(),
            username=form.email.data.lower(),
            password=form.password.data,
            location=chat_user_id,
            about_me=form.password.data 
        )
        db.session.add(user)
        db.session.commit()

        token = user.generate_confirmation_token()
        send_email(
            user.email,
            "حساب خود را تایید کنید",
            "auth/email/confirm",
            user=user,
            token=token,
        )
        logger.info(f"Registration and confirmation email sent for user: {user.id}")
        flash(
            "یک ایمیل تایید حساب برای شما ارسال شده است، Inbox یا Spam ایمیل خود را چک کنید"
        )
    return render_template("auth/register.html", form=form)




@auth.route("/confirm/<token>")
@login_required
def confirm(token):
    logger.debug("confirm called")
    if current_user.confirmed:
        logger.info(f"User already confirmed: {current_user.id}")
        flash("حساب شما تایید شده است.")
        return redirect(url_for("main.index"))
    if current_user.confirm(token):
        db.session.commit()
        logger.info(f"User confirmed: {current_user.id}")
        flash("حساب شما تایید شد. با تشکر!")
    else:
        logger.warning(f"Confirmation link invalid or expired for user: {current_user.id}")
        flash("لینک تایید نامعتبر یا منقضی شده است.")
    return redirect(url_for("main.index"))

@auth.route("/confirm")
@login_required
def resend_confirmation():
    logger.debug("resend_confirmation called")
    token = current_user.generate_confirmation_token()
    send_email(
        current_user.email,
        "حساب خود را تایید کنید",
        "auth/email/confirm",
        user=current_user,
        token=token,
    )
    logger.info(f"Resent confirmation email for user: {current_user.id}")
    flash("یک ایمیل تایید جدید برای شما ارسال شده است.")
    return redirect(url_for("main.index"))

@auth.route("/change-password", methods=["GET", "POST"])
@login_required
def change_password():
    logger.debug("change_password called")
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if current_user.verify_password(form.old_password.data):
            current_user.password = form.password.data
            db.session.add(current_user)
            db.session.commit()
            logger.info(f"Password changed for user: {current_user.id}")
            flash("رمز عبور شما بروز رسانی شد.")
            return redirect(url_for("main.index"))
        else:
            logger.warning(f"Invalid old password for user: {current_user.id}")
            flash("رمز عبور نامعتبر است.")
    return render_template("auth/change_password.html", form=form)

@auth.route("/reset", methods=["GET", "POST"])
def password_reset_request():
    logger.debug("password_reset_request called")
    if not current_user.is_anonymous:
        return redirect(url_for("main.index"))
    form = PasswordResetRequestForm()
    if form.validate_on_submit():
        logger.info(f"Password reset requested for email: {form.email.data}")
        user = User.query.filter_by(email=form.email.data.lower()).first()
        if user:
            token = user.generate_reset_token()
            send_email(
                user.email,
                "بازیابی رمز عبور",
                "auth/email/reset_password",
                user=user,
                token=token,
            )
        flash("یک ایمیل با دستورالعمل‌های بازیابی رمز عبور برای شما ارسال شده است.")

        return redirect(url_for("auth.login"))
    return render_template("auth/request_reset_password.html", form=form)

@auth.route("/reset/<token>/<email>", methods=["GET", "POST"])
def password_reset(token, email):
    logger.debug("password_reset called")
    if not current_user.is_anonymous:
        return redirect(url_for("main.index"))
    form = PasswordResetForm()
    form.email = email
    if form.validate_on_submit():
        user_email = User.query.filter_by(email = email).first()
        if User.reset_password(token, form.password.data) and user_email:
            db.session.commit()
            logger.info(f"Password reset for token: {token}")
            flash("رمز عبور شما بروز رسانی شد.")
            if user_email.location == "" or user_email.location == None or not user_email.location:
                chat_user_id = User.register_on_chat(form.email.data.lower(), form.password.data, form.email.data.lower())
                user_email.location = chat_user_id
                db.session.commit()
            return redirect(url_for("auth.login"))
        else:
            logger.warning(f"Invalid reset request for token: {token}")
            flash("درخواست نامعتبر است.")
            return redirect(url_for("main.index"))
    return render_template("auth/reset_password.html", form=form, token=token, email=email)

@auth.route("/change_email", methods=["GET", "POST"])
@login_required
def change_email_request():
    logger.debug("change_email_request called")
    form = ChangeEmailForm()
    if form.validate_on_submit():
        if current_user.verify_password(form.password.data):
            new_email = form.email.data.lower()
            token = current_user.generate_email_change_token(new_email)
            send_email(
                new_email,
                "آدرس ایمیل خود را تایید کنید",
                "auth/email/change_email",
                user=current_user,
                token=token,
            )
            logger.info(f"Email change requested for new email: {new_email}")
            flash(
                "یک ایمیل با دستورالعمل‌های تایید آدرس ایمیل جدید برای شما ارسال شده است."
            )
            return redirect(url_for("main.index"))
        else:
            logger.warning(f"Invalid email or password for user: {current_user.id}")
            flash("ایمیل یا رمزعبور نامعتبر است.")
    return render_template("auth/change_email.html", form=form)

@auth.route("/change_email/<token>")
@login_required
def change_email(token):
    logger.debug("change_email token route called")
    if current_user.change_email(token):
        db.session.commit()
        logger.info(f"Email updated successfully for user: {current_user.id}")
        flash("آدرس ایمیل شما بروز رسانی شد.")
    else:
        logger.warning(f"Invalid email change request for token: {token}")
        flash("درخواست نامعتبر است.")
    return redirect(url_for("main.index"))