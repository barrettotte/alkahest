"""Exercise valid and deliberately invalid controlled-reuse contracts."""

import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR.parents[1] / "src"))

from alkahest.common import ContractError
from alkahest.reuse import validate_reuse

FIXTURE = SCRIPT_DIR.parents[1] / "tests" / "reuse" / "base"


def load(root):
    return json.loads((root / "reusable-content.json").read_text(encoding="utf-8"))


def save(root, registry):
    (root / "reusable-content.json").write_text(
        json.dumps(registry, indent=2) + "\n", encoding="utf-8"
    )


def replace(root, relative, old, new):
    path = root / relative
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"error: reuse fixture edit did not match {old!r}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def registry_edit(callback):
    def mutate(root):
        registry = load(root)
        callback(registry)
        save(root, registry)

    return mutate


def append_fragment(root, text):
    path = root / "reuse/safety-disconnect.md"
    path.write_text(path.read_text(encoding="utf-8") + text, encoding="utf-8")
    registry = load(root)
    registry["items"]["reuse-safety-disconnect"]["sha256"] = hashlib.sha256(
        path.read_bytes()
    ).hexdigest()
    save(root, registry)


def expect_failure(name, expected, mutate):
    with tempfile.TemporaryDirectory(prefix=f"alkahest-reuse-{name}-") as temporary:
        root = Path(temporary)
        shutil.copytree(FIXTURE, root, dirs_exist_ok=True)
        mutate(root)
        try:
            validate_reuse(root)
        except ContractError as error:
            if expected not in str(error):
                raise RuntimeError(
                    f"error: reuse fixture {name} missed expected diagnostic '{expected}': {error}"
                ) from error
        else:
            raise RuntimeError(f"error: reuse fixture unexpectedly passed: {name}")


