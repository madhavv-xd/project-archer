/** Parity check for the landing demo's copy of the backend keyword router.
 *  Stdlib only — no test framework in this app:
 *
 *      node --experimental-strip-types components/landing/routeRules.test.ts
 *
 *  Every case below is the rule order from `app/core/router.py`, including the
 *  one that bites: the <15-word check runs BEFORE analysis, so a short
 *  "compare X and Y" routes simple, not analysis. */
import assert from "node:assert/strict";
import { decide } from "./routeRules.ts";

const cases: [string, string][] = [
  ["Write a binary search in Rust", "coding_keywords"], // coding wins over "write"
  ["Derive the integral of x·ln(x)", "math_keywords"],
  ["Draft a launch email for our new pricing", "writing_keywords"],
  ["hi", "simple_query"],
  ["compare these two", "simple_query"], // short-circuits before analysis
  [
    "Give me a comprehensive look at the tradeoffs between the two hosting vendors we shortlisted last quarter for our team",
    "analysis_keywords",
  ],
  [
    "pros and cons of moving our whole reporting stack over to the new vendor before the next fiscal year starts, please",
    "analysis_keywords",
  ],
  [
    "Tell me at length about the history of the Silk Road trading routes across central Asia and their lasting cultural influence",
    "default",
  ],
];

for (const [prompt, expected] of cases) {
  assert.equal(decide(prompt).reason, expected, `${prompt} → ${decide(prompt).reason}`);
}
console.log(`routeRules: ${cases.length} cases pass`);
