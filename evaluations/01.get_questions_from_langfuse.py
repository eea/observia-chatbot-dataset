import json
import os
from dotenv import load_dotenv
load_dotenv()
import utils

GS_ORIG = os.environ["LANGFUSE_GOLDENSET_ORIGINAL"]


langfuse = utils.init_langfuse()
def fetch_traces(dest_file):
    cnt = 0
    with open(dest_file, "w") as f_dest:
        page = 1
        while True:
            traces = langfuse.fetch_traces(page=page, limit=50, session_id=GS_ORIG)
            if len(traces.data) == 0:
                break
            for trace in traces.data:
                question = trace.input["question"]
                main_row = {'cnt':cnt, 'question': question}
                cnt+=1
                f_dest.write(json.dumps(main_row) + "\n")
            page+=1


def ensure_folder_exsits(directory):
    if not os.path.isdir(directory):
        os.makedirs(directory)

if __name__ == "__main__":
    dest_folder = os.environ.get('JSONS_FOLDER', 'tmp')
    ensure_folder_exsits(dest_folder)
    fetch_traces(os.path.join(dest_folder, "01.questions.jsonl"))
