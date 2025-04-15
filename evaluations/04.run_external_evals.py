import datetime
import json
import os
import requests
import time

from utils import load_jsonl

from dotenv import load_dotenv
load_dotenv()

jsons_folder = os.environ.get('JSONS_FOLDER', 'tmp')


external_llm_host = os.environ.get("EXTERNAL_LLM_HOST")


external_llm_key = os.environ.get("EXTERNAL_LLM_KEY")
external_llm_model = os.environ.get("EXTERNAL_LLM_MODEL")


with open("evaluation-config.json", "r") as f:
    evaluation_criteria = json.load(f)["evaluation_criteria"]


def evaluate_response_req(question, answer):
    """
    Evaluates a response based on multiple criteria using LiteLLM API.
    Returns a dictionary of evaluation scores.
    """
    scores = {}
    for criterion in evaluation_criteria:
        prompt = criterion["prompt"].format(question=question, response=answer)

        payload = {
            "model": external_llm_model ,  # Adjust based on your local LiteLLM model
            "messages": [
                {"role": "system", "content": "You are an AI evaluator. Rate responses based on given criteria."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.2  # Low temperature for consistent scoring
        }

        headers = {
            "Authorization": f"Bearer {external_llm_key}",
            "Content-Type": "application/json"
        }
        try:
            response = requests.post(f"{external_llm_host}/chat/completions", json=payload, headers=headers)
            response_json = response.json()
            llm_response = response_json["choices"][0]["message"]["content"].strip()

            # Extract numeric rating (0-3) from LLM response
            for score in criterion["scale"]:
                if f"{score}" in llm_response:
                    scores[criterion["name"]] = score
                    break
            else:
                scores[criterion["name"]] = "N/A"  # Handle unexpected responses

            time.sleep(1)  # Avoid overwhelming the server

        except Exception as e:

            print(f"Error evaluating {criterion['name']}: {e}")
            scores[criterion["name"]] = "Error"

    return scores




def eval_external(data):
    with open(os.path.join(jsons_folder, "04.external.jsonl"), "w") as f:
        cnt = 0

        for trace in data:
            now = datetime.datetime.now()
            print(f"{cnt} - {now}")

            cnt+=1
            question = trace["question"]
            answer = trace["answer"]
            scores = evaluate_response_req(question, answer)
            res = {"question": question }
            for key in scores.keys():
                score_mapping = {}
                for eval_crit in evaluation_criteria:
                    if eval_crit["name"] == key:
                        score_mapping = eval_crit["score_mapping"]
                score_str = str(scores[key])
                res[f"{key}_numeric"] = score_mapping[score_str]["nr"]
                res[f"{key}_text"] = score_mapping[score_str]["str"]
            f.write(json.dumps(res) + "\n")

if __name__ == "__main__":
    qas = load_jsonl(json.path.join(jsons_folder, "02.qa.jsonl"))

    eval_external(qas)
