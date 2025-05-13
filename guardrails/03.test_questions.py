import json
import os
import requests
from utils import load_jsonl

LLM_GUARDRAIL_ENDPOINT=os.environ.get("LLM_GUARDRAIL_ENDPOINT")
jsons_folder = os.environ.get('JSONS_FOLDER', 'tmp')

def test_question(question):
    payload = {
      "prompt": question
    }
    llm_guard_response = requests.post(LLM_GUARDRAIL_ENDPOINT, json=payload)
    error = None
    if llm_guard_response.ok:
        result = llm_guard_response.json()
        if not result.get("is_valid", False):
            error=llm_guard_response.text

    else:
        error=llm_guard_response.text
    return error

def eval_guardrails(questions, dest_file):
    cnt = 0
    with open(dest_file, "w") as f_dest:
        for question in questions:
            print(cnt)
            cnt += 1
            error = test_question(question['question'])
            if error:
                print (f"rejected: {question['question']} {question['name']}")
                main_row = {"cnt":question['cnt'],"question":question["question"], "error":error}
                f_dest.write(json.dumps(main_row) + "\n")

#        print (test_question(question['question']))

if __name__ == "__main__":
    dest_folder = os.environ.get('JSONS_FOLDER', 'tmp')

    print("GS")
#    gs_questions = load_jsonl(os.path.join(jsons_folder, "01.gs_questions.jsonl"))
#    eval_guardrails(gs_questions, os.path.join(dest_folder, "01.gs_guardrails.jsonl"))
    print("user")
    user_questions = load_jsonl(os.path.join(jsons_folder, "02.user_questions.jsonl"))
    eval_guardrails(user_questions, os.path.join(dest_folder, "02.user_guardrails.jsonl"))
