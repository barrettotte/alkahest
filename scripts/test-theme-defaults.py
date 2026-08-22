"""Exercise theme schema, inheritance, determinism, and stale-output failures."""

import copy
import json
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR / "lib"))

from alkahest.theme import ThemeError, sync_project_theme, theme_outputs


ROOT = SCRIPT_DIR.parent
DEFAULTS = json.loads(
    (ROOT / "book/alkahest-theme-defaults.json").read_text(encoding="utf-8")
)
OVERRIDES = {"schema_version": 1, "colors": {}, "typography": {}}


def encoded(value):
    return (json.dumps(value, sort_keys=True) + "\n").encode("utf-8")


def expect_failure(name, expected, callback):
    try:
        callback()
    except ThemeError as error:
        if expected not in str(error):
            raise RuntimeError(
                f"error: theme fixture {name} missed {expected!r}: {error}"
            ) from error
    else:
        raise RuntimeError(f"error: theme fixture {name} unexpectedly passed")


def document_failure(name, expected, mutate_defaults=None, mutate_overrides=None):
    defaults = copy.deepcopy(DEFAULTS)
    overrides = copy.deepcopy(OVERRIDES)
    if mutate_defaults is not None:
        mutate_defaults(defaults)
    if mutate_overrides is not None:
        mutate_overrides(overrides)
    expect_failure(
        name,
        expected,
        lambda: theme_outputs(encoded(defaults), encoded(overrides)),
    )


def main():
    document_failure(
        "defaults-schema",
        "schema_version must be 1",
        mutate_defaults=lambda value: value.update(schema_version=2),
    )
    document_failure(
        "missing-default",
        "default colors",
        mutate_defaults=lambda value: value["colors"].pop("accent"),
    )
    document_failure(
        "unknown-color",
        "unknown field",
        mutate_overrides=lambda value: value["colors"].update(neon="#00ff00"),
    )
    document_failure(
        "invalid-color",
        "#RRGGBB",
        mutate_overrides=lambda value: value["colors"].update(primary="blue"),
    )
    document_failure(
        "unknown-font",
        "unknown field",
        mutate_overrides=lambda value: value["typography"].update(footnote="Serif"),
    )
    document_failure(
        "empty-font",
        "nonempty font-family",
        mutate_overrides=lambda value: value["typography"].update(body=""),
    )
    document_failure(
        "unsafe-font",
        "unsupported characters",
        mutate_overrides=lambda value: value["typography"].update(body="Serif}; bad"),
    )

    defaults_before = copy.deepcopy(DEFAULTS)
    overrides = copy.deepcopy(OVERRIDES)
    overrides["colors"]["primary"] = "#7c2d12"
    resolved, first = theme_outputs(encoded(DEFAULTS), encoded(overrides))
    _second_resolved, second = theme_outputs(encoded(DEFAULTS), encoded(overrides))
    if first != second or DEFAULTS != defaults_before:
        raise RuntimeError("error: theme resolution is nondeterministic or mutates defaults")
    if resolved["colors"]["line"] != DEFAULTS["colors"]["line"]:
        raise RuntimeError("error: partial theme override did not inherit shared defaults")

    with tempfile.TemporaryDirectory(prefix="alkahest-theme-fixture.") as temporary:
        root = Path(temporary)
        book = root / "book"
        (book / ".alkahest").mkdir(parents=True)
        (book / ".alkahest/theme-defaults.json").write_bytes(encoded(DEFAULTS))
        (book / "theme.json").write_bytes(encoded(OVERRIDES))
        sync_project_theme(root)
        sync_project_theme(root, check=True)
        (book / "generated/theme-overrides.css").write_bytes(b"stale\n")
        expect_failure(
            "stale-adapter",
            "missing or stale",
            lambda: sync_project_theme(root, check=True),
        )
    print(
        "ok: theme-default fixtures "
        "(partial inheritance and deterministic adapters; 7 schema and 1 stale failure rejected)"
    )


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, ThemeError, UnicodeError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)
