from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField, HiddenField
from wtforms.validators import DataRequired, Length, Email, Regexp, EqualTo
from wtforms import ValidationError
from ..models import User
from flask import flash

class BaseForm(FlaskForm):
    def validate(self, *args, **kwargs):
        is_valid = super(BaseForm, self).validate(*args, **kwargs)
        if not is_valid:
            for field, errors in self.errors.items():
                for error in errors:
                    flash(f"خطا در ورود  {getattr(self, field).label.text}، {error}", 'danger')
        return is_valid

class LoginForm(BaseForm):
    email = StringField('ایمیل', validators=[DataRequired(), Length(1, 64), Email()])
    password = PasswordField('رمز عبور', validators=[DataRequired()])
    remember_me = BooleanField('این دستگاه را بخاطر بسپار', default=True)
    next_url = HiddenField('next_url')
    submit = SubmitField('ورود')

class RegistrationForm(BaseForm):
    email = StringField('ایمیل', validators=[DataRequired(), Length(1, 64), Email()])
    username = StringField('نام کاربری')
    password = PasswordField('رمزعبور', validators=[
        DataRequired(), EqualTo('password2', message='رمزعبور اشتباه است')])
    password2 = PasswordField('تکرار رمزعبور', validators=[DataRequired()])
    submit = SubmitField('ثبت‌نام')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data.lower()).first():
            # flash('این ایمیل قبلا ثبت شده است', 'danger')
            raise ValidationError('این ایمیل قبلا ثبت شده است')

    def validate_username(self, field):
        if User.query.filter_by(username=field.data).first():
            # flash('این نام‌کاربری قبلا استفاده شده است', 'danger')
            raise ValidationError('این نام‌کاربری قبلا استفاده شده است')

class ChangePasswordForm(BaseForm):
    old_password = PasswordField('رمز‌عبور قدیمی', validators=[DataRequired()])
    password = PasswordField('رمزعبور جدید', validators=[
        DataRequired(), EqualTo('password2', message='رمزعبور باید همسان باشد')])
    password2 = PasswordField('تکرار رمز عبور جدید', validators=[DataRequired()])
    submit = SubmitField('به‌روزرسانی')

class PasswordResetRequestForm(BaseForm):
    email = StringField('ایمیل', validators=[DataRequired(), Length(1, 64), Email()])
    submit = SubmitField('بازنشانی رمزعبور')

class PasswordResetForm(BaseForm):
    email = StringField('ایمیل', validators=[DataRequired(), Length(1, 64), Email()])
    password = PasswordField('رمز عبور جدید', validators=[
        DataRequired(), EqualTo('password2', message='رمزعبور باید همسان باشد')])
    password2 = PasswordField('تکرار رمز عبور جدید', validators=[DataRequired()])
    submit = SubmitField('بازنشانی رمز عبور')

class ChangeEmailForm(BaseForm):
    email = StringField('ایمیل جدید', validators=[DataRequired(), Length(1, 64), Email()])
    password = PasswordField('رمزعبور', validators=[DataRequired()])
    submit = SubmitField('به‌روزرسانی ایمیل جدید')

    def validate_email(self, field):
        if User.query.filter_by(email=field.data.lower()).first():
            flash('این ایمیل قبلا ثبت شده است', 'danger')
            raise ValidationError('این ایمیل قبلا ثبت شده است')