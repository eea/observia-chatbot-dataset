# Golden Dataset generation process

## Step one: download the Vespa database

This works by connecting to the Postgresql database, getting a list of all document ids, then downloading all chunks for that document id.

The database connection information is hardcoded in the script, it may need adjusting.

```bash
python step1-download-vespa-database.py
```

## Step two: generate topic-based questions

```bash
python step2-topic-generation.py data-download/GS_CEMS/ datasets/GS_CEMS-topics.json 200
```

## Step 2.1: extract the questions to a new text file

```bash
python step2.1-extract-primary-questions.py datasets/GS_CEMS-topics.json datasets/GS_CEMS-questions.txt
```
