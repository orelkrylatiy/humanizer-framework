const $ = (selector) => document.querySelector(selector);
const state = { options: null, currentView: "generator", busy: false };
const pageCopy = {
  generator: ["WORKSPACE / GENERATOR", "Генератор текста", "Выберите режим, задайте задачу и получите проверенный результат."],
  activity: ["OBSERVABILITY / ACTIVITY", "Активность", "Техническая история запусков, длительность и результаты проверок."],
  system: ["RUNTIME / SYSTEM", "Система", "Провайдеры, окружение и настройки приватности."]
};
function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;"
  })[char]);
}
function authHeaders() {
  const token = sessionStorage.getItem("humanizer-admin-token");
  const headers = { "Content-Type": "application/json" };
  if (token) headers.Authorization = "Bearer " + token;
  return headers;
}
async function api(path, options = {}) {
  const response = await fetch(path, { ...options, headers: { ...authHeaders(), ...(options.headers || {}) } });
  if (response.status === 401) {
    const token = window.prompt("Введите HUMANIZER_ADMIN_TOKEN для доступа к админке:");
    if (token) { sessionStorage.setItem("humanizer-admin-token", token); return api(path, options); }
  }
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || data.error || ("HTTP " + response.status));
  return data;
}
function fillSelect(selector, items, selected) {
  const node = $(selector);
  node.innerHTML = items.map((item) => '<option value="' + escapeHtml(item.value) + '">' + escapeHtml(item.label) + "</option>").join("");
  if (selected) node.value = selected;
}
function updateCounts() {
  $("#prompt-count").textContent = $("#prompt").value.length + " / 3000";
  $("#source-count").textContent = $("#source-text").value.length + " / 1800";
}
function lines(selector) {
  return $(selector).value.split(/\r?\n/).map((value) => value.trim()).filter(Boolean);
}
function buildPayload() {
  let context;
  try { context = JSON.parse($("#context-json").value || "{}"); }
  catch (error) { throw new Error("Контекст должен быть корректным JSON: " + error.message); }
  if (!context || Array.isArray(context) || typeof context !== "object") throw new Error("Контекст должен быть JSON-объектом.");
  return {
    prompt: $("#prompt").value.trim(),
    source_text: $("#source-text").value.trim(),
    message_type: $("#mode").value,
    domain: $("#domain").value,
    channel: $("#channel").value,
    language: $("#language").value,
    profile: $("#profile").value.trim() || "default",
    context,
    business_rules: lines("#business-rules"),
    voice: {
      id: "custom",
      description: $("#voice-description").value.trim(),
      prefer: lines("#voice-prefer"),
      avoid: lines("#voice-avoid"),
      examples: lines("#voice-examples").slice(0, 3)
    }
  };
}
function showFormError(message) {
  const node = $("#form-error"); node.textContent = message; node.hidden = false;
}
function clearFormError() { $("#form-error").hidden = true; $("#form-error").textContent = ""; }
function setResultStatus(text, kind) {
  const node = $("#result-status"); node.textContent = text; node.className = "result-status " + kind;
}
function setBusy(value) {
  state.busy = value;
  $("#generate-button").disabled = value;
  $("#preview-button").disabled = value;
  $("#generate-button").innerHTML = value ? "◌ Генерируем…" : '<span>✳</span> Сгенерировать <span class="button-arrow">↗</span>';
}
function renderResult(data, isError) {
  $("#result-empty").hidden = true; $("#result-content").hidden = false;
  $("#result-text").value = data.text || "";
  const valid = data.valid === true;
  $("#result-validity").textContent = valid ? "✓ Проверки пройдены" : "⚠ Требуется проверка";
  $("#result-validity").className = "validity" + (valid ? "" : " warn");
  const meta = [];
  if (data.provider) meta.push("Провайдер: " + data.provider);
  if (data.model) meta.push("Модель: " + data.model);
  if (data.plan && data.plan.action) meta.push("Действие: " + data.plan.action);
  if (data.elapsed_ms != null) meta.push(data.elapsed_ms + " мс");
  if (data.rewritten) meta.push("Выполнена корректировка");
  $("#result-meta").innerHTML = meta.map((item) => '<span class="meta-chip">' + escapeHtml(item) + "</span>").join("");
  const issues = Array.isArray(data.issues) ? data.issues : [];
  const issueBox = $("#issues-box");
  if (issues.length) {
    issueBox.hidden = false;
    issueBox.innerHTML = "<strong>Замечания валидатора</strong>" + issues.map((issue) =>
      '<div>• ' + escapeHtml(issue.code) + (issue.hard ? " · критично" : " · рекомендация") + "</div>"
    ).join("");
  } else { issueBox.hidden = true; issueBox.textContent = ""; }
  setResultStatus(isError ? "Есть замечания" : "Готово", isError ? "error" : "success");
}
async function generate(event) {
  event.preventDefault();
  if (state.busy) return;
  clearFormError();
  let payload;
  try {
    payload = buildPayload();
    if (!payload.prompt) throw new Error("Заполните поле «Что нужно написать».");
  } catch (error) { showFormError(error.message); return; }
  setBusy(true); setResultStatus("Выполняется", "loading");
  try {
    let response = await fetch("/api/generate", { method: "POST", headers: authHeaders(), body: JSON.stringify(payload) });
    let data = await response.json().catch(() => ({}));
    if (response.status === 401) {
      const token = window.prompt("Введите HUMANIZER_ADMIN_TOKEN для доступа к админке:");
      if (token) {
        sessionStorage.setItem("humanizer-admin-token", token);
        response = await fetch("/api/generate", { method: "POST", headers: authHeaders(), body: JSON.stringify(payload) });
        data = await response.json().catch(() => ({}));
      }
    }
    if (!response.ok) {
      if (data.text || data.issues) renderResult(data, true);
      throw new Error(data.error || data.detail || ("HTTP " + response.status));
    }
    renderResult(data, false); loadActivity(); loadSystem();
  } catch (error) { setResultStatus("Ошибка", "error"); showFormError(error.message); }
  finally { setBusy(false); }
}
async function previewPrompt() {
  clearFormError();
  let payload;
  try { payload = buildPayload(); if (!payload.prompt) throw new Error("Сначала укажите задачу для генерации."); }
  catch (error) { showFormError(error.message); return; }
  $("#preview-button").disabled = true;
  try {
    const data = await api("/api/preview", { method: "POST", body: JSON.stringify(payload) });
    const plan = data.plan || {};
    $("#preview-plan").innerHTML = [
      "Действие: " + (plan.action || "—"), "Этап: " + (plan.stage || "—"),
      "Длина: " + (plan.target_length || "—"), "Лимит: " + (plan.max_chars || "—") + " символов",
      "Вопрос: " + (plan.ask_question ? "разрешен" : "не запрашивается"),
      "CTA: " + (plan.allow_cta ? "разрешен" : "запрещен")
    ].map((item) => '<span class="meta-chip">' + escapeHtml(item) + "</span>").join("");
    $("#prompt-preview").textContent = data.messages.map((message) => "[" + message.role.toUpperCase() + "]\n" + message.content).join("\n\n");
    $("#preview-panel").hidden = false;
    $("#preview-panel").scrollIntoView({ behavior: "smooth", block: "start" });
  } catch (error) { showFormError(error.message); }
  finally { $("#preview-button").disabled = false; }
}
function switchView(view) {
  state.currentView = view;
  document.querySelectorAll(".nav-item").forEach((button) => button.classList.toggle("active", button.dataset.view === view));
  document.querySelectorAll(".view").forEach((node) => node.classList.toggle("active", node.id === "view-" + view));
  $("#page-eyebrow").textContent = pageCopy[view][0];
  $("#page-title").textContent = pageCopy[view][1];
  $("#page-subtitle").textContent = pageCopy[view][2];
  if (view === "activity") loadActivity();
  if (view === "system") loadSystem();
}
async function loadOptions() {
  const data = await api("/api/options"); state.options = data;
  fillSelect("#mode", data.modes, "channel_post");
  fillSelect("#domain", data.domains, "generic");
  fillSelect("#channel", data.channels, "generic");
  fillSelect("#language", data.languages, "ru");
  updateModeDescription();
}
function updateModeDescription() {
  const mode = state.options?.modes.find((item) => item.value === $("#mode").value);
  $("#mode-description").textContent = mode ? mode.description : "";
}
async function loadStatus() {
  try {
    const data = await api("/api/status");
    $("#sidebar-version").textContent = data.version; $("#footer-version").textContent = data.version;
    const ready = (data.provider_chain || []).some((item) => item.ready === true);
    $("#top-status-dot").style.background = ready ? "var(--green)" : "var(--amber)";
    $("#top-status-text").textContent = ready ? "Провайдер настроен" : "Настройте провайдер";
  } catch (error) {
    $("#top-status-dot").style.background = "var(--red)"; $("#top-status-text").textContent = "Нет связи с API";
  }
}
async function loadSystem() {
  try {
    const data = await api("/api/status");
    $("#system-summary").innerHTML = [
      ["Версия библиотеки", data.version], ["Python", data.python],
      ["Телеметрия", data.telemetry.enabled ? "Включена" : "Отключена"]
    ].map((item) => '<article class="system-card"><span>' + escapeHtml(item[0]) + '</span><strong>' + escapeHtml(item[1]) + "</strong></article>").join("");
    $("#provider-list").innerHTML = (data.provider_chain || []).map((provider, index) => {
      const ready = provider.ready === true;
      const unknown = provider.ready === null;
      return '<div class="provider-row"><div class="provider-name">' + (index + 1) + ". " + escapeHtml(provider.name) + "</div>" +
        '<div class="provider-model">' + escapeHtml(provider.model || "Модель задается провайдером") + "</div>" +
        '<span class="provider-state ' + (ready ? "ready" : "missing") + '">' + (ready ? "Настроен" : unknown ? "Настроен отдельно" : "Не готов") + "</span>" +
        '<div class="provider-detail">' + escapeHtml(provider.detail || "") + "</div></div>";
    }).join("") || '<div class="table-empty">Цепочка провайдеров не обнаружена.</div>';
  } catch (error) { $("#system-summary").innerHTML = '<div class="notice">' + escapeHtml(error.message) + "</div>"; }
}
function formatTime(value) {
  if (!value) return "—";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
}
async function loadActivity() {
  try {
    const data = await api("/api/activity?limit=100");
    const summary = data.summary || {};
    $("#metric-success").textContent = summary.successes ?? "—";
    $("#metric-failures").textContent = summary.failures ?? "—";
    $("#metric-duration").textContent = summary.average_ms == null ? "—" : summary.average_ms;
    $("#metric-rewritten").textContent = summary.rewritten ?? "—";
    $("#activity-caption").textContent = "Показано: " + (summary.shown || 0);
    $("#activity-disabled").hidden = data.enabled !== false;
    const rows = data.items || [];
    $("#activity-rows").innerHTML = rows.length ? rows.map((item) =>
      "<tr><td>" + escapeHtml(formatTime(item.timestamp)) + "</td>" +
      "<td>" + escapeHtml(item.project || "—") + "</td>" +
      "<td>" + escapeHtml(item.message_type || "—") + "</td>" +
      "<td>" + escapeHtml(item.channel || "—") + "</td>" +
      "<td>" + escapeHtml(item.provider || "—") + (item.model ? "<br><small>" + escapeHtml(item.model) + "</small>" : "") + "</td>" +
      "<td>" + ((item.usage_totals || []).map((usage) => {
        const hasTokens = ["total_tokens", "input_tokens", "output_tokens", "prompt_tokens", "completion_tokens"]
          .some((key) => typeof usage[key] === "number");
        const total = usage.total_tokens ?? ((usage.input_tokens || usage.prompt_tokens || 0) + (usage.output_tokens || usage.completion_tokens || 0));
        const cost = usage.cost_usd ?? usage.cost;
        return escapeHtml(usage.model || usage.provider || "usage") + ": " + escapeHtml(hasTokens ? total + " ток." : "нет данных") +
          (cost == null ? "" : "<br><small>" + escapeHtml(cost + " cost") + "</small>");
      }).join("<br>") || "—") + "</td>" +
      "<td>" + (item.elapsed_ms == null ? "—" : escapeHtml(item.elapsed_ms + " мс")) + "</td>" +
      '<td><span class="pill ' + (item.status === "success" ? "success" : "error") + '">' + (item.status === "success" ? "Успешно" : "Ошибка") + "</span></td></tr>"
    ).join("") : '<tr><td colspan="8" class="table-empty">' + (data.enabled === false ? "Телеметрия отключена." : "Пока нет записей генерации.") + "</td></tr>";
  } catch (error) { $("#activity-rows").innerHTML = '<tr><td colspan="8" class="table-empty">' + escapeHtml(error.message) + "</td></tr>"; }
}
document.querySelectorAll(".nav-item").forEach((button) => button.addEventListener("click", () => switchView(button.dataset.view)));
$("#generator-form").addEventListener("submit", generate);
$("#preview-button").addEventListener("click", previewPrompt);
$("#close-preview").addEventListener("click", () => { $("#preview-panel").hidden = true; });
$("#mode").addEventListener("change", updateModeDescription);
$("#prompt").addEventListener("input", updateCounts);
$("#source-text").addEventListener("input", updateCounts);
$("#refresh-activity").addEventListener("click", loadActivity);
$("#refresh-system").addEventListener("click", loadSystem);
$("#copy-button").addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText($("#result-text").value);
    $("#copy-button").innerHTML = "✓ <span>Скопировано</span>";
    setTimeout(() => { $("#copy-button").innerHTML = "▢ <span>Копировать</span>"; }, 1500);
  } catch (error) { $("#result-text").select(); document.execCommand("copy"); }
});
(async function init() {
  updateCounts();
  try { await loadOptions(); await loadStatus(); }
  catch (error) { showFormError("Не удалось загрузить настройки: " + error.message); }
})();
