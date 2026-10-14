export const CATEGORIES = ["staple", "protein", "vegetable", "fruit"];
export const DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"];
const STORAGE_KEY = "bca.configuration.v1";
let temporary = null;
let notice = "";
const clone = value => JSON.parse(JSON.stringify(value));

export async function api(path, options = {}) {
  let response;
  try {
    response = await fetch(path, {...options, headers: {"Content-Type": "application/json", ...options.headers}, body: options.body && typeof options.body !== "string" ? JSON.stringify(options.body) : options.body});
  } catch {
    throw new Error("Cannot reach the Python host. Check that it is running and your device is connected.");
  }
  if (response.status === 204) return null;
  let payload;
  try { payload = await response.json(); } catch { throw new Error(`The Python host returned an unreadable response (${response.status}).`); }
  if (!response.ok) {
    const detail = payload.detail;
    const message = Array.isArray(detail) ? detail.map(item => `${(item.loc || []).filter(key => key !== "body").join(" → ")}: ${item.msg}`).join("\n") : typeof detail === "string" ? detail : `Host request failed (${response.status}).`;
    const error = new Error(message);
    error.status = response.status;
    throw error;
  }
  return payload;
}

// Validate transport inputs, never compute the objective or make search decisions.
export function validateConfiguration(value) {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("Configuration must be a JSON object with catalog, planning and algorithm.");
  const configuration = {catalog: value.catalog, planning: value.planning, algorithm: value.algorithm};
  const text = (value, label) => {
    if (typeof value !== "string" || !value.trim() || value.trim().length > 160) throw new Error(`${label} must contain 1–160 characters.`);
  };
  const numeric = (value, label, min = 0, max = 10000000, integer = false) => {
    if (typeof value !== "number" || !Number.isFinite(value) || value < min || value > max || (integer && !Number.isSafeInteger(value))) throw new Error(`${label} must be ${integer ? "a whole number" : "a number"} between ${min} and ${max}.`);
  };
  const object = (value, keys, label) => {
    if (!value || typeof value !== "object" || Array.isArray(value) || keys.some(key => !(key in value))) throw new Error(`${label} is missing required fields: ${keys.join(", ")}.`);
    const extra = Object.keys(value).filter(key => !keys.includes(key));
    if (extra.length) throw new Error(`${label} contains unknown fields: ${extra.join(", ")}.`);
  };
  const list = (value, label) => { if (!Array.isArray(value) || value.length > 100) throw new Error(`${label} must be a list of at most 100 items.`); };
  if (!Array.isArray(configuration.catalog) || configuration.catalog.length < 4 || configuration.catalog.length > 1000) throw new Error("Catalog must contain 4–1000 components, with at least one eligible option in each category.");
  const ids = new Set();
  for (const [index, item] of configuration.catalog.entries()) {
    const label = `Component ${index + 1}`;
    object(item, ["id", "name", "category", "cost", "energy", "protein", "fiber", "tags", "ingredients", "batch_size", "work_minutes"], label);
    text(item.id, `${label} ID`); text(item.name, `${label} name`);
    if (ids.has(item.id.trim())) throw new Error(`Component ID must be unique: ${item.id}`);
    ids.add(item.id.trim());
    if (!CATEGORIES.includes(item.category)) throw new Error(`${label} category must be staple, protein, vegetable or fruit.`);
    for (const key of ["cost", "energy", "protein", "fiber", "work_minutes"]) numeric(item[key], `${label} ${key}`);
    numeric(item.batch_size, `${label} batch size`, 1, 1000000, true);
    list(item.tags, `${label} tags`); for (const tag of item.tags) text(tag, `${label} tag`);
    list(item.ingredients, `${label} ingredients`);
    for (const ingredient of item.ingredients) {
      object(ingredient, ["id", "name", "quantity", "unit"], `${label} ingredient`);
      for (const key of ["id", "name", "unit"]) text(ingredient[key], `${label} ingredient ${key}`);
      numeric(ingredient.quantity, `${label} ingredient quantity`);
    }
  }
  const p = configuration.planning;
  object(p, ["servings", "budget_per_serving", "energy_min", "energy_max", "protein_min", "fiber_min", "kitchen_capacity", "max_protein_repeats", "max_menu_repeats", "exclusions", "weights"], "Planning");
  if (!Array.isArray(p.servings) || p.servings.length !== 5) throw new Error("Enter exactly five daily serving counts.");
  p.servings.forEach((value, index) => numeric(value, `${DAYS[index]} servings`, 1, 1000000, true));
  for (const key of ["budget_per_serving", "energy_min", "energy_max", "protein_min", "fiber_min", "kitchen_capacity"]) numeric(p[key], key, 0.001);
  if (p.energy_max < p.energy_min) throw new Error("Maximum energy must be at least minimum energy.");
  for (const key of ["max_protein_repeats", "max_menu_repeats"]) numeric(p[key], key, 1, 5, true);
  list(p.exclusions, "Dietary exclusions"); for (const tag of p.exclusions) text(tag, "Dietary exclusion");
  object(p.weights, ["cost", "budget", "nutrition", "variety", "workload"], "Scoring weights");
  for (const [key, value] of Object.entries(p.weights)) numeric(value, `${key} weight`);
  const a = configuration.algorithm;
  object(a, ["sources", "onlookers", "limit", "max_cycles", "patience", "seed"], "Algorithm");
  for (const [key, min, max] of [["sources", 2, 80], ["onlookers", 1, 160], ["limit", 1, 10000], ["max_cycles", 1, 2000], ["patience", 0, 2000], ["seed", Number.MIN_SAFE_INTEGER, Number.MAX_SAFE_INTEGER]]) numeric(a[key], key, min, max, true);
  const exclusions = p.exclusions.map(tag => tag.trim());
  const missing = CATEGORIES.filter(category => !configuration.catalog.some(item => item.category === category && !item.tags.some(tag => exclusions.includes(tag.trim()))));
  if (missing.length) throw new Error(`No eligible components for: ${missing.join(", ")}. Add an option or adjust dietary exclusions.`);
  const clean = clone(configuration);
  for (const item of clean.catalog) {
    item.id = item.id.trim(); item.name = item.name.trim();
    item.tags = item.tags.map(tag => tag.trim());
    for (const ingredient of item.ingredients) for (const key of ["id", "name", "unit"]) ingredient[key] = ingredient[key].trim();
  }
  clean.planning.exclusions = clean.planning.exclusions.map(tag => tag.trim());
  return clean;
}

