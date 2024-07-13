from flask import render_template, jsonify, abort, request, url_for, flash, redirect
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
import uuid
import os
import logging

from app.translator.forms import TranslateForm, FileTranslateForm
from app.dashboard import dashboard
from app import db
from app.finance.models import Charge
from app.file_management.models import ContentFile
from app.dashboard.repository import create_content, create_job_record, update_article_pro, get_content_by_id
from app.translator.business import persian_translator
from app.const import FILE_TRANSLATION, TEXT_TRANSLATION
from app.translator.tasks import translate_file, calculate_estimated_cost

logger = logging.getLogger(__name__)

@dashboard.route("/translate/to-persian", methods=["GET", "POST"])
@dashboard.route("/translate/to-persian/<id>", methods=["GET", "POST"])
@login_required
def translate_to_persian(id=None):
    if current_user.remain_charge < 0:
        flash('شارژ شما کافی نمیباشد. لطفا از قسمت افزایش اعتبار شارژ خود را افزایش دهید', 'error')
        return redirect(url_for('finance.create_pay'))

    form = TranslateForm()
    content = None
    translated_text = None

    if form.is_submitted():
        form_data = request.form.to_dict()
        llm_model = form_data['llm_model']
        text_to_translate = form_data['text_to_translate']
        
        content = create_content(user_input=form_data, author=current_user, llm=llm_model)
        create_job_record(job_id=uuid.uuid4(), content=content)
        
        translated_text, _ = persian_translator(text=text_to_translate, llm=llm_model)
        
        update_article_pro(content_id=content.id, body=translated_text)
        total_words = len(translated_text.split())
        
        content.body = translated_text
        content.word_count = total_words
        content.system_title = text_to_translate[:100] + '...'
        
        db.session.commit()
        
        Charge.reduce_user_charge(user_id=current_user.id, total_words=total_words, model=llm_model, content_id=content.id)
        
        return jsonify({"translated_text": translated_text})

    if id:
        content = get_content_by_id(id)
        if not content or content.content_type != TEXT_TRANSLATION:
            abort(404)
        form.body.data = content.body
        form.text_to_translate.data = content.get_input('text_to_translate')

    return render_template(
        "dashboard/translate/translate_to_persian.html", 
        form=form, 
        content=content, 
        translated_text=translated_text,
        just_view='True' if id else None
    )

@dashboard.route("/translate/to-persian-file", methods=["GET", "POST"])
@dashboard.route("/translate/to-persian-file/<id>", methods=["GET", "POST"])
@login_required
def translate_to_persian_file(id=None):
    if current_user.remain_charge < 0:
        flash('شارژ شما کافی نمیباشد. لطفا از قسمت افزایش اعتبار شارژ خود را افزایش دهید', 'error')
        return redirect(url_for('finance.create_pay'))

    form = FileTranslateForm()
    content = None
    translated_data = None

    if form.validate_on_submit():
        form_data = request.form.to_dict()
        uploaded_file = request.files['file']
        
        filename = secure_filename(uploaded_file.filename)
        temp_path = os.path.join('./tmp/', filename)
        uploaded_file.save(temp_path)
        
        supported_file_formats = {
            'application/pdf': translate_file,
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': translate_file
        }
        
        if uploaded_file.mimetype.strip() in supported_file_formats:
            content = create_content(user_input=form_data, author=current_user, llm=form_data['llm_model'])
            job = supported_file_formats[uploaded_file.mimetype.strip()].delay(content.id, form_data)
            create_job_record(job_id=job.id, content=content)
            flash('فایل شما در حال ترجمه است ، چند دقیقه دیگر بررسی نمایید')
            return redirect(url_for('dashboard.index'))

    if id:
        content = get_content_by_id(id)
        if not content or content.content_type != FILE_TRANSLATION:
            abort(404)
        
        content_files = ContentFile.get_files_for_content(content.id)
        if not content_files:
            flash('فایل‌ شما هنوز در حال ترجمه میباشد. لطفا کمی بعدتر این صفحه را به روز کنید')
        
        translated_data = [{'file_name': cf.file.file_name, 'url': cf.file.get_file_url()} for cf in content_files]

    return render_template(
        "dashboard/translate/translate_to_persian_file.html",
        form=form, 
        translated_data=translated_data,
        content=content
    )

@dashboard.route("/translate/estimate-cost", methods=["POST"])
@login_required
def estimate_cost():
    uploaded_file = request.files['file']
    
    if not uploaded_file:
        return jsonify({'estimated_cost': 'فایلی انتخاب نشده است'})
    
    filename = secure_filename(uploaded_file.filename)
    temp_path = os.path.join('./tmp/', filename)
    uploaded_file.save(temp_path)

    estimated_cost_value = calculate_estimated_cost(temp_path, request.form['llm_model'], file_type=uploaded_file.mimetype)
    
    if estimated_cost_value is None:
        return jsonify({'estimated_cost': -1, 'meme': 'file not supported'})
    
    return jsonify({'estimated_cost': estimated_cost_value, 'meme': uploaded_file.mimetype})