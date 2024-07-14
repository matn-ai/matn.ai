import os, random, json, time
from datetime import datetime
from dotenv import load_dotenv

from bs4 import BeautifulSoup
from redis import StrictRedis
from openai import OpenAI
from flask import current_app
import docx

from .. import celery_app as celery, db

from ..finance.models import Charge
from ..finance.business import calculate_reduce_charge
from ..models import Content, Job
from ..dashboard.repository import save_html_to_docx, update_article_pro

from ..file_management.models import File, ContentFile

from logging import getLogger

import pymupdf # imports the pymupdf library
from .business import persian_translator

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


def pdf_paraph_reader(file_path):
    doc = pymupdf.open(file_path) 
    for page in doc: 
        yield page.get_text()

def docx_paraph_reader(file_path):
    doc = docx.Document(file_path)
    for para in doc.paragraphs:
        yield para.text


file_reader_mapper = {
    'pdf': pdf_paraph_reader,
    'docx': docx_paraph_reader
}

def get_reader(file_type):
    if 'pdf' in file_type:
        file_type = 'pdf'
    elif 'openxml' in file_type:
        file_type = 'docx'
    else:
        return None
    
    return file_reader_mapper[file_type]
  
def calculate_estimated_cost(file_path, llm_model, file_type='pdf'):
    usage = 0
    reader = get_reader(file_type)
    if not reader:
        return None
    for text in reader(file_path=file_path):
        usage += len(text.split())
    
    return int(calculate_reduce_charge(usage, llm_model) * 1.5)


@celery.task
def translate_file(content_id, user_input=None):
    logger.info(f'Going to translate <content {content_id}>')
    start_time = time.time()
    content = db.session.query(Content).get(content_id)
    file_path = content.get_input('file_path')
    print(file_path)
    file_name = content.get_input('file_path').split('/')[-1]
    mimetype = content.get_input('mimetype')
    logger.info('Going to upload the main file')
    file = File.upload_file(local_file_path=file_path,
                     bucket='local',
                     file_name=file_name,
                     content_type=mimetype)
    ContentFile.add_file_for_content(content_id=content.id, file_id=file.id)

    llm_model = content.llm
    reader = get_reader(file_type=mimetype)
    usage = 0
    token_usage = 0
    translated_texts = []
    logger.info(f'Going to translate [{file_path}]')
    page = 0
    for text in reader(file_path=file_path): 
        logger.info(f'Going to translate page {page}')
        translated_text, local_usage = persian_translator(text=text, llm=llm_model)
        logger.info(f'translated text {translated_text}')
        token_usage += local_usage.total_tokens
        translated_texts.append([text, translated_text])
        usage += len(translated_text.split())
        page += 1
    logger.info(content.author)
    logger.info(f'For [{file_path}], total usage is {usage} by model {llm_model}')
    logger.info(f'For [{file_path}], going to upload the file')
    
    output_path = '.'.join(file_path.split('.')[:-1]) + '_translated.docx'
    translated_text = '<br>'.join([t[1] for t in translated_texts])
    print(translated_text)
    save_html_to_docx(translated_text, output_path)
    file = File.upload_file(local_file_path=output_path,
                     bucket='local',
                     file_name=output_path.split('/')[-1],
                     content_type=mimetype)
    ContentFile.add_file_for_content(content_id=content.id, file_id=file.id)
    logger.info(f'For [{content.id}], file uploaded {file}')
    user = content.author
    content.body = translated_text
    content.set_input({'output_path': output_path})
    logger.info(f'For [{content.id}], updating the mongo data')
    update_article_pro(content_id=content.id, body=output_path)
    charge = Charge.reduce_user_charge(user_id=user.id, 
                              total_words=usage, 
                              model=llm_model,
                              content_id=content.id)
    content.word_count = usage if usage > 0 else usage * -1
    content.system_title = 'ترجمه فایل: ' + file_name
    content.job
    content.set_input({'token_usage': token_usage})
    db.session.commit()
    logger.info(f'For [{content.id}], Charge reduced {user.id} amount {charge.word_count}')
    with open(output_path.replace('docx', 'html'), 'w') as f:
        f.write(translated_text)

    job = Job.query.filter_by(job_id=translate_file.request.id).first()
    if job:
        job.job_status = 'SUCCESS'
        job.running_duration = (time.time() - start_time)
        db.session.add(job)
        db.session.commit()
    
    return {'status': 'SUCCESS', 
            'content_id': content.id, 
            'type': 'file_translation',
            'output_path': output_path}

    
    
