import os
from langfuse import Langfuse

from utils import load_jsonl

from dotenv import load_dotenv
load_dotenv()

jsons_folder = os.environ.get('JSONS_FOLDER', 'tmp')

langfuse_host = os.environ.get("LANGFUSE_STORE_HOST")
langfuse_public_key = os.environ.get("LANGFUSE_STORE_PUBLIC_KEY")
langfuse_secret_key = os.environ.get("LANGFUSE_STORE_SECRET_KEY")
langfuse_session_name_suffix = os.environ.get("LANGFUSE_SESSION_NAME_SUFFIX")
langfuse_session_tags = [val.strip() for val in os.environ.get("LANGFUSE_SESSION_TAGS").split(",")]


langfuse = Langfuse(
    secret_key=langfuse_secret_key,
    public_key=langfuse_public_key,
    host=langfuse_host
)


from utils import load_jsonl

def init_trace(query, response, context, session):
    return langfuse.trace(name=query, session_id=session, input={"question":query, "context":context}, output={"answer": response}, tags=langfuse_session_tags)


def score_trace(trid, scores):
    for key in scores.keys():
        langfuse.score(
            trace_id=trid,
            name=key,
            value=scores[key]
        )

def store_in_langfuse(sets):
    session = f"Goldenset {langfuse_session_name_suffix}"
    print(session)
    cnt = 0
    for row in sets:
        print(cnt)
        cnt+=1
        question = row.get("question")
        contexts = row.get("context")
        answer = row.get("answer")
        trace = init_trace(query=question, response=answer, context=contexts, session=session)
        score_trace(trid=trace.id, scores=row.get("ragas_evals"))
        score_trace(trid=trace.id, scores=row.get("custom_evals"))


def join_jsonl(qas, ragas, external):
    all_joined = []
    for qa in qas:
        joined = {}
        for key in qa.keys():
            joined[key] = qa[key];

        joined["ragas_evals"] = {}
        joined["custom_evals"] = {}
        for row in ragas:
            if row['question'] == qa['question']:
                for key in row.keys():
                    if key != 'question':
                        joined["ragas_evals"][key] = row[key]
        for row in external:
            if row['question'] == qa['question']:
                for key in row.keys():
                    if key != 'question':
                        joined["custom_evals"][key] = row[key]
        all_joined.append(joined)
    return(all_joined)


if __name__ == "__main__":
    qas = load_jsonl(os.path.join(jsons_folder, "02.qa.jsonl"))
    ragas = load_jsonl(os.path.join(jsons_folder, "03.ragas.jsonl"))
    external = load_jsonl(os.path.join(jsons_folder, "04.external.jsonl"))

    data = join_jsonl(qas, ragas, external)
    store_in_langfuse(data)
