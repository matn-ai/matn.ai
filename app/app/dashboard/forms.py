from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, SubmitField, FieldList, FormField, TextAreaField, HiddenField
from wtforms.validators import DataRequired, Length, Email, Regexp, EqualTo, URL
from wtforms import ValidationError
from ..models import User
from flask import flash


class URLFieldForm(FlaskForm):
    url = StringField('لینک‌ورودی', validators=[URL(message='آدرس نامعتبر')])


class GenerateArticleBlog(FlaskForm):
    user_topic = TextAreaField('عنوان', validators=[DataRequired(), Length(1, 500)])
    tags = StringField('کلمات کلیدی', validators=[DataRequired()])
    lang = SelectField('زبان', choices=[('fa', 'فارسی'), ('en', 'انگلیسی')])
    body = TextAreaField('محتوا')
    content_type = HiddenField(default=0)
    submit = SubmitField('تولید مقاله')
    


class GenerateArticle(FlaskForm):
    user_topic = TextAreaField('عنوان', validators=[DataRequired(), Length(1, 500)])
    tags = StringField('کلمات کلیدی', validators=[DataRequired()])
    lang = SelectField('زبان', choices=[('fa', 'فارسی'), ('en', 'انگلیسی')])
    body = TextAreaField('محتوا')
    content_type = HiddenField(default=1)
    submit = SubmitField('تولید مقاله')


class GenerateArticlePro(FlaskForm):
    user_topic = TextAreaField('عنوان', validators=[DataRequired(), Length(1, 500)])
    urls = FieldList(FormField(URLFieldForm), min_entries=1, max_entries=10)
    tags = StringField('کلمات کلیدی', validators=[DataRequired()])
    lang = SelectField('زبان', choices=[('fa', 'فارسی'), ('en', 'انگلیسی')])
    body = TextAreaField('محتوا')
    content_type = HiddenField(default=2)
    submit = SubmitField('تولید مقاله')

    def __init__(self, *args, **kwargs):
        super(GenerateArticlePro, self).__init__(*args, **kwargs)
        if not self.urls.entries:
            self.urls.append_entry()
