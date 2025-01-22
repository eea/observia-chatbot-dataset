import argparse
import json
import pandas as pd


def json_to_excel(json_file, out_path):
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    rows = []
    for i, question in enumerate(data["question"]):
        gts = "\n".join(data["ground_truths"][i])
        urls = "\n".join(data["urls"][i])
        answer = data["answer"][i]

        rows.append([question, answer, gts, urls])

    df = pd.DataFrame(rows, columns=["Question", "Answer", "Ground Truth", "URLs"])

    df.to_excel(out_path, index=False, engine="openpyxl")


def main():
    parser = argparse.ArgumentParser(
        description="Convert a JSON file to an Excel file."
    )
    parser.add_argument(
        "input",
        nargs="+",
        help="Input JSON file paths. Accepts multiple files",
    )

    # parser.add_argument("output", help="Path to the output Excel file.")
    args = parser.parse_args()

    for path in args.input:
        output = f"{path.split('json')[0]}xls"
        json_to_excel(path, output)

        print(f"Excel file '{output}' has been created.")


if __name__ == "__main__":
    main()
