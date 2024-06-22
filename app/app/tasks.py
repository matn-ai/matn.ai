import json
from bs4 import BeautifulSoup
from redis import StrictRedis
from openai import OpenAI
from os import getenv
from . import app as flask_app
from . import celery_app as celery
from . import db, contents_collection
from .models import Content, Job



client = OpenAI(
    base_url="https://api.tosiehgar.ir/v1/", api_key=getenv("OPENROUTER_API_KEY")
)


# Initialize Redis client
redis_client = StrictRedis(host=getenv("REDIS_SERVER"), port=getenv("REDIS_PORT"), db=getenv("REDIS_DB"))


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


def generate_title(user_title, lang, llm_type=""):
    # templates = [
    #     "How to ...",
    #     "The secret to ...",
    #     "There are [Number] things ...",
    #     "[Number] Things Every ... Should Include",
    #     "Top [Number] [Things/Tools/Strategies] for [Achieving a Goal]",
    #     "What Is [Topic]? [Number] Things You Should Know",
    #     "Why [Topic] Matters: [Number] Reasons You Should Care",
    #     "[Number] Myths About [Topic] Debunked",
    #     "Truth About [Topic]: [Number] Myths Busted",
    #     "The Definitive List of Pros and Cons for [Topic]",
    #     "Why [Topic] is Important for [Audience]",
    #     "How to Improve Your [Skill/Knowledge] in [Topic]",
    #     "The Impact of [Topic] on [Industry/Society]",
    #     "Common Mistakes to Avoid in [Topic]",
    #     "[Number] Tips for Success in [Topic]",
    #     "The Future of [Topic]: Trends to Watch",
    #     "How [Topic] is Changing the [Industry]",
    #     "[Number] Essential Tools for [Topic]",
    #     "How to Master [Topic]",
    #     "4 Big Mistakes to Avoid in [Topic]",
    #     "The Pros and Cons of [Topic]: What You Need to Know",
    #     "[Number] Pros and Cons of [Topic] Explained",
    #     "Pros and Cons of [Topic]: An In-Depth Analysis",
    #     "Is [Topic] Right for You? The Pros and Cons",
    #     "Understanding the Pros and Cons of [Topic]",
    #     "Weighing the Pros and Cons of [Topic]",
    #     "The Complete Guide to the Pros and Cons of [Topic]",
    #     "Everything You Need to Know About the Pros and Cons of [Topic]",
    #     "The Definitive List of Pros and Cons for [Topic]",
    #     "Balancing the Pros and Cons of [Topic]: A Comprehensive Overview",
    #     "Exploring the Pros and Cons of [Topic]",
    #     "The Benefits and Drawbacks of [Topic]: Pros and Cons",
    #     "The Upsides and Downsides of [Topic]: A Detailed Look",
    #     "Pros and Cons of [Topic] You Should Consider",
    #     "Key Pros and Cons of [Topic]",
    #     "A Close Look at the Pros and Cons of [Topic]",
    #     "[Topic]: Pros and Cons for [Year]",
    #     "Pros and Cons of [Topic]: Expert Insights",
    #     "Evaluating the Pros and Cons of [Topic]",
    #     "What Are the Pros and Cons of [Topic]?",
    # ]
    # rand = random.randint(1, len(templates))

    # user_prompt = (
    #     f"Suggest one SEO-optimized article title, which is used for a blog post`;\n"
    # )
    # user_prompt += f"Only return the title.\n\n"
    # user_prompt += f"This is the content: {user_title}\n"
    # user_prompt += f"The content language is {lang}\n"
    # user_prompt += f"As a template, use below list. Use number template no: {rand}\n\n"

    # for i, template in enumerate(templates, 1):
    #     user_prompt += f"{i}. {template}\n"


    user_prompt = f"generate a catchy and informative title for a blog post about {user_title}. \
        The title should be engaging and appealing to general and should reflect a professional tone."
    user_prompt += f"The content language is {lang}\n"
    assistant_promot = f"you write SEO-optimized title for articles. You have correct grammer. Only return the title.\n"

    message = [
        {"role": "assistant", "content": assistant_promot},
        {"role": "user", "content": user_prompt},
    ]
    title = chat(llm_type, message)
    return title


