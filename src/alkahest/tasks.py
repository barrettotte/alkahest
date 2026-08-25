"""Central task inventory and subprocess execution for the Alkahest toolkit."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from .process import run_process

ROOT: Final = Path(__file__).resolve().parents[2]
SCRIPTS: Final = ROOT / "scripts"
LOCKED_PYTHON: Final = Path("/opt/alkahest/tools/bin/python")


@dataclass(frozen=True)
class ScriptTask:
    """One named task implemented by a module, direct operation, or process."""

    name: str
    script: str
    description: str
    locked_python: bool = False
    arguments: tuple[str, ...] = ()
    writes_workspace: bool = False


SOURCE_CHECKS: Final = (
    ScriptTask(
        "execution-policy",
        "@alkahest.checks.execution_policy",
        "static manuscript execution policy",
    ),
    ScriptTask("reproducibility", "@alkahest.checks.reproducibility", "reproducibility policy"),
    ScriptTask("golden-pages", "@alkahest.checks.golden_pages", "golden-page source policy"),
    ScriptTask("publication-metadata", ":check-publication-metadata", "publication metadata"),
    ScriptTask("manifestations", ":check-manifestations", "publication manifestations"),
    ScriptTask("covers", ":check-covers", "cover inputs and geometry"),
    ScriptTask("metadata-generation", ":check-metadata-generation", "generated metadata adapters"),
    ScriptTask("graphs", "@alkahest.checks.graphs", "graphs and chart derivatives"),
    ScriptTask("circuits", "@alkahest.checks.circuits", "circuit sources and derivatives", True),
    ScriptTask(
        "chemistry", "@alkahest.checks.chemistry", "chemistry sources and derivatives", True
    ),
    ScriptTask("computing-diagrams", "@alkahest.checks.computing", "computing diagrams"),
    ScriptTask("physics-diagrams", "@alkahest.checks.physics", "physics diagrams"),
    ScriptTask("rich-media", "@alkahest.checks.rich_media", "rich media and fallbacks"),
    ScriptTask("asset-rights", ":check-asset-rights", "asset rights and privacy"),
    ScriptTask("new-book", "@alkahest.checks.new_book", "minimal generated-book scaffold"),
    ScriptTask("theme-defaults", ":check-theme-defaults", "theme defaults and adapters"),
    ScriptTask("release-profiles", ":check-release-profiles", "full and excerpt profiles"),
    ScriptTask("pdf-backend", "@alkahest.checks.pdf_backend", "PDF backend decision"),
    ScriptTask(
        "pdf-accessibility-policy",
        "@alkahest.checks.pdf_accessibility",
        "PDF accessibility evidence policy",
    ),
    ScriptTask("editorial-integrity", "@alkahest.checks.editorial", "source integrity"),
    ScriptTask("identities", ":check-identities", "persistent content identities"),
    ScriptTask("editions", ":check-editions", "edition structure and privacy"),
    ScriptTask("learning", ":check-learning", "learning roles and relationships"),
    ScriptTask("companions", ":check-companions", "companion materials"),
    ScriptTask("reuse", ":check-reuse", "controlled reusable content"),
    ScriptTask("citations", "@alkahest.checks.citations", "citations and bibliography calls"),
    ScriptTask("glossary", "@alkahest.checks.glossary", "glossary entries and references"),
    ScriptTask("generated-lists", "@alkahest.checks.generated_lists", "generated reference lists"),
    ScriptTask("icons", "@alkahest.checks.icons", "semantic inline icons"),
    ScriptTask("index", "@alkahest.checks.index", "subject and person index"),
    ScriptTask("notes", "@alkahest.checks.notes", "semantic notes"),
    ScriptTask("localization", "@alkahest.checks.localization", "localized source profiles"),
)


CHECKS: Final = {
    "writing-toolchain": ScriptTask(
        "writing-toolchain",
        "@alkahest.checks.writing",
        "locked writing tools",
        True,
        arguments=("toolchain",),
    ),
    "writing": ScriptTask(
        "writing",
        "@alkahest.checks.writing",
        "spelling, terminology, and prose",
        True,
        arguments=("all",),
    ),
    "spelling": ScriptTask(
        "spelling",
        "@alkahest.checks.writing",
        "canonical-source spelling",
        True,
        arguments=("spelling",),
    ),
    "prose": ScriptTask(
        "prose",
        "@alkahest.checks.writing",
        "terminology and prose",
        True,
        arguments=("prose",),
    ),
    "writing-terminology": ScriptTask(
        "writing-terminology",
        "@alkahest.generators.writing_terminology",
        "generated writing terminology",
        arguments=("--check",),
    ),
    "writing-overrides": ScriptTask(
        "writing-overrides", "@alkahest.checks.writing_overrides", "writing override policy"
    ),
    "glyph-coverage": ScriptTask(
        "glyph-coverage", "@alkahest.checks.glyph_coverage", "font glyph coverage", True
    ),
    "rights-report": ScriptTask("rights-report", ":check-rights-report", "rights report bytes"),
    "companion-bundles": ScriptTask(
        "companion-bundles", ":check-companion-bundles", "companion bundle artifacts"
    ),
    "preview": ScriptTask(
        "preview",
        "@alkahest.checks.suites",
        "rendered preview privacy",
        True,
        arguments=("preview",),
    ),
    "accessibility": ScriptTask(
        "accessibility",
        "@alkahest.checks.suites",
        "HTML accessibility",
        True,
        arguments=("accessibility",),
    ),
    "epub-accessibility": ScriptTask(
        "epub-accessibility",
        "@alkahest.checks.suites",
        "EPUB accessibility",
        True,
        arguments=("epub-accessibility",),
    ),
    "pdf-profiles": ScriptTask(
        "pdf-profiles", "@alkahest.checks.pdf_profiles", "rendered PDF profiles", True
    ),
    "pdf-preflight": ScriptTask(
        "pdf-preflight", "@alkahest.checks.pdf_preflight", "PDF print preflight", True
    ),
    "publication": ScriptTask(
        "publication",
        "@alkahest.checks.suites",
        "rendered publication",
        True,
        arguments=("publication",),
    ),
    "release-assets": ScriptTask(
        "release-assets", ":check-release-assets", "release asset privacy", True
    ),
    "golden-pages": ScriptTask(
        "golden-pages",
        "@alkahest.checks.golden_pages",
        "rendered golden pages",
        True,
        arguments=("--artifacts",),
        writes_workspace=True,
    ),
    "cover-artifacts": ScriptTask(
        "cover-artifacts", ":check-cover-artifacts", "rendered cover geometry", True
    ),
    "reproducibility": ScriptTask(
        "reproducibility",
        "@alkahest.checks.reproducibility",
        "rendered reproducibility fingerprints",
        arguments=("--artifacts",),
    ),
    "rendered-notes": ScriptTask(
        "rendered-notes",
        "@alkahest.checks.rendered",
        "rendered notes",
        True,
        arguments=("notes",),
    ),
    "rendered-identities": ScriptTask(
        "rendered-identities",
        "@alkahest.checks.rendered",
        "rendered persistent IDs",
        True,
        arguments=("identities",),
    ),
    "rendered-index": ScriptTask(
        "rendered-index",
        "@alkahest.checks.rendered",
        "rendered indexes",
        True,
        arguments=("index",),
    ),
    "rendered-lists": ScriptTask(
        "rendered-lists",
        "@alkahest.checks.rendered",
        "rendered lists",
        True,
        arguments=("lists",),
    ),
    "rendered-localization": ScriptTask(
        "rendered-localization",
        "@alkahest.checks.rendered_localization",
        "rendered localization",
    ),
}


GENERATORS: Final = {
    task.name: task
    for task in (
        ScriptTask(
            "publication-metadata",
            ":generate-publication-metadata",
            "publication metadata adapters",
        ),
        ScriptTask("graphs", "@alkahest.generators.graphs", "graphs and charts"),
        ScriptTask(
            "circuits",
            "@alkahest.generators.circuits",
            "electrical circuits",
            True,
            writes_workspace=True,
        ),
        ScriptTask(
            "chemistry",
            "@alkahest.generators.chemistry",
            "chemical diagrams",
            True,
            writes_workspace=True,
        ),
        ScriptTask("computing-diagrams", "@alkahest.generators.computing", "computing diagrams"),
        ScriptTask("physics-diagrams", "@alkahest.generators.physics", "physics diagrams"),
        ScriptTask("rich-media-fixtures", "@alkahest.generators.rich_media", "rich-media fixtures"),
        ScriptTask("rights-report", ":generate-rights-report", "rights report"),
        ScriptTask("covers", ":generate-covers", "cover artifacts", True, writes_workspace=True),
        ScriptTask(
            "writing-terminology",
            "@alkahest.generators.writing_terminology",
            "writing terminology",
        ),
        ScriptTask("theme", "sync-theme.py", "theme adapters"),
        ScriptTask("release-profiles", "sync-release-profiles.py", "release profiles"),
    )
}


PACKAGERS: Final = {
    task.name: task
    for task in (
        ScriptTask("companion-bundles", ":package-companion-bundles", "companion bundles"),
    )
}


RENDER_PROFILES: Final = (
    "all",
    "complete",
    "html",
    "epub",
    "pdf",
    "typst",
    "latex",
    "preview",
    "print-6x9",
    "review",
    "pdf-profiles",
    "locale-smoke",
    "citation-smoke",
    "edition-smoke",
    "notes-smoke",
    "pdf-accessibility-smoke",
    "pdf-ua-typst",
    "pdf-ua-latex",
)


def script_path(task: ScriptTask) -> Path:
    """Find a registered external script at the stable process boundary."""
    if task.script.startswith((":", "@")):
        raise ValueError(f"direct operation has no script path: {task.script[1:]}")
    path = SCRIPTS / task.script
    if not path.is_file():
        raise RuntimeError(f"task script does not exist: {task.script}")
    return path


def script_command(task: ScriptTask) -> list[str]:
    """Resolve one script task to its concrete subprocess argument vector."""
    if task.script.startswith("@"):
        module = task.script.removeprefix("@")
        if task.locked_python:
            configured = os.environ.get("ALKAHEST_LOCKED_PYTHON")
            if configured:
                command = [configured, "-m", module]
            elif ROOT == Path("/workspace") and LOCKED_PYTHON.is_file():
                command = [str(LOCKED_PYTHON), "-m", module]
            else:
                command = [str(SCRIPTS / "python-tools.sh")]
                if not task.writes_workspace:
                    command.append("--read-only")
                command.extend(("-m", module))
        else:
            python = (
                LOCKED_PYTHON
                if ROOT == Path("/workspace") and LOCKED_PYTHON.is_file()
                else Path(sys.executable)
            )
            command = [str(python), "-m", module]
        return [*command, *task.arguments]
    path = script_path(task)
    if task.locked_python:
        configured = os.environ.get("ALKAHEST_LOCKED_PYTHON")
        if configured:
            command = [configured, str(path)]
        elif ROOT == Path("/workspace") and LOCKED_PYTHON.is_file():
            command = [str(LOCKED_PYTHON), str(path)]
        else:
            command = [str(SCRIPTS / "python-tools.sh")]
            if not task.writes_workspace:
                command.append("--read-only")
            command.append(str(path.relative_to(ROOT)))
    elif path.suffix == ".py":
        python = (
            LOCKED_PYTHON
            if ROOT == Path("/workspace") and LOCKED_PYTHON.is_file()
            else Path(sys.executable)
        )
        command = [str(python), str(path)]
    else:
        command = [str(path)]
    return [*command, *task.arguments]


def run_task(task: ScriptTask, extra_arguments: tuple[str, ...] = ()) -> int:
    """Run one registered direct operation or external script."""
    if task.script.startswith(":"):
        from .operations import run_operation

        operation = task.script.removeprefix(":")
        arguments = (*task.arguments, *extra_arguments)
        if task.locked_python and ROOT != Path("/workspace"):
            command = [str(SCRIPTS / "python-tools.sh")]
            if not task.writes_workspace:
                command.append("--read-only")
            return run_process(
                [*command, "-m", "alkahest.operations", operation, *arguments],
                cwd=ROOT,
                check=False,
            ).returncode
        return run_operation(operation, arguments)
    environment = os.environ.copy()
    existing = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = (
        f"{ROOT / 'src'}{os.pathsep}{existing}" if existing else str(ROOT / "src")
    )
    return run_process(
        [*script_command(task), *extra_arguments], cwd=ROOT, env=environment, check=False
    ).returncode


def by_name(tasks: tuple[ScriptTask, ...]) -> dict[str, ScriptTask]:
    """Index a tuple of tasks and reject accidental duplicate names."""
    indexed = {task.name: task for task in tasks}
    if len(indexed) != len(tasks):
        raise RuntimeError("duplicate Alkahest task name")
    return indexed
