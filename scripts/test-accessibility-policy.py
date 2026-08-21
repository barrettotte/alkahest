"""Exercise valid and invalid WCAG policy and manual-evidence contracts."""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
CHECKER = ROOT / "scripts" / "check-accessibility-policy.py"


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def prepare(parent, name):
    case = parent / name
    (case / "media").mkdir(parents=True)
    files = {
        "policy": ROOT / "config" / "accessibility" / "wcag-2.2-aa.json",
        "evidence": ROOT / "book" / "accessibility-review.json",
        "theme": ROOT / "book" / "theme" / "alkahest.scss",
        "html_config": ROOT / "book" / "_quarto-html.yml",
        "include": ROOT / "book" / "theme" / "accessibility-before-body.html",
    }
    for name_key, source in files.items():
        target = case / source.name
        shutil.copy2(source, target)
        files[name_key] = target
    for source in (
        ROOT / "book" / "media" / "orbit-animation.html",
        ROOT / "book" / "media" / "vector-interactive.html",
    ):
        shutil.copy2(source, case / "media" / source.name)
    files["media_root"] = case / "media"
    files["animation"] = case / "media" / "orbit-animation.html"
    return files


def run(files):
    environment = os.environ.copy()
    for variable, key in (
        ("ALKAHEST_ACCESSIBILITY_POLICY", "policy"),
        ("ALKAHEST_ACCESSIBILITY_EVIDENCE", "evidence"),
        ("ALKAHEST_ACCESSIBILITY_THEME", "theme"),
        ("ALKAHEST_ACCESSIBILITY_HTML_CONFIG", "html_config"),
        ("ALKAHEST_ACCESSIBILITY_INCLUDE", "include"),
        ("ALKAHEST_ACCESSIBILITY_MEDIA_ROOT", "media_root"),
    ):
        environment[variable] = str(files[key])
    return subprocess.run(
        [sys.executable, str(CHECKER)],
        env=environment,
        text=True,
        capture_output=True,
        check=False,
    )


def expect_failure(parent, name, expected, mutation):
    files = prepare(parent, name)
    mutation(files)
    result = run(files)
    output = result.stdout + result.stderr
    if result.returncode == 0:
        raise RuntimeError(f"error: accessibility policy fixture {name} passed")
    if expected not in output:
        raise RuntimeError(
            f"error: accessibility policy fixture {name} missed {expected!r}:\n{output}"
        )


def edit_json(key, mutate):
    def apply(files):
        value = json.loads(files[key].read_text(encoding="utf-8"))
        mutate(value)
        write_json(files[key], value)

    return apply


def edit_text(key, old, new):
    def apply(files):
        content = files[key].read_text(encoding="utf-8")
        if old not in content:
            raise RuntimeError(f"error: fixture mutation cannot find {old!r}")
        files[key].write_text(content.replace(old, new, 1), encoding="utf-8")

    return apply


def main():
    with tempfile.TemporaryDirectory(prefix="alkahest-accessibility-policy.") as temp:
        parent = Path(temp)
        valid = prepare(parent, "valid")
        result = run(valid)
        if result.returncode:
            raise RuntimeError(
                "error: valid accessibility policy fixture failed:\n"
                + result.stdout
                + result.stderr
            )
        expect_failure(
            parent,
            "engine-drift",
            "must be pinned to axe-core 4.13.0",
            edit_json("policy", lambda value: value["engine"].update(version="latest")),
        )
        expect_failure(
            parent,
            "missing-category",
            "complete policy set",
            edit_json("policy", lambda value: value["manual_categories"].pop()),
        )
        expect_failure(
            parent,
            "missing-evidence",
            "cover every policy category exactly once",
            edit_json("evidence", lambda value: value["reviews"].pop()),
        )
        expect_failure(
            parent,
            "short-rationale",
            "needs a rationale",
            edit_json(
                "evidence",
                lambda value: value["reviews"][0].update(rationale="Later."),
            ),
        )
        expect_failure(
            parent,
            "unsupported-claim",
            "requires every manual category to pass",
            edit_json("evidence", lambda value: value.update(conformance_claim=True)),
        )
        expect_failure(
            parent,
            "incomplete-pass",
            "needs an ISO test date",
            edit_json(
                "evidence", lambda value: value["reviews"][0].update(status="pass")
            ),
        )
        expect_failure(
            parent,
            "contrast-drift",
            "theme contrast for captions and secondary text",
            edit_text("theme", "$alkahest-muted: #64748b;", "$alkahest-muted: #aaaaaa;"),
        )
        expect_failure(
            parent,
            "missing-focus",
            "button:focus-visible",
            edit_text("theme", "button:focus-visible", "button:hover"),
        )
        expect_failure(
            parent,
            "missing-reduced-motion",
            "@media (prefers-reduced-motion: reduce)",
            edit_text(
                "theme",
                "@media (prefers-reduced-motion: reduce)",
                "@media (prefers-reduced-motion: no-preference)",
            ),
        )
        expect_failure(
            parent,
            "disabled-zoom",
            "must not disable browser zoom",
            edit_text(
                "html_config",
                "html-math-method: mathml",
                "html-math-method: mathml\n    maximum-scale=1",
            ),
        )
        expect_failure(
            parent,
            "missing-landmark",
            "needs a main landmark",
            edit_text("animation", "<main>", "<div>"),
        )
    print(
        "ok: accessibility policy fixtures "
        "(valid WCAG target, palette, theme, and review ledger; "
        "11 invalid contracts rejected)"
    )


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)
