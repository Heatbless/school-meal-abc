// Render and download evaluations produced by the Python host. No scoring here.
function download(descriptor) {
  if (typeof document !== "undefined") {
    const url = URL.createObjectURL(new Blob([descriptor.content], {type: descriptor.mime}));
    const link = document.createElement("a");
    link.href = url;
    link.download = descriptor.filename;
    document.body.append(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  return descriptor;
}

export function exportResults(best, configuration, format = "json") {
  if (!best?.evaluation) throw new Error("Evaluate a schedule or run the colony before exporting results.");
  if (format === "csv") return download({filename: "abc-school-meals.csv", mime: "text/csv;charset=utf-8", content: resultCSV(best, configuration)});
  if (format !== "json") throw new Error("Unknown export format.");
  return download({
    filename: "abc-school-meals.json", mime: "application/json;charset=utf-8",
    content: JSON.stringify({schema_version: 1, exported_at: new Date().toISOString(), configuration, best}, null, 2),
  });
}

function resultCSV(best, configuration) {
  const rows = [["section", "day", "category", "id", "name", "value", "unit", "details"]];
  const add = (section, day = "", category = "", id = "", name = "", value = "", unit = "", details = "") => rows.push([section, day, category, id, name, value, unit, typeof details === "object" ? JSON.stringify(details) : details]);
  const result = best.evaluation;
  add("configuration", "", "", "", "Complete replay inputs", "", "", configuration);
  add("schedule", "", "", "", "Component IDs in weekday/category order", "", "", best.schedule);
  add("summary", "", "", "score", "Objective score", result.score);
  add("summary", "", "", "fitness", "Fitness", result.fitness);
  add("summary", "", "", "targets_met", "All configured targets met", result.targets_met);
  for (const [key, value] of Object.entries(result.totals)) {
    if (key !== "ingredients") add("total", "", "", key, key, value, key === "cost" || key === "budget" ? "IDR" : key === "workload" ? "person-minutes" : "servings");
  }
  for (const [key, value] of Object.entries(result.contributions)) add("score", "", "", key, "Weighted contribution", value, "", {normalized_term: result.metrics[key], weight: configuration.planning.weights[key]});
  for (const day of result.days) {
    add("day", day.day, "", "", "Daily menu summary", day.cost, "IDR", {servings: day.servings, cost_per_serving: day.cost_per_serving, budget: day.budget, workload: day.workload, nutrition_per_serving: day.nutrition});
    for (const item of day.components) {
      const quantity = day.component_quantities.find(row => row.id === item.id);
      add("component", day.day, item.category, item.id, item.name, quantity.servings, "servings", {batches: quantity.batches, cost_per_serving: item.cost, nutrition_per_serving: {energy: item.energy, protein: item.protein, fiber: item.fiber}, batch_size: item.batch_size, work_minutes_per_batch: item.work_minutes});
    }
    for (const ingredient of day.ingredients) add("daily-ingredient", day.day, "", ingredient.id, ingredient.name, ingredient.quantity, ingredient.unit);
  }
  for (const ingredient of result.totals.ingredients) add("purchasing", "", "", ingredient.id, ingredient.name, ingredient.quantity, ingredient.unit);
  for (const violation of result.violations) add("violation", "", "", "", violation);
  return rows.map(row => row.map(value => {
    let text = String(value ?? "");
    // Spreadsheet applications must treat catalog labels as text, including formula prefixes.
    if (typeof value === "string" && /^[\s]*[=+@-]|^[\t\r\n]/.test(text)) text = "'" + text;
    return '"' + text.replaceAll('"', '""') + '"';
  }).join(",")).join("\r\n") + "\r\n";
}

const number = new Intl.NumberFormat("en", {maximumFractionDigits: 3});
const money = new Intl.NumberFormat("id-ID", {style: "currency", currency: "IDR", maximumFractionDigits: 0});
function element(tag, text, className) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  if (className) node.className = className;
  return node;
}
function table(headers, rows, label) {
  const wrapper = element("div", undefined, "table-scroll");
  wrapper.tabIndex = 0;
  wrapper.setAttribute("role", "region");
  wrapper.setAttribute("aria-label", label);
  const table = element("table");
  const head = element("thead"), heading = element("tr");
  for (const title of headers) { const th = element("th", title); th.scope = "col"; heading.append(th); }
  head.append(heading);
  const body = element("tbody");
  for (const row of rows) { const tr = element("tr"); for (const value of row) tr.append(element("td", value)); body.append(tr); }
  table.append(head, body); wrapper.append(table);
  return wrapper;
}

export function renderResults(container, best, configuration) {
  container.replaceChildren();
  if (!best?.evaluation) { container.append(element("p", "A scored schedule will appear here after an evaluation or colony run.", "muted")); return; }
  const result = best.evaluation;
  const summary = element("div", undefined, "result-summary");
  for (const [title, value] of [["Objective score", number.format(result.score)], ["Five-day cost", money.format(result.totals.cost)], ["School servings", number.format(result.totals.servings)], ["Total workload", number.format(result.totals.workload) + " person-min"]]) {
    const card = element("div", undefined, "result-stat"); card.append(element("span", title), element("strong", value)); summary.append(card);
  }
  container.append(summary);
  const targets = element("div", undefined, result.targets_met ? "target-status success" : "target-status warning");
  targets.append(element("strong", result.targets_met ? "All configured targets met" : "Best schedule found · targets remain unmet"));
  targets.append(element("p", `Weekly budget: ${money.format(result.totals.budget)}. Nutrition is per student; costs, ingredients and workload are school totals. This is demonstration data, not an official MBG nutrition assessment.`));
  if (result.violations.length) { const list = element("ul"); for (const violation of result.violations) list.append(element("li", violation)); targets.append(list); }
  container.append(targets);
  const score = element("details", undefined, "score-details"); score.append(element("summary", "Inspect score and configured targets"));
  score.append(element("p", "A lower weighted score is better. Zero-weight targets still appear as unmet when violated."));
  score.append(table(["Priority", "Normalized term", "Weight", "Contribution"], Object.keys(result.metrics).map(key => [key, number.format(result.metrics[key]), number.format(configuration.planning.weights[key]), number.format(result.contributions[key])]), "Score contributions"));
  const p = configuration.planning;
  score.append(element("p", `Per-serving targets: ${number.format(p.energy_min)}–${number.format(p.energy_max)} kcal, ≥ ${number.format(p.protein_min)} g protein, ≥ ${number.format(p.fiber_min)} g fiber. Budget ${money.format(p.budget_per_serving)}/serving. Kitchen capacity ${number.format(p.kitchen_capacity)} person-minutes/day. Protein repeat limit ${p.max_protein_repeats}; identical menu limit ${p.max_menu_repeats}.`));
  container.append(score);
  const menus = element("div", undefined, "result-menu-grid");
  for (const day of result.days) {
    const card = element("article", undefined, "result-day");
    card.append(element("p", `${number.format(day.servings)} school servings`, "eyebrow"), element("h3", day.day));
    const list = element("ul", undefined, "component-menu");
    for (const item of day.components) { const li = element("li"); li.append(element("span", item.category, "category-label"), element("strong", item.name)); list.append(li); }
    card.append(list);
    card.append(element("p", `${number.format(day.nutrition.energy)} kcal · ${number.format(day.nutrition.protein)} g protein · ${number.format(day.nutrition.fiber)} g fiber`, "nutrition-line"));
    card.append(element("p", `${money.format(day.cost)} total · ${money.format(day.cost_per_serving)} per serving`));
    card.append(element("p", `${number.format(day.workload)} person-minutes · budget ${money.format(day.budget)}`));
    const quantities = element("details"); quantities.append(element("summary", "Batch preparation & ingredients"));
    quantities.append(table(["Component", "Servings", "Batches"], day.component_quantities.map(row => [row.name, number.format(row.servings), number.format(row.batches)]), `${day.day} batch quantities`));
    quantities.append(table(["Ingredient", "Quantity", "Unit"], day.ingredients.map(row => [row.name, number.format(row.quantity), row.unit]), `${day.day} ingredients`));
    card.append(quantities);
    if (day.violations.length) { const violations = element("ul", undefined, "day-violations"); for (const message of day.violations) violations.append(element("li", message)); card.append(violations); }
    menus.append(card);
  }
  container.append(menus);
  const purchasing = element("section", undefined, "purchasing-summary"); purchasing.append(element("h3", "Five-day purchasing list"), element("p", "Ingredient quantities come from the host evaluation. Different units stay separate; quantities are not rounded into packs or converted."));
  purchasing.append(table(["Ingredient", "Identifier", "Quantity", "Unit"], result.totals.ingredients.map(row => [row.name, row.id, number.format(row.quantity), row.unit]), "Weekly purchasing quantities"));
  container.append(purchasing);
  const actions = element("div", undefined, "result-actions");
  for (const format of ["json", "csv"]) { const button = element("button", `Download results ${format.toUpperCase()}`); button.type = "button"; button.dataset.export = format; button.addEventListener("click", () => exportResults(best, configuration, format)); actions.append(button); }
  container.append(actions);
}
