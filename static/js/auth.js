const TOKEN_KEY = "eventmatch.access-token";
const REFRESH_KEY = "eventmatch.refresh-token";
let accessToken = sessionStorage.getItem(TOKEN_KEY) || "";
let refreshToken = sessionStorage.getItem(REFRESH_KEY) || "";
let currentUser = null;
let onStateChange = () => {};

export function getAccessToken() {
  return accessToken;
}

export async function apiFetch(url, options = {}) {
  const retryOptions = { ...options };
  const headers = new Headers(options.headers || {});
  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);
  if (options.body && !headers.has("Content-Type")) headers.set("Content-Type", "application/json");
  let response = await fetch(url, { ...options, headers });
  if (response.status === 401 && refreshToken && !url.endsWith("/auth/refresh")) {
    try {
      const refreshed = await fetch("/api/auth/refresh", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
      const session = await refreshed.json();
      if (refreshed.ok && session.access_token) {
        setSession(session.access_token, session.user, session.refresh_token);
        const retryHeaders = new Headers(retryOptions.headers || {});
        retryHeaders.set("Authorization", `Bearer ${accessToken}`);
        if (retryOptions.body && !retryHeaders.has("Content-Type")) retryHeaders.set("Content-Type", "application/json");
        response = await fetch(url, { ...retryOptions, headers: retryHeaders });
      }
    } catch (_) { /* The original 401 below clears the expired session. */ }
  }
  if (response.status === 401 && accessToken) {
    accessToken = "";
    refreshToken = "";
    currentUser = null;
    sessionStorage.removeItem(TOKEN_KEY);
    sessionStorage.removeItem(REFRESH_KEY);
    onStateChange(null);
  }
  return response;
}

function setSession(token, user, refresh = refreshToken) {
  accessToken = token || "";
  refreshToken = refresh || "";
  currentUser = user || null;
  if (accessToken) sessionStorage.setItem(TOKEN_KEY, accessToken);
  else sessionStorage.removeItem(TOKEN_KEY);
  if (refreshToken) sessionStorage.setItem(REFRESH_KEY, refreshToken);
  else sessionStorage.removeItem(REFRESH_KEY);
  onStateChange(currentUser);
}

export async function initAuth(onChange) {
  onStateChange = onChange;
  const callbackParams = new URLSearchParams(window.location.hash.replace(/^#/, ""));
  const callbackToken = callbackParams.get("access_token");
  const callbackRefreshToken = callbackParams.get("refresh_token");
  if (callbackToken) {
    setSession(callbackToken, { email: "" }, callbackRefreshToken);
    window.history.replaceState({}, document.title, window.location.pathname + window.location.search);
  }
  const button = document.querySelector("#auth-button");
  const dialog = document.querySelector("#auth-dialog");
  const form = document.querySelector("#auth-form");
  const emailInput = document.querySelector("#auth-email");
  const passwordInput = document.querySelector("#auth-password");
  const title = document.querySelector("#auth-title");
  const submit = document.querySelector("#auth-submit");
  const modeButton = document.querySelector("#auth-mode-button");
  const message = document.querySelector("#auth-message");
  let mode = "login";

  const configResponse = await fetch("/api/config");
  const config = configResponse.ok ? await configResponse.json() : {};
  if (!config.accounts_enabled) {
    button.disabled = true;
    button.title = "Для аккаунтов настройте Supabase в .env и запустите SQL-миграцию.";
    button.textContent = "Аккаунты не настроены";
  } else {
    button.addEventListener("click", async () => {
      if (accessToken) {
        try { await apiFetch("/api/auth/logout", { method: "POST" }); } catch (_) { /* Clear local session regardless. */ }
        setSession("", null);
        return;
      }
      message.textContent = "";
      message.dataset.kind = "";
      dialog.showModal();
    });
  }

  modeButton.addEventListener("click", () => {
    mode = mode === "login" ? "signup" : "login";
    title.textContent = mode === "login" ? "Войти" : "Создать аккаунт";
    submit.textContent = title.textContent;
    passwordInput.autocomplete = mode === "login" ? "current-password" : "new-password";
    modeButton.textContent = mode === "login" ? "Создать аккаунт" : "Уже есть аккаунт? Войти";
    message.textContent = "";
    message.dataset.kind = "";
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!form.reportValidity()) return;
    submit.disabled = true;
    message.textContent = mode === "login" ? "Входим…" : "Создаём аккаунт…";
    message.dataset.kind = "";
    try {
      const response = await fetch(`/api/auth/${mode}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: emailInput.value.trim(), password: passwordInput.value }),
      });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || "Не удалось выполнить вход.");
      if (result.confirmation_required) {
        message.textContent = `Проверьте почту ${result.email}: Supabase отправил ссылку подтверждения. Затем войдите.`;
        passwordInput.value = "";
        return;
      }
      setSession(result.access_token, result.user, result.refresh_token);
      passwordInput.value = "";
      dialog.close();
    } catch (error) {
      message.textContent = error.message || "Не удалось связаться с сервисом.";
      message.dataset.kind = "error";
    } finally {
      submit.disabled = false;
    }
  });

  for (const close of dialog.querySelectorAll("[data-close-dialog]")) close.addEventListener("click", () => dialog.close());
  dialog.addEventListener("click", (event) => { if (event.target === dialog) dialog.close(); });

  if (accessToken) {
    try {
      const response = await apiFetch("/api/auth/me");
      if (!response.ok) setSession("", null);
      else setSession(accessToken, await response.json());
    } catch (_) {
      setSession("", null);
    }
  } else {
    onStateChange(null);
  }

  return config;
}
