
from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, SubmitField, FieldList, FormField, TextAreaField, HiddenField, RadioField, FileField
from wtforms.validators import DataRequired, Length, URL
from flask import flash
from ..const import (
    ARTICLE_BLOG_POST, ARTICLE_PRO, LANG_CHOICES, ARTICLE_LENGTH_CHOICES,
    POINT_OF_VIEW_CHOICES, TARGET_AUDIENCE_CHOICES, ARTICLE_LENGTH_PRO_CHOICES, VOICE_TUNE_CHOICES
)


LLM_MODEL_CHOICES = [
    ('claude-3-haiku', 'Haiku - مدل ضعیف - هزینه ۱ کلمه'),
    ('gpt-3.5-turbo', 'GPT 3.5 - مدل معمولی - هزینه ۲ کلمه'),
    ('claude-3.5-sonnet', 'Sonnet 3.5 - مدل قدرتمند - هزینه ۴ کلمه'),
    ('gpt-4o', 'GPT 4o - مدل قدرتمند - هزینه ۵ کلمه'),
    
]

class TranslateForm(FlaskForm):
    text_to_translate = TextAreaField('متنی که میخواهید به فارسی ترجمه کنید', validators=[DataRequired(), Length(1, 5000)])
    llm_model = SelectField('مدل انتخابی ترجمه', choices=LLM_MODEL_CHOICES, validators=[DataRequired()])
    body = TextAreaField('محتوا')
    submit = SubmitField('ترجمه کن!')
    
    

class FileTranslateForm(FlaskForm):
    file = FileField('فایل مورد نظر: pdf, word, docx, srt', validators=[DataRequired()])
    llm_model = SelectField('مدل انتخابی ترجمه', choices=LLM_MODEL_CHOICES, validators=[DataRequired()])
    submit = SubmitField('Get Estimate Cost')
    start_translation = SubmitField('Start Translation')
    confirm = HiddenField(default='no')