#!/bin/bash

# Check if a directory is provided as an argument
if [ -z "$1" ]; then
        echo "Usage: $0 <directory> <out_directory>"
        exit 1
fi

PYTHON="poetry run python"

# Get the full directory path and folder name
FULL_PATH="$1"
FOLDER_NAME=$(basename "$FULL_PATH")

OUT_PATH="$2"

QUESTIONS_JSON_FILE="${OUT_PATH}/${FOLDER_NAME}.json"
QUESTIONS_JSON_EN_FILE="${OUT_PATH}/${FOLDER_NAME}-en.json"
QUESTIONS_TXT_FILE="${OUT_PATH}/${FOLDER_NAME}.txt"
GS_JSON_FILE="${OUT_PATH}/${FOLDER_NAME}-goldenset.json"
OUT_CSV_FILE="${OUT_PATH}/${FOLDER_NAME}-goldenset.csv"

# Print the folder name (optional, for debugging)
echo "Dataset generating from: $FOLDER_NAME"

mkdir -p "$OUT_PATH"

echo "Making topic-based questions json file to ${QUESTIONS_JSON_FILE}"
#poetry run python step2.0-topic-generation.py "$FULL_PATH" "$QUESTIONS_JSON_FILE" 200

echo "Filtering non-English questions, output in ${QUESTIONS_JSON_EN_FILE}"
$PYTHON step2.1-filter-for-english.py "${QUESTIONS_JSON_FILE}" "${QUESTIONS_JSON_EN_FILE}"

echo "Writing questions text file to ${QUESTIONS_TXT_FILE}"
$PYTHON step2.2-extract-primary-questions.py "$QUESTIONS_JSON_EN_FILE" "$QUESTIONS_TXT_FILE"

echo "Making danswer-based dataset, saved to ${GS_JSON_FILE}"

$PYTHON step3.0-generate-danswer-dataset.py "$QUESTIONS_TXT_FILE" "$GS_JSON_FILE"

echo "Converting ${GS_JSON_FILE} to ${OUT_CSV_FILE}"

$PYTHON step4.dataset2xls.py "$GS_JSON_FILE" "$OUT_CSV_FILE"
