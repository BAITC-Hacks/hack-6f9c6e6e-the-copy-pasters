import { apiFetch } from "./auth.js";

export async function analyzeProvider(providerId, criteria) {
  const response = await apiFetch(`/api/providers/${encodeURIComponent(providerId)}/analysis`, {
    method: "POST",
    body: JSON.stringify(criteria),
  });
  const result = await response.json();
  if (!response.ok) throw new Error(result.detail || "ИИ-анализ сейчас недоступен.");
  return result.analysis;
}
