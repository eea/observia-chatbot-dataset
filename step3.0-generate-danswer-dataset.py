#!/bin/env python3

"""Based on a list of questions, produces a "goldenset" of danswer records"""

import argparse
import logging
import json

import requests

from langchain_together.chat_models import ChatTogether
from langchain.schema import HumanMessage
from collections import namedtuple

from vespa.application import Vespa

url = "http://10.50.5.60:64797/"
app = Vespa(url=url)

logger = logging.getLogger("qa")
logger.setLevel(logging.INFO)  # Set the default logging level for the logger

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)

formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
console_handler.setFormatter(formatter)

logger.addHandler(console_handler)

# ["danswer_url", "danswer_username", "danswer_password", "persona_id"]

with open("settings.json") as f:
    data_dict = json.load(f)
    Conf = namedtuple("Conf", data_dict.keys())
    conf = Conf(**data_dict)


def get_login_cookie():
    url = f"{conf.danswer_url}/api/auth/login"
    data = {
        "username": conf.danswer_username,
        "password": conf.danswer_password,
        "scope": "",
        "client_id": "",
        "client_secret": "",
        "grant_type": "",
    }
    resp = requests.post(url, data)
    cookie = resp.headers["set-cookie"]
    return cookie


def start_session(persona_id, login_cookie=None):
    url = f"{conf.danswer_url}/api/chat/create-chat-session"
    data = {"persona_id": persona_id, "description": "Test chat session"}
    cookies = login_cookie or get_login_cookie()
    resp = requests.post(url, json=data, headers={"Cookie": cookies})
    data = resp.json()
    return data["chat_session_id"]


def get_personas(login_cookie=None):
    url = f"{conf.danswer_url}/api/persona"
    cookies = login_cookie or get_login_cookie()
    resp = requests.get(url, headers={"Cookie": cookies})
    return resp.json()
    # print(url)
    # print(cookies)
    # print(resp.json())


def get_answer_with_citation(question, persona_id, login_cookie=None):
    url = f"{conf.danswer_url}/api/chat/send-message"
    cookies = login_cookie or get_login_cookie()
    chat_session_id = start_session(persona_id, login_cookie)
    body = {
        "chat_session_id": chat_session_id,
        "message": question,
        "parent_message_id": None,
        "file_descriptors": [],
        "filters": {},
        "prompt_id": 0,
        "search_doc_ids": [],
        "retrieval_options": {},
    }
    resp = requests.post(url, json=body, headers={"Cookie": cookies})
    lines = list(resp.iter_lines(decode_unicode=True))

    msg = None
    for line in lines:
        _msg = json.loads(line)
        if "message_id" in _msg:
            msg = _msg

    return msg


def simplify_doc(doc):
    keys = [
        "semantic_identifier",  # title
        "blurb",  # description
        "chunk_ind",  # chunk index
        "db_doc_id",  # vespa id
        "document_id",  # semantic doc id (URL of page)
        "link",  # url of page
        "match_highlights",  # snippets
    ]
    out = {k: doc[k] for k in keys}
    return out


def extract_context_documents(msg):
    res = []
    context_docs = msg["context_docs"]["top_documents"]
    for doc in context_docs:
        sdoc = simplify_doc(doc)
        res.append(sdoc)

    return res


def extract_cited_documents(msg):
    out = {}
    context_docs = msg["context_docs"]["top_documents"]
    for citation_index, doc_id in msg["citations"].items():
        for doc in context_docs:
            if doc["db_doc_id"] == doc_id:
                out[citation_index] = simplify_doc(doc)

    return out


def get_answer(question, persona_id):
    msg = get_answer_with_citation(question, persona_id=persona_id)
    answer = msg["message"]
    citations = extract_cited_documents(msg)
    context = extract_context_documents(msg)

    rec = dict(answer=answer, citations=citations, context=context)
    return rec


