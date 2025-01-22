#!/bin/env python3

import argparse
import json
import pandas as pd
import openai

__doc__ = (
    """Removes non-interesting questions and associated records from a JSON dataset"""
)

# model = "deepseek-ai/DeepSeek-V3"
model = "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo"
TOGETHERAI_API_KEY = ""
llm_chat_key = ""


def load_env():
    with open("./settings.json") as f:
        settings = json.load(f)
    globals().update(settings)


load_env()
TOGETHERAI_API_KEY = llm_chat_key
assert TOGETHERAI_API_KEY


sys_message = """I have a list of questions, one per line. The topic of the questions are centered around environmental issues and details about systems or programmes dealing with the environment, including IT software that processes maps, datasets, etc.
You will remove all the questions that fail the following criteria:

- they should not be about information about a website, such as GDPR
- eliminate questions that are duplicated or very similar to other
- eliminate questions that are too not interesting (too generic).

Reply with the optimized, filtered list of questions, no preamble or details of what was done is needed.
The questions should be presserved and not altered in any way.

QUESTIONS:
"""


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
    return response.choices[0].message.content


def load_dataset(paths):
    out = {}
    for path in paths:
        with open(path) as fp:
            data = json.load(fp)

        df = pd.DataFrame(data)
        out[path] = df

    return out


def clean_records(df, llm_client, max_count=60):
    questions = df["question"].tolist()
    print(f"Calling LLM to optimize {len(questions)} questions")

    text = "\n".join(questions)
    resp = make_llm_call(sys_message, text, model, llm_client)
    new_questions = resp.split("\n")
    clean_df = df.loc[df["question"].isin(new_questions)]
    return clean_df.head(max_count)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "input",
        nargs="+",
        help="Input JSON file paths. Accepts multiple files",
    )
    parser.add_argument(
        "--max_count", type=int, help="Maximum questions to be preserved", default=60
    )
    args = parser.parse_args()

    llm_client = openai.OpenAI(
        api_key=TOGETHERAI_API_KEY,
        base_url="https://api.together.xyz/v1",
    )

    data = load_dataset(args.input)
    for path in data:
        df = data[path]

        clean_df = clean_records(df, llm_client, args.max_count)
        df_data = clean_df.to_dict(orient="list")
        clean_path = f"{path.split('.json')[0]}-max{args.max_count}.json"
        print(f"Writing {clean_path}")

        with open(clean_path, "w") as fp:
            json.dump(df_data, fp)

    print("Done")
