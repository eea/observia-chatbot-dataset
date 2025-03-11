import os
import datetime

from dotenv import load_dotenv

from langfuse import Langfuse

load_dotenv()

langfuse = Langfuse(
    secret_key=os.environ["LANGFUSE_SECRET_KEY"],
    public_key=os.environ["LANGFUSE_PUBLIC_KEY"],
    host=os.environ["LANGFUSE_HOST"],
)

API_KEY = os.environ["API_KEY"]
API_URL = os.environ["API_URL"]


model = "meta-llama/Llama-3.3-70B-Instruct"

with open("evaluation_config-small.json", "r") as f:
    evaluation_criteria = json.load(f)["evaluation_criteria"]


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


def make_prompt(criterion, question, answer):
    sys_prompt = "You are an AI evaluator. Rate responses based on given criteria.\n"
    sys_prompt += (
        criterion["sys_prompt"].format(
            question=question, response=answer) + "\n"
    )

    for i, label in enumerate(criterion["score_labels"]):
        sys_prompt += f"{i}: {label}\n"

    user_prompt = criterion["user_prompt"].format(
        question=question, response=answer)
    return [sys_prompt, user_prompt]


def evaluate_response_req(question, answer, llm_client):
    """
    Evaluates a response based on multiple criteria using LiteLLM API.
    Returns a dictionary of evaluation scores.
    """
    scores = {}

    for criterion in evaluation_criteria:
        sys_prompt, user_prompt = make_prompt(criterion, question, answer)

        try:
            resp = make_llm_call(
                sys_prompt, user_prompt, model=model, llm_client=llm_client
            ).strip()
        except Exception as e:
            print(f"Error evaluating {criterion['name']}: {e}")
            scores[criterion["name"]] = "Error"
            continue

        for score in criterion["scale"]:
            if f"{score}" in llm_response:
                scores[criterion["name"]] = score
                break
        else:
            # Handle unexpected responses
            scores[criterion["name"]] = "N/A"

        time.sleep(1)  # Avoid overwhelming the server

    return scores


def main():
    traces = langfuse.fetch_traces(session_id="GS")
    # print (traces.data)

    now = datetime.datetime.now()
    print(now)

    llm_client = openai.OpenAI(
        api_key=API_KEY,
        base_url=API_URL,
    )

    for idx, trace in enumerate(traces.data):
        # if trace.id in ["88f8ce1d-2c79-41f9-b672-20c6a9e6e5b0", "3c897c61-5e0d-4b78-b8bb-b0b5065fecb0"]:
        #     print("already done, skip")
        #     continue

        print("----")
        print(idx)
        print("----")
        print(trace.id)
        question = trace.input["question"]
        answer = trace.output["answer"]
        print(question)
        #    print(answer)
        scores = evaluate_response_req(question, answer, llm_client)

        # for score in scores.keys():
        #     langfuse.score(trace_id=trace.id, name=score,
        #                    value=str(scores[score]))

        #        print(score)
        #        print(scores[score])
        now = datetime.datetime.now()
        print(now)

    print("done")


if __name__ == "__main__":
    main()
