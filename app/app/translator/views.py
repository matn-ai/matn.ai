from flask import render_template, jsonify, abort, request, url_for, send_file, flash
from werkzeug.utils import secure_filename
from flask_login import login_required, current_user
from app.translator.forms import TranslateForm, FileTranslateForm
from app.dashboard import dashboard
from ..tasks import generate_blog_simple, generate_pro_article
import json, os, logging
import uuid
from ..utils import utils_gre2jalali
from .. import app, db

from ..finance.models import Charge
from ..models import Job
from ..dashboard.repository import create_content, create_job_record, update_article_pro
from .business import persian_translator
from ..const import FILE_TRANSLATION

from .tasks import translate_file, calculate_estimated_cost

logger = logging.getLogger(__name__)

@dashboard.route("/translate/to-persian", methods=["GET", "POST"])
@login_required
def translate_to_persian():
    form = TranslateForm()
    content = None
    translated_text = None
    if form.validate_on_submit():
        form_data = request.form.to_dict()
        user = current_user
        llm_model = form_data['llm_model']
        content = create_content(user_input=form_data, author=current_user, llm=llm_model)
        translated_text, usage = persian_translator(text=form_data['text_to_translate'], 
                                                    llm=llm_model)
        update_article_pro(content_id=content.id, body=translated_text)
        total_words = len(translated_text.split())
        form.body.data = translated_text
        Charge.reduce_user_charge(user_id=user.id,
                                  total_words=total_words,
                                  model=llm_model)

    else:
        flash('داده‌ها ولید نیستند', 'danger')

    return render_template(
        "dashboard/translate/translate_to_persian.html", 
        form=form, 
        content=content, 
        translated_text=translated_text
    )


@dashboard.route("/translate/to-persian-file", methods=["GET", "POST"])
@login_required
def translate_to_persian_file():
    form = FileTranslateForm()
    translated_text = None
    if form.validate_on_submit():
        form_data = request.form.to_dict()
        user = current_user
        db.session.expunge(user)
        llm_model = form_data['llm_model']
        uploaded_file = request.files['file']
        
        filename = secure_filename(uploaded_file.filename)
        temp_path = os.path.join('./tmp/', filename)
        uploaded_file.save(temp_path)
        supported_file_formats = {
            'application/pdf': translate_file,
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': translate_file
        }
        form_data['body'] = filename
        form_data['content_type'] = FILE_TRANSLATION
        form_data['file_path'] = temp_path
        form_data['mimetype'] = uploaded_file.mimetype.strip()
        if uploaded_file.mimetype.strip() in supported_file_formats:
            func = supported_file_formats[uploaded_file.mimetype.strip()]
            content = create_content(user_input=form_data, author=current_user, llm=llm_model)
            job = func.delay(content.id, form_data)
            create_job_record(job_id=job.id, content=content)
            j_date = utils_gre2jalali(content.job.created_at)
            translated_text = 'فایل شما در حال بررسی و ترجمه می‌باشد'
            flash('فایل‌ شما در حال اماده سازیست. بعد از اتمام به شما خبر میدیم')
            # return jsonify(job_id=job.id, content_id=content.id, job_date=j_date)
        else:
            pass
            
        
        # translated_text = '\n\n'.join([txt[1] for txt in translated_texts])
            
    return render_template("dashboard/translate/translate_to_persian_file.html",
                           form=form, 
                           translated_text=translated_text,
                           )
    

@dashboard.route("/translate/estimate-cost", methods=["POST"])
@login_required
def estimate_cost():
    form_data = request.form.to_dict()
    llm_model = form_data['llm_model']
    uploaded_file = request.files['file']
    if not uploaded_file:
        return jsonify({'estimated_cost': 'فایلی انتخاب نشده است'})
    print('file_meme: ' ,uploaded_file.mimetype)
    filename = secure_filename(uploaded_file.filename)
    temp_path = os.path.join('./tmp/', filename)
    uploaded_file.save(temp_path)

    estimated_cost_value = calculate_estimated_cost(temp_path, llm_model, file_type=uploaded_file.mimetype)  # Assuming a function to calculate cost
    if estimated_cost_value is None:
        return jsonify({'estimated_cost': -1, 'meme': 'file not supported'})
    
    return jsonify({'estimated_cost': estimated_cost_value, 'meme': uploaded_file.mimetype})