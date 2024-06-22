from sqlalchemy import or_
from .. import db, contents_collection
from app.models import Content, Job
from bson import ObjectId
import json

def get_user_contents(user, search_query='', sort_order='desc', page=1, per_page=5):
    query = Content.query.filter_by(author_id=user.id)
    
    if search_query:
        query = query.filter(Content.system_title.like(f'%{search_query}%'))
    
    if sort_order == 'asc':
        query = query.order_by(Content.timestamp.asc())
    else:
        query = query.order_by(Content.timestamp.desc())
    
    return query.paginate(page, per_page, False)



def create_content(user_input, author):
    # Extract body from user input
    body = user_input.get('body')
    # Store body in MongoDB
    result = contents_collection.insert_one({'body': body})
    mongo_id = str(result.inserted_id)

    
    # Create SQL content instance
    content = Content(user_input=json.dumps(user_input), author=author, mongo_id=mongo_id)
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
    content = Content.query.get_or_404(content_id)
    if content:
        body_doc = contents_collection.find_one({"_id": ObjectId(content.mongo_id)})
        content.body = body_doc["body"] if body_doc else None
    return content