import json
import sys
import argparse


def extract_primary_questions(input_path: str, output_path: str) -> None:
    """
    Read JSON file containing questions data and write primary questions to output file.

    Args:
        input_path: Path to input JSON file
        output_path: Path to output text file

    Raises:
        FileNotFoundError: If input file doesn't exist
        json.JSONDecodeError: If input file isn't valid JSON
        KeyError: If JSON objects don't have expected structure
    """
    try:
        # Read and parse JSON file
        with open(input_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Extract primary questions
        primary_questions = [item["primary_question"] for item in data]

        # Write questions to output file
        with open(output_path, "w", encoding="utf-8") as f:
            f.write("\n".join(primary_questions))

    except FileNotFoundError:
        print(f"Error: Input file '{input_path}' not found")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: '{input_path}' contains invalid JSON")
        sys.exit(1)
    except KeyError as e:
        print("Error: JSON object missing required 'primary_question' field")
        sys.exit(1)


def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(
        description="Extract primary questions from JSON file"
    )
    parser.add_argument("input_file", help="Path to input JSON file")
    parser.add_argument("output_file", help="Path to output text file")

    # Parse arguments
    args = parser.parse_args()

    # Process the files
    extract_primary_questions(args.input_file, args.output_file)


if __name__ == "__main__":
    main()
