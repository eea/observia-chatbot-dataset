import argparse
import json
import pandas as pd


def json_to_excel(json_file, excel_file):
    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Prepare a list of rows for the Excel sheet
    rows = []
    for i, question in enumerate(data["question"]):
        gts = "\n".join(data["ground_truths"][i])
        answer = data["answer"][i]

        # Add the topic and keywords to the first row
        rows.append([question, answer, gts])

    # Create a DataFrame from the rows
    df = pd.DataFrame(rows, columns=["Question", "Answer", "Ground Truth"])

    # Save the DataFrame to an Excel file
    df.to_excel(excel_file, index=False, engine="openpyxl")


def main():
    parser = argparse.ArgumentParser(
        description="Convert a JSON file to an Excel file."
    )
    parser.add_argument("input", help="Path to the input JSON file.")
    parser.add_argument("output", help="Path to the output Excel file.")
    args = parser.parse_args()

    json_to_excel(args.input, args.output)
    print(f"Excel file '{args.output}' has been created.")


if __name__ == "__main__":
    main()

