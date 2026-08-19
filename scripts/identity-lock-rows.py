"""Emit active identity-lock records as shell-friendly rows."""

import json
import sys
from pathlib import Path


data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
for entry in data["identities"]:
    if entry.get("status") == "active":
        print("|".join(entry[field] for field in ("namespace", "kind", "id", "source")))
