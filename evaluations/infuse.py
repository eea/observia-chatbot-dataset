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


def evaluate_response_req(question, answer):
    """
    Evaluates a response based on multiple criteria using LiteLLM API.
    Returns a dictionary of evaluation scores.
    """
    scores = {}

    for criterion in evaluation_criteria:
        # Format the evaluation prompt
        prompt = criterion["prompt"].format(question=question, response=answer)

        # Prepare the request payload
        payload = {
            # Adjust based on your local LiteLLM model
            "model": "meta-llama/Llama-3.3-70B-Instruct",
            "messages": [
                {
                    "role": "system",
                    "content": "You are an AI evaluator. Rate responses based on given criteria.",
                },
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,  # Low temperature for consistent scoring
        }
        # import ipdb; ipdb.set_trace()

        # Set headers with access key
        headers = {
            "Authorization": f"Bearer {LITELLM_ACCESS_KEY}",
            "Content-Type": "application/json",
        }
        #        print(headers)
        #        print(payload)
        try:
            # Send request to LiteLLM API
            response = requests.post(
                LITELLM_API_URL, json=payload, headers=headers)
            response_json = response.json()
            # print("-----------------------")
            # print(criterion['name'])
            # print(prompt)
            # print(response_json)
            # Extract response text
            llm_response = response_json["choices"][0]["message"]["content"].strip(
            )

            # Extract numeric rating (0-3) from LLM response
            for score in criterion["scale"]:
                if f"{score}" in llm_response:
                    scores[criterion["name"]] = score
                    break
            else:
                # Handle unexpected responses
                scores[criterion["name"]] = "N/A"

            time.sleep(1)  # Avoid overwhelming the server

        except Exception as e:
            print(f"Error evaluating {criterion['name']}: {e}")
            scores[criterion["name"]] = "Error"

    return scores


def main():
    traces = langfuse.fetch_traces(session_id="GS")
    # print (traces.data)
    idx = 0

    now = datetime.datetime.now()
    print(now)

    for trace in traces.data:
        # if trace.id in ["88f8ce1d-2c79-41f9-b672-20c6a9e6e5b0", "3c897c61-5e0d-4b78-b8bb-b0b5065fecb0"]:
        #     print("already done, skip")
        #     continue

        print("----")
        print(idx)
        idx += 1
        print("----")
        print(trace.id)
        question = trace.input["question"]
        answer = trace.output["answer"]
        print(question)
        #    print(answer)
        scores = evaluate_response_req(question, answer)

        for score in scores.keys():
            langfuse.score(trace_id=trace.id, name=score,
                           value=str(scores[score]))

        #        print(score)
        #        print(scores[score])
        now = datetime.datetime.now()
        print(now)

    print("done")


if __name__ == "__main__":
    main()
