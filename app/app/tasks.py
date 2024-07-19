import os, random, json, time, requests
from datetime import datetime
from dotenv import load_dotenv

from bs4 import BeautifulSoup
from redis import StrictRedis
from openai import OpenAI
from flask import current_app

from . import app as flask_app, celery_app as celery, db
from .models import Content, Job

from .finance.models import Charge

from logging import getLogger

logger = getLogger(__name__)

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
# openai_client = OpenAI(api_key=API_KEY)

redis_client = StrictRedis(host=REDIS_SERVER, port=REDIS_PORT, db=REDIS_DB)


def chat(llm_type, messages, json_format=None):
    # print(OPENROUTER_API)
    # print(API_KEY)
    try:
        response = openai_client.chat.completions.create(
            model=llm_type, messages=messages, temperature=0.8,
            response_format={ "type": "json_object" } if json_format else None
        )
        result = response.choices[0].message.content
        if json_format:
            return json.loads(result.replace('json', ''))
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

    assistant_prompt = '''
        You write SEO-optimized titles for articles. Ensure correct grammar
        Just return the json string! Do not include anything else
        ```json_schema = {
			"type": "object",
			"properties": {
				"title": {
					"type": "string", 
					"description": "SEO-optimized title for articles in correct grammar."
     			}
     		}
     	}```
    '''

    messages = [
        {"role": "assistant", "content": assistant_prompt},
        {"role": "user", "content": user_prompt},
    ]
    result = chat(llm_type, messages, json_format=True)
    return result['title']


def best_suitable_blog_size(user_title, lang, article_length, llm_type):
    user_prompt = f"""For the topic ```{user_title}``` in language ```{lang}``` what is the best number of headlines and number of words?
    I want the article be {article_length} 
    """
    assistant_prompt = """
	You are a professional SEO-optimized blog writer, who knows about the google/bing algorithm.
    Just return the json string! Do not include anything else
	```json_schema = {
		"type": "object",
		"properties": {
			"type": "object",
			"properties": {
				"total_words": {
					"type": "number", 
					"description": "The whole article total words"
				},
				"headline_numbers": {
					"type": "number", 
					"description": "number of headlines for given topic and number of words"
					}
				}
		}```
    """
    messages = [
        {"role": "assistant", "content": assistant_prompt},
        {"role": "user", "content": user_prompt},
    ]
    result = chat(llm_type, messages, json_format=True)
    return result


def generate_outlines_blog_post(user_title, lang, article_length, llm_type):
    # print(article_length)
    # print("*"*10)
	optimized_numbers = best_suitable_blog_size(user_title, lang, article_length, llm_type)
	user_prompt = f"The content language is {lang}\n"
	user_prompt += f"Use numbering for list. \n"
	headline_numbers = optimized_numbers['headline_numbers']	
	user_prompt += (
		f"Generate a concise outline for a short blog post on the following topic: {user_title}\n"
		f"The outline should include an introduction, {headline_numbers} main headline and no sub headline , and a conclusion.\n"
		f"Ensure each section is relevant to the topic and provides essential information without unnecessary detail. \n"
	)

	assistant_prompt = '''You are a professional SEO-optimized blog writer, who knows about the google/bing algorithm.
 Just return the json string! Do not include anything else
 ```json_schema = {
	"type": "object",
	"properties": {
		"headlines": {
			"type": "array",
			"description": "Headlines for given topic/title. The headlines must cover the topic idea comprehensively.",
			"items": {
				"type": "object", 
				"description": "a headline data",
				"required": ["html_tag", "text",
						"level", "ordering"],
				"properties": {
					"html_tag": {
						"type": "string", 
						"enum": ["h1", "h2" , "h3" , "h4"],
						"description": "headline html tag based on its level on text"
					},
					"text": {
						"type": "string",
						"description": "The headline text"
					},
					"level": {
						"type": "number",
						"description": "The headline level based on its parent. 1 means it is parent"
					},
					"ordering": {
						"type": "number",
						"description": "The headline order in the text."
					},
					"paragraph_words": {
						"type": "number",
						"description": "The number of words that can be written in under this headline for this topic"
					}
				}
			}
		}
	}
}```
 '''

	messages = [
		{"role": "assistant", "content": assistant_prompt},
		{"role": "user", "content": user_prompt},
	]
	return chat(llm_type, messages, json_format=True)


