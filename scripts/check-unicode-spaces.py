"""Verify documented nonbreaking-space forms survive rendered output."""

import argparse
from pathlib import Path


parser = argparse.ArgumentParser()
parser.add_argument("mode", choices=("html", "epub"))
parser.add_argument("path")
args = parser.parse_args()
text = Path(args.path).read_text(encoding="utf-8")
valid = "Français\u202f:" in text
if args.mode == "epub": valid = valid and "25\u00a0MHz" in text and "Figure\u00a01" in text
raise SystemExit(not valid)
