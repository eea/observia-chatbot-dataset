import json
import os
from dotenv import load_dotenv
load_dotenv()
import utils


langfuse = utils.init_langfuse()
def fetch_traces(dest_file):
    cnt = 0
    with open(dest_file, "w") as f_dest:
        page = 1
        while True:
            traces = langfuse.fetch_traces(page=page, limit=50)
            if len(traces.data) == 0:
                break
            for trace in traces.data:
                if trace.name.startswith('litellm-'):
                    continue
                question = ""
                for message in trace.input.get('messages',[]):
                    if message.get('role', '') == 'user':
                        content = message.get('content', '')
#                        import pdb; pdb.set_trace()
                        question = content.split("QUERY:\n")[-1].split("\nAnswer:\n")[0].split("Question:")[-1].strip()
                        cnt+=1
                        main_row = {'cnt':cnt, 'question': question, 'name': trace.name}
                        f_dest.write(json.dumps(main_row) + "\n")

#                        import pdb; pdb.set_trace()
#                return
#                question = trace.input["question"]
#                print(cnt)
#                main_row = {'cnt':cnt, 'question': question}
#                cnt+=1
#                f_dest.write(json.dumps(main_row) + "\n")
#            return
            page+=1


def ensure_folder_exsits(directory):
    if not os.path.isdir(directory):
        os.makedirs(directory)

if __name__ == "__main__":
    dest_folder = os.environ.get('JSONS_FOLDER', 'tmp')
    ensure_folder_exsits(dest_folder)
    fetch_traces(os.path.join(dest_folder, "02.user_questions.jsonl"))