def generate_blog_post_sections(
    headline, outlines, keywords, lang, length, llm_type
):
	headline_text = headline['text']
	headline_word_count = headline['paragraph_words']
	avoid_list = [
		"در نهایت",
		"به طوری کلی",
		"بنابراین",
		"همچنین",
	]
	json_schema = '''
 Just return the json string! Do not include anything else
	```json_schema = {
	"type": "object",
	"properties": {
		"section_text": {
			"type": "string", 
			"description": "The section text in %s words for given outlines with <p> html tag like <p> [text here] </p> <p> [text here] </p><p> [text here] </p>"
		}
	}
}```
''' % (headline_word_count)

	prompt = (
		f"Write few paragraphs for the section titled '{headline_text}' of a blog post. \n"
		f"The content should be well-researched, engaging, and informative. \n"
		f"The section should be engaging, informative, and concise, suitable for a broad audience. It should include actionable advice and real-life examples to illustrate the points.\n"
		f"You are writing part of an article with outlines: {outlines}\n"
		f"Do not include an introduction or conclusion. Focus exclusively on expanding and explaining '{headline_text}'. \n"
		f"Avoid writing a paragraph or sentence related to the summary of the text or words like at the end or similar like below:\n"
		f"Avoid finish the paragraph with {' and '.join(avoid_list)}\n"
	)

	if keywords:
		for item in keywords:
			item = str(item).replace("[", " ")
			item = str(item).replace("]", " ")
			_keywords = json.loads(item.strip())
			prompt += f"Use the following keyword if relevant: {_keywords['value']}\n"


	assistant_prompt = (
		f"Your language is {lang}. You are an SEO-optimized blog post writer. "
		f"Ensure correct grammar. Return the result in HTML with <p> tags."
		f"Do not include the headline title again.\n"
	)
	assistant_prompt += json_schema

	messages = [
		{"role": "assistant", "content": assistant_prompt},
		{"role": "user", "content": prompt},
	]
	result = chat(llm_type, messages, json_format=True)
	return result['section_text']


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

	headlines_elements = outlines['headlines']
	outlines_text = '\n'.join([ot['text'] for ot in headlines_elements])
	inside = ""
	for headline_element in headlines_elements:
		tag = headline_element['html_tag']
		logger.info('Getting data for {}. {}'.format(headline_element['ordering'], headline_element['text']))
		inside += f"<br/><{tag}>{headline_element['text']}</{tag}>"
		inside += generate_blog_post_sections(
			headline_element, outlines_text, keywords, lang, length, llm_type
		)

	return f"<h1>{title}</h1><br/>{inside}"


def get_web_data(url):
    content = requests.get(url).content
    soup = BeautifulSoup(content, features="lxml")
    return soup.body.text


def generate_sections_article_pro(
    sub_heading,
    main_tag,
    keywords,
    lang,
    language_model,
    point_ofview,
    target_audience,
    voice_tune,
    matched_content,
):
    prompt = (
        f"Write detailed paragraphs for the section titled '{sub_heading}' of a professional article. "
        f"The content should be well-researched, engaging, and informative. "
        f"The content language is {lang}. Use the '{point_ofview}' point of view, and target audience as '{target_audience}'. "
        f"Make sure to maintain a '{voice_tune}' tune throughout the text.\n"
    )
    
    if matched_content:
        prompt += f'Use the content below to enhance your context.\nContent:```{matched_content}```'

    if keywords:
        prompt += f"Use the following keywords where relevant: {', '.join(keywords)}.\n"

    if main_tag:
        prompt += f"Make sure to include the main tag: {main_tag}.\n"

    json_schema = '''
    ** Just return the json string! Do not include anything else! Do not write json **
    return result in json without any text around it:
        ```json_schema = {
        "type": "object",
        "properties": {
            "text": {
                "type": "string", 
                "description": "The paragraphs text for given title, point of view and tune with <p> html tag like <p> [text here] </p> <p> [text here] </p><p> [text here] </p>"
            }
        }
        }```
'''

    assistant_prompt = (
        f"You are an SEO-optimized professional article writer. Ensure correct grammar. "
        f"Return the result in HTML with <p> tags. Do not include the heading title again or any extra information.\n"
    )
    # assistant_prompt += json_schema

    messages = [
        {"role": "assistant", "content": assistant_prompt},
        {"role": "user", "content": prompt},
    ]

    result = chat(language_model, messages, json_format=False)
    logger.info(f'Result of generate_sections_article_pro text {result}')
    # return result['text]
    return result


