from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy import or_
from .. import db, contents_collection
from app.models import Content, Job
from bson import ObjectId
import json, requests, os, random, time
from openai import OpenAI
from bs4 import BeautifulSoup
import re

API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_API = os.getenv("OPENROUTER_API")

# Initialize OpenAI and Redis clients
openai_client = OpenAI(base_url=OPENROUTER_API, api_key=API_KEY)


def suggest_outlines(user_title, lang, llm_type="gpt-4o"):

    user_prompt = f"The content language is {lang}\n"
    user_prompt += f"Use numbering for list. \n"
    random.seed(int(time.time()))
    rand = random.randint(4, 6)
    user_prompt += (
        f"Generate two detailed outline for a blog post on the following topic: {user_title}.\n"
        f"The outline should include an introduction, {rand} main headlines (h1) and 2 to 3 sub-headlines (h2), and a conclusion.\n"
        f"Ensure each section flows logically and covers the topic comprehensively.\n"
        f"Template:"
        f"<list>"
        f"<block>"
        f"<h1> .. </h1>"
        f"<h2> .. </h2>"
        f"<h2> .. </h2>"
        f"<h2> .. </h2>"
        f"</block>"
        f"<block>"
        f"<h1> .. </h1>"
        f"<h2> .. </h2>"
        f"<h2> .. </h2>"
        f"<h2> .. </h2>"
        f"</block>"
        f"...\n"
        f"</list>"
    )

    assistant_prompt = (
        f"You write SEO-optimized blog posts' titles. Ensure correct grammar.\n"
        f"Only return the outlines and h1 and h2 HTML tags.\n"
    )

    messages = [
        {"role": "assistant", "content": assistant_prompt},
        {"role": "user", "content": user_prompt},
    ]

    try:
        response = openai_client.chat.completions.create(
            model=llm_type, messages=messages, temperature=0.8
        )
        result = response.choices[0].message.content

        soup = BeautifulSoup(result, "html.parser")
        lists = []

        for list_tag in soup.find_all("list"):
            list_dict = []
            for block in list_tag.find_all("block"):
                for h1_tag in block.find_all("h1"):
                    h1 = h1_tag.get_text()
                h2_dict = []
                for h2_tag in block.find_all("h2"):
                    h2_dict.append(h2_tag.get_text())
                list_dict.append({"head": h1, "subs": h2_dict})

            lists.append(list_dict)

        return lists

    except Exception as e:
        print(f"Error calling OpenAI API: {str(e)}")
        return None


def suggest_titles(topic, lang, llm_type="gpt-4o"):
    user_prompt = (
        f"Generate 6 catchy and informative title for a blog post about {topic}. "
        f"The title should be engaging and appealing to the general audience and "
        f"should reflect a professional tone. The content language is {lang}\n"
    )
    assistant_prompt = (
        "You write SEO-optimized titles for articles. Ensure correct grammar. "
        "Only return the in <h1> tags.\n"
        "<h1> .. </h1>\n"
        "<h1> .. </h1>\n"
        "<h1> .. </h1>\n"
    )

    messages = [
        {"role": "assistant", "content": assistant_prompt},
        {"role": "user", "content": user_prompt},
    ]

    try:
        response = openai_client.chat.completions.create(
            model=llm_type, messages=messages, temperature=0.8
        )
        result = response.choices[0].message.content
        # print(result)
        soup = BeautifulSoup(result, "html.parser")
        headlines_elements = soup.find_all(["h1"])
        titles = []
        for headline_element in headlines_elements:
            headline_text = headline_element.get_text()
            titles.append(headline_text)
        print(titles)
        return titles
    except Exception as e:
        print(f"Error calling OpenAI API: {str(e)}")
        return None


def search_resources(topic):
    base_url = os.getenv("WEB_SEARCH_API")
    print(base_url)
    search = f"{base_url}?q={topic}&format=json"
    print(search)
    response = requests.get(search)
    result = json.loads(response.text)
    # print(_resp)
    return result["results"]


def get_user_contents(user, search_query="", sort_order="desc", page=1, per_page=5):
    query = Content.query.filter_by(author_id=user.id)

    if search_query:
        query = query.filter(Content.system_title.like(f"%{search_query}%"))

    if sort_order == "asc":
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
        body = user_input.get("body")
        contents_collection.update_one(
            {"_id": ObjectId(mongo_id)}, {"$set": {"body": body}}
        )

        # Update the SQL content instance
        content.user_input = json.dumps(user_input)
        content.content_type = user_input.get("content_type")
        content.system_title = user_input.get("system_title")

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
    body = user_input.get("body")
    # Store body in MongoDB
    result = contents_collection.insert_one({"body": body})
    mongo_id = str(result.inserted_id)

    content_type = user_input.get("content_type")

    # Create SQL content instance
    content = Content(
        user_input=json.dumps(user_input),
        author=author,
        mongo_id=mongo_id,
        content_type=content_type,
    )
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
