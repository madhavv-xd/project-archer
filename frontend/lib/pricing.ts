// Rough "what a premium model would have cost" estimate for the dashboard.
// Archer's pool is free-tier, so every token routed through it is money not
// spent on a paid frontier model. This is a marketing estimate, not a bill:
// one blended reference rate, labeled "estimated" wherever it's shown.
//
// Reference: GPT-4o-class blended ~$5 / 1M tokens (input+output averaged).
// Update this constant when the reference market rate drifts.
export const REFERENCE_USD_PER_1K_TOKENS = 0.005;

export function estimateCostSaved(totalTokens: number): number {
  return (totalTokens / 1000) * REFERENCE_USD_PER_1K_TOKENS;
}