def outline_resource_rag(headlines, resource_text, llm_type='gpt-3.5-turbo'):
    user_prompt = (
        f"Give the related content for each headline from the text. Summarize the related text in maximum 100 words and put it under the headline\n",
        f"- Headlines: ```{headlines}```\n",
        f"- Text: ```{resource_text}```\n",

    )


    assistant_prompt = (
        "You are a professional content matcher. You can match the part of the text to the given outlines.\n",
        # "If there is no content for headline, return headline text but empty matched_text.\n",
        """```json_schema = {
        "type": "object",
        "properties": {
            "headlines": {
                "type": "array",
                "description": "Headlines and summarized matched text with the headlines like a neural search engine",
                "headlines_matched_text": {
                    "type": "object", 
                    "description": "a headline data",
                    "required": ["matched_text", "headline_text"],
                    "properties": {
                        "matched_text": {
                            "type": "string",
                            "description": "The summarized text that matched the headline"
                        },
                        "headline_text": {
                            "type": "string",
                            "description": "The headline text"
                        }
                    }
                }
            }
        }
    }```"""
    )
    messages = [
        {"role": "assistant", "content": ''.join(assistant_prompt)},
        {"role": "user", "content": ''.join(user_prompt)},
    ]


    response = openai_client.chat.completions.create(
        model=llm_type, messages=messages, temperature=0.2,
        response_format={ "type": "json_object" }
    )
    
    result = json.loads(response.choices[0].message.content)
    return result


def generate_headlines_resources_relevance_text(user_input):
    outlines = user_input['outlines']
    headlines = '-' + '- \n'.join([o['head'] for o in outlines])
    resources = user_input['selected_resources']
    resource_outlines = {}
    for o in outlines:
        resource_outlines[o['head']] = []
    for resource in resources:
        logger.info(f"Going to extract data for headlines {resource['type']} -> {resource['url']}")
        if resource['type'] == 'web':
            content = get_web_data(resource['url'])[:5000]
        elif resource['type'] == 'file':
            pass
        else:
            continue
            
        local_resource_outlines = outline_resource_rag(headlines, content)
        print(f'Result: {local_resource_outlines}')
        for ro in local_resource_outlines['headlines']:
            print(ro)
            #TODO
            if ro and 'headline_text' in ro and ro['headline_text'] in resource_outlines and ro.get('matched_text'):
                resource_outlines[ro['headline_text']] += [ro['matched_text']]
    return resource_outlines

def generate_article_pro_body(
    title,
    main_tag,
    language_model,
    keywords,
    lang,
    outlines,
    point_ofview,
    target_audience,
    voice_tune,
    headline_resources_text=None
):

    body = f"<h1>{title}</h1>"
  

    for outline in outlines:
        head = outline.get("head")
        subs = outline.get("subs", [])
        image = outline.get("image")

        body += f"<br/><br/><h2>{head}</h2>"
        logger.info(f'Creating section body -> {head} [{main_tag}] ({point_ofview})/{target_audience} [{voice_tune}]')
        matched_content = headline_resources_text.get(head)
        matched_content = '\n'.join(matched_content)
        section = generate_sections_article_pro(
            head,
            main_tag,
            keywords,
            lang,
            language_model,
            point_ofview,
            target_audience,
            voice_tune,
            matched_content
        )
        
        section = str(section).replace("html", "").replace("", "").replace("```", "")
        
        body += section
        
        if image:
            body += f"<img src='{image}' width=512 />" 


        for sub in subs:
            body += f"<br/><h3>{sub}</h3>"
            logger.info(f'Creating section body -> {sub}')
            section_content = generate_sections_article_pro(
                sub,
                main_tag,
                keywords,
                lang,
                language_model,
                point_ofview,
                target_audience,
                voice_tune,
                matched_content
            )
            section_content = str(section_content).replace("html", "").replace("", "").replace("```", "")
            body += section_content
            body += "<br/>"

    return body



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


