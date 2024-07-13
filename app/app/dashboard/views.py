from flask import render_template, jsonify, abort, request, url_for, send_file
from werkzeug.utils import secure_filename
from flask_login import login_required, current_user
from app.dashboard.forms import GenerateArticleBlog, GenerateArticlePro, ChatForm
from app.dashboard import dashboard
from ..tasks import generate_blog_simple, generate_pro_article
from .repository import (
    get_user_contents,
    create_content,
    create_job_record,
    get_job_by_cid,
    get_content_by_id,
    get_job_by_id,
    get_content_info,
    search_resources,
    suggest_outline_images,
    suggest_titles,
    suggest_outlines,
    delete_article_pro,
    update_article_pro,
    html_to_docx,
    get_search_images
)
import json, os
import uuid
from ..utils import utils_gre2jalali
from .. import app
from ..tasks import chat
from .chat import do_chat, forget_conversation
from ..translator.views import *


@dashboard.route("/forget_conversation", methods=["GET"])
@login_required
def forget_chat():
    user = current_user
    forget_conversation(user)        
    flash('مکالمه از نو بارگزاری شد...')
    return redirect(url_for('dashboard.chat'))
    
    
@dashboard.route("/chat", methods=["GET", "POST"])
@login_required
def chat():
    user = current_user
    session_id = f"chat_session_{user.id}"
    if current_user.remain_charge < 0:
        flash('شارژ شما کافی نمیباشد. لطفا از قسمت افزایش اعتبار شارژ خود را افزایش دهید', 'error')
        return redirect(url_for('finance.create_pay'))

    if request.method == "POST":
        form_data = request.json  # Receive JSON data
        logger.info(f"Received chat request data: {form_data}")

        llm_model = form_data.get('llm_model')
        _request = form_data.get('message')

        if current_user.remain_charge < 0:
            flash('شارژ شما کافی نمیباشد. لطفا از قسمت افزایش اعتبار شارژ خود را افزایش دهید', 'error')
            return jsonify({"error": "No creadit provided"}), 200

        
        if not _request:
            return jsonify({"error": "No message provided"}), 400

        try:
            answer = do_chat(_request, llm_model, session_id)
            total_words = len(str(answer).split())

            Charge.reduce_user_charge(user_id=user.id, total_words=total_words, model=llm_model)
            
            return jsonify({"answer": answer})
        except Exception as e:
            logger.error(f"Error during chat processing: {e}")
            return jsonify({"error": str(e)}), 500

    return render_template("dashboard/chat.html", form=ChatForm(), content=None)


@dashboard.route("/", methods=["GET"])
@login_required
def index():
    if current_user.remain_charge < 0:
        flash('شارژ شما کافی نمیباشد. لطفا از قسمت افزایش اعتبار شارژ خود را افزایش دهید' , 'error')
        return redirect(url_for('finance.create_pay'))
 

    search_query = request.args.get("q", "")
    sort_order = request.args.get("sort", "desc")
    page = request.args.get("page", 1, type=int)
    per_page = 8
    logger.info(f"User {current_user.id} requested dashboard index with query '{search_query}' and sort order '{sort_order}' on page '{page}'.")

    user_contents = get_user_contents(
        current_user, search_query, sort_order, page, per_page
    )
    next_url = (
        url_for(
            "dashboard.index",
            page=user_contents.next_num,
            q=search_query,
            sort=sort_order,
        )
        if user_contents.has_next
        else None
    )
    prev_url = (
        url_for(
            "dashboard.index",
            page=user_contents.prev_num,
            q=search_query,
            sort=sort_order,
        )
        if user_contents.has_prev
        else None
    )

    contents = []
    for content in user_contents.items:
        if content.job:
            contents.append(
                {
                    "id": content.id,
                    "system_title": content.system_title,
                    "user_topic": content.get_input("user_topic"),
                    "word_count": content.word_count,
                    "content_type": content.content_type,
                    "timestamp": content.timestamp,
                    "job_status": content.job.job_status,
                    "job_id": content.job.job_id,
                }
            )

    logger.info(f"User {current_user.id} loaded {len(contents)} contents.")
    
    return render_template(
        "dashboard/main/index.html",
        contents=contents,
        next_url=next_url,
        prev_url=prev_url,
        search_query=search_query,
        sort_order=sort_order,
    )

