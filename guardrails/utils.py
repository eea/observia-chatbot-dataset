import os
import json
from dotenv import load_dotenv

load_dotenv()

from langfuse import Langfuse

def init_langfuse():
    langfuse = Langfuse(
        secret_key=os.environ["LANGFUSE_SECRET_KEY"],
        public_key=os.environ["LANGFUSE_PUBLIC_KEY"],
        host=os.environ["LANGFUSE_HOST"] 
    )
    return langfuse


def load_jsonl(input_file):
    with open(input_file, "r", encoding="utf-8") as f:
        data = [json.loads(line) for line in f]
    return(data)
