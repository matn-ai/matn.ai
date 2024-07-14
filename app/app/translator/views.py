from flask import render_template, jsonify, abort, request, url_for, send_file, flash, redirect
from werkzeug.utils import secure_filename
from flask_login import login_required, current_user
from app.translator.forms import TranslateForm, FileTranslateForm
from app.dashboard import dashboard
from ..tasks import generate_blog_simple, generate_pro_article
import json, os, logging
import uuid
from ..utils import utils_gre2jalali
from .. import app, db

from ..finance.models import Charge, calculate_reduce_charge
from ..file_management.models import File, ContentFile
from ..dashboard.repository import create_content, create_job_record, update_article_pro, get_content_by_id
from .business import persian_translator
from ..const import FILE_TRANSLATION, TEXT_TRANSLATION

from .tasks import translate_file, calculate_estimated_cost

logger = logging.getLogger(__name__)

@dashboard.route("/translate/to-persian", methods=["GET", "POST"])
@dashboard.route("/translate/to-persian/<id>", methods=["GET", "POST"])
@login_required
def translate_to_persian(id=None):
    form = TranslateForm()
    content = None
    translated_text = None
    user = current_user
    just_view = None
    if user.remain_charge < 0:
        flash('شارژ شما کافی نمیباشد. لطفا از قسمت افزایش اعتبار شارژ خود را افزایش دهید', 'error')
    if form.validate_on_submit():
        form_data = request.form.to_dict()

        llm_model = form_data['llm_model']
        form_data['user_topic'] = form_data['text_to_translate']
        form_data['system_title'] = form_data['text_to_translate']
        form_data['content_type'] = TEXT_TRANSLATION
        total_words = calculate_reduce_charge(len(form_data['text_to_translate'].split()), 'gpt-3.5-turbo')
        if user.remain_charge < total_words * 1.5:
            flash('شارژ شما کافی نمیباشد. لطفا از قسمت افزایش اعتبار شارژ خود را افزایش دهید')
            return redirect(url_for('finance.create_pay'))
        else:
            content = create_content(user_input=form_data, author=current_user, llm=llm_model)
            job = create_job_record(job_id=uuid.uuid4(), content=content)
            translated_text, usage = persian_translator(text=form_data['text_to_translate'], 
                                                        llm=llm_model)
            update_article_pro(content_id=content.id, body=translated_text)
            total_words = len(translated_text.split())
            content.body = translated_text
            form.body.data = translated_text
            content.word_count = total_words
            content.system_title = form_data['text_to_translate'][:100] + '...'
            job.job_status = 'SUCCESS'
            job.running_duration = 1
            db.session.add(content)
            db.session.add(job)
            db.session.commit()
            Charge.reduce_user_charge(user_id=user.id,
                                    total_words=total_words,
                                    model=llm_model,
                                    content_id=content.id)
            return jsonify({"translated_text": translated_text})


    if request.method == "GET" and id:
        logger.info('going to show translation file page')
        content = get_content_by_id(id)
        if not content and content.content_type != TEXT_TRANSLATION:
            return abort(404)
        form.body.data = content.body
        form.text_to_translate.data = content.get_input('text_to_translate')
        just_view = 'True'


    return render_template(
        "dashboard/translate/translate_to_persian.html", 
        form=form, 
        content=content, 
        translated_text=translated_text,
        just_view=just_view
    )


@dashboard.route("/translate/to-persian-file", methods=["GET", "POST"])
@dashboard.route("/translate/to-persian-file/<id>", methods=["GET", "POST"])
@login_required
def translate_to_persian_file(id=None):
    form = FileTranslateForm()
    user = current_user
    translated_data = None
    content=None
    if user.remain_charge < 0:
        flash('شارژ شما کافی نمیباشد. لطفا از قسمت افزایش اعتبار شارژ خود را افزایش دهید', 'error')
    if form.validate_on_submit():
        form_data = request.form.to_dict()
        
        # db.session.expunge(user)
        llm_model = form_data['llm_model']
        uploaded_file = request.files['file']
        
        filename = secure_filename(uploaded_file.filename)
        temp_path = os.path.join('./tmp/', filename)
        uploaded_file.save(temp_path)
        supported_file_formats = {
            'application/pdf': translate_file,
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': translate_file
        }
        estimated_cost_value = calculate_estimated_cost(temp_path, llm_model, file_type=uploaded_file.mimetype)
        if user.remain_charge < estimated_cost_value:
            flash('شارژ شما کافی نمیباشد. لطفا از قسمت افزایش اعتبار شارژ خود را افزایش دهید')
        else:
            form_data['body'] = filename
            form_data['user_topic'] = filename
            form_data['system_title'] = filename
            form_data['content_type'] = FILE_TRANSLATION
            form_data['file_path'] = temp_path
            form_data['mimetype'] = uploaded_file.mimetype.strip()
            if uploaded_file.mimetype.strip() in supported_file_formats:
                func = supported_file_formats[uploaded_file.mimetype.strip()]
                content = create_content(user_input=form_data, author=current_user, llm=llm_model)
                job = func.delay(content.id, form_data)
                create_job_record(job_id=job.id, content=content)
                # j_date = utils_gre2jalali(content.job.created_at)
                flash('فایل شما در حال ترجمه است ، چند دقیقه دیگر بررسی نمایید')
                return redirect(url_for('dashboard.index'))

    if request.method == "GET" and id:
        logger.info('going to show translation file page')
        content = get_content_by_id(id)
        translated_data = []
        if not content and content.content_type != FILE_TRANSLATION:
            return abort(404)
        content_files = ContentFile.get_files_for_content(content.id)
        if not content_files:
            flash('فایل‌ شما هنوز در حال ترجمه میباشد. لطفا کمی بعدتر این صفحه را به روز کنید')
        for cf in content_files:
            translated_data.append({
                'file_name': cf.file.file_name,
                'url': cf.file.get_file_url()
            })
            
        
        # translated_text = '\n\n'.join([txt[1] for txt in translated_texts])
    # print(translated_data)
    return render_template("dashboard/translate/translate_to_persian_file.html",
                           form=form, 
                           translated_data=translated_data,
                           content=content
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