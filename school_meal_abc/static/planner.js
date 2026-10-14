import {api, loadConfiguration, saveConfiguration, resetConfiguration, validateConfiguration, configurationNotice, CATEGORIES, DAYS} from "./configuration.js";
import {renderResults} from "./results.js";

const $ = selector => document.querySelector(selector);
let configuration, schedule = [], best = null, busy = false;
const labels = {staple: "Staple", protein: "Protein dish", vegetable: "Vegetable dish", fruit: "Fruit"};
const listText = text => text.split(",").map(item => item.trim()).filter(Boolean);
function node(tag, text, className) { const element = document.createElement(tag); if (text !== undefined) element.textContent = text; if (className) element.className = className; return element; }
function message(target, text) { const element = $(target); element.textContent = text; element.hidden = !text; }
function error(problem) { message("#error", problem.message || String(problem)); $("#error").focus(); }
function clearError() { message("#error", ""); }
function changed() {
  $("#save-status").textContent = "Unsaved changes · save before opening the bee lab";
  if (best) { best = null; $("#preview-results").replaceChildren(node("p", "Inputs changed. Evaluate this schedule again to refresh its results.", "muted")); }
}
function field(id, label, value, update, options = {}) {
  const wrapper = node("div", undefined, "field");
  const labelNode = node("label", label); labelNode.htmlFor = id;
  const input = node(options.choices ? "select" : "input"); input.id = id; input.name = id;
  if (options.choices) { for (const [key, text] of options.choices) { const option = node("option", text); option.value = key; input.append(option); } }
  else { input.type = options.text ? "text" : "number"; if (!options.text) { input.min = options.min ?? 0; input.max = options.max ?? 10000000; input.step = options.integer ? 1 : "any"; } else input.maxLength = options.list ? 16100 : 160; }
  input.value = value;
  input.required = !options.optional;
  input.addEventListener("input", () => { update(options.text || options.choices ? input.value : input.valueAsNumber); if (options.draft !== false) changed(); });
  wrapper.append(labelNode, input);
  if (options.help) { const help = node("p", options.help, "field-help"); help.id = id + "-help"; input.setAttribute("aria-describedby", help.id); wrapper.append(help); }
  return wrapper;
}
function renderPlanning() {
  const p = configuration.planning, a = configuration.algorithm;
  $("#serving-fields").replaceChildren(...DAYS.map((day, index) => field(`servings-${index}`, `${day} servings`, p.servings[index], value => p.servings[index] = value, {min: 1, max: 1000000, integer: true})));
  const settings = [
    ["budget_per_serving", "Budget / student (Rp)", {min: 0.001}],
    ["energy_min", "Minimum energy (kcal)", {min: 0.001}],
    ["energy_max", "Maximum energy (kcal)", {min: 0.001}],
    ["protein_min", "Minimum protein (g)", {min: 0.001}],
    ["fiber_min", "Minimum fiber (g)", {min: 0.001}],
    ["kitchen_capacity", "Kitchen capacity / day", {min: 0.001, help: "Person-minutes of work available per day."}],
    ["max_protein_repeats", "Protein repetition limit", {min: 1, max: 5, integer: true, help: "Maximum appearances of one protein dish in five days."}],
    ["max_menu_repeats", "Identical menu repetition limit", {min: 1, max: 5, integer: true, help: "Maximum appearances of the same four-component menu."}],
  ];
  $("#planning-fields").replaceChildren(...settings.map(([key, label, options]) => field(key, label, p[key], value => p[key] = value, options)));
  $("#dietary-field").replaceChildren(field("exclusions", "Dietary exclusions (tags)", p.exclusions.join(", "), value => { p.exclusions = listText(value); renderSchedule(); }, {text: true, list: true, optional: true, help: "Comma-separated tags, e.g. soy, egg, fish. A matching tag excludes the whole component. Every category must keep at least one option."}));
  const weightHelp = {cost: "Weekly cost relative to the weekly budget.", budget: "Daily spending beyond the budget.", nutrition: "Energy, protein and fiber target deviations.", variety: "Repeated protein dishes and identical menus.", workload: "Kitchen work beyond daily capacity."};
  $("#weight-fields").replaceChildren(...Object.keys(p.weights).map(key => field(`weight-${key}`, `${key.charAt(0).toUpperCase() + key.slice(1)} weight`, p.weights[key], value => p.weights[key] = value, {help: weightHelp[key]})));
  const algorithmFields = [
    ["sources", "Food sources / employed bees", 2, 80, "Each source is one complete weekly schedule."],
    ["onlookers", "Onlooker attempts / cycle", 1, 160, "Fitness-weighted selections during each cycle."],
    ["limit", "Abandonment limit", 1, 10000, "Consecutive failed attempts before a source becomes a scout."],
    ["max_cycles", "Maximum cycles", 1, 2000, "Maximum employed, onlooker and scout phase passes."],
    ["patience", "Cycles without improvement", 0, 2000, "Stop when the best score stagnates. Use 0 to disable."],
    ["seed", "Random seed", Number.MIN_SAFE_INTEGER, Number.MAX_SAFE_INTEGER, "A whole number. Same inputs and seed reproduce the same run."],
  ];
  $("#algorithm-fields").replaceChildren(...algorithmFields.map(([key, label, min, max, help]) => field(key, label, a[key], value => a[key] = value, {min, max, integer: true, help})));
}
function renderCatalog() {
  const list = $("#catalog-list"); list.replaceChildren();
  for (const [index, item] of configuration.catalog.entries()) {
    const card = node("details", undefined, "catalog-card"); card.dataset.index = index;
    const summary = node("summary");
    const summaryText = node("span", item.name || "Unnamed component", "component-name");
    const category = node("span", labels[item.category], "category-chip");
    summary.append(summaryText, category); card.append(summary);
    const content = node("div", undefined, "catalog-content"), grid = node("div", undefined, "field-grid");
    grid.append(field(`component-${index}-id`, "Component ID", item.id, value => { item.id = value; renderSchedule(); }, {text: true, help: "Unique ID used in schedules and result exports."}));
    grid.append(field(`component-${index}-name`, "Component name", item.name, value => { item.name = value; summaryText.textContent = value || "Unnamed component"; renderSchedule(); }, {text: true}));
    grid.append(field(`component-${index}-category`, "Component category", item.category, value => { item.category = value; category.textContent = labels[value]; renderSchedule(); }, {choices: CATEGORIES.map(key => [key, labels[key]])}));
    for (const [key, label] of [["cost", "Cost / serving (Rp)"], ["energy", "Energy / serving (kcal)"], ["protein", "Protein / serving (g)"], ["fiber", "Fiber / serving (g)"], ["batch_size", "Servings / batch"], ["work_minutes", "Person-minutes / batch"]]) grid.append(field(`component-${index}-${key}`, label, item[key], value => item[key] = value, key === "batch_size" ? {min: 1, max: 1000000, integer: true} : {}));
    grid.append(field(`component-${index}-tags`, "Dietary / allergen tags", item.tags.join(", "), value => { item.tags = listText(value); renderSchedule(); }, {text: true, list: true, optional: true, help: "Comma-separated exact tags. These match dietary exclusions."}));
    content.append(grid);
    const ingredientHeader = node("div", undefined, "ingredient-header"); ingredientHeader.append(node("h3", "Ingredients per serving"));
    const addIngredient = node("button", "+ Add ingredient"); addIngredient.type = "button"; addIngredient.id = `add-ingredient-${index}`;
    const ingredientList = node("div", undefined, "ingredient-list");
    function renderIngredients() {
      ingredientList.replaceChildren();
      for (const [position, ingredient] of item.ingredients.entries()) {
        const row = node("div", undefined, "ingredient-row");
        for (const [key, label] of [["id", "Ingredient ID"], ["name", "Ingredient name"], ["quantity", "Quantity / serving"], ["unit", "Unit"]]) row.append(field(`ingredient-${index}-${position}-${key}`, label, ingredient[key], value => ingredient[key] = value, {text: key !== "quantity"}));
        const remove = node("button", "Remove"); remove.type = "button"; remove.className = "danger quiet"; remove.setAttribute("aria-label", `Remove ingredient ${position + 1} from ${item.name}`);
        remove.addEventListener("click", () => { item.ingredients.splice(position, 1); renderIngredients(); changed(); addIngredient.focus(); }); row.append(remove); ingredientList.append(row);
      }
      if (!item.ingredients.length) ingredientList.append(node("p", "No ingredients entered. Add them to include this component in the purchasing list.", "muted"));
      addIngredient.disabled = item.ingredients.length >= 100;
    }
    addIngredient.addEventListener("click", () => { item.ingredients.push({id: "", name: "", quantity: 0, unit: "g"}); renderIngredients(); changed(); $(`#ingredient-${index}-${item.ingredients.length - 1}-id`).focus(); });
    ingredientHeader.append(addIngredient); content.append(ingredientHeader, ingredientList, node("p", "Use the same ingredient ID and unit to aggregate purchases. Keep units consistent; g and kg are intentionally kept separate.", "field-help")); renderIngredients();
    const remove = node("button", "Delete component", "danger quiet"); remove.type = "button"; remove.id = `delete-component-${index}`; remove.setAttribute("aria-label", `Delete component ${item.name}`);
    remove.addEventListener("click", () => { configuration.catalog.splice(index, 1); changed(); renderCatalog(); renderSchedule(); $("#add-component").focus(); }); content.append(remove);
    card.append(content); list.append(card);
  }
  filterCatalog();
}
function filterCatalog() {
  if (!configuration) return;
  const query = $("#catalog-search").value.trim().toLocaleLowerCase(), category = $("#catalog-category").value;
  let visible = 0;
  for (const card of $("#catalog-list").children) { const item = configuration.catalog[Number(card.dataset.index)]; card.hidden = !!((category && item.category !== category) || (query && !`${item.name} ${item.id}`.toLocaleLowerCase().includes(query))); if (!card.hidden) visible++; }
  $("#catalog-count").textContent = `${visible} of ${configuration.catalog.length} components shown`;
  $("#add-component").disabled = configuration.catalog.length >= 1000;
}
function eligible(category) { return configuration.catalog.filter(item => item.category === category && !item.tags.some(tag => configuration.planning.exclusions.includes(tag))); }
function renderSchedule(fill = false) {
  const container = $("#schedule-fields"); container.replaceChildren();
  for (const [dayIndex, day] of DAYS.entries()) {
    const card = node("div", undefined, "schedule-day"); card.append(node("h3", day));
    for (const [categoryIndex, category] of CATEGORIES.entries()) {
      const position = dayIndex * 4 + categoryIndex, choices = eligible(category);
      if (fill || !choices.some(item => item.id === schedule[position])) schedule[position] = choices[dayIndex % (choices.length || 1)]?.id || "";
      const options = choices.length ? choices.map(item => [item.id, item.name]) : [["", "No eligible components"]];
      card.append(field(`schedule-${position}`, labels[category], schedule[position], value => { schedule[position] = value; if (best) { best = null; $("#preview-results").replaceChildren(node("p", "Menu changed. Evaluate again to see current results.", "muted")); } }, {choices: options, draft: false}));
    }
    container.append(card);
  }
}
function renderAll() { schedule = []; best = null; renderPlanning(); renderCatalog(); renderSchedule(true); $("#preview-results").replaceChildren(); }
function readConfiguration() {
  const form = $("#configuration-form");
  if (!form.checkValidity()) {
    const invalid = form.querySelector(":invalid");
    for (let parent = invalid?.parentElement; parent; parent = parent.parentElement) { if (parent.tagName === "DETAILS") parent.open = true; if (parent.hidden) parent.hidden = false; }
    invalid?.reportValidity(); invalid?.focus(); throw new Error("Complete the highlighted field with a valid value before continuing.");
  }
  const validated = validateConfiguration(configuration);
  schedule = schedule.map(id => id.trim());
  return validated;
}
async function evaluate(validated) { return api("/api/evaluate", {method: "POST", body: {catalog: validated.catalog, planning: validated.planning, schedule}}); }
async function action(callback) {
  if (busy) return;
  busy = true; clearError();
  const editorControls = [...document.querySelectorAll("input,select,#add-component,#fill-schedule,#catalog-list button")].map(control => [control, control.disabled]);
  for (const [control] of editorControls) control.disabled = true;
  for (const id of ["save-configuration", "evaluate-preview", "reset-configuration", "export-configuration"]) $("#" + id).disabled = true;
  try { await callback(); } catch (problem) { error(problem); }
  finally { busy = false; for (const [control, disabled] of editorControls) control.disabled = disabled; for (const id of ["save-configuration", "evaluate-preview", "reset-configuration", "export-configuration"]) $("#" + id).disabled = !configuration; }
}
$("#configuration-form").addEventListener("submit", event => event.preventDefault());
$("#save-configuration").addEventListener("click", () => action(async () => {
  const validated = readConfiguration(); await evaluate(validated);
  const saved = saveConfiguration(validated); message("#notice", saved.message || "");
  $("#save-status").textContent = saved.persisted ? "Saved · ready for the bee lab" : "Ready in this page · download to preserve";
}));
$("#evaluate-preview").addEventListener("click", () => action(async () => {
  const validated = readConfiguration(); $("#evaluate-preview").textContent = "Evaluating…";
  try { const evaluation = await evaluate(validated); best = {schedule: [...schedule], evaluation}; renderResults($("#preview-results"), best, validated); }
  finally { $("#evaluate-preview").textContent = "Evaluate on Python host"; }
}));
$("#fill-schedule").addEventListener("click", () => { renderSchedule(true); best = null; $("#preview-results").replaceChildren(); clearError(); });
$("#export-configuration").addEventListener("click", () => action(async () => {
  const validated = readConfiguration(), url = URL.createObjectURL(new Blob([JSON.stringify(validated, null, 2)], {type: "application/json;charset=utf-8"}));
  const link = node("a"); link.href = url; link.download = "abc-configuration.json"; document.body.append(link); link.click(); link.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
}));
$("#import-configuration").addEventListener("change", event => action(async () => {
  const file = event.target.files[0]; if (!file) return;
  try {
    if (file.size > 20000000) throw new Error("Configuration file is too large (maximum 20 MB).");
    let parsed; try { parsed = JSON.parse(await file.text()); } catch { throw new Error("This file is not valid JSON. Import an exported ABC configuration or results JSON."); }
    const imported = validateConfiguration(parsed.configuration || parsed);
    // Validation stays on the host before replacing the current draft.
    const options = Object.fromEntries(CATEGORIES.map(category => [category, imported.catalog.filter(item => item.category === category && !item.tags.some(tag => imported.planning.exclusions.includes(tag)))]));
    const probe = DAYS.flatMap((_, day) => CATEGORIES.map(category => options[category][day % options[category].length].id));
    await api("/api/evaluate", {method: "POST", body: {catalog: imported.catalog, planning: imported.planning, schedule: probe}});
    configuration = imported; renderAll(); changed(); message("#notice", "Configuration imported. Review it and save to use it in the bee lab.");
  } finally { event.target.value = ""; }
}));
$("#reset-configuration").addEventListener("click", () => action(async () => { configuration = await resetConfiguration(); renderAll(); $("#save-status").textContent = "Demonstration defaults restored"; message("#notice", "Demo defaults restored. Previously created runs keep their original input snapshot."); }));
$("#add-component").addEventListener("click", () => {
  if (!configuration) return;
  const category = $("#catalog-category").value || "staple";
  let index = 1; while (configuration.catalog.some(item => item.id === `new-component-${index}`)) index++;
  configuration.catalog.push({id: `new-component-${index}`, name: "New component", category, cost: 0, energy: 0, protein: 0, fiber: 0, tags: [], ingredients: [], batch_size: 100, work_minutes: 0});
  $("#catalog-search").value = ""; renderCatalog(); renderSchedule(); changed();
  const card = $("#catalog-list").lastElementChild; card.open = true; $(`#component-${configuration.catalog.length - 1}-name`).focus();
});
$("#catalog-search").addEventListener("input", filterCatalog); $("#catalog-category").addEventListener("change", filterCatalog);
try {
  configuration = await loadConfiguration(); renderAll();
  for (const id of ["save-configuration", "export-configuration", "reset-configuration", "evaluate-preview", "fill-schedule"]) $("#" + id).disabled = false;
  $("#save-status").textContent = "Ready · settings saved in this browser"; message("#notice", configurationNotice());
} catch (problem) { error(problem); $("#save-status").textContent = "Host unavailable · reload after starting the Python app"; }
