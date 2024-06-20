from sqlalchemy import or_
from .. import db, contents_collection
from app.models import Content, Job
from bson import ObjectId

# def get_user_contents(current_user, search_query, sort_order, page, per_page):
#     sort_column = Content.timestamp.desc() if sort_order == 'desc' else Content.timestamp.asc()
#     return Content.query.filter(
#         Content.author_id == current_user.id,
#         or_(Content.body.like(f'%{search_query}%'), Content.body.like(f'%{search_query}%'))
#     ).order_by(sort_column).paginate(page, per_page, False)


def get_user_contents(user, search_query='', sort_order='desc', page=1, per_page=5):
    query = Content.query.filter_by(author_id=user.id)
    # Add search and sorting logic here
    return query.paginate(page, per_page, False)

def create_content(user_input, author):
    # Extract body from user input
    body = user_input.get('body')
    # Store body in MongoDB
    result = contents_collection.insert_one({'body': body})
    mongo_id = str(result.inserted_id)

    # Create SQL content instance
    content = Content(user_input=user_input, author=author, mongo_id=mongo_id)
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
    content = Content.query.get(content_id)
    if content:
        body_doc = contents_collection.find_one({"_id": ObjectId(content.mongo_id)})
        content.body = body_doc["body"] if body_doc else None
    return content