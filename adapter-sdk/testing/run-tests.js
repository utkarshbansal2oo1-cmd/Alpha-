#!/usr/bin/env node
/**
 * Adapter testing framework -- runs every fixture in testing/fixtures/
 * through the full registry pipeline and asserts the winning adapter's
 * output matches (a subset of) expected.json. This is what makes "add a
 * new adapter in under a day" credible: writing an adapter and its
 * fixture together, then running `node adapter-sdk/testing/run-tests.js`,
 * is the whole verification loop -- no manual browser testing required.
 *
 * Fixture folder contract (testing/fixtures/<name>/):
 *   - input.html | input.txt | input.json  -- exactly one; determines the
 *     SourceInput kind (dom / text / row respectively).
 *   - meta.json (optional) -- `{ "url": "..." }`, passed as SourceInput meta
 *     and, for input.html fixtures, used as the jsdom document's URL.
 *   - expected.json -- `{ adapterUsed, multi?, fields }`. `fields` is
 *     checked as a PARTIAL match (every key in expected.fields must equal
 *     the actual value; extra actual fields are fine) -- this keeps
 *     fixtures short and focused on what that adapter is responsible for,
 *     rather than pinning every normalize() default.
 *
 * Requires `jsdom` (devDependency, see adapter-sdk/package.json) for any
 * fixture using input.html. Run `npm install` inside adapter-sdk/ first.
 */
const fs = require("fs");
const path = require("path");

const { AdapterRegistry } = require("../core/registry");
const { SourceInput } = require("../core/source-input");
const { genericHtmlAdapter } = require("../adapters/generic-html");
const { jsonLdAdapter } = require("../adapters/json-ld");
const { resumeTextAdapter } = require("../adapters/resume-text");
const { csvRowAdapter } = require("../adapters/csv-row");
const { careerPageListingAdapter } = require("../adapters/career-page-listing");

function buildRegistry() {
  const registry = new AdapterRegistry();
  [genericHtmlAdapter, jsonLdAdapter, resumeTextAdapter, csvRowAdapter, careerPageListingAdapter].forEach(
    (a) => registry.register(a)
  );
  return registry;
}

function loadInput(fixtureDir) {
  const metaPath = path.join(fixtureDir, "meta.json");
  const meta = fs.existsSync(metaPath) ? JSON.parse(fs.readFileSync(metaPath, "utf-8")) : {};

  const htmlPath = path.join(fixtureDir, "input.html");
  const textPath = path.join(fixtureDir, "input.txt");
  const rowPath = path.join(fixtureDir, "input.json");

  if (fs.existsSync(htmlPath)) {
    const { JSDOM } = require("jsdom");
    const html = fs.readFileSync(htmlPath, "utf-8");
    const dom = new JSDOM(html, { url: meta.url || "https://example.com/" });
    return SourceInput.fromDocument(dom.window.document, meta);
  }
  if (fs.existsSync(textPath)) {
    return SourceInput.fromText(fs.readFileSync(textPath, "utf-8"), meta);
  }
  if (fs.existsSync(rowPath)) {
    return SourceInput.fromRow(JSON.parse(fs.readFileSync(rowPath, "utf-8")), meta);
  }
  throw new Error(`Fixture ${fixtureDir} has no input.html/input.txt/input.json`);
}

function partialMatch(expected, actual, pathPrefix = "") {
  const mismatches = [];
  for (const [key, expectedValue] of Object.entries(expected)) {
    const actualValue = actual ? actual[key] : undefined;
    const label = `${pathPrefix}${key}`;

    if (Array.isArray(expectedValue)) {
      if (!Array.isArray(actualValue) || JSON.stringify(actualValue) !== JSON.stringify(expectedValue)) {
        mismatches.push(`${label}: expected ${JSON.stringify(expectedValue)}, got ${JSON.stringify(actualValue)}`);
      }
    } else if (typeof expectedValue === "object" && expectedValue !== null) {
      mismatches.push(...partialMatch(expectedValue, actualValue, `${label}.`));
    } else if (actualValue !== expectedValue) {
      mismatches.push(`${label}: expected ${JSON.stringify(expectedValue)}, got ${JSON.stringify(actualValue)}`);
    }
  }
  return mismatches;
}

function runFixture(name, fixtureDir, registry) {
  const expected = JSON.parse(fs.readFileSync(path.join(fixtureDir, "expected.json"), "utf-8"));
  const input = loadInput(fixtureDir);
  const result = registry.runPipeline(input);

  const failures = [];

  if (!result.matched) {
    failures.push("No adapter matched this fixture's input");
    return { name, passed: false, failures };
  }
  if (result.adapterUsed !== expected.adapterUsed) {
    failures.push(`adapterUsed: expected "${expected.adapterUsed}", got "${result.adapterUsed}"`);
  }

  const expectedMulti = Boolean(expected.multi);
  const actualMulti = Array.isArray(result.fields);
  if (expectedMulti !== actualMulti) {
    failures.push(`multi: expected ${expectedMulti}, got ${actualMulti}`);
  } else if (expectedMulti) {
    expected.fields.forEach((expectedEntry, i) => {
      failures.push(...partialMatch(expectedEntry, result.fields[i], `fields[${i}].`));
    });
  } else {
    failures.push(...partialMatch(expected.fields, result.fields, "fields."));
  }

  return { name, passed: failures.length === 0, failures };
}

function main() {
  const fixturesRoot = path.join(__dirname, "fixtures");
  const fixtureNames = fs.readdirSync(fixturesRoot).filter((f) =>
    fs.statSync(path.join(fixturesRoot, f)).isDirectory()
  );

  const registry = buildRegistry();
  const results = fixtureNames.map((name) => runFixture(name, path.join(fixturesRoot, name), registry));

  let failCount = 0;
  for (const r of results) {
    if (r.passed) {
      console.log(`PASS  ${r.name}`);
    } else {
      failCount++;
      console.log(`FAIL  ${r.name}`);
      r.failures.forEach((f) => console.log(`        - ${f}`));
    }
  }

  console.log(`\n${results.length - failCount}/${results.length} fixtures passed.`);
  process.exit(failCount > 0 ? 1 : 0);
}

if (require.main === module) {
  main();
}

module.exports = { runFixture, buildRegistry, partialMatch };