def main():
    validate_reuse(FIXTURE)
    items = lambda r: r["items"]
    cases = [
        ("version", "registry version must be 1", registry_edit(lambda r: r.update(version=2))),
        (
            "missing-kind",
            "has no legal specimen",
            registry_edit(lambda r: items(r)["reuse-rights-review"].update(kind="notice")),
        ),
    ]

    def invalid_id(root):
        registry = load(root)
        registry["items"]["bad-safety-disconnect"] = registry["items"].pop(
            "reuse-safety-disconnect"
        )
        save(root, registry)
        replace(root, "chapter.qmd", "reuse-safety-disconnect", "bad-safety-disconnect")

    cases.extend(
        (
            ("invalid-id", "invalid reusable-content ID 'bad-safety-disconnect'", invalid_id),
            (
                "unknown-field",
                "unknown field 'mystery'",
                registry_edit(
                    lambda r: items(r)["reuse-safety-disconnect"].update(mystery="value")
                ),
            ),
            (
                "duplicate-path",
                "path 'reuse/safety-disconnect.md' is registered more than once",
                registry_edit(
                    lambda r: items(r)["reuse-observed-value-definition"].update(
                        path="reuse/safety-disconnect.md"
                    )
                ),
            ),
            (
                "missing-file",
                "references missing fragment 'reuse/safety-disconnect.md'",
                lambda root: (root / "reuse/safety-disconnect.md").rename(
                    root / "reuse/missing.md"
                ),
            ),
            (
                "semantic-version",
                "invalid semantic version",
                registry_edit(
                    lambda r: items(r)["reuse-safety-disconnect"].update(version="latest")
                ),
            ),
            (
                "checksum-format",
                "invalid SHA-256",
                registry_edit(lambda r: items(r)["reuse-safety-disconnect"].update(sha256="bad")),
            ),
            (
                "checksum-drift",
                "checksum drift",
                lambda root: (root / "reuse/safety-disconnect.md").write_text(
                    (root / "reuse/safety-disconnect.md").read_text(encoding="utf-8")
                    + "\nchanged\n",
                    encoding="utf-8",
                ),
            ),
            (
                "origin",
                "invalid origin",
                registry_edit(
                    lambda r: items(r)["reuse-safety-disconnect"].update(origin="Other Book")
                ),
            ),
            (
                "scope",
                "unsupported scope",
                registry_edit(
                    lambda r: items(r)["reuse-safety-disconnect"].update(scope="remote-book")
                ),
            ),
            (
                "registry-context",
                "invalid context 'nowhere'",
                registry_edit(
                    lambda r: items(r)["reuse-safety-disconnect"].update(
                        allowed_contexts=["nowhere"]
                    )
                ),
            ),
            (
                "invalid-parameter",
                "invalid parameter 'Bad'",
                registry_edit(
                    lambda r: items(r)["reuse-safety-disconnect"].update(parameters=["Bad"])
                ),
            ),
            (
                "heading",
                "must not contain headings",
                lambda root: append_fragment(root, "\n## Hidden heading\n"),
            ),
            (
                "persistent-id",
                "must not define persistent IDs",
                lambda root: append_fragment(root, "\nMarker[]{#hidden-id}\n"),
            ),
            (
                "nested",
                "must not contain nested reuse calls",
                lambda root: append_fragment(root, "\n{{< alk-reuse reuse-safety-disconnect >}}\n"),
            ),
            (
                "include",
                "must not contain include directives",
                lambda root: append_fragment(root, "\n{{< include other.md >}}\n"),
            ),
            (
                "raw-backend",
                "must remain backend-neutral Markdown",
                lambda root: append_fragment(root, "\n<aside>raw</aside>\n"),
            ),
            (
                "undeclared-placeholder",
                "uses undeclared parameter 'unknown'",
                lambda root: append_fragment(root, "\n{{unknown}}\n"),
            ),
            (
                "unused-parameter",
                "declares unused parameter 'extra'",
                registry_edit(
                    lambda r: items(r)["reuse-safety-disconnect"].update(
                        parameters=["equipment", "extra"]
                    )
                ),
            ),
            (
                "unregistered-file",
                "unregistered reusable fragment 'reuse/extra.md'",
                lambda root: (root / "reuse/extra.md").write_text(
                    "unregistered\n", encoding="utf-8"
                ),
            ),
            (
                "unknown-reference",
                "unknown reusable-content ID 'reuse-unknown'",
                lambda root: replace(
                    root, "chapter.qmd", "reuse-safety-disconnect", "reuse-unknown"
                ),
            ),
            (
                "missing-id",
                'needs id="reuse-use-..."',
                lambda root: replace(root, "chapter.qmd", ' id="reuse-use-safety-disconnect"', ""),
            ),
            (
                "duplicate-instance",
                "duplicate reusable-content instance 'reuse-use-safety-disconnect'",
                lambda root: replace(
                    root,
                    "chapter.qmd",
                    "reuse-use-observed-value-definition",
                    "reuse-use-safety-disconnect",
                ),
            ),
            (
                "disallowed-context",
                "is not allowed in context 'front-matter'",
                lambda root: replace(
                    root,
                    "chapter.qmd",
                    'context="chapter" equipment=',
                    'context="front-matter" equipment=',
                ),
            ),
            (
                "missing-parameter",
                "needs parameter 'equipment'",
                lambda root: replace(root, "chapter.qmd", ' equipment="the fixture"', ""),
            ),
            (
                "unexpected-argument",
                "has unexpected argument 'extra'",
                lambda root: replace(
                    root,
                    "chapter.qmd",
                    ' equipment="the fixture"',
                    ' equipment="the fixture" extra="value"',
                ),
            ),
            (
                "missing-reference",
                "item 'reuse-safety-disconnect' is never referenced",
                lambda root: replace(
                    root,
                    "chapter.qmd",
                    next(
                        line
                        for line in (root / "chapter.qmd")
                        .read_text(encoding="utf-8")
                        .splitlines(keepends=True)
                        if line.startswith("{{< alk-reuse reuse-safety-disconnect")
                    ),
                    "",
                ),
            ),
            (
                "raw-path",
                "use alk-reuse rather than a raw reusable-fragment path",
                lambda root: (root / "chapter.qmd").write_text(
                    (root / "chapter.qmd").read_text(encoding="utf-8")
                    + "\n[raw](reuse/safety-disconnect.md)\n",
                    encoding="utf-8",
                ),
            ),
        )
    )
    for name, expected, mutate in cases:
        expect_failure(name, expected, mutate)
    print(
        "ok: controlled-reuse fixtures (valid contract; 29 invalid registry, fragment, parameter, context, identity, and dependency contracts rejected)"
    )


def test_contract():
    result = main()
    assert result in (None, 0)
