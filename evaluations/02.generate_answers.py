import os
import json
import logging
import requests
from vespa.application import Vespa
from langchain_together.chat_models import ChatTogether
from langchain.schema import HumanMessage


import argparse
parser = argparse.ArgumentParser()
parser.add_argument("--config", help="Path to config file")
args = parser.parse_args()


from dotenv import load_dotenv
load_dotenv(".env")


if args.config:
    load_dotenv(args.config, override=True)


logger = logging.getLogger("qa")
logger.setLevel(logging.INFO)  # Set the default logging level for the logger

console_handler = logging.StreamHandler()

formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger.addHandler(console_handler)
console_handler.setFormatter(formatter)

gptlab_url = os.environ.get("GPTLAB_URL")
gptlab_api_key = os.environ.get("GPTLAB_API_KEY")
gptlab_persona_id = os.environ.get("GPTLAB_PERSONA_ID")

resp_style = os.environ.get("RESP_STYLE")

gptlab_custom_model = os.environ.get("GPTLAB_CUSTOM_MODEL")
gptlab_custom_model_provider = os.environ.get("GPTLAB_CUSTOM_MODEL_PROVIDER")

vespa_host = os.environ.get("VESPA_HOST")
app = Vespa(url=vespa_host)

headers = {
    "Authorization": f"Bearer {gptlab_api_key}"
}

together_ai_chat_model = os.environ.get("TOGETHER_AI_CHAT_MODEL")
together_ai_key = os.environ.get("TOGETHER_AI_KEY")

def start_session():
    url = f"{gptlab_url}/api/chat/create-chat-session"
    data = {"persona_id": gptlab_persona_id, "description": "Test chat session"}
    resp = requests.post(url, json=data, headers=headers)
    data = resp.json()
    return data["chat_session_id"]


def get_answer_with_citation(question, api_key=None):
    url = f"{gptlab_url}/api/chat/send-message"
    chat_session_id = start_session()
    body = {
        "chat_session_id": chat_session_id,
        "message": question,
        "parent_message_id": None,
        "file_descriptors": [],
        "filters": {},
        "prompt_id": 0,
        "search_doc_ids": [],
        "retrieval_options": {},
        "llm_override": {"model_version":gptlab_custom_model, "model_provider": gptlab_custom_model_provider}
    }
    print(body)
    resp = requests.post(url, json=body, headers=headers)
    lines = list(resp.iter_lines(decode_unicode=True))

    if resp_style == 'old':
        msg = None
        for line in lines:
            _msg = json.loads(line)
            if "message_id" in _msg:
                msg = _msg
    else:
        msg_text = ''
        citations = None
        context_docs = []
        for line in lines:
            _msg = json.loads(line)
            if (_msg.get("obj", {}).get("type","") == "message_delta"):
                msg_text += _msg.get("obj", {}).get("content","")
            if (_msg.get("obj", {}).get("type","") == "message_start"):
                context_docs = _msg.get("obj", {}).get("final_documents",[])

        if len(msg_text) > 0:
            msg = {"message": msg_text}

        msg["context_docs"] = {}
        msg["context_docs"]["top_documents"] = context_docs
        msg["citations"] = citations
        #import pdb; pdb.set_trace()

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
    if msg["citations"] is not None:
        for citation_index, doc_id in msg["citations"].items():
            for doc in context_docs:
                if doc["db_doc_id"] == doc_id:
                    out[citation_index] = simplify_doc(doc)

    return out


def get_answer(question):
    msg = get_answer_with_citation(question)
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
    msg = get_answer(question)
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


def make_record(question):
    record = {
        "question": question,
        "ground_truths": [],
        "answer": None,
        "contexts": [],
    }
    msg = get_answer(question)
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
        model_name=together_ai_chat_model,
        api_key=together_ai_key,
        streaming=False,  # Disable streaming to get a simple text response
    )
    response = llm([HumanMessage(content=prompt)])
    return response.content


if __name__ == "__main__":
    jsons_folder = os.environ.get('JSONS_FOLDER', 'tmp')

    questions_file_name = os.path.join(jsons_folder, "01.questions.jsonl")
    questions = []


    with open(questions_file_name, "r") as f:
        for line in f:
            questions.append(json.loads(line).get("question",""))  # Convert JSON string to dictionary

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

    with open(os.path.join(jsons_folder, "02.qa.jsonl"), "w") as f:
        for row in dataset:
            out = {"question":row['question'], "answer":row["answer"], "contexts":row["contexts"]}
            f.write(json.dumps(out) + '\n')
