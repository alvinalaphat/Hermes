import os
import openai 
import mimetypes
from PIL import Image
import pdfreader
import pytest
import csv
import PyPDF2
import pymongo
import json
import redis
import time
import requests
from docx import Document
from datetime import timedelta
from flask import Flask, render_template, request, Flask, send_file, abort
from flask_limiter import Limiter
from llama_index import GPTVectorStoreIndex
from flask_limiter.util import get_remote_address
from werkzeug.utils import secure_filename
from llama_index.prompts import PromptTemplate
from pathlib import Path
import concurrent.futures
from dotenv import load_dotenv
from datetime import timedelta
from redis import Redis
from llama_index import SimpleDirectoryReader
from main import app

load_dotenv()

os.environ["OPENAI_API_KEY"] = os.getenv("OPENAI_API_KEY")
MONGODB_URI = os.getenv("MONGODB_URI")
redis_conn = redis.Redis(host='localhost', port=6379, db=0)

client = pymongo.MongoClient(MONGODB_URI, connectTimeoutMS=None, socketTimeoutMS=None, connect=True)
db = client['Cluster0']
collection = db['files']

def error_response(error_code, error_description):
    return render_template('error.html', error_code=error_code, error_description=error_description), error_code

def get_file_type(file_path):

    file_type_mappings = {
        '.jpeg': 'Image',
        '.jpg': 'Image',
        '.png': 'Image',
        '.gif': 'Image',
        '.docx': 'Document',
        '.pdf': 'Document',
        '.txt': 'Document',
        '.doc': 'Document',
        '.html': 'Code',
        '.py': 'Code',
        '.js': 'Code',
        '.css': 'Code',
        '.cpp': 'Code',
        '.c': 'Code',
        '.java': 'Code',
        '.csv': 'Sheet',
        '.xlsx': 'Sheet'
    };
    
    ending = os.path.splitext(file_path)[1]
    if ending and ending in file_type_mappings:
        return file_type_mappings[ending]
    else:
        return "Unknown"
    
def determine_rate_limit(file_type):

    # values based on industry norms
    # first element is request limit, second is timeframe in s
    file_type_limits = {
        "Image": [10, 60],
        "Document": [15, 60],
        "Code": [15, 60],
        "Sheet": [5, 60],
        "Unknown": [5, 60]
    }

    retrieve = file_type_limits.get(file_type, "5 per minute")
    return retrieve[0], retrieve[1]
    
# def request_is_limited(file_type, limit, timeframe):

def request_is_limited(redis_key: str, redis_limit: int, redis_period: timedelta):
    if redis_conn.setnx(redis_key, redis_limit):
        redis_conn.expire(redis_key, int(redis_period.total_seconds()))
    bucket_val = redis_conn.get(redis_key)
    if bucket_val and int(bucket_val) > 0:
        redis_conn.decrby(redis_key, 1)
        return False
    return True

def smart_categorize(uploaded_file, filetype, past_categories):

    try: 

        if "image" in filetype.lower():

            # because images can't be read by an LLM
            return "Images" 
        
        else:

            filename_fn = lambda filename: {'file_name': filename}
            reader = SimpleDirectoryReader(input_files=[uploaded_file], file_metadata=filename_fn)
            documents = reader.load_data()
            index = GPTVectorStoreIndex.from_documents(documents)

            text_qa_template_str = (
                "You have four rules you are required to follow\n"
                "1. You can ONLY answer with one word\n"
                "2. Your task is to summarize the following file's contents with a broad category\n"
                f"3. Reuse categories where applicable. Past categories: {past_categories}\n"
                "4. If you can't come up with a category, respond with: Misc\n"
                "The file's content is below.\n"
                "---------------------\n"
                "{context_str}\n"
                "---------------------\n"
                "Using the content information, "
                "{query_str}\n"
            )

            text_qa_template = PromptTemplate(text_qa_template_str)
            response = index.as_query_engine(text_qa_template=text_qa_template).query("in one word, categorize the info inside the file. Category: ")
            answer = response.response

            # sometimes model leaves a period at end of answer
            if "." in answer: answer = answer.replace(".", "")

            return answer
    
    except Exception as e:

        print(e)
        return "Misc"
