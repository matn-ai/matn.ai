from flask import render_template, jsonify, abort, request, url_for
from flask_login import login_required, current_user
from app.dashboard.forms import GenerateArticleBlog, GenerateArticle, GenerateArticlePro
from app.dashboard import dashboard
from ..tasks import generate_blog_simple, generate_pro_article, generate_general_article
from .repository import get_user_contents, create_content, create_job_record, get_job_by_cid, get_content_by_id, get_job_by_id, get_content_info
import json

@dashboard.route('/dashboard', methods=['GET'])
@login_required
def index():
    search_query = request.args.get('q', '')
    sort_order = request.args.get('sort', 'desc')
    page = request.args.get('page', 1, type=int)
    per_page = 8

    user_contents = get_user_contents(current_user, search_query, sort_order, page, per_page)
    next_url = url_for('dashboard.index', page=user_contents.next_num, q=search_query, sort=sort_order) if user_contents.has_next else None
    prev_url = url_for('dashboard.index', page=user_contents.prev_num, q=search_query, sort=sort_order) if user_contents.has_prev else None

    # Ensure the contents include the job_id attribute
    contents = []
    for content in user_contents.items:
        # job_id = content.job.id
        if content.job:
            # job_record = get_job_by_cid(content.job.id)
            contents.append({
                'id': content.id,
                'system_title': content.system_title,
                'user_topic': content.get_input('user_topic'),
                'word_count': content.word_count,
                'content_type': content.content_type,
                'timestamp': content.timestamp,
                'job_status': content.job.job_status,
                'job_id': content.job.job_id
            })

    return render_template('dashboard/main/index.html', contents=contents, next_url=next_url, prev_url=prev_url, search_query=search_query, sort_order=sort_order)


### BLOG

@dashboard.route('/dashboard/article', methods=['GET', 'POST'])
@dashboard.route('/dashboard/article/<id>', methods=['GET', 'POST'])
@login_required
def article(id=None):
    form = GenerateArticle()
    content = "false"
    if form.validate_on_submit():
        form_data = request.form.to_dict()
        content = create_content(user_input=form_data, author=current_user)
        
        job = generate_general_article.delay(content.id, form_data)
        create_job_record(job_id=job.id, content=content)

        return jsonify(job_id=job.id, content_id=content.id)

    if request.method == 'GET' and id:
        content = get_content_by_id(id)
        if not content:
            return abort(404)
        inputs = json.loads(content.user_input)
        form.user_topic.data = inputs["user_topic"]
        form.lang.data = inputs["lang"]
        form.tags.data = inputs["tags"]
        form.body.data = content.body
        
    return render_template('dashboard/article/article.html', form=form, content=content)

@dashboard.route('/dashboard/article/professional', methods=['GET', 'POST'])
@dashboard.route('/dashboard/article/professional/<id>', methods=['GET', 'POST'])
@login_required
def article_pro(id=None):
    form = GenerateArticlePro()
    if form.validate_on_submit():
        form_data = request.form.to_dict()
        content = create_content(user_input=form_data, author=current_user)
        
        job = generate_pro_article.delay(content.id, form_data)
        create_job_record(job_id=job.id, content=content)

        return jsonify(job_id=job.id, content_id=content.id)

    if request.method == 'GET' and id:
        print(id)
        content = get_content_by_id(id)
        if not content:
            return abort(404)
        inputs = json.loads(content.user_input)
        form.user_topic.data = inputs["user_topic"]
        form.lang.data = inputs["lang"]
        form.tags.data = inputs["tags"]
        form.body.data = content.body
        
    return render_template('dashboard/article/article_pro.html', form=form)

@dashboard.route('/dashboard/article/blog', methods=['GET', 'POST'])
@dashboard.route('/dashboard/article/blog/<id>', methods=['GET', 'POST'])
@login_required
def article_blog(id=None):
    
    form = GenerateArticleBlog()
    content = None
    if form.validate_on_submit():
        form_data = request.form.to_dict()
        content = create_content(user_input=form_data, author=current_user)
        
        job = generate_blog_simple.delay(content.id, form_data)
        create_job_record(job_id=job.id, content=content)

        return jsonify(job_id=job.id, content_id=content.id)

    if request.method == 'GET' and id:
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

    return render_template('dashboard/article/article_blog.html', form=form, content=content)


@dashboard.route('/dashboard/article/info/<content_id>', methods=['GET'])
@login_required
def article_info(content_id):
    info = get_content_info(content_id)
    if info:
        return jsonify({'info': info.get_info()})
    return abort(404)

@dashboard.route('/dashboard/article/blog/status/id/<job_id>', methods=['GET'])
@dashboard.route('/dashboard/article/blog/status/cid/<job_id>', methods=['GET'])
@login_required
def article_blog_status(job_id):
    job_cid = get_job_by_cid(job_id)
    job_id = get_job_by_id(job_id)
    if job_cid:
        return jsonify({'status': job_cid.job_status})
    elif job_id:
        return jsonify({'status': job_id.job_status})        
    return abort(404)

@dashboard.route('/dashboard/article/blog/list/<content_id>', methods=['GET'])
@login_required
def article_blog_content_list(content_id):
    content = get_content_by_id(content_id)
    return jsonify({'title': content.system_title, "count": content.word_count})



@dashboard.route('/dashboard/article/blog/content/<content_id>', methods=['GET'])
@login_required
def article_blog_content(content_id):
    content = get_content_by_id(content_id)
    return jsonify({'content': content.body})




### PRODUCT



@dashboard.route('/dashboard/product/product-description', methods=['GET', 'POST'])
@login_required
def product_describe():
    return render_template('dashboard/product/product_describe.html')

@dashboard.route('/dashboard/idea/brainstorming', methods=['GET', 'POST'])
@login_required
def idea_brainstorming():
    return render_template('dashboard/idea_brainstorming.html')



### TRANSLATE




@dashboard.route('/dashboard/translate/to-persian', methods=['GET', 'POST'])
@login_required
def translate_to_persian():
    return render_template('dashboard/translate/translate_to_persian.html')

@dashboard.route('/dashboard/translate/from-persian', methods=['GET', 'POST'])
@login_required
def translate_from_persian():
    return render_template('dashboard/translate/translate_from_persian.html')