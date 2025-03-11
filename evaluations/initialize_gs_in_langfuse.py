import json
import pandas as pd
from langfuse import Langfuse
import os

langfuse = Langfuse(
    secret_key=os.environ["LANGFUSE_SECRET_KEY"],
    public_key=os.environ["LANGFUSE_PUBLIC_KEY"],
    host=os.environ["LANGFUSE_HOST"] 
)

excel_file = 'dataset/Observia Goldenset.xlsx'
json_files = ['dataset/Copernicus Land (CLMS)-goldenset.json',
            'dataset/EEA Website-goldenset.json',
            'dataset/GS_CEMS-goldenset.json',
            'dataset/GS_ECMWF-goldenset.json',
            'dataset/GS_ESA-goldenset.json',
            'dataset/GS_MOI-goldenset.json',
            'dataset/Copernicus WEkEO-goldenset.json',
            'dataset/GS_ai4copernicus-project.eu-goldenset.json',
            'dataset/GS_DEFIS-goldenset.json',
            'dataset/GS_EEA-goldenset.json',
            'dataset/GS_EUMETSAT-goldenset.json',
            'dataset/GS_SATCEN-goldenset.json']

columns_to_check = ["Evaluation", "Comment"]
def load_gs_json(gs_jsons):
    frames = []
    for gs_json in gs_jsons:
        with open(gs_json, "r", encoding="utf-8") as f:
            data = json.load(f)
        df = pd.DataFrame(data)
        frames.append(df)
    full_df = pd.concat(frames)
    return full_df


def find_contexts(question, all_contexts):
    found = False
    contexts = []
    for index, row in all_contexts.iterrows():
        if row.get("question") == question:
            found = True
            contexts = row.get("contexts")
            break
    return contexts

def init_trace(query, response, context, session):
    return langfuse.trace(name=query, session_id=session, input={"question":query, "context":context}, output={"answer": response})

def init_traces_for_sheets(sheets):
    for sheet in sheets.keys():
        print(f"init sheet: {sheet}")
        for index, row in sheets[sheet].iterrows():
            trace = init_trace(query=row['query'], response=row['response'], context=row['contexts'], session="GS")


def load_dataset_from_excel(gs_excel, all_contexts):
    xl = pd.ExcelFile(gs_excel)
    print (xl.sheet_names)
    sheets = {}
    for sheet_name in xl.sheet_names[1:]:
        dataset = []
        print(sheet_name)
        sheet = xl.parse(sheet_name)
        for index, row in sheet.iterrows():
            should_add = True
            for col in columns_to_check:
                if not pd.isna(row.get(col)):
                    if not row.get("Evaluation","3: good question - good answer") == "3: good question - good answer":
                        should_add = False
            if should_add:
                if pd.isna(row.get("Question")):
                    break
                question = row.get("Question").strip()
                answer = row.get("Answer")

                contexts = find_contexts(question, all_contexts)
                new_row = {"query":question,"response":answer, "contexts": contexts}
                dataset.append(new_row)
        sheets[sheet_name] = pd.DataFrame(dataset)
    print("done")
    return sheets

all_contexts = load_gs_json(gs_jsons = json_files)
print("contexts loaded")
sheets = load_dataset_from_excel(gs_excel = excel_file, all_contexts = all_contexts)
print("sheets loaded and merged with contexts")
init_traces_for_sheets(sheets)
print("done")