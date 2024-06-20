from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, SubmitField, FieldList, FormField
from wtforms.validators import DataRequired, Length, Email, Regexp, EqualTo, URL
from wtforms import ValidationError
from ..models import User
from flask import flash


class URLFieldForm(FlaskForm):
    url = StringField('لینک‌ورودی', validators=[DataRequired(), URL(message='آدرس نامعتبر')])


class GenerateArticleBlog(FlaskForm):
    user_topic = StringField('عنوان', validators=[DataRequired(), Length(1, 500)])
    tags = StringField('کلمات کلیدی', validators=[DataRequired()])
    lang = SelectField('زبان', choices=[('fa', 'فارسی'), ('en', 'انگلیسی')])
    submit = SubmitField('تولید مقاله')


class GenerateArticle(FlaskForm):
    user_topic = StringField('عنوان', validators=[DataRequired(), Length(1, 500)])
    tags = StringField('کلمات کلیدی', validators=[DataRequired()])
    lang = SelectField('زبان', choices=[('fa', 'فارسی'), ('en', 'انگلیسی')])
    submit = SubmitField('تولید مقاله')


class GenerateArticlePro(FlaskForm):
    user_topic = StringField('عنوان', validators=[DataRequired(), Length(1, 500)])
    urls = FieldList(FormField(URLFieldForm), min_entries=1, max_entries=10)
    tags = StringField('کلمات کلیدی', validators=[DataRequired()])
    lang = SelectField('زبان', choices=[('fa', 'فارسی'), ('en', 'انگلیسی')])
    submit = SubmitField('تولید مقاله')

    def __init__(self, *args, **kwargs):
        super(GenerateArticlePro, self).__init__(*args, **kwargs)
        if not self.urls.entries:
            self.urls.append_entry()


# class RegistrationForm(FlaskForm):
#     email = StringField('ایمیل', validators=[DataRequired(), Length(1, 64),
#                                              Email()])
#     username = StringField('نام کاربری', validators=[
#         DataRequired(), Length(1, 64),
#         Regexp('^[A-Za-z][A-Za-z0-9_.]*$', 0,
#                'Usernames must have only letters, numbers, dots or '
#                'underscores')])
#     password = PasswordField('رمزعبور', validators=[
#         DataRequired(), EqualTo('password2', message='رمزعبور اشتباه است')])
#     password2 = PasswordField('تکرار رمزعبور', validators=[DataRequired()])
#     submit = SubmitField('ثبت‌نام')

#     def validate_email(self, field):
#         if User.query.filter_by(email=field.data.lower()).first():
#             flash('این ایمیل قبلا ثبت شده است.')
#             raise ValidationError

#     def validate_username(self, field):
#         if User.query.filter_by(username=field.data).first():
#             flash('این نام‌کاربری قبلا استفاده شده است')
#             raise ValidationError


# class ChangePasswordForm(FlaskForm):
#     old_password = PasswordField('رمز‌عبور قدیمی', validators=[DataRequired()])
#     password = PasswordField('رمزعبور جدید', validators=[
#         DataRequired(), EqualTo('password2', message='Passwords must match.')])
#     password2 = PasswordField('تکرار رمز عبور جدید',
#                               validators=[DataRequired()])
#     submit = SubmitField('به‌روزرسانی')


# class PasswordResetRequestForm(FlaskForm):
#     email = StringField('ایمیل', validators=[DataRequired(), Length(1, 64),
#                                              Email()])
#     submit = SubmitField('بازنشانی رمزعبور')


# class PasswordResetForm(FlaskForm):
#     password = PasswordField('رمز عبور جدید', validators=[
#         DataRequired(), EqualTo('password2', message='Passwords must match')])
#     password2 = PasswordField('تکرار رمز عبور جدید', validators=[DataRequired()])
#     submit = SubmitField('بازنشانی رمز عبور')


# class ChangeEmailForm(FlaskForm):
#     email = StringField('ایمیل جدید', validators=[DataRequired(), Length(1, 64),
#                                                  Email()])
#     password = PasswordField('رمزعبور', validators=[DataRequired()])
#     submit = SubmitField('به‌روزرسانی ایمیل جدید')

#     def validate_email(self, field):
#         if User.query.filter_by(email=field.data.lower()).first():
#             flash('این ایمیل قبلا ثبت شده است.')
#             raise ValidationError