export function configurationNotice() { return notice; }

export async function loadConfiguration() {
  const defaults = await api("/api/bootstrap");
  notice = "";
  if (temporary) return {...clone(temporary), categories: CATEGORIES, days: DAYS};
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      try { return {...validateConfiguration(JSON.parse(stored)), categories: CATEGORIES, days: DAYS}; }
      catch { notice = "Saved settings were unreadable or invalid. The demonstration defaults have been loaded; you can import a valid configuration."; }
    }
  } catch { notice = "Browser storage is unavailable. Settings can be used in this page and downloaded as JSON."; }
  return {...validateConfiguration(defaults), categories: CATEGORIES, days: DAYS};
}

export function saveConfiguration(configuration) {
  const validated = validateConfiguration(configuration);
  temporary = clone(validated);
  try { localStorage.setItem(STORAGE_KEY, JSON.stringify(validated)); notice = ""; return {persisted: true}; }
  catch { notice = "Browser storage is unavailable. Download configuration JSON to preserve these changes; other pages will use defaults until you import it."; return {persisted: false, message: notice}; }
}

export async function resetConfiguration() {
  temporary = null;
  try { localStorage.removeItem(STORAGE_KEY); } catch { /* The host defaults remain usable. */ }
  const defaults = await api("/api/bootstrap");
  return {...validateConfiguration(defaults), categories: CATEGORIES, days: DAYS};
}
