#!/usr/bin/env node
/**
 * Scan a built frontend artifact for literal "/api/..." endpoint strings.
 * Intended for truth-envelope wiring inventory (no network calls, no secrets).
 */

const fs = require("fs");

const target = process.argv[2];
if (!target) {
  console.error("Usage: node verification/scan_dist_endpoints.js <path-to-built-file>");
  process.exit(2);
}

const buf = fs.readFileSync(target);
const s = buf.toString("utf8");

const re = /\/api\/[A-Za-z0-9_\-\/]+/g;
const set = new Set();
let m;
while ((m = re.exec(s))) set.add(m[0]);

const endpoints = Array.from(set).sort();
console.log("ENDPOINTS_FOUND");
for (const e of endpoints) console.log(e);

