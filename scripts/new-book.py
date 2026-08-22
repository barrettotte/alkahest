"""Create a minimal independent book repository from the Alkahest engine."""

import argparse
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR / "lib"))

from alkahest.common import ContractError
from alkahest.new_book import create_new_book


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Create a minimal book repository from the reusable Alkahest engine."
    )
    parser.add_argument("--destination", required=True, help="new repository path")
    parser.add_argument("--title", required=True, help="book title")
    parser.add_argument("--author", required=True, help="author display name")
    parser.add_argument("--book-id", help="lowercase kebab-case work identity")
    parser.add_argument("--subtitle", help="book subtitle")
    parser.add_argument("--language", help="primary language tag (default: en-US)")
    parser.add_argument("--created", help="creation date as YYYY-MM-DD (default: today)")
    return parser.parse_args()


def main():
    arguments = parse_arguments()
    result = create_new_book(
        SCRIPT_DIR.parent,
        arguments.destination,
        title=arguments.title,
        author=arguments.author,
        book_id=arguments.book_id,
        subtitle=arguments.subtitle,
        language=arguments.language,
        created=arguments.created,
    )
    options = result["options"]
    print(
        f"created: {result['destination']} "
        f"({result['files']} files; id {options['id']}; {options['epub_identifier']})"
    )


if __name__ == "__main__":
    try:
        main()
    except (ContractError, OSError, UnicodeError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)
