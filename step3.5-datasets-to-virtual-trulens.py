import argparse
import json
import pandas as pd
from trulens.providers.openai import OpenAI
from trulens.core import Feedback
from trulens.apps.virtual import VirtualApp
from trulens.core import TruSession
from trulens.dashboard.run import run_dashboard
from trulens.apps.virtual import TruVirtual


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


def load_trulens(in_data):
    session = TruSession()
    session.reset_database()

    from trulens.apps.virtual import VirtualRecord
    from trulens.core import Select

    retriever_component = Select.RecordCalls.retriever

    context_call = retriever_component.get_context

    for version in in_data.keys():
        virtual_app = VirtualApp()  # can start with the prior dictionary
        virtual_app[Select.RecordCalls.llm.maxtokens] = 1024
        virtual_app.app_id = "RAG"
        virtual_app.app_name = "RAG"
        virtual_app.app_version = version

        # session.add_app(virtual_app)

        df = in_data[version]
        data_dict = df.to_dict("records")

        records = []
        for record in data_dict:
            rec = VirtualRecord(
                main_input=record["query"],
                main_output=record["response"],
                calls={
                    context_call: {
                        "args": [record["query"]],
                        "rets": record["contexts"],
                    }
                },
            )
            records.append(rec)

        context = context_call.rets[:]
        f_context_relevance = (
            Feedback(provider.context_relevance, name="Context Relevance")
            .on_input()
            .on(context)
        )

        feedbacks = [f_context_relevance]
        virtual_recorder = TruVirtual(
            app_name="RAG",
            app=virtual_app,
            app_version=version,
            feedbacks=feedbacks,
        )

        # import pdb
        #
        # pdb.set_trace()
        for record in records:
            feedback_results = session.run_feedback_functions(
                record, feedbacks, virtual_app
            )
            fr = list(feedback_results)
            # .add_feedbacks(feedback_results)
            virtual_recorder.add_record(record)

    run_dashboard(session, port=8000, force=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load Goldenset dataset in trulens")
    parser.add_argument(
        "input", nargs="+", help="Input JSON file paths. Accepts multiple files"
    )
    args = parser.parse_args()
    data = load_dataset(args.input)
    load_trulens(data)