def save_article_to_db(content_id, body, title, outlines, content_length, model='gpt-4o'):
    with flask_app.app_context():
        content = Content.query.get(content_id)
        
        if content:
            content.word_count = content_length
            content.body=body
            content.system_title = title
            content.outlines = str(outlines)
            content.llm = model
            db.session.add(content)
            db.session.commit()
            
            ## Reduce Charge
            logger.info(f'Reducing charge from user {content.author_id}')
            charge = Charge.reduce_user_charge(
                user_id=content.author_id,
                total_words=content_length,
                model=model
            )
            logger.info(f'Reducing charge from user {content.author_id} -> {content_length} [{model}] == {charge.word_count}')
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


@celery.task(retry_kwargs={'max_retries': 2})
def generate_blog_simple(content_id, user_input):
    start_time = datetime.now()
    logger.info(f'Going to create blog post for <{content_id}>')
    title = user_input["user_topic"]
    keywords = user_input["tags"].split(",")
    lang = "فارسی" if user_input["lang"] else "English"
    llm = "gpt-3.5-turbo"
    logger.info(f'The LLM is {llm}')
    article_length = user_input["article_length"]
    title = generate_title_blog_post(title, lang, article_length, llm)
    logger.info(f'Generated Title: {title}')
    outlines = generate_outlines_blog_post(title, lang, article_length, llm)
    logger.info(f'<Content:{content_id}>  The outlines has been created')
    body = generate_blog_post_body(title, outlines, keywords, lang, article_length, llm)
    logger.info(f'<Content:{content_id}>   The body has been created')
    content_length = len(body.split())
    logger.info(f'<Content:{content_id}>  Going to save the article. Length of the article {content_length}')
    content_id = save_article_to_db(content_id, body, title, outlines, content_length, model=llm)

    task_status = "SUCCESS" if content_id else "FAILURE"
    end_time = datetime.now()
    duration = end_time - start_time
    logger.info(f'<Content:{content_id}> elapsed time {duration}')  


    update_job_status(generate_blog_simple.request.id, task_status, duration.seconds)

    return content_id


@celery.task(retry_kwargs={'max_retries': 3})
def generate_pro_article(content_id, user_input):
    start_time = datetime.now()

    title = user_input["user_topic"]

    main_tag = user_input["main_tag"]
    # language_model = user_input["language_model"]
    language_model = user_input["language_model"]
    keywords = user_input["tags"]
    lang = "فارسی" if user_input["lang"] == "fa" else user_input["lang"]
    outlines = user_input["outlines"]
    point_ofview = user_input["point_ofview"]
    target_audience = user_input["target_audience"]
    voice_tune = user_input["voice_tune"]
    
    headlines_resources = generate_headlines_resources_relevance_text(user_input=user_input)


    body = generate_article_pro_body(
        title,
        main_tag,
        language_model,
        keywords,
        lang,
        outlines,
        point_ofview,
        target_audience,
        voice_tune,
        headlines_resources
    )


    content_length = len(body.split())
    content_id = save_article_to_db(content_id, body, title, outlines, content_length, model=language_model)

    task_status = "SUCCESS" if content_id else "FAILURE"
    end_time = datetime.now()
    duration = end_time - start_time
    update_job_status(generate_pro_article.request.id, task_status, duration.seconds)

    return content_id
