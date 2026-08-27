// Run pinned axe-core WCAG 2.2 A/AA rules in headless Chrome over rendered HTML.

import { spawnSync } from "node:child_process";
import {
  mkdtempSync,
  readFileSync,
  readdirSync,
  rmSync,
  statSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const AXE_PATH = process.env.ALKAHEST_AXE_PATH ?? "/opt/alkahest/writing/node_modules/axe-core/axe.min.js";
const CHROME = process.env.QUARTO_CHROMIUM;
const RULE_TAGS = ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"];
const SUPPLEMENTAL_RULES = ["tabindex"];
const RESULT_MARKER = "ALKAHest_AXE_RESULTS:";

function harnessSource(axeSource, urls) {
  const encodedAxe = JSON.stringify(axeSource).replaceAll("</script", "<\\/script");
  return `<!doctype html><html><head><meta charset="utf-8"><title>Alkahest axe runner</title></head><body><script>
const axeSource = ${encodedAxe};
const urls = ${JSON.stringify(urls)};
const tags = ${JSON.stringify(RULE_TAGS)};
const supplementalRules = ${JSON.stringify(SUPPLEMENTAL_RULES)};
async function loadFrame(url) {
  const frame = document.createElement("iframe");
  frame.src = url;
  document.body.append(frame);
  await new Promise((resolve, reject) => {
    const timer = setTimeout(() => reject(new Error("timed out loading " + url)), 15000);
    frame.addEventListener("load", () => { clearTimeout(timer); resolve(); }, { once: true });
    frame.addEventListener("error", () => { clearTimeout(timer); reject(new Error("failed to load " + url)); }, { once: true });
  });
  return frame;
}
async function run() {
  const reports = [];
  for (const url of urls) {
    const frame = await loadFrame(url);
    const script = frame.contentDocument.createElement("script");
    script.textContent = axeSource;
    frame.contentDocument.head.append(script);
    const result = await frame.contentWindow.axe.run(frame.contentDocument, {
      runOnly: { type: "tag", values: tags },
      resultTypes: ["violations", "incomplete", "passes"]
    });
    const supplemental = await frame.contentWindow.axe.run(frame.contentDocument, {
      runOnly: { type: "rule", values: supplementalRules },
      resultTypes: ["violations", "incomplete", "passes"]
    });
    const violationIds = new Set(result.violations.map(item => item.id));
    const incompleteIds = new Set(result.incomplete.map(item => item.id));
    for (const item of supplemental.violations) {
      if (!violationIds.has(item.id)) result.violations.push(item);
    }
    for (const item of supplemental.incomplete) {
      if (!incompleteIds.has(item.id)) result.incomplete.push(item);
    }
    reports.push({
      url,
      engine: result.testEngine.version,
      violations: result.violations,
      incomplete: result.incomplete.map(item => ({ id: item.id, nodes: item.nodes.length })),
      passes: result.passes.length + supplemental.passes.length
    });
    frame.remove();
  }
  const payload = btoa(unescape(encodeURIComponent(JSON.stringify(reports))));
  document.documentElement.innerHTML = "<head><title>Complete</title></head><body><pre>" +
    ${JSON.stringify(RESULT_MARKER)} + payload + "</pre></body>";
}
run().catch(error => {
  const payload = btoa(unescape(encodeURIComponent(JSON.stringify({ error: String(error.stack || error) }))));
  document.documentElement.innerHTML = "<head><title>Failed</title></head><body><pre>" +
    ${JSON.stringify(RESULT_MARKER)} + payload + "</pre></body>";
});
</script></body></html>`;
}

export function auditFiles(files) {
  if (!CHROME) {
    throw new Error("QUARTO_CHROMIUM is not configured");
  }
  const axeSource = readFileSync(AXE_PATH, "utf8");
  const urls = files.map((file) => pathToFileURL(path.resolve(file)).href);
  const directory = mkdtempSync(path.join(tmpdir(), "alkahest-axe."));
  const harness = path.join(directory, "runner.html");

  try {
    writeFileSync(harness, harnessSource(axeSource, urls), "utf8");
    const result = spawnSync(
      CHROME,
      [
        "--headless=new",
        "--no-sandbox",
        "--disable-gpu",
        "--allow-file-access-from-files",
        "--virtual-time-budget=30000",
        "--dump-dom",
        pathToFileURL(harness).href,
      ],
      { encoding: "utf8", maxBuffer: 32 * 1024 * 1024, timeout: 60000 },
    );

    if (result.error) {
      throw result.error;
    }
    const marker = result.stdout.indexOf(RESULT_MARKER);
    if (marker < 0) {
      throw new Error(
        `headless Chrome produced no axe result (status ${result.status}): ${result.stderr}`,
      );
    }

    const encoded = result.stdout.slice(marker + RESULT_MARKER.length).split("<", 1)[0].trim();
    const parsed = JSON.parse(Buffer.from(encoded, "base64").toString("utf8"));
    if (parsed.error) {
      throw new Error(parsed.error);
    }
    return parsed;
  } finally {
    rmSync(directory, { recursive: true, force: true });
  }
}

function reportFailure(report, root) {
  const file = path.relative(root, fileURLToPath(report.url));
  for (const violation of report.violations) {
    console.error(`  ${file}: ${violation.id} (${violation.impact ?? "unknown impact"}): ${violation.help}`);
    for (const node of violation.nodes) {
      console.error(`    ${node.target.join(" ")}: ${node.failureSummary ?? "failed"}`);
    }
  }
}

function main() {
  const root = path.resolve(process.argv[2] ?? "book/_build/html");
  const files = process.argv.slice(3).length ? process.argv.slice(3).map((file) => path.resolve(file)) : [];
  if (!files.length) {
    const visit = (directory) => {
      for (const name of readdirSync(directory).sort()) {
        const candidate = path.join(directory, name);
        if (statSync(candidate).isDirectory()) {
          visit(candidate);
        } else if (candidate.endsWith(".html")) {
          files.push(candidate);
        }
      }
    };
    visit(root);
  }

  if (!files.length) {
    throw new Error(`no rendered HTML files below ${root}`);
  }
  const reports = auditFiles(files);
  let violations = 0;
  let incomplete = 0;
  let passes = 0;
  const reviewRules = new Map();

  for (const report of reports) {
    if (report.engine !== "4.13.0") {
      throw new Error(`unexpected axe-core version ${report.engine}`);
    }
    violations += report.violations.length;
    incomplete += report.incomplete.length;
    passes += report.passes;
    for (const item of report.incomplete) {
      const current = reviewRules.get(item.id) ?? { documents: 0, nodes: 0 };
      current.documents += 1;
      current.nodes += item.nodes;
      reviewRules.set(item.id, current);
    }
    reportFailure(report, root);
  }
  if (violations) {
    throw new Error(`axe-core found ${violations} WCAG 2.2 A/AA rule violations across ${reports.length} documents`);
  }
  for (const [rule, count] of [...reviewRules].sort()) {
    console.log(`review: ${rule} needs human judgment in ${count.documents} documents (${count.nodes} nodes)`);
  }
  console.log(`ok: axe-core WCAG scan (${reports.length} documents; ${passes} rule passes; ${incomplete} results need manual review; 0 violations)`);
}

if (process.argv[1] && pathToFileURL(process.argv[1]).href === import.meta.url) {
  try {
    main();
  } catch (error) {
    console.error(`error: ${error.message}`);
    process.exitCode = 1;
  }
}
