from sqlalchemy import or_
from .. import db
from app.models import Content, Job

def get_user_contents(current_user, search_query, sort_order, page, per_page):
    sort_column = Content.timestamp.desc() if sort_order == 'desc' else Content.timestamp.asc()
    return Content.query.filter(
        Content.author_id == current_user.id,
        or_(Content.body.like(f'%{search_query}%'), Content.body.like(f'%{search_query}%'))
    ).order_by(sort_column).paginate(page, per_page, False)

def create_content(user_input, author):
    content = Content(user_input=str(user_input), author=author)
    db.session.add(content)
    db.session.commit()
    return content

def create_job_record(job_id, content):
    job_record = Job(job_status="PENDING", job_id=job_id, content=content)
    db.session.add(job_record)
    db.session.commit()
    return job_record

def get_job_by_id(job_id):
    return Job.query.filter_by(job_id=job_id).first()

def get_content_by_id(content_id):
    return Content.query.get_or_404(content_id)