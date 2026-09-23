import { apiFetch, initAuth } from "./auth.js";
import { initProviders, onAuthChanged, openProviderById } from "./providers.js";

const form = document.querySelector("#search-form");
const citySelect = document.querySelector("#city");
const formatSelect = document.querySelector("#event-format");
const categorySelect = document.querySelector("#category");
const languageSelect = document.querySelector("#language");
const results = document.querySelector("#results");
const resultCount = document.querySelector("#result-count");
const catalogNote = document.querySelector("#catalog-note");
const submitButton = document.querySelector("#submit-button");
let allCategories = [];

const rejectionLabels = {
  busy: "заняты на выбранную дату",
  format: "не подходят по формату",
  budget: "выше бюджета или цена не указана",
  language: "язык не подтверждён в профиле",
  hours: "не подходят по длительности или длительность не указана",
};

function setOptions(select, values, placeholder, selected = "") {
  select.replaceChildren();
  const first = document.createElement("option");
  first.value = "";
  first.textContent = placeholder;
  select.append(first);
  for (const value of values) {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = value;
    select.append(option);
  }
  if (selected && values.includes(selected)) select.value = selected;
  select.disabled = values.length === 0;
}

async function getOptions(city = "") {
  const query = new URLSearchParams();
  if (city) query.set("city", city);
  const response = await apiFetch(`/api/options${query.size ? `?${query}` : ""}`);
  if (!response.ok) throw new Error("Не удалось загрузить варианты для формы.");
  return response.json();
}

function showStatus(title, detail = "", kind = "info", reasons = null) {
  resultCount.textContent = "";
  results.replaceChildren();
  const panel = document.createElement("div");
  panel.className = "status-panel";
  panel.dataset.kind = kind;
  const heading = document.createElement("strong");
  heading.className = "status-title";
  heading.textContent = title;
  panel.append(heading);
  if (detail) {
    const copy = document.createElement("p");
    copy.className = "status-detail";
    copy.textContent = detail;
    panel.append(copy);
  }
  if (reasons) {
    const list = document.createElement("ul");
    list.className = "reason-list";
    for (const [key, count] of Object.entries(reasons)) {
      if (!count || !rejectionLabels[key]) continue;
      const item = document.createElement("li");
      item.textContent = `${count}: ${rejectionLabels[key]}`;
      list.append(item);
    }
    if (list.childElementCount) panel.append(list);
    const note = document.createElement("p");
    note.className = "overlap-note";
    note.textContent = "Причины могут пересекаться: один профиль иногда не проходит несколько условий.";
    panel.append(note);
  }
  results.append(panel);
  catalogNote.hidden = true;
}

function makeTag(label, className = "") {
  const tag = document.createElement("span");
  tag.className = `tag ${className}`.trim();
  tag.textContent = label;
  return tag;
}

function formatPrice(value) {
  return `${new Intl.NumberFormat("ru-RU").format(value)} ₸`;
}

function renderMatchTable(matches, selectedDate) {
  const table = document.createElement("table");
  table.className = "match-table";
  const head = document.createElement("thead");
  const headingRow = document.createElement("tr");
  for (const [label, className] of [["Подрядчик", ""], ["Условия профиля", ""], ["Цена", "price"]]) {
    const heading = document.createElement("th");
    heading.scope = "col";
    heading.className = className;
    heading.textContent = label;
    headingRow.append(heading);
  }
  head.append(headingRow);
  const body = document.createElement("tbody");

  for (const match of matches.slice(0, 3)) {
    const mainRow = document.createElement("tr");
    mainRow.className = "match-main-row";
    const providerCell = document.createElement("td");
    providerCell.className = "provider-cell";
    const name = document.createElement("button");
    name.type = "button";
    name.className = "provider-link provider-name";
    name.textContent = match.name;
    name.addEventListener("click", () => openProviderById(match.id).catch((error) => showStatus("Не удалось открыть профиль", error.message, "error")));
    const category = document.createElement("span");
    category.className = "provider-category";
    category.textContent = match.categories.join(" · ");
    providerCell.append(name, category);

    const metaCell = document.createElement("td");
    metaCell.className = "meta-cell";
    const meta = document.createElement("div");
    meta.className = "provider-meta";
    const shownDate = new Date(`${selectedDate}T00:00:00`).toLocaleDateString("ru-RU");
    meta.append(makeTag(`На ${shownDate}: не отмечена как занята`, "tag-available"));
    if (match.languages.length) meta.append(makeTag(match.languages.join(" · ")));
    if (match.max_hours !== null) meta.append(makeTag(`до ${match.max_hours} ч`));
    if (match.synthetic) meta.append(makeTag("Синтетический профиль", "tag-data"));
    if (match.city_imputed) meta.append(makeTag("Город восстановлен", "tag-data"));
    if (match.price_imputed) meta.append(makeTag("Цена восстановлена", "tag-data"));
    metaCell.append(meta);

    const priceCell = document.createElement("td");
    priceCell.className = "price-cell price";
    priceCell.append(document.createTextNode(formatPrice(match.price_from_kzt)));
    const priceCaption = document.createElement("span");
    priceCaption.className = "price-caption";
    priceCaption.textContent = "цена от";
    priceCell.append(priceCaption);
    mainRow.append(providerCell, metaCell, priceCell);

    const explanationRow = document.createElement("tr");
    explanationRow.className = "match-explanation-row";
    const explanationCell = document.createElement("td");
    explanationCell.colSpan = 3;
    const explanation = document.createElement("p");
    explanation.className = "explanation";
    explanation.textContent = match.explanation;
    explanationCell.append(explanation);
    explanationRow.append(explanationCell);
    body.append(mainRow, explanationRow);
  }

  table.append(head, body);
  results.replaceChildren(table);
  resultCount.textContent = `Найдено: ${matches.length}`;
  catalogNote.hidden = false;
}

