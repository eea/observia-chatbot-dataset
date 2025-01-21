# Define variables
PYTHON = poetry run python

# Input variables
FULL_PATH = $(dir)
OUT_PATH = $(out_dir)
FOLDER_NAME = $(notdir $(patsubst %/,%,$(FULL_PATH)))

# Output files
QUESTIONS_JSON_FILE = $(OUT_PATH)/$(FOLDER_NAME).json
QUESTIONS_JSON_EN_FILE = $(OUT_PATH)/$(FOLDER_NAME)-en.json
QUESTIONS_TXT_FILE = $(OUT_PATH)/$(FOLDER_NAME).txt
GS_JSON_FILE = $(OUT_PATH)/$(FOLDER_NAME)-goldenset.json
OUT_XLS_FILE = $(OUT_PATH)/$(FOLDER_NAME)-goldenset.xls

# Check arguments
ifneq ($(strip $(dir)),)
ifneq ($(strip $(out_dir)),)
.DEFAULT_GOAL := all
else
$(error Usage: make dir=<directory> out_dir=<out_directory>)
endif
else
$(error Usage: make dir=<directory> out_dir=<out_directory>)
endif

# Targets
all: prepare_dir generate_questions filter_english extract_questions generate_danswer_dataset convert_to_xls

prepare_dir:
	@echo "Dataset generating from: $(FOLDER_NAME) to $(OUT_PATH)"
	mkdir -p $(OUT_PATH)

generate_questions:
	@echo "Making topic-based questions JSON file to $(QUESTIONS_JSON_FILE)"
	$(PYTHON) step2.0-topic-generation.py $(FULL_PATH) $(QUESTIONS_JSON_FILE) 200

filter_english:
	@echo "Filtering non-English questions, output in $(QUESTIONS_JSON_EN_FILE)"
	$(PYTHON) step2.1-filter-for-english.py $(QUESTIONS_JSON_FILE) $(QUESTIONS_JSON_EN_FILE)

extract_questions:
	@echo "Writing questions text file to $(QUESTIONS_TXT_FILE)"
	$(PYTHON) step2.2-extract-primary-questions.py $(QUESTIONS_JSON_EN_FILE) $(QUESTIONS_TXT_FILE)

generate_danswer_dataset:
	@echo "Making danswer-based dataset, saved to $(GS_JSON_FILE)"
	$(PYTHON) step3.0-generate-danswer-dataset.py $(QUESTIONS_TXT_FILE) $(GS_JSON_FILE)

convert_to_xls:
	@echo "Converting $(GS_JSON_FILE) to $(OUT_XLS_FILE)"
	$(PYTHON) step4.0-dataset2xls.py $(GS_JSON_FILE) $(OUT_XLS_FILE)