def generate_outlines(user_title, lang, llm_type):

    # user_prompt = f"Outline a comprehensive  blog article for this title `{user_title}`, Consider all requirements; \n"
    # user_prompt += f"Ensure the outline flows logically and is designed to engage and inform readers\n"
    # user_prompt += f"Only return the title.\n\n"
    # user_prompt += f"The content language is {lang}\n"
    # user_prompt += f"Use numbering for list\n"
    # user_prompt += f"At least should be 3 outlines\n"
    # user_prompt += f"Have a conclusion part which provides actionable advice or insights."

    user_prompt = f"Create a comprehensive outline for a blog post about {user_title}. \
        The outline should include a title, a clear introduction with a hook and overview, \
        several main points with subpoints for each section, and a strong conclusion that summarizes the post and provides actionable advice or insights. \
        Ensure the outline flows logically and is designed to engage and inform readers."
    user_prompt += f"The content language is {lang}\n"
    user_prompt += f"Use numbering for list\n"

    assistant_promot = f"you write SEO-optimized blog post writer. \n You have correct grammer. \n Only return the outlines and in html (h2 and h3) .\n"

    message = [
        {"role": "assistant", "content": assistant_promot},
        {"role": "user", "content": user_prompt},
    ]
    outlines = chat(llm_type, message)
    return outlines

def generate_sections(headline_text, outlines, keywords, lang, llm_type):
    prompt = (
        f"Write detailed paragraphs for the section titled '{headline_text}' of a blog post. "
        f"The content should be well-researched, engaging, and informative. "
        f"You are writing part of an article with outlines: {outlines}\n"
        f"Do not include an introduction or conclusion, ending, section. "
        f"Focus exclusively on expanding and explaining '{headline_text}'. "
        f"The response should be formatted in HTML using <p> tags for each paragraph. "
        f"Ensure that the writing is free from stereotypes. "
        f"Use correct grammar and maintain a professional tone suitable for the blog's target audience. "
        f"The content language is {lang}. "
    )

    if keywords:
        prompt += f"Use the following keywords where relevant: {', '.join(keywords)}\n"

    assistant_prompt = (
        f"Your language is {lang}. You are an SEO-optimized blog post writer. "
        f"Ensure correct grammar. Return the result in HTML with <p> tags. "
        f"Do not include the headline title again.\n"
    )

    message = [
        {"role": "assistant", "content": assistant_prompt},
        {"role": "user", "content": prompt},
    ]

    text = chat(llm_type, message)
    return text


@celery.task
def generate_blog_simple(content_id, user_input):
    title = user_input["user_topic"]
    keywords = [tag.strip() for tag in user_input["tags"].split(",")]
    lang = 'فارسی' if user_input["lang"] else 'English'
    llm = "gpt-4o"
    # llm = "gpt-3.5-turbo"

    with flask_app.app_context():
        # Simulate a long-running task
        # time.sleep(60)  # Placeholder for the actual processing

        title = generate_title(title, lang, llm)
        # print(title)
        generated_outlines = generate_outlines(title, lang, llm)
        # print(outlines)

        soup = BeautifulSoup(generated_outlines, "html.parser")
        headlines_elements = soup.find_all(["h2", "h3", "h4", "h5", "h6"])

        outlines = "\n".join("\n".join(map(str, item)) for item in headlines_elements)

        # print(outlines)

        inside = f""
        toc = []
        for headline_element in headlines_elements:
            headline_text = headline_element.get_text()
            toc.append(str(headline_element))
            inside += f"<br/>"
            inside += f"{str(headline_element)}"
            inside += (
                f"{generate_sections(headline_text,outlines, keywords, lang, llm)}"
            )

        toc = "".join(toc)
        body = f"""
            <h1>
                {str(title)}
            </h1>            
            <br/>
            <hr/>
            <br/>
            {str(toc)}
            <br/>
            <hr/>
            <br/>
            {inside}
        """

        # Save the body to MongoDB
        body_document = {
            "body": body
        }
        mongo_result = contents_collection.insert_one(body_document)
        mongo_id = str(mongo_result.inserted_id)
        
        # Fetch the Content record
        content = Content.query.get(content_id)
        if content:
            content.word_count = len(body.split())
            content.content_type = 0
            content.mongo_id = mongo_id
            content.system_title = title
            content.outlines = outlines
            db.session.add(content)
            db.session.commit()

            # Update the job status
            job = Job.query.filter_by(job_id=generate_blog_simple.request.id).first()
            if job:
                job.job_status = "SUCCESS"
                db.session.add(job)
                db.session.commit()

            return content.id
        else:
            # Handle case where the content was not found
            job = Job.query.filter_by(job_id=generate_blog_simple.request.id).first()
            if job:
                job.job_status = "FAILURE"
                db.session.add(job)
                db.session.commit()

            return None