function showValidationError(error) {
  const detail = error?.detail;
  let message = "Проверьте заполненные условия и попробуйте ещё раз.";
  if (Array.isArray(detail) && detail.length) {
    const item = detail[0];
    const fieldName = item.loc?.at(-1);
    message = `${fieldName ? `Проверьте поле «${fieldName}». ` : ""}${item.msg || message}`;
  } else if (detail?.message) {
    message = detail.message;
  }
  showStatus("Не удалось выполнить поиск", message, "error");
}

async function loadInitialOptions() {
  try {
    const previousCity = citySelect.value;
    const previousFormat = formatSelect.value;
    const previousLanguage = languageSelect.value;
    const options = await getOptions();
    setOptions(citySelect, options.cities, "Выберите город", previousCity);
    setOptions(formatSelect, options.event_formats, "Выберите формат", previousFormat);
    setOptions(languageSelect, options.languages, "Любой язык", previousLanguage);
    allCategories = options.categories;
    if (options.cities.length) {
      citySelect.value = options.cities[0];
      await updateCategories();
    }
  } catch (error) {
    showStatus("Не удалось загрузить каталог", "Обновите страницу. Если ошибка повторится, проверьте, запущено ли приложение.", "error");
  }
}

async function updateCategories() {
  const previous = categorySelect.value;
  try {
    const options = await getOptions(citySelect.value);
    const localCategories = new Set(options.categories.map((value) => value.toLocaleLowerCase("ru")));
    categorySelect.replaceChildren();
    const first = document.createElement("option");
    first.value = "";
    first.textContent = "Выберите категорию";
    categorySelect.append(first);
    for (const category of allCategories) {
      const option = document.createElement("option");
      option.value = category;
      option.textContent = localCategories.has(category.toLocaleLowerCase("ru"))
        ? category
        : `${category} — нет в городе`;
      categorySelect.append(option);
    }
    categorySelect.disabled = allCategories.length === 0;
    if (allCategories.includes(previous)) categorySelect.value = previous;
  } catch (error) {
    setOptions(categorySelect, [], "Не удалось загрузить категории");
    showStatus("Не удалось обновить каталог", "Измените город или обновите страницу.", "error");
  }
}

citySelect.addEventListener("change", updateCategories);

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!form.reportValidity()) return;

  const payload = {
    city: citySelect.value,
    event_date: form.elements.event_date.value,
    event_format: formatSelect.value,
    category: categorySelect.value,
    budget_kzt: Number(form.elements.budget_kzt.value),
    language: languageSelect.value || null,
    hours: form.elements.hours.value ? Number(form.elements.hours.value) : null,
  };

  submitButton.disabled = true;
  submitButton.textContent = "Подбираем…";
  results.setAttribute("aria-busy", "true");
  showStatus("Проверяем условия каталога…");

  try {
  const response = await apiFetch("/api/match", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json();
    if (!response.ok) {
      showValidationError(data);
    } else if (data.status === "no_category") {
      showStatus("В этом городе нет такой категории", "В каталоге пока не найден подрядчик с выбранной категорией.");
    } else if (data.status === "filtered_out") {
      showStatus(`Найдено профилей: ${data.candidate_count}, подходящих нет`, "Измените дату, бюджет или дополнительные условия.", "info", data.reasons);
    } else {
      renderMatchTable(data.matches, payload.event_date);
    }
  } catch (error) {
    showStatus("Не удалось связаться с сервисом", "Проверьте соединение и попробуйте отправить поиск ещё раз.", "error");
  } finally {
    results.setAttribute("aria-busy", "false");
    submitButton.disabled = false;
    submitButton.textContent = "Подобрать подрядчиков";
  }
});

const dateInput = form.elements.event_date;
const today = new Date();
const localToday = new Date(today.getTime() - today.getTimezoneOffset() * 60_000).toISOString().slice(0, 10);
dateInput.min = localToday;
dateInput.value = localToday;

async function initialize() {
  let runtimeConfig = {};
  let authReady = false;
  try {
    runtimeConfig = await initAuth((user) => {
      onAuthChanged(user);
      if (authReady) loadInitialOptions();
    });
  } catch (_) {
    document.querySelector("#auth-button").disabled = true;
  }
  initProviders({
    config: runtimeConfig,
    getCriteria: () => ({
      city: citySelect.value || null,
      event_date: form.elements.event_date.value || null,
      event_format: formatSelect.value || null,
      category: categorySelect.value || null,
      budget_kzt: form.elements.budget_kzt.value ? Number(form.elements.budget_kzt.value) : null,
      language: languageSelect.value || null,
      hours: form.elements.hours.value ? Number(form.elements.hours.value) : null,
    }),
    onChange: loadInitialOptions,
  });
  authReady = true;
  await loadInitialOptions();
}

initialize();
