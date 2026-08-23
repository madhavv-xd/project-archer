/** Client-side port of `backend/app/core/router.py::keyword_route()`, used only
 *  by the landing page's routing demo. Same sets, same priority order.
 *
 *  Why a copy and not a real call: `/v1/chat/completions` needs an `arch_sk_`
 *  key and a landing visitor has none, and the production path leads with the
 *  embedding router anyway — these rules are what it falls back to. The demo
 *  says so in its own copy. Run `routeRules.test.ts` after touching router.py.
 *
 *  The domain→model map below is DB-driven in production (`models.routing_domains`,
 *  migration 007) — mirrored here for display only. */

const CODING = new Set(
  "code function class debug error bug python javascript typescript java rust go api database sql algorithm implement programming syntax compile runtime framework library".split(" "),
);
const MATH = new Set(
  "math calculate solve equation integral derivative matrix vector probability statistics formula theorem proof algebra calculus geometry".split(" "),
);
const WRITING = new Set(
  "write essay story poem blog email draft rewrite paraphrase letter article compose".split(" "),
);
const ANALYSIS = new Set(
  "analyze compare evaluate research detailed comprehensive tradeoffs".split(" "),
);
const ANALYSIS_PHRASES = ["pros and cons", "in depth", "explain thoroughly"];
const SIMPLE_PREFIXES = [
  "hi", "hello", "thanks", "what is", "who is", "when did", "where is", "define", "yes", "no",
];

export const DOMAIN_MODEL: Record<string, { model: string; provider: string }> = {
  coding: { model: "gpt-oss-120b", provider: "Groq" },
  math: { model: "gpt-oss-120b", provider: "Groq" },
  writing: { model: "gemma4-31b", provider: "Ollama Cloud" },
  simple: { model: "qwen3.6-27b", provider: "Groq" },
  analysis: { model: "nemotron-3-ultra", provider: "Ollama Cloud" },
  general: { model: "gpt-oss-20b", provider: "Groq" },
};

export function tokens(text: string): string[] {
  return text
    .toLowerCase()
    .split(/\s+/)
    .filter(Boolean)
    .map((t) => t.replace(/^[.,!?;:'"()[\]]+|[.,!?;:'"()[\]]+$/g, ""));
}

export type Decision = {
  domain: keyof typeof DOMAIN_MODEL;
  reason: string;
  match: string;
  rule: string;
};

export function decide(text: string): Decision {
  const lowered = text.toLowerCase().trim();
  const words = tokens(lowered);
  const hit = (set: Set<string>) => words.find((w) => set.has(w));

  let m = hit(CODING);
  if (m) return { domain: "coding", reason: "coding_keywords", match: m, rule: "1 · coding keywords" };
  m = hit(MATH);
  if (m) return { domain: "math", reason: "math_keywords", match: m, rule: "2 · math keywords" };
  m = hit(WRITING);
  if (m) return { domain: "writing", reason: "writing_keywords", match: m, rule: "3 · writing keywords" };
  if (lowered.split(/\s+/).length < 15 || SIMPLE_PREFIXES.some((p) => lowered.startsWith(p)))
    return { domain: "simple", reason: "simple_query", match: "< 15 words", rule: "4 · short or greeting" };
  m = hit(ANALYSIS) ?? ANALYSIS_PHRASES.find((p) => lowered.includes(p));
  if (m) return { domain: "analysis", reason: "analysis_keywords", match: m, rule: "5 · analysis keywords" };
  return { domain: "general", reason: "default", match: "no rule fired", rule: "6 · default" };
}
