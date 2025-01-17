from tenacity import retry
from tenacity import stop_after_attempt
from tenacity import wait_random_exponential
from trulens.apps.custom import TruCustomApp
from trulens.apps.custom import instrument
from trulens.core import Feedback
from trulens.core import Select
from trulens.core import TruSession
from trulens.dashboard.run import run_dashboard
from trulens.providers.openai import OpenAI
import argparse
import json
import pandas as pd


TOGETHERAI_API_KEY = ""
llm_chat_key = ""


def load_env():
    with open("./settings.json") as f:
        settings = json.load(f)
    globals().update(settings)


load_env()
TOGETHERAI_API_KEY = llm_chat_key
assert TOGETHERAI_API_KEY


llm_model_params = {
    "api_key": TOGETHERAI_API_KEY,
    "base_url": "https://api.together.xyz/v1",
    "model": "Qwen/Qwen2.5-7B-Instruct-Turbo",
}
provider = OpenAI(model_engine=llm_model_params.pop("model"), **llm_model_params)


def load_dataset(paths):
    out = {}
    for path in paths:
        with open(path) as f:
            data = json.load(f)

        # questions = data['question']
        # ground_truths = data['ground_truths']
        # answers = data['answer']
        # contexts = data['contexts']

        dataset = {
            "query": data["question"],
            "response": data["answer"],
            "contexts": data["contexts"],
        }
        df = pd.DataFrame(dataset)
        out[path] = df
    return out


class CustomApp:
    def __init__(self, records):
        self.records = {}
        for rec in records:
            self.records[rec["query"]] = rec

    @instrument
    def query(self, question):
        record = self.records[question]
        return record["response"]


def load_trulens(in_data):
    session = TruSession()
    session.reset_database()

    for version in in_data.keys():
        df = in_data[version]
        data_dict = df.to_dict("records")

        app = CustomApp(data_dict)
        f_context_relevance = (
            Feedback(
                provider.groundedness_measure_with_cot_reasons,
                name="Groundedness - LLM Judge",
            )
            .on(Select.RecordInput)
            .on(Select.RecordOutput)
        )

        feedbacks = [f_context_relevance]

        tru_recorder = TruCustomApp(
            app=app,
            app_name="RAG",
            app_version=version,
            feedbacks=feedbacks,
        )

        @retry(wait=wait_random_exponential(min=1, max=60), stop=stop_after_attempt(6))
        def run_with_backoff(doc):
            print("running", doc)
            return tru_recorder.with_record(app.query, question=doc)

        for record in data_dict:
            llm_response = run_with_backoff(record["query"])
            print(llm_response)

    run_dashboard(session, port=8000, force=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load Goldenset dataset in trulens")
    parser.add_argument(
        "input", nargs="+", help="Input JSON file paths. Accepts multiple files"
    )
    args = parser.parse_args()
    data = load_dataset(args.input)
    load_trulens(data)
