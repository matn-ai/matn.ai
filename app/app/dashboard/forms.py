from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, SubmitField, FieldList, FormField, TextAreaField, HiddenField, RadioField
from wtforms.validators import DataRequired, Length, URL
from flask import flash
from ..const import (
    ARTICLE_BLOG_POST, ARTICLE_PRO, LANG_CHOICES, ARTICLE_LENGTH_CHOICES,
    POINT_OF_VIEW_CHOICES, TARGET_AUDIENCE_CHOICES, ARTICLE_LENGTH_PRO_CHOICES, VOICE_TUNE_CHOICES
)


class URLFieldForm(FlaskForm):
    url = StringField('لینک‌ورودی', validators=[URL(message='آدرس نامعتبر')])


class GenerateArticleBlog(FlaskForm):
    user_topic = TextAreaField('شرح مقاله', validators=[DataRequired(), Length(1, 500)])
    tags = StringField('کلمات کلیدی', validators=[DataRequired()])
    lang = SelectField('زبان', choices=LANG_CHOICES)
    body = TextAreaField('محتوا')
    article_length = RadioField('Article Length', choices=ARTICLE_LENGTH_CHOICES, default='short')
    content_type = HiddenField(default=ARTICLE_BLOG_POST)
    submit = SubmitField('تولید مقاله')


class GenerateArticlePro(FlaskForm):
    user_topic = TextAreaField('شرح مقاله', validators=[DataRequired(), Length(1, 500)])
    urls = FieldList(FormField(URLFieldForm), min_entries=1, max_entries=10)
    main_tag = StringField('گزاره اصلی (یک گزاره)', validators=[DataRequired()])
    tags = StringField('گزاره‌های فرعی')
    lang = SelectField('زبان', choices=LANG_CHOICES)
    body = TextAreaField('محتوا')
    content_type = HiddenField(default=ARTICLE_PRO)
    submit = SubmitField('تولید مقاله')

    point_ofview = SelectField('زاویه دید را انتخاب کنید', choices=POINT_OF_VIEW_CHOICES, default='first_person_singular')
    target_audience = SelectField('گروه هدف را انتخاب کنید', choices=TARGET_AUDIENCE_CHOICES, default='general_public')
    article_length = SelectField('طول مقاله را انتخاب کنید', choices=ARTICLE_LENGTH_PRO_CHOICES, default='normal')
    voice_tune = SelectField('لحن نوشته را انتخاب کنید', choices=VOICE_TUNE_CHOICES, default='official_pro')

    def __init__(self, *args, **kwargs):
        super(GenerateArticlePro, self).__init__(*args, **kwargs)
        if not self.urls.entries:
            self.urls.append_entry()