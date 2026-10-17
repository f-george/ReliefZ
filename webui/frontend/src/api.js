async function handle(response) {
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.error || `HTTP ${response.status}`);
  }
  return response.json();
}

export function getJSON(url) {
  return fetch(url).then(handle);
}

export function postJSON(url, body, signal) {
  return fetch(url, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    signal,
  }).then(handle);
}

// Number of decimals implied by a slider step (1 -> 0, 0.1 -> 1, 0.05 -> 2)
export function decimals(step) {
  return step >= 1 ? 0 : Math.min(3, Math.ceil(-Math.log10(step) - 1e-9));
}

export function formatValue(value, def) {
  const text = Number(value).toFixed(decimals(def.step));
  return def.unit ? `${text} ${def.unit}` : text;
}
