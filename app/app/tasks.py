import os, random, json, time
from datetime import datetime
from dotenv import load_dotenv

from bs4 import BeautifulSoup
from redis import StrictRedis
from openai import OpenAI
from flask import current_app

from . import app as flask_app, celery_app as celery, db, contents_collection
from .models import Content, Job

load_dotenv()


if os.getenv("DEBUG_OPENAI"):
    import logging

    loggers = [logging.getLogger(name) for name in logging.root.manager.loggerDict]
    openai_loggers = [logger for logger in loggers if logger.name.startswith("openai")]

    logging.getLogger("openai._base_client").setLevel(logging.DEBUG)

# Constants
REDIS_SERVER = os.getenv("REDIS_SERVER", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB = int(os.getenv("REDIS_DB", 0))
API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_API = os.getenv("OPENROUTER_API")

# Initialize OpenAI and Redis clients
openai_client = OpenAI(base_url=OPENROUTER_API, api_key=API_KEY)
redis_client = StrictRedis(host=REDIS_SERVER, port=REDIS_PORT, db=REDIS_DB)


def chat(llm_type, messages):
    # print(OPENROUTER_API)
    # print(API_KEY)
    try:
        response = openai_client.chat.completions.create(
            model=llm_type, messages=messages, temperature=0.8
        )
        result = response.choices[0].message.content
        return result
    except Exception as e:
        print(f"Error calling OpenAI API: {str(e)}")
        return None


def add_to_memory(role, content, list_key):
    message = {"role": role, "content": content}
    redis_client.rpush(list_key, json.dumps(message))


def get_conversation_history(list_key):
    items = redis_client.lrange(list_key, 0, -1)
    return [json.loads(item) for item in items]


def generate_title(user_title, lang, llm_type):
    user_prompt = (
        f"Generate a catchy and informative title for a blog post about {user_title}. "
        "The title should be engaging and appealing to the general audience and "
        "should reflect a professional tone. The content language is {lang}\n"
    )
    assistant_prompt = (
        "You write SEO-optimized titles for articles. Ensure correct grammar. "
        "Only return the title.\n"
    )

    messages = [
        {"role": "assistant", "content": assistant_prompt},
        {"role": "user", "content": user_prompt},
    ]
    return chat(llm_type, messages)



def generate_title_blog_post(user_title, lang, article_length, llm_type):
    user_prompt = f"The content language is {lang}\n"
    if article_length == "short":
        user_prompt += (
            f"Create an engaging ,optimized and seo-friendly title for a blog post related to {user_title}. "
            f"Ensure the title is compelling, accurately reflects the content, and incorporates relevant keywords to attract the target audience.\n"
            f"The title should be concise, attention-grabbing, and encourage readers to click and read the post.\n"
        )
    else:
        user_prompt += (
            f"Create a compelling and informative title for a blog post related to {user_title}. "
            f"Ensure the title is compelling, accurately reflects the content, and incorporates relevant keywords to attract the target audience.\n"
            f"The title should be concise, attention-grabbing, and encourage readers to click and read the post.\n"
        )
    user_prompt += f"Only return title. \n"

    assistant_prompt = (
        "You write SEO-optimized titles for articles. Ensure correct grammar. "
        "Only return the title.\n"
    )

    messages = [
        {"role": "assistant", "content": assistant_prompt},
        {"role": "user", "content": user_prompt},
    ]
    return chat(llm_type, messages)


def generate_outlines_blog_post(user_title, lang, article_length, llm_type):
    # print(article_length)
    # print("*"*10)
    user_prompt = f"The content language is {lang}\n"
    user_prompt += f"Use numbering for list. \n"
    if article_length == "long":
        random.seed(int(time.time()))
        rand = random.randint(13, 15)
        user_prompt += (
            f"Generate a detailed outline for a blog post on the following topic: {user_title}.\n"
            f"The outline should include an introduction, {rand} main headline and no sub headline , and a conclusion.\n"
            f"Ensure each section flows logically and covers the topic comprehensively.\n"
        )
    else:
        random.seed(int(time.time()))
        rand = random.randint(9, 13)
        user_prompt += (
            f"Generate a concise outline for a short blog post on the following topic: {user_title}\n"
            f"The outline should include an introduction, {rand} main headline and no sub headline , and a conclusion.\n"
            f"Ensure each section is relevant to the topic and provides essential information without unnecessary detail. \n"
        )

    assistant_prompt = (
        "You write SEO-optimized blog posts's title. Ensure correct grammar. "
        "Only return the outlines and in HTML ( h1, h2 , h3 , h4 ) tags.\n"
    )

    messages = [
        {"role": "assistant", "content": assistant_prompt},
        {"role": "user", "content": user_prompt},
    ]
    return chat(llm_type, messages)


def generate_outlines(user_title, lang, llm_type):
    user_prompt = (
        f"Create a comprehensive outline for a blog post about {user_title}. "
        "The outline should include a title, a clear introduction with a hook and overview, several main points with subpoints "
        "for each section, and a strong conclusion that summarizes the post and provides actionable advice or insights. "
        "Ensure the outline flows logically and is designed to engage and inform readers."
        f"The content language is {lang}\nUse numbering for list\n"
    )
    assistant_prompt = (
        "You write SEO-optimized blog posts. Ensure correct grammar. "
        "Only return the outlines and in HTML (h2 and h3).\n"
    )

    messages = [
        {"role": "assistant", "content": assistant_prompt},
        {"role": "user", "content": user_prompt},
    ]
    return chat(llm_type, messages)


def generate_blog_post_sections(
    headline_text, outlines, keywords, lang, length, llm_type
):
    if length == "short":
        prompt = (
            f"Write few paragraphs for the section titled '{headline_text}' of a blog post. \n"
            f"Write a section of a short blog post that provides practical tips for improving productivity.\n"
            f"The section should be engaging, informative, and concise, suitable for a broad audience. It should include actionable advice and real-life examples to illustrate the points.\n"
            f"You are writing part of an article with outlines: {outlines}\n"
            f"Do not include an introduction or conclusion. Focus exclusively on expanding and explaining '{headline_text}'. \n"
            f"The response should be formatted in HTML using <p> tags for each paragraph. Ensure that the writing is free from stereotypes. \n"
            f"Use correct grammar and maintain a professional tone suitable for the blog's target audience. \n"
        )
    else:
        prompt = (
            f"Write detailed paragraphs for the section titled '{headline_text}' of a blog post. \n"
            f"The content should be well-researched, engaging, and informative. \n"
            f"You are writing part of an article with outlines: {outlines}\n"
            f"Do not include an introduction or conclusion. Focus exclusively on expanding and explaining '{headline_text}'. \n"
            f"The response should be formatted in HTML using <p> tags for each paragraph. Ensure that the writing is free from stereotypes. \n"
            f"Use correct grammar and maintain a professional tone suitable for the blog's target audience.\n"
        )
        
    avoid_list = [
        "در نهایت",
        "به طوری کلی",
        "بنابراین",
        "همچنین",
    ]

    prompt += f"The content language is {lang}. \n"
    prompt += f"Ensure correct grammar. Return the result in HTML with only <p> tags."
    prompt += f"Avoid writing a paragraph or sentence related to the summary of the text or words like at the end or similar like below:\n"
    prompt += f"Avoid finish the paragraph with {' and '.join(avoid_list)}\n"
    prompt += f"\nDo not include the headline title again.\n"
    prompt += f"Like: <p> [text here] </p> <p> [text here] </p><p> [text here] </p>\n"
    
    #[{\"value\":\"\u06a9\u0627\u0634\u062a\u0646 \u0628\u0644\u0648\u0628\u0631\u06cc\"},{\"value\":\"\u062f\u0631\u062e\u062a\"},{\"value\":\"\u062a\u0631\"}]
    print(keywords)
    print(type(keywords))
    print("*"*90)
    if keywords:
        for item in keywords:
            item = str(item).replace("["," ")
            item = str(item).replace("]"," ")
            _keywords = json.loads(item.strip())
            prompt += f"Use the following keyword if relevant: {_keywords['value']}\n"

    assistant_prompt = (
        f"Your language is {lang}. You are an SEO-optimized blog post writer. "
        f"Ensure correct grammar. Return the result in HTML with <p> tags."
        f"Do not include the headline title again.\n"
    )

    messages = [
        {"role": "assistant", "content": assistant_prompt},
        {"role": "user", "content": prompt},
    ]

    return chat(llm_type, messages)

['[{"value":"کاشت درخت سیب"}', '{"value":"درخت آلبالو"}]']

def generate_sections(headline_text, outlines, keywords, lang, llm_type):
    prompt = (
        f"Write detailed paragraphs for the section titled '{headline_text}' of a blog post. "
        f"The content should be well-researched, engaging, and informative. "
        f"You are writing part of an article with outlines: {outlines}\n"
        f"Do not include an introduction or conclusion. Focus exclusively on expanding and explaining '{headline_text}'. "
        f"The response should be formatted in HTML using <p> tags for each paragraph. Ensure that the writing is free from stereotypes. "
        f"Use correct grammar and maintain a professional tone suitable for the blog's target audience. The content language is {lang}. "
    )

    if keywords:
        prompt += f"Use the following keywords where relevant: {', '.join(keywords)}\n"

    assistant_prompt = (
        f"Your language is {lang}. You are an SEO-optimized blog post writer. "
        f"Ensure correct grammar. Return the result in HTML with <p> tags. "
        f"Do not include the headline title again.\n"
    )

    messages = [
        {"role": "assistant", "content": assistant_prompt},
        {"role": "user", "content": prompt},
    ]

    return chat(llm_type, messages)


def generate_blog_post_body(title, outlines, keywords, lang, length, llm_type):
    soup = BeautifulSoup(outlines, "html.parser")
    headlines_elements = soup.find_all(["h2", "h3", "h4", "h5", "h6"])

    outlines_text = "\n".join(map(str, headlines_elements))
    toc = "".join(map(str, headlines_elements))

    inside = ""
    for headline_element in headlines_elements:
        headline_text = headline_element.get_text()
        inside += f"<br/>{str(headline_element)}"
        inside += generate_blog_post_sections(
            headline_text, outlines_text, keywords, lang, length, llm_type
        )

    return f"<h1>{title}</h1><br/>{inside}"


def generate_article_body(title, outlines, keywords, lang, llm_type):
    soup = BeautifulSoup(outlines, "html.parser")
    headlines_elements = soup.find_all(["h2", "h3", "h4", "h5", "h6"])

    outlines_text = "\n".join(map(str, headlines_elements))
    toc = "".join(map(str, headlines_elements))
    title = str(title).strip()

    inside = ""
    for headline_element in headlines_elements:
        headline_text = headline_element.get_text()
        inside += f"<br/>{str(headline_element)}"
        inside += generate_sections(
            headline_text, outlines_text, keywords, lang, llm_type
        )

    return f"<h1>{title}</h1><br/>{toc}<br/><hr/><br/>{inside}"




def save_article_to_db(content_id, body, title, outlines, content_length):
    with flask_app.app_context():
        body_document = {"body": body}
        mongo_result = contents_collection.insert_one(body_document)
        mongo_id = str(mongo_result.inserted_id)

        content = Content.query.get(content_id)
        if content:
            content.word_count = content_length
            content.mongo_id = mongo_id
            content.system_title = title
            content.outlines = outlines
            db.session.add(content)
            db.session.commit()

            return content.id
        return None


def update_job_status(task_id, status, duration=None):
    job = Job.query.filter_by(job_id=task_id).first()
    if job:
        job.job_status = status
        if duration:
            job.running_duration = (
                duration  # Assuming there is a `duration` field in the Job model
            )
        db.session.add(job)
        db.session.commit()


@celery.task
def generate_blog_simple(content_id, user_input):
    start_time = datetime.now()

    title = user_input["user_topic"]
    keywords = user_input["tags"].split(",")
    lang = "فارسی" if user_input["lang"] else "English"
    llm = "gpt-4o"
    article_length = user_input["article_length"]

    title = generate_title_blog_post(title, lang, article_length, llm)
    outlines = generate_outlines_blog_post(title, lang, article_length, llm)
    body = generate_blog_post_body(title, outlines, keywords, lang, article_length, llm)

    content_length = len(body.split())
    content_id = save_article_to_db(content_id, body, title, outlines, content_length)

    task_status = "SUCCESS" if content_id else "FAILURE"
    end_time = datetime.now()
    duration = end_time - start_time

    update_job_status(generate_blog_simple.request.id, task_status, duration.seconds)

    return content_id



@celery.task
def generate_pro_article(content_id, user_input):
    start_time = datetime.now()

    title = user_input["user_topic"]
    keywords = user_input["tags"].split(",")
    lang = "فارسی" if user_input["lang"] else "English"
    llm = "gpt-4o"

    title = generate_title(title, lang, llm)
    outlines = generate_outlines(title, lang, llm)
    body = generate_article_body(title, outlines, keywords, lang, llm)

    content_length = len(body.split())
    content_id = save_article_to_db(content_id, body, title, outlines, content_length)

    task_status = "SUCCESS" if content_id else "FAILURE"
    end_time = datetime.now()
    duration = end_time - start_time
    update_job_status(generate_pro_article.request.id, task_status, duration.seconds)

    return content_id
