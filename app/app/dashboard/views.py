from flask import render_template, jsonify, abort, request, url_for
from flask_login import login_required, current_user
from app.dashboard.forms import GenerateArticleBlog, GenerateArticlePro
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
    suggest_titles,
    suggest_outlines
)
import json, os
from ..utils import utils_gre2jalali
from .. import app


@dashboard.route("/", methods=["GET"])
@login_required
def index():
    search_query = request.args.get("q", "")
    sort_order = request.args.get("sort", "desc")
    page = request.args.get("page", 1, type=int)
    per_page = 8

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

    # Ensure the contents include the job_id attribute
    contents = []
    for content in user_contents.items:
        # job_id = content.job.id
        if content.job:
            # job_record = get_job_by_cid(content.job.id)
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
    if form.validate_on_submit():
        form_data = request.form.to_dict()
        content = create_content(user_input=form_data, author=current_user)

        job = generate_blog_simple.delay(content.id, form_data)
        create_job_record(job_id=job.id, content=content)
        j_date = utils_gre2jalali(content.job.created_at)

        return jsonify(job_id=job.id, content_id=content.id, job_date=j_date)

    if request.method == "GET" and id:
        # print(id)
        content = get_content_by_id(id)
        if not content:
            return abort(404)
        inputs = json.loads(content.user_input)
        form.user_topic.data = inputs["user_topic"]
        form.lang.data = inputs["lang"]
        form.tags.data = inputs["tags"]
        form.article_length.data = inputs["article_length"]
        form.content_type.data = inputs["content_type"]
        form.body.data = content.body

    return render_template(
        "dashboard/article/article_blog.html", form=form, content=content
    )


@dashboard.route("/article/professional", methods=["GET", "POST"])
@dashboard.route("/article/professional/<id>", methods=["GET", "POST"])
@login_required
def article_pro(id=None):
    form = GenerateArticlePro()
    if form.validate_on_submit():
        form_data = request.form.to_dict()
        content = create_content(user_input=form_data, author=current_user)

        job = generate_pro_article.delay(content.id, form_data)
        create_job_record(job_id=job.id, content=content)

        return jsonify(job_id=job.id, content_id=content.id)

    if request.method == "GET" and id:
        # print(id)
        content = get_content_by_id(id)
        if not content:
            return abort(404)
        inputs = json.loads(content.user_input)
        form.user_topic.data = inputs["user_topic"]
        form.lang.data = inputs["lang"]
        form.tags.data = inputs["tags"]
        form.body.data = content.body

    return render_template("dashboard/article/article_pro.html", form=form)

@dashboard.route("/article/resources/upload", methods=["POST"])
def upload_resource():
    if 'file' not in request.files:
        return jsonify({'error': 'لطفا یک فایل انتخاب کنید'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'لطفا یک فایل انتخاب کنید'}), 400
    if file:
        filename = file.filename
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        return jsonify({'filename': filename, 'url': filepath}), 200



@dashboard.route("/article/resources", methods=["POST"])
@login_required
def get_resources():
    data = request.data
    topic = json.loads(data)
    # topic = data['user_topic']
    # print (topic)
    resources = search_resources(topic['user_topic'])
    return jsonify(resources)


@dashboard.route("/article/get_titles", methods=["POST"])
@login_required
def get_titles():
    data = request.data
    topic = json.loads(data)
    # topic = data['user_topic']
    # print (topic)
    resources = suggest_titles(topic['user_topic'], 'persian')
    return jsonify(resources)


@dashboard.route("/article/get_outlines", methods=["POST"])
@login_required
def get_outlines():
    data = request.data
    topic = json.loads(data)
    # topic = data['user_topic']
    # print (topic)
    resources = suggest_outlines(topic['user_topic'])
    return jsonify(resources)



@dashboard.route("/article/info/<content_id>", methods=["GET"])
@login_required
def article_info(content_id):
    info = get_content_info(content_id)
    if info:
        return jsonify({"info": info.get_info()})
    return abort(404)


@dashboard.route("/article/blog/status/id/<job_id>", methods=["GET"])
@dashboard.route("/article/blog/status/cid/<job_id>", methods=["GET"])
@login_required
def article_blog_status(job_id):
    job_cid = get_job_by_cid(job_id)
    job_id = get_job_by_id(job_id)
    
    if job_cid:
        if job_cid.job_status == "SUCCESS":
            return jsonify(
                {"status": job_cid.job_status, "running_duration": job_cid.running_duration}
            )
        else:
            return jsonify(
                {"status": job_cid.job_status}
            )
    elif job_id:
        if job_id.job_status == "SUCCESS":
            return jsonify(
                {"status": job_id.job_status, "running_duration": job_id.running_duration}
            )
        else:
            return jsonify(
                {"status": job_id.job_status}
            )
    return abort(404)


@dashboard.route("/article/blog/list/<content_id>", methods=["GET"])
@login_required
def article_blog_content_list(content_id):
    content = get_content_by_id(content_id)
    return jsonify({"title": content.system_title, "count": content.word_count})


@dashboard.route("/article/blog/content/<content_id>", methods=["GET"])
@login_required
def article_blog_content(content_id):
    content = get_content_by_id(content_id)
    return jsonify({"content": content.body})


### PRODUCT


@dashboard.route("/product/product-description", methods=["GET", "POST"])
@login_required
def product_describe():
    return render_template("dashboard/product/product_describe.html")


@dashboard.route("/idea/brainstorming", methods=["GET", "POST"])
@login_required
def idea_brainstorming():
    return render_template("dashboard/idea_brainstorming.html")


### TRANSLATE


@dashboard.route("/translate/to-persian", methods=["GET", "POST"])
@login_required
def translate_to_persian():
    return render_template("dashboard/translate/translate_to_persian.html")


@dashboard.route("/translate/from-persian", methods=["GET", "POST"])
@login_required
def translate_from_persian():
    return render_template("dashboard/translate/translate_from_persian.html")
