"""Normalize rendered HTML or PDF text for stable publication assertions."""

import argparse
import html
import re
import sys


def normalize(text, mode):
    """Normalize rendered HTML or PDF text for stable assertions."""
    if mode == "html":
        text = re.sub(r"<[^>]+>", " ", text)
        text = html.unescape(text)
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"\s+([,.;:)])", r"\1", text)
        return re.sub(r"([(])\s+", r"\1", text)
    text = re.sub(r"([^\W_])-[ \t]*\r?\n[ \t]*([^\W_])", r"\1-\2", text)
    text = re.sub("\u00ad\\s*", "", text)
    text = re.sub(r"\s+", " ", text)
    return re.sub(r"/\s+", "/", text)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("html", "pdf"))
    arguments = parser.parse_args()
    sys.stdout.write(normalize(sys.stdin.read(), arguments.mode))


if __name__ == "__main__":
    main()
