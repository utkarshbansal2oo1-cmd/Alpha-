#!/usr/bin/env node
/**
 * Performance benchmarking harness -- runs every adapter's detect()+
 * extract() against its own fixture (from testing/fixtures/) many times
 * and reports avg/p95 latency, flagging anything over a latency budget.
 * This is what keeps "add a new adapter in under a day" from silently
 * regressing into "add a slow adapter that stalls the popup" -- every new
 * adapter+fixture pair gets a real number here for free.
 *
 * Budget: DETECT_BUDGET_MS / EXTRACT_BUDGET_MS below are deliberately
 * generous for a POC (the popup already shows a spinner during
 * extraction), but exist so a pathological adapter (e.g. an accidental
 * O(n^2) DOM walk) shows up as a FAIL instead of silently shipping.
 *
 * Usage: `node adapter-sdk/testing/benchmark.js [iterations]`
 * (default iterations: 200 per fixture)
 */
const fs = require("fs");
const path = require("path");

const { buildRegistry } = require("./run-tests");
const { SourceInput } = require("../core/source-input");

const DETECT_BUDGET_MS = 5;
const EXTRACT_BUDGET_MS = 15;
const DEFAULT_ITERATIONS = 200;

function loadInput(fixtureDir) {
  const metaPath = path.join(fixtureDir, "meta.json");
  const meta = fs.existsSync(metaPath) ? JSON.parse(fs.readFileSync(metaPath, "utf-8")) : {};

  const htmlPath = path.join(fixtureDir, "input.html");
  const textPath = path.join(fixtureDir, "input.txt");
  const rowPath = path.join(fixtureDir, "input.json");

  if (fs.existsSync(htmlPath)) {
    const { JSDOM } = require("jsdom");
    const html = fs.readFileSync(htmlPath, "utf-8");
    // A fresh JSDOM per iteration would measure JSDOM's own parse cost, not
    // the adapter -- build one DOM and reuse it for every timed iteration,
    // same as a real browser page persists across popup opens.
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

function percentile(sortedValues, p) {
  const idx = Math.min(sortedValues.length - 1, Math.floor((p / 100) * sortedValues.length));
  return sortedValues[idx];
}

function benchmarkAdapter(adapter, input, iterations) {
  const detectTimes = [];
  const extractTimes = [];

  for (let i = 0; i < iterations; i++) {
    const detectStart = process.hrtime.bigint();
    const matched = adapter.detect(input);
    const detectEnd = process.hrtime.bigint();
    detectTimes.push(Number(detectEnd - detectStart) / 1e6);

    if (matched) {
      const extractStart = process.hrtime.bigint();
      adapter.extract(input);
      const extractEnd = process.hrtime.bigint();
      extractTimes.push(Number(extractEnd - extractStart) / 1e6);
    }
  }

  detectTimes.sort((a, b) => a - b);
  extractTimes.sort((a, b) => a - b);

  const avg = (arr) => (arr.length ? arr.reduce((a, b) => a + b, 0) / arr.length : 0);

  return {
    detectAvg: avg(detectTimes),
    detectP95: detectTimes.length ? percentile(detectTimes, 95) : 0,
    extractAvg: avg(extractTimes),
    extractP95: extractTimes.length ? percentile(extractTimes, 95) : 0,
  };
}

function main() {
  const iterations = parseInt(process.argv[2], 10) || DEFAULT_ITERATIONS;
  const fixturesRoot = path.join(__dirname, "fixtures");
  const fixtureNames = fs
    .readdirSync(fixturesRoot)
    .filter((f) => fs.statSync(path.join(fixturesRoot, f)).isDirectory());

  const registry = buildRegistry();
  const results = [];
  let anyOverBudget = false;

  for (const fixtureName of fixtureNames) {
    const expected = JSON.parse(
      fs.readFileSync(path.join(fixturesRoot, fixtureName, "expected.json"), "utf-8")
    );
    const adapter = registry.list().find((a) => a.name === expected.adapterUsed);
    if (!adapter) {
      console.log(`SKIP  ${fixtureName} (no adapter named "${expected.adapterUsed}" registered)`);
      continue;
    }

    const input = loadInput(path.join(fixturesRoot, fixtureName));
    const stats = benchmarkAdapter(adapter, input, iterations);
    const overBudget = stats.detectP95 > DETECT_BUDGET_MS || stats.extractP95 > EXTRACT_BUDGET_MS;
    if (overBudget) anyOverBudget = true;

    results.push({ fixtureName, adapter: adapter.name, ...stats, overBudget });
  }

  console.log(`\nBenchmark (${iterations} iterations per fixture):\n`);
  console.log(
    "adapter".padEnd(22) +
      "detect avg".padEnd(13) +
      "detect p95".padEnd(13) +
      "extract avg".padEnd(14) +
      "extract p95".padEnd(14) +
      "status"
  );
  for (const r of results) {
    console.log(
      r.adapter.padEnd(22) +
        `${r.detectAvg.toFixed(3)}ms`.padEnd(13) +
        `${r.detectP95.toFixed(3)}ms`.padEnd(13) +
        `${r.extractAvg.toFixed(3)}ms`.padEnd(14) +
        `${r.extractP95.toFixed(3)}ms`.padEnd(14) +
        (r.overBudget ? "OVER BUDGET" : "OK")
    );
  }

  console.log(`\nBudget: detect p95 <= ${DETECT_BUDGET_MS}ms, extract p95 <= ${EXTRACT_BUDGET_MS}ms`);
  process.exit(anyOverBudget ? 1 : 0);
}

if (require.main === module) {
  main();
}

module.exports = { benchmarkAdapter };
