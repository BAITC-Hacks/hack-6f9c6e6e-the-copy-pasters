import { apiFetch, getAccessToken } from "./auth.js";
import { analyzeProvider } from "./ai.js";

const personalSection = document.querySelector("#personal-section");
const personalList = document.querySelector("#personal-list");
const personalCount = document.querySelector("#personal-count");
const providerDialog = document.querySelector("#provider-dialog");
const providerForm = document.querySelector("#provider-form");
const detailDialog = document.querySelector("#detail-dialog");
const detailContent = document.querySelector("#detail-content");
const detailMessage = document.querySelector("#detail-message");
const aiResult = document.querySelector("#ai-result");
const analyzeButton = document.querySelector("#analyze-button");
const ownerActions = document.querySelector("#detail-owner-actions");
let currentProfile = null;
let aiEnabled = false;
let currentCriteria = () => ({});
let onPersonalChange = () => {};

const fields = {
  name: "#provider-name-input", city: "#provider-city-input", categories: "#provider-categories-input",
  event_formats: "#provider-formats-input", price_from_kzt: "#provider-price-input",
  languages: "#provider-languages-input", max_hours: "#provider-hours-input", busy_dates: "#provider-busy-input",
  description: "#provider-description-input", phone: "#provider-phone-input",
  website: "#provider-website-input", social_link: "#provider-social-input",
};

function message(element, text = "", kind = "") {
  element.textContent = text;
  element.dataset.kind = kind;
}

function splitList(value) {
  return value.split(/[\n,;]+/).map((item) => item.trim()).filter(Boolean);
}

function money(value) {
  return value == null ? "Не указана" : `${new Intl.NumberFormat("ru-RU").format(value)} ₸`;
}

function item(label, value, full = false) {
  if (value == null || value === "" || (Array.isArray(value) && !value.length)) return null;
  const wrapper = document.createElement("div");
  wrapper.className = `detail-item${full ? " detail-item-full" : ""}`;
  const term = document.createElement("dt");
  term.textContent = label;
  const description = document.createElement("dd");
  description.textContent = Array.isArray(value) ? value.join(" · ") : String(value);
  wrapper.append(term, description);
  return wrapper;
}

function detailLink(label, value) {
  if (!value) return null;
  const wrapper = document.createElement("div");
  wrapper.className = "detail-item";
  const term = document.createElement("dt");
  term.textContent = label;
  const description = document.createElement("dd");
  const link = document.createElement("a");
  link.href = value;
  link.target = "_blank";
  link.rel = "noopener noreferrer";
  link.textContent = value;
  description.append(link);
  wrapper.append(term, description);
  return wrapper;
}

function renderDetails(profile) {
  detailContent.replaceChildren();
  const values = [
    item("Город", profile.city),
    item("Категории", profile.categories),
    item("Цена от", money(profile.price_from_kzt)),
    item("Форматы мероприятий", profile.event_formats),
    item("Языки", profile.languages),
    item("Максимум часов", profile.max_hours == null ? "Не указано" : `${profile.max_hours} ч`),
    item("Занятые даты", profile.busy_dates),
    item("Описание", profile.description || "Описание не заполнено.", true),
    item("Телефон", profile.phone),
    detailLink("Сайт", profile.website),
    detailLink("Соцсеть", profile.social_link),
  ];
  if (profile.synthetic) values.push(item("Данные", "Синтетический профиль"));
  if (profile.city_imputed) values.push(item("Город", "Восстановлен при подготовке данных"));
  if (profile.price_imputed) values.push(item("Цена", "Восстановлена при подготовке данных"));
  if (profile.source === "personal") values.push(item("Видимость", "Личный профиль, виден только вам"));
  for (const value of values.filter(Boolean)) detailContent.append(value);
}

function openDetail(profile) {
  currentProfile = profile;
  document.querySelector("#detail-title").textContent = profile.name;
  renderDetails(profile);
  ownerActions.hidden = profile.source !== "personal";
  analyzeButton.disabled = !aiEnabled;
  message(detailMessage, aiEnabled ? "" : "Добавьте OPENAI_API_KEY в .env, чтобы включить анализ.");
  aiResult.textContent = "Запустите анализ, чтобы получить краткое объяснение сильных сторон и недостающей информации.";
  detailDialog.showModal();
}

async function fetchDetails(providerId) {
  const response = await apiFetch(`/api/providers/${encodeURIComponent(providerId)}`);
  const profile = await response.json();
  if (!response.ok) throw new Error(profile.detail || "Не удалось загрузить профиль.");
  openDetail(profile);
}

export function openProviderById(providerId) {
  return fetchDetails(providerId);
}

function profileButton(profile) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "provider-link";
  button.textContent = profile.name;
  button.addEventListener("click", () => fetchDetails(profile.id).catch((error) => alert(error.message)));
  return button;
}