@dashboard.route("/article/blog", methods=["GET", "POST"])
@dashboard.route("/article/blog/<id>", methods=["GET", "POST"])
@login_required
def article_blog(id=None):
    form = GenerateArticleBlog()
    content = None
    not_enough_charge = False

    if current_user.remain_charge < 0:
        flash('شارژ شما کافی نمیباشد. لطفا از قسمت افزایش اعتبار شارژ خود را افزایش دهید', 'error')
        not_enough_charge = True
        return redirect(url_for('finance.create_pay'))

    if current_user.remain_charge < 3000:
        flash('شارژ شما کافی نمیباشد. لطفا از قسمت افزایش اعتبار شارژ خود را افزایش دهید', 'error')


    if form.validate_on_submit() and not not_enough_charge:
        form_data = request.form.to_dict()
        total_words = 600 if form_data['article_length'] == 'short' else 1300
        if current_user.remain_charge < total_words:
            flash('شارژ شما کافی نمیباشد. لطفا از قسمت افزایش اعتبار شارژ خود را افزایش دهید')
            return redirect(url_for('finance.create_pay'))
        else:
            content = create_content(user_input=form_data, author=current_user)
            job = generate_blog_simple.delay(content.id, form_data)
            create_job_record(job_id=job.id, content=content)
            j_date = utils_gre2jalali(content.job.created_at)

            logger.info(f"User {current_user.id} created new blog article with content ID {content.id} and job ID {job.id}.")

            return jsonify(job_id=job.id, content_id=content.id, job_date=j_date)

    if request.method == "GET" and id:
        content = get_content_by_id(id)
        if not content:
            logger.warning(f"User {current_user.id} tried to access non-existing content ID {id}.")
            return abort(404)
        inputs = json.loads(content.user_input)
        form.user_topic.data = inputs["user_topic"]
        form.lang.data = inputs["lang"]
        form.tags.data = inputs["tags"]
        form.article_length.data = inputs["article_length"]
        form.content_type.data = inputs["content_type"]
        form.body.data = content.body

        logger.info(f"User {current_user.id} accessed blog article with content ID {id}.")

    return render_template(
        "dashboard/article/article_blog.html", form=form, content=content, not_enough_charge=not_enough_charge
    )

@dashboard.route("/article/pro/create", methods=["POST"])
@login_required
def create_article_pro():
    if current_user.remain_charge < 0:
        flash('شارژ شما کافی نمیباشد. لطفا از قسمت افزایش اعتبار شارژ خود را افزایش دهید', 'error')
        # return redirect(url_for('finance.create_pay'))

    try:
        data = request.data
        article_data = json.loads(data)
        
        content = create_content(user_input=article_data, author=current_user)
        job = generate_pro_article.delay(content.id, article_data)
        create_job_record(job_id=job.id, content=content)
        j_date = utils_gre2jalali(content.job.created_at)

        logger.info(f"User {current_user.id} created new pro article with content ID {content.id} and job ID {job.id}.")

        return jsonify(job_id=job.id, content_id=content.id, job_date=j_date)
    except Exception as e:
        logger.error(f"Error in create_article_pro route for user {current_user.id}: {e}")
        return abort(500)

@dashboard.route("/article/pro", methods=["GET", "POST"])
@login_required
def article_pro():
    try:
        if current_user.remain_charge < 0:
            flash('شارژ شما کافی نمیباشد. لطفا از قسمت افزایش اعتبار شارژ خود را افزایش دهید', 'error')
            return redirect(url_for('finance.create_pay'))

        form = GenerateArticlePro()

        logger.info(f"User {current_user.id} accessed pro article creation form.")

        return render_template("dashboard/article/article_pro.html", form=form)
    except Exception as e:
        logger.error(f"Error in article_pro route for user {current_user.id}: {e}")
        return abort(500)

@dashboard.route("/article/pro/update/<content_id>", methods=["POST", "PUT"])
@login_required
def update_article_pro_route(content_id):
    data = request.get_json()
    update_article_pro(content_id, data['body'])

    logger.info(f"User {current_user.id} updated pro article with content ID {content_id}.")

    return jsonify({"message": "Article updated successfully"}), 200

@dashboard.route('/article/get_docx', methods=['POST'])
def get_docx():
    try:
        data = request.get_json()
        print("*"*100)
        print(data)
        content = get_content_by_id(data['content_id'])
        docx_buffer = html_to_docx(content.body)

        logger.info(f"User {current_user.id} requested DOCX conversion for content ID {data['content_id']}.")

        return send_file(
            docx_buffer,
            as_attachment=True,
            download_name='converted.docx',
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )
    except Exception as e:
        logger.error(f"Error in get_docx route: {e}")
        return abort(500)

