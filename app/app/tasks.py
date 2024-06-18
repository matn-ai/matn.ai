import json
import random
import time
import uuid
from flask import Flask
from celery import shared_task
from sqlalchemy.orm import sessionmaker
from bs4 import BeautifulSoup
from redis import StrictRedis
from openai import OpenAI
from os import getenv
from . import app as flask_app 
from . import celery_app as celery
from . import db
from .models import Content, Job
# from . import celery_app as celery_app

# Initialize the OpenAI client
# client = OpenAI(api_key="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")
client = OpenAI(
  base_url="https://api.tosiehgar.ir/v1/",
  api_key=getenv("OPENROUTER_API_KEY"))


# Initialize Redis client
redis_client = StrictRedis(host="localhost", port=6379, db=0)

# Functions for OpenAI interactions
def chat(llm_type, messages):
    response = client.chat.completions.create(
        model=llm_type, messages=messages, temperature=0.8
    )
    result = response.choices[0].message.content
    return result

def add_to_memory(role, content, list_key, llm_type):
    message = {"role": role, "content": content}
    redis_client.rpush(list_key, json.dumps(message))

def get_conversation_history(list_key):
    messages = []
    for item in redis_client.lrange(list_key, 0, -1):
        messages.append(json.loads(item))
    return messages

def generate_title(user_title, lang, llm_type = ''):
    templates = [
        "How to ...",
        "The secret to ...",
        "There are [Number] things ...",
        "[Number] Things Every ... Should Include",
        "Top [Number] [Things/Tools/Strategies] for [Achieving a Goal]",
        "What Is [Topic]? [Number] Things You Should Know",
        "Why [Topic] Matters: [Number] Reasons You Should Care",
        "[Number] Myths About [Topic] Debunked",
        "Truth About [Topic]: [Number] Myths Busted",
        "The Definitive List of Pros and Cons for [Topic]",
        "Why [Topic] is Important for [Audience]",
        "How to Improve Your [Skill/Knowledge] in [Topic]",
        "The Impact of [Topic] on [Industry/Society]",
        "Common Mistakes to Avoid in [Topic]",
        "[Number] Tips for Success in [Topic]",
        "The Future of [Topic]: Trends to Watch",
        "How [Topic] is Changing the [Industry]",
        "[Number] Essential Tools for [Topic]",
        "How to Master [Topic]",
        "4 Big Mistakes to Avoid in [Topic]",
        "The Pros and Cons of [Topic]: What You Need to Know",
        "[Number] Pros and Cons of [Topic] Explained",
        "Pros and Cons of [Topic]: An In-Depth Analysis",
        "Is [Topic] Right for You? The Pros and Cons",
        "Understanding the Pros and Cons of [Topic]",
        "Weighing the Pros and Cons of [Topic]",
        "The Complete Guide to the Pros and Cons of [Topic]",
        "Everything You Need to Know About the Pros and Cons of [Topic]",
        "The Definitive List of Pros and Cons for [Topic]",
        "Balancing the Pros and Cons of [Topic]: A Comprehensive Overview",
        "Exploring the Pros and Cons of [Topic]",
        "The Benefits and Drawbacks of [Topic]: Pros and Cons",
        "The Upsides and Downsides of [Topic]: A Detailed Look",
        "Pros and Cons of [Topic] You Should Consider",
        "Key Pros and Cons of [Topic]",
        "A Close Look at the Pros and Cons of [Topic]",
        "[Topic]: Pros and Cons for [Year]",
        "Pros and Cons of [Topic]: Expert Insights",
        "Evaluating the Pros and Cons of [Topic]",
        "What Are the Pros and Cons of [Topic]?",
    ]
    rand = random.randint(1, len(templates))

    user_prompt = f"Suggest one SEO-optimized article title, which is used for a blog post`;\n"
    user_prompt += f"Only return the title.\n\n"
    user_prompt += f"This is the content: {user_title}\n"
    user_prompt += f"The content language is {lang}\n"
    user_prompt += (
        f"As a template, use below list. Use number template no: {rand}\n\n"
    )

    for i, template in enumerate(templates, 1):
        user_prompt += f"{i}. {template}\n"


    assistant_promot = f"you write SEO-optimized title for articles. You have correct grammer. Only return the title.\n"

    message = [
        {"role": "assistant", "content": assistant_promot},
        {"role": "user", "content": user_prompt},
    ]
    title = chat(llm_type, message)
    return title

