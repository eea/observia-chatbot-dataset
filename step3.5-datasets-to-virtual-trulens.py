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


def custom_feedback(query, response, contexts):
    # print(f"\n---=Query: {query}\n")
    # print(f"\n---=Response: {response}\n")
    # print(f"\n---=Contezts: {contexts}\n")
    # print(f"Custom Feedback for {question}")
    # print(f"Custom Response for {response}")
    return (1.0 / (1.0 + len(query) * len(query)) * 100, {"reasons": "de-aia"})


def load_trulens(in_data):
    from trulens.apps.virtual import VirtualRecord
    from trulens.apps.virtual import TruVirtual
    from trulens.apps.virtual import VirtualApp

    session = TruSession()
    session.reset_database()

    retriever = Select.RecordCalls.retriever

    synthesizer = Select.RecordCalls.synthesizer
    generation = synthesizer.generate

    for version in in_data.keys():
        df = in_data[version]
        data_dict = df.to_dict("records")
        records = [
            VirtualRecord(
                main_input=rec["query"],
                main_output=rec["response"],
                calls={
                    retriever: dict(
                        args=[rec["query"]],
                        rets=rec["contexts"],
                    ),
                    generation: dict(
                        args=[""" to be filled in """],
                        rets=rec["response"],
                    ),
                },
            )
            for rec in data_dict
        ]

        f_coherence = Feedback(
            provider.coherence_with_cot_reasons,
            name="Coherence COT",
        ).on_output()

        f_relevance = Feedback(
            provider.relevance_with_cot_reasons,
            name="Relevance COT",
        ).on_input_output()

        # # See https://www.trulens.org/component_guides/evaluation/feedback_selectors/selecting_components/
        # f_custom = (
        #     Feedback(custom_feedback, name="Custom feedback")
        #     .on_input_output()
        #     # .on(
        #     #     Select.RecordCalls.retriever.args.query
        #     # )
        #     .on(Select.RecordCalls.retriever.rets)
        # )

        feedbacks = [f_coherence, f_relevance]
        virtual_app = VirtualApp()

        tru_recorder = TruVirtual(
            app=virtual_app,
            app_name="RAG",
            app_version=version,
            feedbacks=feedbacks,
            # feedback_mode="deferred",  # optional
        )

        for i, record in enumerate(records):
            tru_recorder.add_record(record)

            # .on_input()
            # .on(context)
            # .on(Select.RecordInput)
            # .on(Select.RecordOutput)

    session.start_evaluator()
    run_dashboard(session, port=8000, force=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load Goldenset dataset in trulens")
    parser.add_argument(
        "input", nargs="+", help="Input JSON file paths. Accepts multiple files"
    )
    args = parser.parse_args()
    data = load_dataset(args.input)
    load_trulens(data)
