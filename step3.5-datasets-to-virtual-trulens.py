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


def load_trulens(data):
    for name, df in data.items():
        virtual_app = VirtualApp()
        context = VirtualApp.select_context()
        # Question/statement relevance between question and each context chunk.
        f_context_relevance = (
            Feedback(
                provider.context_relevance_with_cot_reasons, name="Context Relevance"
            )
            .on_input()
            .on(context)
        )

        # Define a groundedness feedback function
        f_groundedness = (
            Feedback(
                provider.groundedness_measure_with_cot_reasons, name="Groundedness"
            )
            .on(context.collect())
            .on_output()
        )

        # Question/answer relevance between overall question and answer.
        f_qa_relevance = Feedback(
            provider.relevance_with_cot_reasons, name="Answer Relevance"
        ).on_input_output()
        virtual_recorder = TruVirtual(
            app_name="RAG",
            app_version=name,
            app=virtual_app,
            feedbacks=[f_context_relevance, f_groundedness, f_qa_relevance],
        )
        virtual_recorder.add_dataframe(df)

    session = TruSession()

    run_dashboard(session, port=8123, force=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load Goldenset dataset in trulens")
    parser.add_argument(
        "input", nargs="+", help="Input JSON file paths. Accepts multiple files"
    )
    args = parser.parse_args()
    data = load_dataset(args.input)
    load_trulens(data)