def generate_outlines(user_title, lang, llm_type):

    user_prompt =  f"Outline a comprehensive  blog article for this title `{user_title}`, Consider all requirements; \n"
    user_prompt += f"Only return the title.\n\n"
    user_prompt += f"The content language is {lang}\n"
    user_prompt += f"Use numbering for list\n"
    user_prompt += f"At least should be 3 outlines\n"

    assistant_promot = f"you write SEO-optimized blog post writer. \n You have correct grammer. \n Only return the outlines and in html (h1 and h2) .\n"

    message = [
        {"role": "assistant", "content": assistant_promot},
        {"role": "user", "content": user_prompt},
    ]
    outlines = chat(llm_type, message)
    return outlines


def generate_sections(headline_text, outlines, keywords, lang, llm_type):

    prompt = (
        f"For you are writing an article with these headlines: \n {outlines} \n"
    )
    prompt += f"Write random number of paragraphs for the headline: {headline_text}\n"
    prompt += f"Avoid starting sentences with words like 'Moreover', 'Understanding', 'Furthermore', 'One of the key', 'Additionally', and similar.\n"
    prompt += f"Just return the paragraphs.\n"
    prompt += f"Exclude an introduction section.\n"
    prompt += f"Exclude a conclusion section.\n"
    prompt += f"You are writing part of an article\n"
    prompt += (
        f"Make sure your writing is specially based on the {headline_text}\n"
    )
    prompt += f"Avoid writing an ending for the section\n"
    prompt += f"Avoid using such as 'In Conclusion', 'at the end', 'Finally', 'overall', 'fortunately', 'lastly' and similar.\n"
    prompt += f"Answer answer response in HTML.\n"
    prompt += f"Avoid writing stereotypes\n"

    # if keywords:
    #     if isinstance(keywords, str):
    #         keywords = json.loads(keywords)
    #     keywords_string = ", ".join(item["value"] for item in keywords)
    #     prompt += f"If keywords: '{keywords_string}' is related to the title '{headline_text}', Use it in the writing\n\n"

    assistant_promot = f"your language is {lang}, \n you write SEO-optimized blog post writer. \n You have correct grammer. \n return in HTML.\n"
    assistant_promot += f"Avoid return title again\n"

    message = [
        {"role": "assistant", "content": assistant_promot},
        {"role": "user", "content": prompt},
    ]
    text = chat(llm_type, message)
    return text

@celery.task
def generate_blog_simple(content_id, user_input):
    title = user_input['user_topic']
    keywords = [tag.strip() for tag in user_input['tags'].split(',')]
    lang = user_input['lang']
    lang = "فارسی"
    llm = "gpt-4o"
    
    with flask_app.app_context():
        # Simulate a long-running task
        # time.sleep(60)  # Placeholder for the actual processing

        
        title = generate_title(title, lang, llm)
        # print(title)
        generated_outlines = generate_outlines(title, lang, llm)
        # print(outlines)

        soup = BeautifulSoup(generated_outlines, "html.parser")
        headlines_elements = soup.find_all(["h1", "h2", "h3", "h4", "h5", "h6"])
        
        outlines = "\n".join(
            "\n".join(map(str, item)) for item in headlines_elements
        )
        
        
        inside = f""
        toc = []
        for headline_element in headlines_elements:
            headline_text = headline_element.get_text()
            toc.append(str(headline_element))
            # inside += f"{headline_text}"
            inside += f"{generate_sections(headline_text,outlines, keywords, lang, llm)}"
            
        toc = "<br/>".join(toc)
        body = f"""
            {str(toc)}
            <br/>
            {inside}
        """ 
        # Fetch the Content record
        content = Content.query.get(content_id)
        if content:
            content.body = body 
            content.system_title = title
            db.session.add(content)
            db.session.commit()
            
            # Update the job status
            job = Job.query.filter_by(job_id=generate_blog_simple.request.id).first()
            if job:
                job.job_status = 'SUCCESS'
                db.session.add(job)
                db.session.commit()

            return content.id
        else:
            # Handle case where the content was not found
            job = Job.query.filter_by(job_id=generate_blog_simple.request.id).first()
            if job:
                job.job_status = 'FAILURE'
                db.session.add(job)
                db.session.commit()

            return None
