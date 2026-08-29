import type { ActionRead } from "../types/api";

/**
 * Classifies an action as "water", "energy", or "other".
 *
 * Primary signal: the action's `category` field set by the AI agent.
 * Fallback: keyword scan of title + rationale for actions the agent
 * tagged as "general" or "waste" but which clearly relate to a resource.
 * This handles the common case where the LLM defaults to "general".
 */

const WATER_KEYWORDS = [
  "water", "irrigation", "leak", "pipe", "tap", "faucet", "plumbing",
  "cooling tower", "water recycl", "rainwater", "hydro", "sewage",
  "wastewater", "greywater", "drip", "sprinkler", "water conserv",
  "water usage", "water consumption",
];

const ENERGY_KEYWORDS = [
  "energy", "electricity", "power", "kwh", "lighting", "light bulb",
  "led", "hvac", "air condition", "heating", "cooling", "solar",
  "generator", "appliance", "motor", "pump", "compressor", "inverter",
  "fossil fuel", "diesel", "natural gas", "thermal", "carbon", "emission",
  "energy usage", "energy consumption", "energy saving",
];

function containsKeyword(text: string, keywords: string[]): boolean {
  const lower = text.toLowerCase();
  return keywords.some((kw) => lower.includes(kw));
}

export function classifyActionResource(action: ActionRead): "water" | "energy" | "other" {
  // Trust the explicit category when it's specific
  if (action.category === "water") return "water";
  if (action.category === "energy") return "energy";

  // For "general" or "waste" — scan the text
  const text = `${action.title} ${action.rationale}`;
  const isWater = containsKeyword(text, WATER_KEYWORDS);
  const isEnergy = containsKeyword(text, ENERGY_KEYWORDS);

  if (isWater && !isEnergy) return "water";
  if (isEnergy && !isWater) return "energy";
  // Both or neither → treat as other (waste/general)
  return "other";
}
