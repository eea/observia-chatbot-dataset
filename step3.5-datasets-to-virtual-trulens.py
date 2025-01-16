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



    session = TruSession()
    session.reset_database()

    for name, df in data.items():
        virtual_app = VirtualApp()
        context = VirtualApp.select_context()
        # Question/statement relevance between question and each context chunk.
        # f_context_relevance = (
        #     Feedback(
        #         provider.context_relevance_with_cot_reasons, name="Context Relevance"
        #     )
        #     .on_input()
        #     .on(context)
        # )
        #
        # # Define a groundedness feedback function
        # f_groundedness = (
        #     Feedback(
        #         provider.groundedness_measure_with_cot_reasons, name="Groundedness"
        #     )
        #     .on(context.collect())
        #     .on_output()
        # )
        #
        # # Question/answer relevance between overall question and answer.
        # f_qa_relevance = Feedback(
        #     provider.relevance_with_cot_reasons, name="Answer Relevance"
        # ).on_input_output()
        # f_in_coherence = Feedback(
        #     provider.coherence_with_cot_reasons, name="Input Coherence"
        # ).on_input()

        # f_input_sentiment = Feedback(
        #     provider.sentiment_with_cot_reasons, name="Input Sentiment"
        # ).on_input()
        #
        # f_output_sentiment = Feedback(
        #     provider.sentiment_with_cot_reasons, name="Output Sentiment"
        # ).on_output()

        f_coherence = Feedback(
            provider.coherence_with_cot_reasons, name="Coherence"
        ).on_output()

        virtual_recorder = TruVirtual(
            app_name="RAG",
            app_version=name,
            app=virtual_app,
            feedbacks=[
                # f_in_coherence,
                f_coherence,
                # f_input_sentiment,
                # f_output_sentiment,
            ],
            # feedbacks=[f_context_relevance, f_groundedness, f_qa_relevance],
        )
        virtual_recorder.add_dataframe(df)

    run_dashboard(session, port=8000, force=True)


def load_trulens2(data):
    virtual_app = VirtualApp()
    context = virtual_app.select_context()

#    f_context_relevance = (
#      Feedback(
#        provider.context_relevance_with_cot_reasons, name="Context Relevance"
#      )
#      .on_input()
#      .on(context)
#    )

    # f_context_relevance = (
    #   Feedback(
    #     provider.context_relevance_with_cot_reasons, name="Context Relevance"
    #   )
    #   .on_input()
    #   .on(context)
    # )

#    Question/statement relevance between question and each context chunk.
    f_context_relevance1 = (
        Feedback(
            provider.context_relevance_with_cot_reasons, name="Context Relevance1"
        )
        .on_input()
        .on(context)
    )
    

    f_context_relevance2 = (
        Feedback(
            provider.context_relevance_with_cot_reasons, name="Context Relevance2"
        )
        .on_input()
        .on(context)
    )

    feedbacks = [f_context_relevance1, f_context_relevance2]
    session = TruSession()
    session.reset_database()


    run_dashboard(session, port=8000, force=True)



    virtual_recorder1 = TruVirtual(
      app_name="gptlab",
      app_version='datasets/gs.json',
      app=virtual_app,
      feedbacks=feedbacks
    )
    virtual_records1 = virtual_recorder1.add_dataframe(data['datasets/gs.json'])
    import pdb; pdb.set_trace()

    virtual_recorder2 = TruVirtual(
      app_name="gptlab",
      app_version='datasets/gs.json 2',
      app=virtual_app,
      feedbacks=feedbacks
    )
    virtual_records2 = virtual_recorder2.add_dataframe(data['datasets/gs.json'])

    virtual_recorder3 = TruVirtual(
      app_name="gptlab",
      app_version='datasets/gs.json 3',
      app=virtual_app,
      feedbacks=feedbacks
    )
    virtual_records3 = virtual_recorder3.add_dataframe(data['datasets/gs.json'])

def load_trulens3(in_data):
    session = TruSession()
    session.reset_database()

    from trulens.apps.virtual import VirtualRecord
    from trulens.core import Select
    retriever_component = Select.RecordCalls.retriever

    context_call = retriever_component.get_context


    virtual_app = dict(
        llm=dict(
            modelname="some llm component model name"
        ),
        template="information about the template I used in my app",
        debug="all of these fields are completely optional"
    )

    virtual_app = VirtualApp(virtual_app) # can start with the prior dictionary
    virtual_app[Select.RecordCalls.llm.maxtokens] = 1024

    df = in_data['datasets/gs.json']
    
    data_dict = df.to_dict('records')

    data = []
    import pdb; pdb.set_trace()
    for record in data_dict:
        rec = VirtualRecord(
            main_input=record['query'],
            main_output=record['response'],
            calls=
                {
                    context_call: dict(
                        args=[record['query']],
                        rets=[record['contexts']]
                    )
                }
            )
        data.append(rec)
    import pdb; pdb.set_trace()
    context = context_call.rets[:]
    f_context_relevance = (
        Feedback(provider.context_relevance)
        .on_input()
        .on(context)
    )

    virtual_recorder = TruVirtual(
        app_name="a virtual app",
        app=virtual_app,
        feedbacks=[f_context_relevance]
    )

    for record in data:
        virtual_recorder.add_record(rec)

    run_dashboard(session, port=8000, force=True)





if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load Goldenset dataset in trulens")
    parser.add_argument(
        "input", nargs="+", help="Input JSON file paths. Accepts multiple files"
    )
    args = parser.parse_args()
    data = load_dataset(args.input)
#    load_trulens(data)
    load_trulens2(data)
#    load_trulens3(data)
