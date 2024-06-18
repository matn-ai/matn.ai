from flask import render_template, jsonify, abort, request, url_for
from flask_login import login_required, current_user
from sqlalchemy import or_
from app.dashboard.forms import GenerateArticleBlog
from app.dashboard import dashboard
from ..tasks import generate_blog_simple
from .. import db
from app.models import Content, Job

@dashboard.route('/dashboard', methods=['GET'])
@login_required
def index():
    # Get the search query
    search_query = request.args.get('q', '')

    # Get the sort order
    sort_order = request.args.get('sort', 'desc')
    sort_column = Content.timestamp.desc() if sort_order == 'desc' else Content.timestamp.asc()

    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = 5  # Number of items per page

    # Filter contents by current user, search query, and order by sort_column
    user_contents = Content.query.filter(
        Content.author_id == current_user.id,
        or_(Content.body.like(f'%{search_query}%'), Content.body_html.like(f'%{search_query}%'))
    ).order_by(sort_column).paginate(page, per_page, False)

    next_url = url_for('dashboard.index', page=user_contents.next_num, q=search_query, sort=sort_order) if user_contents.has_next else None
    prev_url = url_for('dashboard.index', page=user_contents.prev_num, q=search_query, sort=sort_order) if user_contents.has_prev else None

    return render_template('dashboard/dashboard.html', contents=user_contents.items, next_url=next_url, prev_url=prev_url, search_query=search_query, sort_order=sort_order)


@dashboard.route('/dashboard/article', methods=['GET', 'POST'])
@login_required
def article():
    return render_template('dashboard/article/article.html')

@dashboard.route('/dashboard/article/professional', methods=['GET', 'POST'])
@login_required
def article_pro():
    return render_template('dashboard/article/article_pro.html')

@dashboard.route('/dashboard/article/blog', methods=['GET', 'POST'])
@login_required
def article_blog():
    form = GenerateArticleBlog()
    if form.validate_on_submit():
        form_data = request.form.to_dict()
        # Create a new Content record
        print(form_data)
        content = Content(user_input=str(form_data), author=current_user)
        db.session.add(content)
        db.session.commit()
        
        # Start the Celery job with the Content ID
        job = generate_blog_simple.delay(content.id, form_data)
        
        # Create a new Job record
        job_record = Job(job_status="PENDING", job_id=job.id, content=content)
        db.session.add(job_record)
        db.session.commit()
        
        return f"<div id='loading' style='text-align:center'>Loading...<input type='hidden' id='job-id' value='{job.id}'/><input type='hidden' id='content-id' value='{content.id}'/></div>"
    return render_template('dashboard/article/article_blog.html', form=form)

# Endpoint to check job status
@dashboard.route('/dashboard/article/blog/status/<job_id>', methods=['GET'])
@login_required
def article_blog_status(job_id):
    job = Job.query.filter_by(job_id=job_id).first()
    if job:
        return jsonify({'status': job.job_status})
    return abort(404)

# Endpoint to get generated content
@dashboard.route('/dashboard/article/blog/content/<content_id>', methods=['GET'])
@login_required
def article_blog_content(content_id):
    content = Content.query.get_or_404(content_id)
    return jsonify({'content': content.body})

@dashboard.route('/dashboard/product/product-description', methods=['GET', 'POST'])
@login_required
def product_describe():
    return render_template('dashboard/product/product_describe.html')

@dashboard.route('/dashboard/idea/brainstorming', methods=['GET', 'POST'])
@login_required
def idea_brainstorming():
    return render_template('dashboard/idea_brainstorming.html')

@dashboard.route('/dashboard/translate/to-persian', methods=['GET', 'POST'])
@login_required
def translate_to_persian():
    return render_template('dashboard/translate/translate_to_persian.html')

@dashboard.route('/dashboard/translate/from-persian', methods=['GET', 'POST'])
@login_required
def translate_from_persian():
    return render_template('dashboard/translate/translate_from_persian.html')