from sqlalchemy.orm.exc import NoResultFound
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


def update_content(content_id, user_input):
    try:
        # Fetch the content from the SQL database
        content = Content.query.get_or_404(content_id)

        # Fetch the MongoDB document ID from the SQL database
        mongo_id = content.mongo_id

        # Update the MongoDB document
        body = user_input.get('body')
        contents_collection.update_one({'_id': ObjectId(mongo_id)}, {'$set': {'body': body}})

        # Update the SQL content instance
        content.user_input = json.dumps(user_input)
        content.content_type = user_input.get('content_type')
        content.system_title = user_input.get('system_title')

        # Commit the changes to the SQL database
        db.session.commit()

        return content

    except NoResultFound:
        raise ValueError("Content not found")
    except Exception as e:
        db.session.rollback()
        raise e


def create_content(user_input, author):
    # Extract body from user input
    body = user_input.get('body')
    # Store body in MongoDB
    result = contents_collection.insert_one({'body': body})
    mongo_id = str(result.inserted_id)

    content_type = user_input.get('content_type')
    
    # Create SQL content instance
    content = Content(user_input=json.dumps(user_input), author=author, mongo_id=mongo_id, content_type=content_type)
    db.session.add(content)
    db.session.commit()
    return content

def create_job_record(job_id, content):
    job_record = Job(job_status="PENDING", job_id=job_id, content=content)
    db.session.add(job_record)
    db.session.commit()
    return job_record

def get_job_by_id(id):
    return Job.query.filter_by(id=id).first()


def get_job_by_cid(job_id):
    return Job.query.filter_by(job_id=job_id).first()



def get_content_info(content_id):
    content = Content.query.get_or_404(content_id)
    return content

def get_content_by_id(content_id):
    content = Content.query.get_or_404(content_id)
    if content:
        body_doc = contents_collection.find_one({"_id": ObjectId(content.mongo_id)})
        content.body = body_doc["body"] if body_doc else None
    return content