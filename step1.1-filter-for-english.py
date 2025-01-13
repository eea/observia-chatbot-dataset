"""Given a dataset json file, it filters records that are not in English"""

import json
import sys
from langid.langid import LanguageIdentifier, model


def filter_english_records(input_file, output_file):
    # Initialize the language identifier
    identifier = LanguageIdentifier.from_modelstring(model, norm_probs=True)

    with open(input_file, "r", encoding="utf-8") as infile:
        data = json.load(infile)

    filtered_data = []
    for record in data:
        # Check topic language
        topic_lang, topic_confidence = identifier.classify(record["topic"])

        # Check questions languages
        question_languages = [identifier.classify(q)[0] for q in record["questions"]]
        english_count = question_languages.count("en")

        # Keep the record if the topic and majority of questions are in English
        if topic_lang == "en" and english_count >= 3:
            filtered_data.append(record)

    # Write filtered data to output file
    with open(output_file, "w", encoding="utf-8") as outfile:
        json.dump(filtered_data, outfile, indent=2, ensure_ascii=False)
    print(f"Filtered records saved to {output_file}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python filter_records.py <input_file> <output_file>")
    else:
        input_file = sys.argv[1]
        output_file = sys.argv[2]
        filter_english_records(input_file, output_file)
