// Verify that pinned axe-core accepts a valid page and rejects five WCAG defects.

import path from "node:path";
import { fileURLToPath } from "node:url";

import { auditFiles } from "../../scripts/check-accessibility-browser.mjs";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "../..");
const FIXTURES = path.join(ROOT, "tests", "accessibility", "browser");
const expected = {
  "invalid-alt.html": "image-alt",
  "invalid-button.html": "button-name",
  "invalid-contrast.html": "color-contrast",
  "invalid-lang.html": "html-has-lang",
  "invalid-tabindex.html": "tabindex",
};

try {
  const files = ["valid.html", ...Object.keys(expected)].map((name) =>
    path.join(FIXTURES, name),
  );
  const reports = auditFiles(files);
  const byName = Object.fromEntries(
    reports.map((report) => [path.basename(fileURLToPath(report.url)), report]),
  );
  if (byName["valid.html"].violations.length) {
    throw new Error(
      `valid browser fixture failed: ${byName["valid.html"].violations
        .map((item) => item.id)
        .join(", ")}`,
    );
  }
  for (const [name, rule] of Object.entries(expected)) {
    const rules = new Set(byName[name].violations.map((item) => item.id));
    if (!rules.has(rule)) {
      throw new Error(`${name} did not trigger expected axe rule ${rule}`);
    }
  }
  console.log(
    "ok: axe-core browser fixtures " +
      "(valid semantic page; image, control-name, contrast, language, and tabindex failures rejected)",
  );
} catch (error) {
  console.error(`error: ${error.message}`);
  process.exitCode = 1;
}