@dashboard.route("/article/delete/<content_id>", methods=["DELETE"])
@login_required
def delete_article_pro_route(content_id):
    try:
        delete_article_pro(content_id)

        logger.info(f"User {current_user.id} deleted pro article with content ID {content_id}.")

        return jsonify({"message": "Article deleted successfully"}), 200
    except Exception as e:
        logger.error(f"Error in delete_article_pro_route for content ID {content_id}: {e}")
        return jsonify({"error": str(e)}), 400

@dashboard.route("/article/pro/<id>", methods=["GET", "POST"])
@login_required
def article_pro_View(id=None):
    content = get_content_by_id(id)

    if not content:
        logger.warning(f"User {current_user.id} tried to access non-existing pro article content ID {id}.")
        return abort(404)
    
    logger.info(f"User {current_user.id} accessed pro article with content ID {id}.")

    return render_template("dashboard/article/article_pro_view.html", content=content)

# ALLOWED_EXTENSIONS and MAX_FILE_SIZE remain unchanged.
ALLOWED_EXTENSIONS = {'pdf'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@dashboard.route("/article/resources/upload", methods=["POST"])
def upload_resource():
    if 'file' not in request.files:
        logger.warning(f"User {current_user.id} attempted file upload without file.")
        return jsonify({'error': 'لطفا یک فایل انتخاب کنید'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        logger.warning(f"User {current_user.id} attempted file upload with empty filename.")
        return jsonify({'error': 'لطفا یک فایل انتخاب کنید'}), 400
    
    if file and allowed_file(file.filename):
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        if file_size > MAX_FILE_SIZE:
            logger.warning(f"User {current_user.id} attempted file upload exceeding max size: {file_size} bytes.")
            return jsonify({'error': 'حجم فایل بیش از حد مجاز است'}), 400
        
        filename = secure_filename(file.filename)
        unique_filename = f"{uuid.uuid4().hex}_{filename}"
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(filepath)
        mime = file.mimetype.strip()
        
        file_obj = File.upload_file(
            local_file_path=filepath,
            bucket='local',
            file_name=filepath.split('/')[-1]
        )
        

        logger.info(f"User {current_user.id} successfully uploaded file {filename} as {unique_filename}.")

        return jsonify({'url': file_obj.get_file_url(), 'type': mime, 'file_id': file_obj.id}), 200
    
    logger.warning(f"Unallowed file format uploaded by user {current_user.id}.")
    return jsonify({'error': 'فرمت فایل مجاز نیست'}), 400


@dashboard.route("/article/resources", methods=["POST"])
@login_required
def get_resources():
    try:
        data = request.data
        topic = json.loads(data)
        resources = search_resources(topic['main_topic'])

        logger.info(f"User {current_user.id} requested resource search for topic: {topic['main_topic']}.")

        return jsonify(resources)
    except Exception as e:
        logger.error(f"Error in get_resources route for user {current_user.id}: {e}")
        return abort(500)
    
    
@dashboard.route("/article/images", methods=["POST"])
@login_required
def get_images():
    data = request.data
    input = json.loads(data)
    result = suggest_outline_images(input['title'])

    logger.info(f"User {current_user.id} requested resource.")

    return jsonify(result)


@dashboard.route("/article//search/images", methods=["POST"])
@login_required
def search_images():
    data = request.data
    input = json.loads(data)
    result = get_search_images(input['title'], 20)

    logger.info(f"User {current_user.id} requested resource.")

    return jsonify(result)

@dashboard.route("/article/get_titles", methods=["POST"])
@login_required
def get_titles():
    try:
        data = request.data
        topic = json.loads(data)
        resources = suggest_titles(topic['user_topic'], topic['lang'], topic['language_model'])

        logger.info(f"User {current_user.id} requested title suggestions for topic: {topic['user_topic']}.")

        return jsonify(resources)
    except Exception as e:
        logger.error(f"Error in get_titles route for user {current_user.id}: {e}")
        return abort(500)

@dashboard.route("/article/get_outlines", methods=["POST"])
@login_required
def get_outlines():
    try:
        data = request.data
        topic = json.loads(data)
        print(topic)
        resources = suggest_outlines(topic['selected_title'], topic['lang'], topic['language_model'])

        logger.info(f"User {current_user.id} requested outline suggestions for selected title: {topic['selected_title']}.")

        return jsonify(resources)
    except Exception as e:
        logger.error(f"Error in get_outlines route for user {current_user.id}: {e}")
        return abort(500)

@dashboard.route("/article/info/<content_id>", methods=["GET"])
@login_required
def article_info(content_id):
    try:
        info = get_content_info(content_id)
        if info:
            logger.info(f"User {current_user.id} requested info for content ID {content_id}.")
            return jsonify({"info": info.get_info()})
        logger.warning(f"User {current_user.id} tried to access non-existing content info ID {content_id}.")
        return abort(404)
    except Exception as e:
        logger.error(f"Error in article_info route for content ID {content_id}: {e}")
        return abort(500)

@dashboard.route("/article/status/id/<job_id>", methods=["GET"])
@dashboard.route("/article/status/cid/<job_id>", methods=["GET"])
@login_required
def content_status(job_id):
    try:
        job_cid = get_job_by_cid(job_id)
        job_id = get_job_by_id(job_id)
        
        if job_cid:
            logger.info(f"User {current_user.id} requested blog job status (CID) for job ID {job_id}: {job_cid.job_status}.")
            if job_cid.job_status == "SUCCESS":
                return jsonify(
                    {"status": job_cid.job_status, "running_duration": job_cid.running_duration}
                )
            else:
                return jsonify(
                    {"status": job_cid.job_status}
                )
        elif job_id:
            logger.info(f"User {current_user.id} requested blog job status (ID) for job ID {job_id}: {job_id.job_status}.")
            if job_id.job_status == "SUCCESS":
                return jsonify(
                    {"status": job_id.job_status, "running_duration": job_id.running_duration}
                )
            else:
                return jsonify(
                    {"status": job_id.job_status}
                )
        logger.warning(f"User {current_user.id} requested non-existing blog job status for job ID {job_id}.")
        return abort(404)
    except Exception as e:
        logger.error(f"Error in content_status route for job ID {job_id}: {e}")
        return abort(500)

@dashboard.route("/article/blog/list/<content_id>", methods=["GET"])
@login_required
def article_blog_content_list(content_id):
    try:
        content = get_content_by_id(content_id)
        logger.info(f"User {current_user.id} requested blog content list for content ID {content_id}.")
        return jsonify({"title": content.system_title, "count": content.word_count})
    except Exception as e:
        logger.error(f"Error in article_blog_content_list route for content ID {content_id}: {e}")
        return abort(500)


@dashboard.route("/article/content/<content_id>", methods=["GET"])
@login_required
def get_content_data(content_id):
    # try:
    content = get_content_by_id(content_id)
    # print(content)
    # logger.info(f"User {current_user.id} requested blog content for content ID {content_id}.")
    return jsonify(content)
    # except Exception as e:
    #     logger.error(f"Error in article_blog_content route for content ID {content_id}: {e}")
    #     return abort(500)


@dashboard.route("/article/blog/content/<content_id>", methods=["GET"])
@login_required
def article_blog_content(content_id):
    try:
        content = get_content_by_id(content_id)
        print(content)
        logger.info(f"User {current_user.id} requested blog content for content ID {content_id}.")
        return jsonify({"content": content.body})
    except Exception as e:
        logger.error(f"Error in article_blog_content route for content ID {content_id}: {e}")
        return abort(500)

### PRODUCT

@dashboard.route("/product/product-description", methods=["GET", "POST"])
@login_required
def product_describe():
    try:
        logger.info(f"User {current_user.id} accessed product description.")
        return render_template("dashboard/product/product_describe.html")
    except Exception as e:
        logger.error(f"Error in product_describe route for user {current_user.id}: {e}")
        return abort(500)

@dashboard.route("/idea/brainstorming", methods=["GET", "POST"])
@login_required
def idea_brainstorming():
    try:
        logger.info(f"User {current_user.id} accessed idea brainstorming.")
        return render_template("dashboard/idea_brainstorming.html")
    except Exception as e:
        logger.error(f"Error in idea_brainstorming route for user {current_user.id}: {e}")
        return abort(500)

### TRANSLATE


# @dashboard.route("/translate/to-persian", methods=["GET", "POST"])
# @login_required
# def translate_to_persian():
#     return render_template("dashboard/translate/translate_to_persian.html")


# @dashboard.route("/translate/from-persian", methods=["GET", "POST"])
# @login_required
# def translate_from_persian():
#     return render_template("dashboard/translate/translate_from_persian.html")
