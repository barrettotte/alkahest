"""Normalize rendered HTML or PDF text for stable publication assertions."""

import argparse
import html
import re
import sys


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("html", "pdf"))
    arguments = parser.parse_args()
    text = sys.stdin.read()
    if arguments.mode == "html":
        text = re.sub(r"<[^>]+>", " ", text)
        text = html.unescape(text)
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"\s+([,.;:)])", r"\1", text)
        text = re.sub(r"([(])\s+", r"\1", text)
    else:
        text = re.sub(r"([^\W_])-[ \t]*\r?\n[ \t]*([^\W_])", r"\1-\2", text)
        text = re.sub("\u00ad\\s*", "", text)
        text = re.sub(r"\s+", " ", text)
        text = re.sub(r"/\s+", "/", text)
    sys.stdout.write(text)


if __name__ == "__main__": main()