export async function refreshPersonalProviders() {
  if (!getAccessToken()) {
    personalSection.hidden = true;
    return;
  }
  try {
    const response = await apiFetch("/api/personal-providers");
    const profiles = await response.json();
    if (!response.ok) throw new Error(profiles.detail || "Не удалось загрузить личный каталог.");
    personalList.replaceChildren();
    personalCount.textContent = `${profiles.length}`;
    for (const profile of profiles) {
      const row = document.createElement("div");
      row.className = "personal-row";
      const main = document.createElement("div");
      main.className = "personal-row-main";
      main.append(profileButton(profile));
      const meta = document.createElement("span");
      meta.className = "provider-source";
      meta.textContent = `${profile.categories.join(" · ")} · ${profile.city}`;
      main.append(meta);
      const price = document.createElement("span");
      price.className = "personal-price";
      price.textContent = money(profile.price_from_kzt);
      const open = document.createElement("button");
      open.type = "button";
      open.className = "quiet-button personal-open";
      open.textContent = "Открыть";
      open.addEventListener("click", () => fetchDetails(profile.id).catch((error) => alert(error.message)));
      row.append(main, price, open);
      personalList.append(row);
    }
    personalSection.hidden = false;
    if (!profiles.length) {
      const empty = document.createElement("p");
      empty.className = "empty-prompt";
      empty.textContent = "Здесь появятся подрядчики, которых вы добавите для себя.";
      personalList.append(empty);
    }
  } catch (error) {
    personalSection.hidden = false;
    personalList.replaceChildren();
    const failure = document.createElement("p");
    failure.className = "status-panel";
    failure.dataset.kind = "error";
    failure.textContent = error.message;
    personalList.append(failure);
  }
}

function openProviderForm(profile = null) {
  providerForm.reset();
  message(document.querySelector("#provider-form-message"));
  document.querySelector("#provider-id").value = profile?.id || "";
  document.querySelector("#provider-form-title").textContent = profile ? "Изменить подрядчика" : "Добавить подрядчика";
  for (const [key, selector] of Object.entries(fields)) {
    const input = document.querySelector(selector);
    let value = profile?.[key];
    if (Array.isArray(value)) value = value.join(", ");
    if (key === "busy_dates" && Array.isArray(value)) value = value.map((date) => String(date).slice(0, 10)).join(", ");
    input.value = value ?? "";
  }
  providerDialog.showModal();
}

function formPayload() {
  const text = (name) => document.querySelector(fields[name]).value.trim();
  const hours = text("max_hours");
  return {
    name: text("name"),
    city: text("city"),
    categories: splitList(text("categories")),
    event_formats: splitList(text("event_formats")),
    price_from_kzt: Number(text("price_from_kzt")),
    languages: splitList(text("languages")),
    max_hours: hours ? Number(hours) : null,
    busy_dates: splitList(text("busy_dates")),
    description: text("description"),
    phone: text("phone") || null,
    website: text("website") || null,
    social_link: text("social_link") || null,
  };
}

export function initProviders({ getCriteria, config, onChange }) {
  currentCriteria = getCriteria;
  aiEnabled = Boolean(config?.ai_enabled);
  onPersonalChange = onChange;
  const addButton = document.querySelector("#add-provider-button");
  addButton.addEventListener("click", () => openProviderForm());

  providerForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!providerForm.reportValidity()) return;
    const id = document.querySelector("#provider-id").value;
    const saveButton = providerForm.querySelector('[type="submit"]');
    saveButton.disabled = true;
    message(document.querySelector("#provider-form-message"), "Сохраняем…");
    try {
      const response = await apiFetch(id ? `/api/personal-providers/${encodeURIComponent(id)}` : "/api/personal-providers", {
        method: id ? "PUT" : "POST",
        body: JSON.stringify(formPayload()),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || "Не удалось сохранить профиль.");
      providerDialog.close();
      await refreshPersonalProviders();
      await onPersonalChange();
    } catch (error) {
      message(document.querySelector("#provider-form-message"), error.message, "error");
    } finally {
      saveButton.disabled = false;
    }
  });

  document.querySelector("#analyze-button").addEventListener("click", async () => {
    if (!currentProfile || !aiEnabled) return;
    analyzeButton.disabled = true;
    aiResult.textContent = "Анализируем данные профиля…";
    message(detailMessage);
    try {
      aiResult.textContent = await analyzeProvider(currentProfile.id, currentCriteria());
    } catch (error) {
      aiResult.textContent = "";
      message(detailMessage, error.message, "error");
    } finally {
      analyzeButton.disabled = false;
    }
  });

  document.querySelector("#edit-provider-button").addEventListener("click", () => {
    if (!currentProfile || currentProfile.source !== "personal") return;
    detailDialog.close();
    openProviderForm(currentProfile);
  });

  document.querySelector("#delete-provider-button").addEventListener("click", async () => {
    if (!currentProfile || currentProfile.source !== "personal") return;
    if (!window.confirm(`Удалить профиль «${currentProfile.name}» из вашего каталога?`)) return;
    try {
      const response = await apiFetch(`/api/personal-providers/${encodeURIComponent(currentProfile.id)}`, { method: "DELETE" });
      if (!response.ok) {
        const result = await response.json();
        throw new Error(result.detail || "Не удалось удалить профиль.");
      }
      detailDialog.close();
      await refreshPersonalProviders();
      await onPersonalChange();
    } catch (error) {
      message(detailMessage, error.message, "error");
    }
  });

  for (const dialog of [providerDialog, detailDialog]) {
    for (const close of dialog.querySelectorAll("[data-close-dialog]")) close.addEventListener("click", () => dialog.close());
    dialog.addEventListener("click", (event) => { if (event.target === dialog) dialog.close(); });
  }
}

export function onAuthChanged(user) {
  const authButton = document.querySelector("#auth-button");
  const addButton = document.querySelector("#add-provider-button");
  if (user) {
    authButton.textContent = `Выйти · ${user.email || "аккаунт"}`;
    addButton.hidden = false;
  } else {
    authButton.textContent = "Войти";
    addButton.hidden = true;
  }
  refreshPersonalProviders();
}
