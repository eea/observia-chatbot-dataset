import json
import os

import openai
from bertopic import BERTopic
from bertopic.representation import KeyBERTInspired
from hdbscan import HDBSCAN
from sentence_transformers import SentenceTransformer
from sklearn.cluster import KMeans

# leave at 0 to automatically determine size. One question per cluster
n_clusters = 200

# minimum cluster size if auto size
auto_min_cluster_size = 2

model = "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo"

path = "data-download/EEA Website"
out_dataset_path = "datasets/EEA Website.json"
out_questions_path = f"datasets/EEA Website.txt-{n_clusters}.txt"


TOGETHERAI_API_KEY = ""


def load_env():
    with open("conf.json") as f:
        settings = json.load(f)
    globals().update(settings)


load_env()
assert TOGETHERAI_API_KEY


def process_json_files(directory, callback):
    # Ensure the directory exists
    if not os.path.isdir(directory):
        raise ValueError(
            f"The directory '{directory}' does not exist or is not a directory."
        )

    # Iterate through all files in the directory
    for filename in os.listdir(directory):
        if filename.endswith(".json"):  # Filter for JSON files
            filepath = os.path.join(directory, filename)
            if os.path.isfile(filepath):  # Ensure it's a file
                # print(f"Processing JSON file: {filename}")
                try:
                    with open(filepath, "r") as file:
                        callback(file)
                except Exception as e:
                    print(f"Error processing {filename}: {e}")


documents = []


def read_content(fd):
    data = json.load(fd)
    documents.append(data["fields"].get("content", ""))


process_json_files(path, read_content)
len(documents)
client = openai.OpenAI(
    api_key=TOGETHERAI_API_KEY,
    base_url="https://api.together.xyz/v1",
)

if n_clusters:
    cluster_model = KMeans(n_clusters=n_clusters)
else:
    cluster_model = HDBSCAN(
        min_cluster_size=auto_min_cluster_size,
        metric="euclidean",
        cluster_selection_method="eom",
        prediction_data=True,
    )

# Pre-calculate embeddings
embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
embeddings = embedding_model.encode(documents, show_progress_bar=True)

representation_model = KeyBERTInspired()
topic_model = BERTopic(
    representation_model=representation_model,
    embedding_model=embedding_model,
    hdbscan_model=cluster_model,
)
topics, probs = topic_model.fit_transform(documents, embeddings)

for topic_id in topic_model.topic_representations_.keys():
    topics_data = topic_model.topic_representations_[topic_id]
    topic = ", ".join([x[0] for x in topics_data])
    print(topic)


prompt = """Topic: {topic}

Content of documents:
{documents}

Generated questions:
"""

max_prompt = 10000  # 4096
# model = "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo"
# model = "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo


def make_llm_call(
    sys_message, text, model="meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo"
):
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": sys_message},
            {"role": "user", "content": text},
        ],
        stream=False,
    )
    # import pdb; pdb.set_trace()
    return response.choices[0].message.content.split("\n")


def get_questions(topic_model, topic_id, sys_message, model):
    topics_data = topic_model.topic_representations_[topic_id]
    topic = ", ".join([x[0] for x in topics_data])
    docs = topic_model.representative_docs_[topic_id]
    local_prompt = prompt[:]
    local_prompt = local_prompt.replace("{topic}", topic)
    max_docs_chars = (
        max_prompt - len(sys_message) - len(local_prompt.replace("{documents}", ""))
    )
    docs = "\n\n".join(docs)[:max_docs_chars]
    local_prompt = local_prompt.replace("{documents}", docs)
    # print(local_prompt)
    questions = [
        q.strip() for q in make_llm_call(sys_message, local_prompt, model) if q.strip()
    ]
    return (questions, docs, topic)


sys_message = """I'm building a dataset of representative questions that a website visitor might ask.
We're using our documents to build a set of "topics keywords" that represent our documents.
I will provide a topic and the text for the document, your task is to generate a question
that a user might ask, related to that topic, that may find its answer in our document.
Make the question as human as possible and keep it short and not too specific, even if it's not comprehensive,
as the users don't like to type a lot.
It is important to keep the questions centered around the given topic keywords.
Don't generate questions that are really specific to a place or project.
Generate maximum 5 questions.
The answer should be simple text, no introduction, just one question per line.
Don't use dashes at the beginning of lines.
On the last line, extract a topic that summarizes the provided keywords, in the format: Topic: <topic>
"""


def get_primary_question(questions):
    sys_message = """I will provide a set of 5 questions, they are very similar. Your task is to identify the most interesting question and simply print it again, no preamble or other introductory text needed. The questions are:"""
    text = "\n".join(questions)
    question = make_llm_call(
        sys_message, text, "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo"
    )
    return question


dataset = []
primary_questions = []

for topic_id in topic_model.topic_representations_.keys():
    questions, docs, topic_keywords = get_questions(
        topic_model, topic_id, sys_message, model
    )
    qs = []
    pq = get_primary_question(questions)[0]
    primary_questions.append(pq)
    for line in questions:
        if line.startswith("Topic: "):
            topic = line.replace("Topic: ", "")
        else:
            qs.append(line)
    record = {"keywords": topic_keywords, "questions": qs, "topic": topic}
    dataset.append(record)
    print("Topic id: %s" % topic_id)
    print("Topic keywords: %s" % topic_keywords)
    print("Topic: %s" % topic)

    for q in qs:
        print(q)
    print("\n")

with open(out_dataset_path, "w") as f:
    json.dump(dataset, f)

with open(out_questions_path, "w") as f:
    f.write("\n".join(primary_questions))
pqs = [p[0] for p in primary_questions]
with open(out_questions_path, "w") as f:
    f.write("\n".join(pqs))
pqs
