# Golden Dataset generation process

## Step 1: download the Vespa database

This works by connecting to the Postgresql database, getting a list of all document ids, then downloading all chunks for that document id.

The database connection information is hardcoded in the script, it may need adjusting.

```bash
python step1-download-vespa-database.py
```

## Step 2: generate topic-based questions

```bash
python step2.0-topic-generation.py data-download/GS_CEMS/ datasets/GS_CEMS-topics.json 200
```

## Step 2.1: filter only English questions (optional)

```bash
python step2.1-filter-for-english.py datasets/GS_CEMS-topics.json datasets/GS_CEMS-topics-en.json
```

## Step 2.2: extract the questions to a new text file

```bash
python step2.1-extract-primary-questions.py datasets/GS_CEMS-topics-en.json datasets/GS_CEMS-questions.txt
```

## Step 3: generate GoldenSet dataset

```bash
python step3.0-generate-danswer-dataset.py datasets/GS_CEMS-questions.txt datasets/GS_CEMS-goldenset.json
```

## Step 3.5: load multiple goldenset-style datasets in local Trulens

```bash
python step3.5-dataset-to-virtual-trulens.py dataset.json datasets/GS_CEMS-goldenset.json
```

## Step 4: convert GoldenSet to Excel

```bash
python step4.0-dataset2xls.py datasets/GS_CEMS-goldenset.json datasets/GS_CEMS-goldenset.xls
```