def download_document(session, document_id, chunk_id):
    # TODO: identify if chunk number is 400, to allow pagination.
    query = f"""
        select *
        from sources *
        where document_id in ("{document_id}") and chunk_id in ({chunk_id})
        order by chunk_id
        limit 400
    """
    response = session.query(yql=query)
    assert response.is_successful()
    data = response.get_json()

    for chunk in data["root"].get("children", []):
        yield chunk


def make_record(question):
    record = {
        "question": question,
        "ground_truths": [],
        "answer": None,
        "contexts": [],
    }
    msg = get_answer(question, persona_id=conf.persona_id)
    answer = msg["answer"]
    record["answer"] = answer
    logger.info("Answer: \n%s", answer)

    contexts = []
    if msg["citations"]:
        contexts = msg["citations"].values()
    else:
        contexts = msg["context"]

    record["urls"] = []

    logger.info("Extracting ground truths from %s documents", len(contexts))

    for doc in contexts:
        with app.syncio() as session:
            document_id = doc["document_id"]
            chunk_id = doc["chunk_ind"]
            logger.info(f"Fetching {document_id} / {chunk_id} from Vespa")
            docs = list(download_document(session, document_id, chunk_id))
            if docs:
                context = docs[0]["fields"]["content"]
            else:
                context = doc["blurb"]

        gt = extract_ground_truth(question, answer, context)
        if gt.strip().lower() in ["no", "not related.", "not related"]:
            logger.debug("No ground truth in context: \n%s", context)
            continue

        if gt not in record["ground_truths"]:
            logger.info("Extract ground truth: \n%s", gt)
            record["ground_truths"].append(gt)
            if context not in record["contexts"]:
                record["contexts"].append(context)
                record["urls"].append(doc["document_id"])

            # TODO: only accept one ground truth?
            # break

    return record


def make_dataset(questions):
    logger.info(f"Processing {len(questions)} questions")

    dataset = []

    for i, question in enumerate(questions):
        logger.info("Question %s: %s", i, question)
        try:
            record = make_record(question)
        except Exception:
            logger.exception("Error in making a record for question: %s", question)
            continue
        dataset.append(record)

    return dataset


def extract_ground_truth(question, answer, context):
    prompt = f"""I'm creating a database with questions and answers.
I will provide the context document and the provided answer.
You will extract, from the context document, the ground truth that answers the question.
Your answer will be directly the ground truth, as it is extracted from the context document.
If the ground truth is not in the context document, respond with a simple "NO".
If the context document doesn't answer the question, response with "Not related".

Question:
{question}

Provided answer:
{answer}

Context document:

{context}

Ground truth:
"""
    llm = ChatTogether(
        model_name=conf.llm_chat_model,
        api_key=conf.llm_chat_key,
        streaming=False,  # Disable streaming to get a simple text response
    )
    response = llm([HumanMessage(content=prompt)])
    return response.content


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate goldenset dataset based on Danswer"
    )
    parser.add_argument(
      "--persona_id",
      type=int,
      help="The assistant id to be used to generate the dataset",
      default=None
    )

    parser.add_argument("input_file", help="Path to input questions text file")
    parser.add_argument("output_file", help="Path to output dataset JSON file")

    args = parser.parse_args()

    conf = conf._replace(persona_id = args.persona_id or conf.persona_id)
    print(f"persona_id: {conf.persona_id}")
    questions = []
    with open(args.input_file) as f:
        for line in f.readlines():
            if line.strip() and not line.startswith("#"):
                questions.append(line.strip())

    dataset = make_dataset(questions)
    out = {
        "question": [],
        "answer": [],
        "contexts": [],
        "ground_truths": [],
        "urls": [],
    }
    for line in dataset:
        for k, v in line.items():
            out[k].append(v)

    with open(args.output_file, "w") as f:
        pretty = json.dumps(out, sort_keys=True, indent=2)
        f.write(pretty)
