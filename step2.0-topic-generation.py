#!/usr/bin/env python

import argparse
import json
import os

import openai
from sklearn.cluster import KMeans
from bertopic import BERTopic
from bertopic.representation import KeyBERTInspired
from hdbscan import HDBSCAN
from sentence_transformers import SentenceTransformer

# path = "data-download/Climate-ADAPT case studies"
# model = "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo"

model = "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo"

max_prompt = 10000  # 4096

# minimum cluster size if auto size
auto_min_cluster_size = 2

# Don't generate questions that are really specific to a place or project.

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

user_message_prompt = """Topic: {topic}

Content of documents:
{documents}

Generated questions:
"""

TOGETHERAI_API_KEY = ""


# TODO: use settings.json or conf.json, but not both
def load_env():
    with open("settings.json") as f:
        settings = json.load(f)
    globals().update(settings)


load_env()
assert TOGETHERAI_API_KEY


def process_json_files(directory, callback):
    # Ensure the directory exists
    if not os.path.isdir(directory):
        raise ValueError(
            f"Directory '{directory}' does not exist or is not a directory."
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


def make_topics(documents, n_clusters):
    print("Making topics")

    # Pre-calculate embeddings
    embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
    embeddings = embedding_model.encode(documents, show_progress_bar=True)

    if n_clusters:
        cluster_model = KMeans(n_clusters=n_clusters)
    else:
        cluster_model = HDBSCAN(
            min_cluster_size=auto_min_cluster_size,
            metric="euclidean",
            cluster_selection_method="eom",
            prediction_data=True,
        )
    cluster_model = HDBSCAN(
        min_cluster_size=2,
        metric="euclidean",
        cluster_selection_method="eom",
        prediction_data=True,
    )

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

    return topic_model


def make_llm_call(sys_message, text, model, llm_client):
    response = llm_client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": sys_message},
            {"role": "user", "content": text},
        ],
        stream=False,
    )
    # import pdb; pdb.set_trace()
    return response.choices[0].message.content.split("\n")


def get_primary_question(questions, llm_client):
    sys_message = """
I will provide a set of 5 questions, they are very similar.
Your task is to identify the most interesting question and simply print it
again, no preamble or other introductory text needed. The questions are:
"""
    text = "\n".join(questions)
    question = make_llm_call(sys_message, text, model, llm_client)
    return question


def get_questions(topic_model, topic_id, sys_message, model):
    topics_data = topic_model.topic_representations_[topic_id]
    topic = ", ".join([x[0] for x in topics_data])
    docs = topic_model.representative_docs_[topic_id]
    local_prompt = user_message_prompt[:]
    local_prompt = local_prompt.replace("{topic}", topic)
    max_docs_chars = (
        max_prompt - len(sys_message) - len(local_prompt.replace("{documents}", ""))
    )
    docs = "\n\n".join(docs)[:max_docs_chars]
    local_prompt = local_prompt.replace("{documents}", docs)
    # print(local_prompt)

    llm_client = openai.OpenAI(
        api_key=TOGETHERAI_API_KEY,
        base_url="https://api.together.xyz/v1",
    )

    print(f"Get questions for {topic}")

    questions = [
        q.strip()
        for q in make_llm_call(sys_message, local_prompt, model, llm_client)
        if q.strip()
    ]
    primary_question = get_primary_question(questions, llm_client)[0]
    return (questions, primary_question, docs, topic)


def make_dataset(documents, n_topics):
    dataset = []

    topic_model = make_topics(documents, n_topics)

    for topic_id in topic_model.topic_representations_.keys():
        questions, primary_question, docs, topic_keywords = get_questions(
            topic_model, topic_id, sys_message, model
        )
        qs = []
        for line in questions:
            if line.startswith("Topic: "):
                topic = line.replace("Topic: ", "")
            else:
                qs.append(line)
        record = {
            "keywords": topic_keywords,
            "primary_question": primary_question,
            "questions": qs,
            "topic": topic,
        }
        dataset.append(record)

        print("Topic id: %s" % topic_id)
        print("Topic keywords: %s" % topic_keywords)
        print("Topic: %s" % topic)
        print("Primary question: %s" % primary_question)

        for q in qs:
            print(q)
        print("\n")

    return dataset


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate topics for a Vespa download dataset path"
    )
    parser.add_argument("input", help="Input directory path.")
    parser.add_argument("output", help="Path to the output JSON file.")
    parser.add_argument("n_topics", type=int, help="Number of topics")
    args = parser.parse_args()

    documents = []

    def read_content(fd):
        data = json.load(fd)
        documents.append(data["fields"].get("content", ""))

    print("Reading input json files")
    process_json_files(args.input, read_content)

    dataset = make_dataset(documents, args.n_topics)

    print(f"Writing output file {args.output}")
    with open(args.output, "w") as f:
        json.dump(dataset, f, indent=2)


# TODO: allow multiple input folders
