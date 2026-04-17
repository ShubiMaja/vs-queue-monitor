// Bump `index.html` script src `?v=` when changing version (cache bust for ./app.js).
const APP_VERSION = "2.1.11";

/** Desktop notification icon (same-origin). */
const NOTIFICATION_ICON_URL = "./assets/icon.svg";

/** Shipped WAV clips (same-origin). Empty URL field in settings = use these. */
const DEFAULT_WARN_SOUND_URL = "./assets/sounds/warning.wav";
const DEFAULT_COMPLETION_SOUND_URL = "./assets/sounds/completion.wav";
const DEFAULT_INTERRUPT_SOUND_URL = "./assets/sounds/disconnected.wav";

const $ = (id) => /** @type {HTMLElement} */ (document.getElementById(id));

const ui = {
  btnPickLog: $("btnPickLog"),
  btnSettings: $("btnSettings"),
  btnHelp: $("btnHelp"),
  btnHelpClose: $("btnHelpClose"),
  tutorialOverlay: $("tutorialOverlay"),
  tutorialTitle: $("tutorialTitle"),
  tutorialStep: $("tutorialStep"),
  tutorialBody: $("tutorialBody"),
  btnTutorialSkip: $("btnTutorialSkip"),
  btnTutorialBack: $("btnTutorialBack"),
  btnTutorialNext: $("btnTutorialNext"),
  btnTutorialHelp: $("btnTutorialHelp"),
  btnStartStop: $("btnStartStop"),
  btnYScale: $("btnYScale"),
  btnGraphWindow: $("btnGraphWindow"),
  btnClear: $("btnClear"),
  btnCopyGraph: $("btnCopyGraph"),
  btnCopyHistory: $("btnCopyHistory"),
  btnRequestNotify: $("btnRequestNotify"),
  btnNotifyPill: $("btnNotifyPill"),
  notifyHint: $("notifyHint"),
  btnSaveSettings: $("btnSaveSettings"),
  btnCancelSettings: $("btnCancelSettings"),
  toastHost: $("toastHost"),
  restoreBanner: $("restoreBanner"),
  restoreBannerDetail: $("restoreBannerDetail"),
  btnResumeLastLog: $("btnResumeLastLog"),
  btnDismissRestoreBanner: $("btnDismissRestoreBanner"),
  interruptAdoptOverlay: $("interruptAdoptOverlay"),
  interruptAdoptDetail: $("interruptAdoptDetail"),
  btnInterruptAdoptConfirm: $("btnInterruptAdoptConfirm"),
  btnInterruptAdoptNotNow: $("btnInterruptAdoptNotNow"),
  helpOverlay: $("helpOverlay"),
  settingsOverlay: $("settingsOverlay"),
  btnSettingsClose: $("btnSettingsClose"),
  settingsForm: /** @type {HTMLElement} */ (document.querySelector("#settingsOverlay .form")),
  inpHelpSourcePath: /** @type {HTMLInputElement} */ ($("inpHelpSourcePath")),
  btnHelpLoadFile: $("btnHelpLoadFile"),
  btnHelpPlatWin: $("btnHelpPlatWin"),
  btnHelpPlatUnix: $("btnHelpPlatUnix"),
  btnHelpCopyCmd: $("btnHelpCopyCmd"),
  preHelpCmd: $("preHelpCmd"),
  spanHelpPickPath: $("spanHelpPickPath"),
  graphCanvas: /** @type {HTMLCanvasElement} */ ($("graphCanvas")),
  graphHint: $("graphHint"),

  kpiPosition: $("kpiPosition"),
  kpiStatus: $("kpiStatus"),
  kpiStatusLabel: $("kpiStatusLabel"),
  kpiRateLabel: $("kpiRateLabel"),
  kpiRate: $("kpiRate"),
  btnRateEdit: $("btnRateEdit"),
  btnStatusRefreshEdit: $("btnStatusRefreshEdit"),
  statusRefreshPopover: $("statusRefreshPopover"),
  inpStatusRefreshSec: /** @type {HTMLInputElement} */ ($("inpStatusRefreshSec")),
  btnStatusRefreshOk: $("btnStatusRefreshOk"),
  btnStatusRefreshCancel: $("btnStatusRefreshCancel"),
  rateWindowPopover: $("rateWindowPopover"),
  inpRateWindowPoints: /** @type {HTMLInputElement} */ ($("inpRateWindowPoints")),
  btnRateWindowOk: $("btnRateWindowOk"),
  btnRateWindowCancel: $("btnRateWindowCancel"),
  kpiWarnings: $("kpiWarnings"),
  kpiWarningsRail: $("kpiWarningsRail"),
  btnWarnScrollL: $("btnWarnScrollL"),
  btnWarnScrollR: $("btnWarnScrollR"),
  btnWarningsEdit: $("btnWarningsEdit"),
  warningsAddPopover: $("warningsAddPopover"),
  inpWarningsAdd: /** @type {HTMLInputElement} */ ($("inpWarningsAdd")),
  btnWarningsAddOk: $("btnWarningsAddOk"),
  btnWarningsAddCancel: $("btnWarningsAddCancel"),
  kpiElapsed: $("kpiElapsed"),
  kpiRemaining: $("kpiRemaining"),
  kpiProgressLabel: $("kpiProgressLabel"),
  progressBar: $("progressBar"),
  progressFill: $("progressFill"),

  infoSource: $("infoSource"),
  infoResolved: $("infoResolved"),
  infoLastChange: $("infoLastChange"),
  infoLastAlert: $("infoLastAlert"),
  infoGlobalRate: $("infoGlobalRate"),

  inpPollSec: /** @type {HTMLInputElement} */ ($("inpPollSec")),
  inpThresholds: /** @type {HTMLInputElement|null} */ (document.getElementById("inpThresholds")),
  inpWindowPoints: /** @type {HTMLInputElement} */ ($("inpWindowPoints")),
  chkLogEveryChange: /** @type {HTMLInputElement} */ ($("chkLogEveryChange")),
  chkWarnNotify: /** @type {HTMLInputElement} */ ($("chkWarnNotify")),
  chkWarnSound: /** @type {HTMLInputElement} */ ($("chkWarnSound")),
  chkCompletionNotify: /** @type {HTMLInputElement} */ ($("chkCompletionNotify")),
  chkCompletionSound: /** @type {HTMLInputElement} */ ($("chkCompletionSound")),
  chkInterruptNotify: /** @type {HTMLInputElement} */ ($("chkInterruptNotify")),
  chkInterruptSound: /** @type {HTMLInputElement} */ ($("chkInterruptSound")),
  inpWarnSoundUrl: /** @type {HTMLInputElement} */ ($("inpWarnSoundUrl")),
  inpCompletionSoundUrl: /** @type {HTMLInputElement} */ ($("inpCompletionSoundUrl")),
  inpInterruptSoundUrl: /** @type {HTMLInputElement} */ ($("inpInterruptSoundUrl")),
  fileWarnSound: /** @type {HTMLInputElement} */ ($("fileWarnSound")),
  fileCompletionSound: /** @type {HTMLInputElement} */ ($("fileCompletionSound")),
  fileInterruptSound: /** @type {HTMLInputElement} */ ($("fileInterruptSound")),
  btnPickWarnSound: $("btnPickWarnSound"),
  btnPickCompletionSound: $("btnPickCompletionSound"),
  btnPickInterruptSound: $("btnPickInterruptSound"),
  btnWarnSoundAdv: $("btnWarnSoundAdv"),
  btnCompletionSoundAdv: $("btnCompletionSoundAdv"),
  btnInterruptSoundAdv: $("btnInterruptSoundAdv"),
  warnSoundAdv: $("warnSoundAdv"),
  completionSoundAdv: $("completionSoundAdv"),
  interruptSoundAdv: $("interruptSoundAdv"),
  btnClearWarnSoundFile: $("btnClearWarnSoundFile"),
  btnClearCompletionSoundFile: $("btnClearCompletionSoundFile"),
  btnClearInterruptSoundFile: $("btnClearInterruptSoundFile"),
  btnTestWarnSound: $("btnTestWarnSound"),
  btnTestCompletionSound: $("btnTestCompletionSound"),
  btnTestInterruptSound: $("btnTestInterruptSound"),
  btnWarnBuiltin: $("btnWarnBuiltin"),
  btnWarnDefaultUrl: $("btnWarnDefaultUrl"),
  btnCompletionBuiltin: $("btnCompletionBuiltin"),
  btnCompletionDefaultUrl: $("btnCompletionDefaultUrl"),
  btnInterruptBuiltin: $("btnInterruptBuiltin"),
  btnInterruptDefaultUrl: $("btnInterruptDefaultUrl"),
  warnSoundSummary: $("warnSoundSummary"),
  completionSoundSummary: $("completionSoundSummary"),
  interruptSoundSummary: $("interruptSoundSummary"),
  settingsNote: $("settingsNote"),
  historyPre: $("historyPre"),
  footerVersion: $("footerVersion"),
  logActivityWrap: $("logActivityWrap"),
  logActivityLed: $("logActivityLed"),
};

ui.footerVersion.textContent = `v${APP_VERSION}`;

// -----------------------------
// Tutorial (first-run onboarding)
// -----------------------------

const STORAGE_TUTORIAL_DONE_KEY = "vsqm_tutorial_done_v1";
let tutorialActive = false;
let tutorialMinimized = false;
let tutorialStepIdx = 0;
let tutorialPickedDuringRun = false;

function isTutorialDone() {
  try {
    return localStorage.getItem(STORAGE_TUTORIAL_DONE_KEY) === "1";
  } catch {
    return false;
  }
}

function setTutorialDone() {
  try {
    localStorage.setItem(STORAGE_TUTORIAL_DONE_KEY, "1");
  } catch {
    // ignore
  }
}

function openTutorial(reset = true) {
  if (!ui.tutorialOverlay) return;
  if (!tutorialActive) {
    tutorialActive = true;
    tutorialPickedDuringRun = false;
    tutorialStepIdx = 0;
  } else if (reset) {
    tutorialPickedDuringRun = false;
    tutorialStepIdx = 0;
  }
  tutorialMinimized = false;
  ui.tutorialOverlay.hidden = false;
  renderTutorial();
}

function closeTutorial(markDone) {
  if (!ui.tutorialOverlay) return;
  tutorialActive = false;
  tutorialMinimized = false;
  ui.tutorialOverlay.hidden = true;
  if (markDone) setTutorialDone();
}

function minimizeTutorial() {
  if (!ui.tutorialOverlay) return;
  if (!tutorialActive) return;
  tutorialMinimized = true;
  ui.tutorialOverlay.hidden = true;
}

function tutorialHasLogSelected() {
  return !!logFileHandle;
}

function tutorialSetStep(next) {
  tutorialStepIdx = Math.max(0, Math.min(4, next | 0));
  renderTutorial();
}

function renderTutorial() {
  if (!tutorialActive) return;
  if (!ui.tutorialTitle || !ui.tutorialBody || !ui.tutorialStep || !ui.btnTutorialBack || !ui.btnTutorialNext) return;

  const stepN = tutorialStepIdx + 1;
  const total = 5;
  ui.tutorialStep.textContent = `Step ${stepN}/${total}`;

  const hasLog = tutorialHasLogSelected();
  ui.btnTutorialBack.disabled = tutorialStepIdx === 0;

  /** @type {{title:string, html:string, nextLabel?:string, nextDisabled?:boolean}} */
  let s = { title: "Welcome", html: "" };

  if (tutorialStepIdx === 0) {
    s = {
      title: "Welcome",
      html:
        `<div class="tutorial__lead"><strong>Let’s get you monitoring in ~2 minutes.</strong> We’ll pick your log file, tune warnings, tune the rolling rate window, then start monitoring.</div>` +
        `<ul class="tutorial__list">` +
        `<li><span class="tutorial__k">Pick log file…</span> is required (the browser can’t read logs without you choosing one).</li>` +
        `<li>Warnings default to <span class="tutorial__k">10, 5, 1</span> (alerts fire when you cross downward through each threshold).</li>` +
        `<li>Rolling rate defaults to <span class="tutorial__k">10</span> points (more points = smoother but slower to react).</li>` +
        `</ul>` +
        `<div class="tutorial__hint">You can skip this tutorial, but it’s recommended the first time.</div>`,
      nextLabel: "Pick a log",
    };
  } else if (tutorialStepIdx === 1) {
    s = {
      title: "Pick your log file",
      html:
        `<div class="tutorial__lead">Choose <span class="tutorial__k">client-main.log</span> (or <span class="tutorial__k">client.log</span>).</div>` +
        `<div class="tutorial__actions">` +
        `<button type="button" class="btn btn--primary" id="btnTutorialPickNow">Pick log file…</button>` +
        `<button type="button" class="btn btn--secondary" id="btnTutorialOpenHelp">File Picker Guide</button>` +
        `</div>` +
        `<div class="tutorial__hint"><strong>Common paths</strong> (you don’t need to paste these, just a guide):</div>` +
        `<ul class="tutorial__list">` +
        `<li><strong>macOS</strong>: <span class="tutorial__k">~/Library/Application Support/VintagestoryData/Logs/client-main.log</span></li>` +
        `<li><strong>Linux</strong>: <span class="tutorial__k">~/.config/VintagestoryData/Logs/client-main.log</span></li>` +
        `</ul>` +
        `<div class="tutorial__warn">If the picker says <strong>“system files”</strong> (protected folders like AppData), open the <strong>File Picker Guide</strong> to generate a safe workaround (<span class="tutorial__k">mklink /H</span> on Windows or <span class="tutorial__k">ln -s</span> on Mac/Linux).</div>` +
        (hasLog
          ? `<div class="tutorial__hint"><strong>Selected:</strong> ${escapeHtml(String(ui.infoResolved?.textContent || "log"))}</div>`
          : `<div class="tutorial__hint"><strong>Not selected yet.</strong> Pick a log to continue.</div>`),
      nextLabel: "Next",
      nextDisabled: !hasLog,
    };
  } else if (tutorialStepIdx === 2) {
    s = {
      title: "Configure warnings",
      html:
        `<div class="tutorial__lead">Warnings are the milestones that trigger alerts as you move toward the front of the queue.</div>` +
        `<ul class="tutorial__list">` +
        `<li>Defaults: <span class="tutorial__k">10, 5, 1</span></li>` +
        `<li>Alerts fire on <strong>downward crossings</strong> (e.g. 6 → 5 triggers ≤5).</li>` +
        `</ul>` +
        `<div class="tutorial__actions">` +
        `<button type="button" class="btn btn--secondary" id="btnTutorialEditWarnings">Edit WARNINGS…</button>` +
        `</div>` +
        `<div class="tutorial__hint">Tip: keep <span class="tutorial__k">1</span> so you get a “front of queue” warning.</div>`,
      nextLabel: "Next",
    };
  } else if (tutorialStepIdx === 3) {
    s = {
      title: "Configure rolling rate",
      html:
        `<div class="tutorial__lead">Rolling rate estimates how fast you’re moving. The window is measured in <strong>points</strong> (updates).</div>` +
        `<ul class="tutorial__list">` +
        `<li><strong>10 points</strong>: a good default balance.</li>` +
        `<li><strong>5</strong>: more responsive but noisier.</li>` +
        `<li><strong>20</strong>: smoother but slower to react.</li>` +
        `</ul>` +
        `<div class="tutorial__actions">` +
        `<button type="button" class="btn btn--secondary" id="btnTutorialEditRate">Edit rolling window…</button>` +
        `</div>`,
      nextLabel: "Next",
    };
  } else {
    s = {
      title: "Start monitoring",
      html:
        `<div class="tutorial__lead">All set. When you finish, the app will start tailing your selected log and updating the graph live.</div>` +
        `<ul class="tutorial__list">` +
        `<li>You can stop/resume anytime with <span class="tutorial__k">Start/Stop</span>.</li>` +
        `<li>Desktop notifications are optional (Info → Enable notifications).</li>` +
        `</ul>`,
      nextLabel: "Start monitoring",
      nextDisabled: !hasLog,
    };
  }

  ui.tutorialTitle.textContent = s.title;
  ui.tutorialBody.innerHTML = s.html;
  ui.btnTutorialNext.textContent = s.nextLabel || "Next";
  ui.btnTutorialNext.disabled = !!s.nextDisabled;

  // Wire per-step buttons (rebuilt each render).
  const pickNow = document.getElementById("btnTutorialPickNow");
  pickNow?.addEventListener("click", async () => {
    try {
      await pickLogFile();
      tutorialPickedDuringRun = tutorialHasLogSelected();
      renderTutorial();
    } catch {
      renderTutorial();
    }
  });
  const openH = document.getElementById("btnTutorialOpenHelp");
  openH?.addEventListener("click", () => openPickerFixGuide());

  const editWarn = document.getElementById("btnTutorialEditWarnings");
  editWarn?.addEventListener("click", () => {
    try {
      minimizeTutorial();
      ui.btnWarningsEdit?.click();
      showToast("Tutorial", "Edit thresholds, then return to the tutorial to continue.", "info", {
        actionLabel: "Resume tutorial",
        onAction: () => openTutorial(false),
        durationMs: Infinity,
      });
    } catch {
      // ignore
    }
  });

  const editRate = document.getElementById("btnTutorialEditRate");
  editRate?.addEventListener("click", () => {
    try {
      minimizeTutorial();
      openSettingsAndEditRollingWindow();
      showToast("Tutorial", "Adjust Rolling window (points), then return to the tutorial to continue.", "info", {
        actionLabel: "Resume tutorial",
        onAction: () => openTutorial(false),
        durationMs: Infinity,
      });
    } catch {
      // ignore
    }
  });
}

function syncNotifyButtonUi() {
  if (!ui.btnRequestNotify) return;
  const supported = "Notification" in window;
  const secure = typeof window !== "undefined" && "isSecureContext" in window ? window.isSecureContext : false;
  if (!supported) {
    ui.btnRequestNotify.disabled = true;
    ui.btnRequestNotify.title = "This browser does not support desktop notifications.";
    if (ui.notifyHint) {
      ui.notifyHint.textContent = "Not supported in this browser.";
      ui.notifyHint.hidden = false;
    }
    return;
  }
  if (!secure) {
    ui.btnRequestNotify.disabled = true;
    ui.btnRequestNotify.title =
      "Desktop notifications require https:// or http://localhost. Run `python -m http.server 5173` and open http://localhost:5173.";
    if (ui.notifyHint) {
      ui.notifyHint.textContent = "Requires https:// or http://localhost (not file://).";
      ui.notifyHint.hidden = false;
    }
    return;
  }
  ui.btnRequestNotify.disabled = false;
  const p = Notification.permission;
  ui.btnRequestNotify.textContent = p === "granted" ? "Test notification" : "Enable notifications";
  if (ui.notifyHint) ui.notifyHint.hidden = true;
}

syncNotifyButtonUi();

let _baseTitle = document.title || "VS Queue Monitor";
let _attentionActive = false;
function setAttentionBadge(prefix) {
  try {
    if (!_baseTitle) _baseTitle = document.title || "VS Queue Monitor";
    const p = String(prefix || "!");
    document.title = `(${p}) ${_baseTitle}`;
    _attentionActive = true;
  } catch {
    // ignore
  }
}
function clearAttentionBadge() {
  if (!_attentionActive) return;
  try {
    document.title = _baseTitle;
  } catch {
    // ignore
  }
  _attentionActive = false;
}
document.addEventListener("visibilitychange", () => {
  if (document.visibilityState === "visible") clearAttentionBadge();
});
document.addEventListener("click", () => clearAttentionBadge(), { capture: true });

function syncNotifyPill() {
  const pill = ui.btnNotifyPill;
  if (!pill) return;
  try {
    if (!("Notification" in window)) {
      pill.hidden = false;
      pill.className = "pill pill--danger";
      pill.textContent = "Desktop notifications: unsupported";
      return;
    }
    const secure = typeof window !== "undefined" && "isSecureContext" in window ? window.isSecureContext : false;
    if (!secure) {
      pill.hidden = false;
      pill.className = "pill pill--warn";
      pill.textContent = "Desktop notifications: open via localhost";
      return;
    }
    const p = Notification.permission;
    if (p !== "granted") {
      pill.hidden = false;
      pill.className = "pill pill--warn";
      pill.textContent = "Desktop notifications: off";
      return;
    }
    pill.hidden = true;
  } catch {
    pill.hidden = true;
  }
}

syncNotifyPill();

// -----------------------------
// Inline editing (settings)
// -----------------------------

let _swReg = /** @type {ServiceWorkerRegistration|null} */ (null);
async function ensureServiceWorkerReady() {
  try {
    if (!("serviceWorker" in navigator)) return null;
    if (typeof window !== "undefined" && "isSecureContext" in window && !window.isSecureContext) return null;
    if (_swReg) return _swReg;
    // Register once; ignore failures (e.g. file://, blocked contexts).
    await navigator.serviceWorker.register("./sw.js");
    _swReg = await navigator.serviceWorker.ready;
    return _swReg;
  } catch {
    return null;
  }
}

function formatBool(b) {
  return b ? "On" : "Off";
}

function makeInlineField(inputEl, opts) {
  const field = inputEl.closest(".field");
  if (!field) return;
  if (field.getAttribute("data-inline") === "1") return;
  field.setAttribute("data-inline", "1");

  const view = document.createElement("div");
  view.className = "inlineView";

  const val = document.createElement("button");
  val.type = "button";
  val.className = "inlineView__value";

  view.appendChild(val);

  const edit = document.createElement("span");
  edit.className = "inlineView__edit";
  edit.textContent = "✎";
  edit.setAttribute("aria-hidden", "true");
  view.appendChild(edit);

  const label = field.querySelector(".label");
  if (label && label.nextSibling) field.insertBefore(view, label.nextSibling);
  else field.appendChild(view);

  let prev = "";

  const render = () => {
    const mode = opts?.mode || "text";
    let s = "";
    if (mode === "checkbox") s = formatBool(/** @type {HTMLInputElement} */ (inputEl).checked);
    else s = String(/** @type {HTMLInputElement} */ (inputEl).value || "").trim() || "—";
    if (typeof opts?.format === "function") s = String(opts.format());
    val.textContent = s;
    val.title = s;
  };

  const enterEdit = () => {
    prev = inputEl.type === "checkbox" ? String(/** @type {HTMLInputElement} */ (inputEl).checked) : String(inputEl.value ?? "");
    field.classList.add("field--editing");
    if (inputEl.type !== "checkbox") {
      try {
        inputEl.focus();
        inputEl.select?.();
      } catch {
        // ignore
      }
    }
  };

  const commit = () => {
    field.classList.remove("field--editing");
    applyFormToConfig();
    scheduleAutosave("Saved.");
    refreshWarningsKpi();
    updateTimeEstimates();
    if (running) {
      if (pollTimer != null) window.clearInterval(pollTimer);
      pollTimer = window.setInterval(() => pollOnce(), Math.max(200, config.pollSec * 1000));
    }
    render();
  };

  const cancel = () => {
    field.classList.remove("field--editing");
    if (inputEl.type === "checkbox") /** @type {HTMLInputElement} */ (inputEl).checked = prev === "true";
    else inputEl.value = prev;
    applyFormToConfig();
    render();
  };

  val.addEventListener("click", () => {
    if (opts?.mode === "checkbox") {
      /** @type {HTMLInputElement} */ (inputEl).checked = !/** @type {HTMLInputElement} */ (inputEl).checked;
      commit();
      return;
    }
    enterEdit();
  });
  view.addEventListener("dblclick", () => {
    if (opts?.mode === "checkbox") return;
    enterEdit();
  });

  inputEl.addEventListener("keydown", (e) => {
    if (e.key === "Escape") {
      e.preventDefault();
      cancel();
    } else if (e.key === "Enter") {
      e.preventDefault();
      commit();
    }
  });
  inputEl.addEventListener("blur", () => {
    if (!field.classList.contains("field--editing")) return;
    commit();
  });
  inputEl.addEventListener("input", () => render());
  inputEl.addEventListener("change", () => render());

  render();
}

function wireSettingsInlineEditing() {
  // Numeric/text fields
  makeInlineField(ui.inpPollSec);
  if (ui.inpThresholds) makeInlineField(ui.inpThresholds);
  makeInlineField(ui.inpWindowPoints);

  // Sound URLs stay editable as-is (power users); show inline view for consistency.
  makeInlineField(ui.inpWarnSoundUrl, { format: () => ui.warnSoundSummary?.textContent || "—" });
  makeInlineField(ui.inpCompletionSoundUrl, { format: () => ui.completionSoundSummary?.textContent || "—" });
  makeInlineField(ui.inpInterruptSoundUrl, { format: () => ui.interruptSoundSummary?.textContent || "—" });
}

wireSettingsInlineEditing();

function wireSoundAdvancedToggles() {
  /**
   * @param {HTMLElement|null} btn
   * @param {HTMLElement|null} panel
   * @param {HTMLInputElement|null} focusEl
   */
  const wire = (btn, panel, focusEl) => {
    if (!btn || !panel) return;
    btn.addEventListener("click", () => {
      const next = !panel.hidden;
      panel.hidden = next;
      try {
        btn.setAttribute("aria-pressed", (!next).toString());
      } catch {
        // ignore
      }
      if (!next) {
        try {
          focusEl?.focus();
          focusEl?.select?.();
        } catch {
          // ignore
        }
      }
    });
  };

  wire(ui.btnWarnSoundAdv, ui.warnSoundAdv, ui.inpWarnSoundUrl);
  wire(ui.btnCompletionSoundAdv, ui.completionSoundAdv, ui.inpCompletionSoundUrl);
  wire(ui.btnInterruptSoundAdv, ui.interruptSoundAdv, ui.inpInterruptSoundUrl);
}

wireSoundAdvancedToggles();

const STORAGE_HELP_PLAT_KEY = "vsqm_help_plat_v1";
/** @type {"win"|"unix"} */
let helpPlat = "win";

function setHelpPlat(next) {
  helpPlat = next === "unix" ? "unix" : "win";
  try {
    localStorage.setItem(STORAGE_HELP_PLAT_KEY, helpPlat);
  } catch {
    // ignore
  }
  updateHelpPlatUi();
  renderHelpCommandPreview();
}

function updateHelpPlatUi() {
  ui.btnHelpPlatWin?.setAttribute("aria-pressed", helpPlat === "win" ? "true" : "false");
  ui.btnHelpPlatUnix?.setAttribute("aria-pressed", helpPlat === "unix" ? "true" : "false");
}

function showToast(title, body = "", kind = "info", opts = undefined) {
  const host = ui.toastHost;
  if (!host) return;
  const el = document.createElement("div");
  const toastMod =
    kind === "error"
      ? "toast--error"
      : kind === "warn"
        ? "toast--warn"
        : kind === "ok"
          ? "toast--ok"
          : kind === "update"
            ? "toast--update"
            : "";
  el.className = `toast ${toastMod}`.trim();
  const actionLabel = opts && typeof opts.actionLabel === "string" ? opts.actionLabel : "";
  el.innerHTML =
    `<div class="toast__title">${escapeHtml(String(title))}</div>` +
    (body ? `<div class="toast__body">${escapeHtml(String(body))}</div>` : "") +
    (actionLabel ? `<div class="toast__actions"><button type="button" class="toast__btn">${escapeHtml(actionLabel)}</button></div>` : "");
  host.appendChild(el);

  if (actionLabel && opts && typeof opts.onAction === "function") {
    const btn = el.querySelector(".toast__btn");
    btn?.addEventListener("click", () => {
      try {
        opts.onAction();
      } finally {
        try {
          el.remove();
        } catch {
          // ignore
        }
      }
    });
  }

  const durationMs =
    opts && opts.durationMs === Infinity
      ? Infinity
      : opts && Number.isFinite(opts.durationMs)
        ? Math.max(800, opts.durationMs)
        : 2400;
  let timer = null;
  if (durationMs !== Infinity) {
    timer = window.setTimeout(() => {
      try {
        el.remove();
      } catch {
        // ignore
      }
    }, durationMs);
  }

  return {
    remove: () => {
      if (timer != null) window.clearTimeout(timer);
      try {
        el.remove();
      } catch {
        // ignore
      }
    },
  };
}

function escapeHtml(s) {
  return String(s)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

// -----------------------------
// App update (same-origin version.json; no backend)
// -----------------------------

const UPDATE_CHECK_INTERVAL_MS = 10 * 60 * 1000;
const UPDATE_CHECK_FIRST_DELAY_MS = 45 * 1000;
const UPDATE_PROMPT_KEY = "vsqm_update_prompt_version";

/** @returns {null | [number, number, number]} */
function parseSemver(s) {
  const m = /^(\d+)\.(\d+)\.(\d+)$/.exec(String(s).trim());
  if (!m) return null;
  return [Number(m[1]), Number(m[2]), Number(m[3])];
}

function isRemoteNewer(remote, local) {
  const a = parseSemver(remote);
  const b = parseSemver(local);
  if (!a || !b) return String(remote) !== String(local);
  for (let i = 0; i < 3; i++) {
    if (a[i] > b[i]) return true;
    if (a[i] < b[i]) return false;
  }
  return false;
}

let updateCheckInFlight = false;
/** @type {ReturnType<typeof setInterval> | null} */
let updateIntervalTimer = null;
let lastVisibilityCheckAt = 0;

async function checkForRemoteUpdate() {
  if (updateCheckInFlight) return;
  if (typeof location === "undefined" || location.protocol === "file:") return;
  updateCheckInFlight = true;
  try {
    const url = new URL("./version.json", import.meta.url);
    url.searchParams.set("_", String(Date.now()));
    const r = await fetch(url.href, { cache: "no-store" });
    if (!r.ok) return;
    const j = await r.json();
    const remote = j && typeof j.version === "string" ? j.version.trim() : "";
    if (!remote) return;
    if (!isRemoteNewer(remote, APP_VERSION)) return;
    if (sessionStorage.getItem(UPDATE_PROMPT_KEY) === remote) return;
    sessionStorage.setItem(UPDATE_PROMPT_KEY, remote);
    showToast(
      "New version available",
      `You are on v${APP_VERSION}. The site is serving v${remote}. Reload when convenient.`,
      "update",
      {
        durationMs: 120000,
        actionLabel: "Reload",
        onAction: () => location.reload(),
      },
    );
  } catch {
    // ignore (offline, missing version.json, etc.)
  } finally {
    updateCheckInFlight = false;
  }
}

function startUpdateCheckLoop() {
  try {
    if (typeof location === "undefined" || location.protocol === "file:") return;
  } catch {
    return;
  }
  const kick = () => {
    window.setTimeout(() => void checkForRemoteUpdate(), UPDATE_CHECK_FIRST_DELAY_MS);
    if (updateIntervalTimer != null) window.clearInterval(updateIntervalTimer);
    updateIntervalTimer = window.setInterval(() => void checkForRemoteUpdate(), UPDATE_CHECK_INTERVAL_MS);
  };
  if (document.readyState === "complete") kick();
  else window.addEventListener("load", kick, { once: true });

  document.addEventListener("visibilitychange", () => {
    if (document.visibilityState !== "visible") return;
    const t = Date.now();
    if (t - lastVisibilityCheckAt < 60_000) return;
    lastVisibilityCheckAt = t;
    void checkForRemoteUpdate();
  });
}

function openHelp() {
  if (!ui.helpOverlay) return;
  ui.helpOverlay.hidden = false;
  try {
    // Load persisted selection or infer once from platform.
    try {
      const saved = localStorage.getItem(STORAGE_HELP_PLAT_KEY);
      if (saved === "win" || saved === "unix") helpPlat = saved;
    } catch {
      // ignore
    }
    if (helpPlat !== "win" && helpPlat !== "unix") {
      const plat = String(navigator.platform || "").toLowerCase();
      helpPlat = plat.includes("win") ? "win" : "unix";
    }
    updateHelpPlatUi();

    // Set a sensible default in the generator if empty.
    if (ui.inpHelpSourcePath && !ui.inpHelpSourcePath.value) {
      if (helpPlat === "win") ui.inpHelpSourcePath.value = "%APPDATA%\\VintagestoryData";
      else ui.inpHelpSourcePath.value = "~/.config/VintagestoryData/Logs/client-main.log";
    }
    renderHelpCommandPreview();
  } catch {
    // ignore
  }
  try {
    ui.btnHelpClose?.focus();
  } catch {
    // ignore
  }
}

function openPickerFixGuide() {
  openHelp();
  try {
    // Make the “solution” obvious: scroll + focus the generator input.
    ui.inpHelpSourcePath?.scrollIntoView({ block: "center", inline: "nearest" });
    ui.inpHelpSourcePath?.focus();
    ui.inpHelpSourcePath?.select?.();
  } catch {
    // ignore
  }
}

function closeHelp() {
  if (!ui.helpOverlay) return;
  ui.helpOverlay.hidden = true;
  try {
    ui.btnHelp?.focus();
  } catch {
    // ignore
  }
}

function openSettings() {
  if (!ui.settingsOverlay) return;
  ui.settingsOverlay.hidden = false;
  try {
    ui.btnSettingsClose?.focus();
  } catch {
    // ignore
  }
}

function closeSettings() {
  if (!ui.settingsOverlay) return;
  ui.settingsOverlay.hidden = true;
  try {
    ui.btnSettings?.focus();
  } catch {
    // ignore
  }
}

function wireHelpOverlay() {
  ui.btnHelp?.addEventListener("click", () => openHelp());
  ui.btnHelpClose?.addEventListener("click", () => closeHelp());
  ui.helpOverlay?.addEventListener("click", (e) => {
    if (e.target === ui.helpOverlay) closeHelp();
  });
  window.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && ui.helpOverlay && !ui.helpOverlay.hidden) closeHelp();
  });

  ui.inpHelpSourcePath?.addEventListener("input", () => renderHelpCommandPreview());
  ui.btnHelpLoadFile?.addEventListener("click", async () => {
    const expected = String(ui.spanHelpPickPath?.textContent || "").trim();
    if (expected) {
      showToast("Load file", `In the picker, select: ${expected}`, "info", { durationMs: 9000 });
      appendHistory(`Help: expected log path: ${expected}`);
    }
    try {
      await pickLogFile();
    } catch (e) {
      appendHistory(`Pick log cancelled/failed: ${String(e)}`);
    }
  });
  ui.btnHelpPlatWin?.addEventListener("click", () => setHelpPlat("win"));
  ui.btnHelpPlatUnix?.addEventListener("click", () => setHelpPlat("unix"));
  ui.btnHelpCopyCmd?.addEventListener("click", async () => {
    const txt = String(ui.preHelpCmd?.textContent || "");
    if (!txt.trim()) return;
    try {
      await navigator.clipboard.writeText(txt);
      showToast("Copied", "Command copied to clipboard.");
    } catch {
      showToast("Copy failed", "Clipboard access was blocked by the browser.", "error");
    }
  });
}

function wireSettingsOverlay() {
  ui.btnSettings?.addEventListener("click", () => openSettings());
  ui.btnSettingsClose?.addEventListener("click", () => closeSettings());
  ui.settingsOverlay?.addEventListener("click", (e) => {
    if (e.target === ui.settingsOverlay) closeSettings();
  });
  window.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && ui.settingsOverlay && !ui.settingsOverlay.hidden) closeSettings();
  });
}

function normalizeSlashes(s) {
  return String(s).trim().replaceAll("\r", "").replaceAll("\n", "");
}

/**
 * Stable 8-char hex id from the pasted source path + kind (same path → same folder name).
 * @param {string} seedPath
 * @param {"logs"|"data"|"file"} kind
 */
function hashSourcePathForLinkFolder(seedPath, kind) {
  const p = normalizeSlashes(seedPath).replaceAll("\\", "/").toLowerCase();
  let h = 0x811c9dc5;
  const str = `${kind}|${p}`;
  for (let i = 0; i < str.length; i++) {
    h ^= str.charCodeAt(i);
    h = Math.imul(h, 0x01000193);
  }
  return (h >>> 0).toString(16).padStart(8, "0");
}

/**
 * @param {"logs"|"data"|"file"} kind
 * @param {string} seedPath
 */
function linkFolderName(kind, seedPath) {
  return `${kind}-${hashSourcePathForLinkFolder(seedPath, kind)}`;
}

/**
 * Path to the Vintage Story `Logs` folder if `p` contains `\\Logs\\` or ends with `\\Logs`.
 * @param {string} p
 * @returns {string|null}
 */
function findWindowsLogsFolderRoot(p) {
  const n = normalizeSlashes(p).replaceAll("/", "\\");
  if (!n) return null;
  const lower = n.toLowerCase();
  const needle = "\\logs\\";
  const i = lower.lastIndexOf(needle);
  if (i >= 0) return n.slice(0, i + "\\logs".length);
  if (lower.endsWith("\\logs")) return n;
  return null;
}

/**
 * Path under `Logs\\` for a file or folder under that logs root, or "" if `fullPath` is exactly `logsRoot`.
 * @param {string} fullPath
 * @param {string} logsRoot
 * @returns {string|null}
 */
function winPathRelativeBelowLogs(fullPath, logsRoot) {
  const f = normalizeSlashes(fullPath).replaceAll("/", "\\").replace(/\\+$/g, "");
  const lr = normalizeSlashes(logsRoot).replaceAll("/", "\\").replace(/\\+$/g, "");
  const fl = f.toLowerCase();
  const lrl = lr.toLowerCase();
  if (fl === lrl) return "";
  const root = lr + "\\";
  if (!fl.startsWith(root.toLowerCase())) return null;
  return f.slice(root.length).replace(/^\\+/, "");
}

/**
 * Destination path for `mklink /H` — one file directly under Documents\vs-queue-monitor (no subfolder).
 * @param {string} srcLogPath
 */
function winHardLinkExposedLogPath(srcLogPath) {
  const base = srcLogPath.replace(/^.*[\\/]/, "") || "client-main.log";
  const dot = base.lastIndexOf(".");
  const stem = dot >= 0 ? base.slice(0, dot) : base;
  const ext = dot >= 0 ? base.slice(dot) : ".log";
  const hex = hashSourcePathForLinkFolder(srcLogPath, "file");
  return `%USERPROFILE%\\Documents\\vs-queue-monitor\\${stem}-${hex}${ext}`;
}

function renderHelpCommandPreview() {
  if (!ui.preHelpCmd || !ui.inpHelpSourcePath) return;
  const raw = normalizeSlashes(ui.inpHelpSourcePath.value);
  const isWin = helpPlat === "win";
  const isUnix = helpPlat === "unix";
  const wantsFile = /[\\/](client-main\.log|client\.log)$/i.test(raw) || /\.log$/i.test(raw);
  // For guidance, always prefer the canonical client log name.
  const logName = "client-main.log";
  const setPick = (p) => {
    if (ui.spanHelpPickPath) ui.spanHelpPickPath.textContent = p || "";
  };

  if (isWin) {
    const srcIn = raw || "%APPDATA%\\VintagestoryData";
    const looksLikeLogFile =
      /[\\/]client-main\.log$/i.test(srcIn) || /[\\/]client\.log$/i.test(srcIn) || /\.log$/i.test(srcIn);

    // Hard link the log file into Documents (no admin on same volume). Single file under vs-queue-monitor — no subfolder.
    if (looksLikeLogFile) {
      const destFile = winHardLinkExposedLogPath(srcIn);
      let txt =
        `if not exist "%USERPROFILE%\\Documents\\vs-queue-monitor" mkdir "%USERPROFILE%\\Documents\\vs-queue-monitor"\n` +
        `mklink /H "${destFile}" "${srcIn}"`;
      ui.preHelpCmd.textContent = txt;
      setPick(destFile);
      return;
    }

    const srcDir = srcIn;
    ui.preHelpCmd.textContent =
      `echo Paste the full path to client-main.log above (not a folder).\n` +
      `echo Example: %APPDATA%\\VintagestoryData\\Logs\\client-main.log`;
    setPick("%USERPROFILE%\\Documents\\vs-queue-monitor\\client-main.log");
    return;
  }

  if (isUnix) {
    if (wantsFile) {
      const srcFile = raw || "~/.config/VintagestoryData/Logs/client-main.log";
      const leaf = linkFolderName("logs", srcFile);
      ui.preHelpCmd.textContent =
        `mkdir -p ~/vs-queue-monitor/${leaf}\n` +
        `ln -s ${srcFile} ~/vs-queue-monitor/${leaf}/${logName}`;
      setPick(`~/vs-queue-monitor/${leaf}/${logName}`);
      return;
    }
    const srcDir = raw || "~/.config/VintagestoryData";
    const leaf = linkFolderName("data", srcDir);
    ui.preHelpCmd.textContent =
      `mkdir -p ~/vs-queue-monitor/${leaf}\n` +
      `ln -s ${srcDir}/Logs/${logName} ~/vs-queue-monitor/${leaf}/${logName}`;
    setPick(`~/vs-queue-monitor/${leaf}/${logName}`);
    return;
  }

  ui.preHelpCmd.textContent =
    "Open this app in Edge/Chrome.\n" +
    "If the picker is blocked, paste your real VS data/log file path above to generate a workaround command.";
  setPick("");
}

// -----------------------------
// Parsing (ported from core.py)
// -----------------------------

const QUEUE_RE = new RegExp(
  "(?:" +
    "client\\s+is\\s+in\\s+connect\\s+queue\\s+at\\s+position" +
    "|your\\s+position\\s+in\\s+the\\s+queue\\s+is" +
    ")\\D*(\\d+)",
  "gi",
);

/**
 * @param {string} line
 * @returns {number|null}
 */
function queuePositionFromLine(line) {
  const matches = [...line.matchAll(QUEUE_RE)];
  for (let i = matches.length - 1; i >= 0; i--) {
    const m = matches[i];
    const after = line.slice(m.index + m[0].length).trimStart();
    if (after.startsWith("%")) continue;
    const n = Number.parseInt(m[1] ?? "", 10);
    if (Number.isFinite(n)) return n;
    return null;
  }
  return null;
}

const DISCONNECTED_LINE_RES = [
  /\bdisconnected\s+by\s+the\s+server\b/i,
  /\bexiting\s+current\s+game\s+to\s+disconnected\s+screen\b/i,
  /\bconnection\s+closed\s+unexpectedly\b/i,
  /\bforcibly\s+closed\s+by\s+the\s+remote\s+host\b/i,
  /\b(?:connection|connect)\s+(?:to\s+(?:the\s+)?)?(?:server\s+)?(?:lost|closed|failed|aborted|reset|refused|timed\s*out)\b/i,
  /\b(?:lost|closed)\s+connection\b/i,
  /\bdisconnect(?:ed|ing)?\b/i,
  /\bconnection\s+kicked\b/i,
  /\bkicked\s+from\b/i,
  /\b(?:was|been)\s+disconnected\b/i,
];

const GRACE_DISCONNECT_LINE_RES = [
  /\bconnection\s+closed\s+unexpectedly\b/i,
  /\bforcibly\s+closed\s+by\s+the\s+remote\s+host\b/i,
  /\b(?:lost|closed)\s+connection\b/i,
  /\b(?:connection|connect)\s+(?:to\s+(?:the\s+)?)?(?:server\s+)?(?:lost|closed|failed|aborted|reset|refused|timed\s*out)\b/i,
];

const FINAL_CRASH_LINE_RES = [
  /destroying\s+game\s+session/i,
  /waiting\s+up\s+to\s+\d+\s*ms\s+for\s+client\s+threads\s+to\s+exit/i,
];

const RECONNECTING_LINE_RES = [
  /\bconnecting\s+to\s+/i,
  /\binitialized\s+server\s+connection\b/i,
  /\bopening\s+connection\b/i,
  /\btrying\s+to\s+connect\b/i,
];

const POST_QUEUE_PROGRESS_LINE_RES = [
  /loading\s+and\s+pre-starting\s+client\s*-?\s*side\s+mods/i,
  /\bpre-starting\s+client\s*-?\s*side\s+mods\b/i,
  /\bloading\s+client\s*-?\s*side\s+mods\b/i,
  /connected\s+to\s+server.*download/i,
  /\bdownloading\s+(?:data|assets|world|chunks|map|mod)\b/i,
  /\b(?:world|game)\s+loaded\b/i,
  /\bentering\s+(?:the\s+)?(?:world|game)\b/i,
  /\bjoined\s+(?:the\s+)?(?:world|game|server)\b/i,
  /\b(?:ok|okay),?\s+spawn/i,
  /\bspawn(?:ed|ing)?\s+(?:at|in|near)\b/i,
];

// Queue run "session" boundaries.
// Important: some logs contain "connecting/opening connection" lines *during* a single queue wait.
// Treat those as "soft" boundaries only *before* we’ve observed a queue position in the current session.
const QUEUE_RUN_HARD_BOUNDARY_RES = [
  /\b(?:connection|connect)\s+(?:to\s+(?:the\s+)?)?(?:server\s+)?(?:lost|closed|failed|aborted|reset|refused|timed\s*out)\b/i,
  /\b(?:lost|closed)\s+connection\b/i,
  /\bdisconnect(?:ed|ing)?\b/i,
  /\breturned\s+to\s+(?:the\s+)?main\s+menu\b/i,
  /\b(?:server|client)\s+shut\s+down\b/i,
];
const QUEUE_RUN_SOFT_BOUNDARY_RES = [
  /\breconnect(?:ing|ed)?\b/i,
  /\bopening\s+connection\b/i,
  /\bconnecting\s+to\s+/i,
  /\binitialized\s+server\s+connection\b/i,
  /\btrying\s+to\s+connect\b/i,
];

/**
 * Build a session counter (relative to this chunk) that does not split a single queue wait
 * just because the log emitted reconnect/connecting lines mid-queue.
 * @param {string[]} lines
 */
function queueRunSessionBeforeLine(lines) {
  const sessionBeforeLine = new Array(lines.length);
  let session = 0;
  let sawQueueInSession = false;
  for (let i = 0; i < lines.length; i++) {
    sessionBeforeLine[i] = session;
    const s = String(lines[i] || "").trim();
    if (!s) continue;
    const pos = queuePositionFromLine(s);
    if (pos != null) {
      sawQueueInSession = true;
      continue;
    }
    if (QUEUE_RUN_HARD_BOUNDARY_RES.some((r) => r.test(s))) {
      session += 1;
      sawQueueInSession = false;
      continue;
    }
    if (!sawQueueInSession && QUEUE_RUN_SOFT_BOUNDARY_RES.some((r) => r.test(s))) {
      session += 1;
      sawQueueInSession = false;
      continue;
    }
  }
  return sessionBeforeLine;
}

/**
 * @param {string} line
 */
function isQueueRunBoundaryLine(line) {
  const s = line.trim();
  if (!s) return false;
  if (queuePositionFromLine(s) != null) return false;
  return QUEUE_RUN_HARD_BOUNDARY_RES.some((r) => r.test(s)) || QUEUE_RUN_SOFT_BOUNDARY_RES.some((r) => r.test(s));
}

/**
 * @param {string} line
 */
function isGraceDisconnectLine(line) {
  const s = line.trim();
  if (!s) return false;
  if (queuePositionFromLine(s) != null) return false;
  return GRACE_DISCONNECT_LINE_RES.some((r) => r.test(s));
}

/**
 * @param {string} line
 */
function isFinalCrashLine(line) {
  const s = line.trim();
  if (!s) return false;
  if (queuePositionFromLine(s) != null) return false;
  return FINAL_CRASH_LINE_RES.some((r) => r.test(s));
}

/**
 * @param {string} line
 */
function isReconnectingLine(line) {
  const s = line.trim();
  if (!s) return false;
  if (queuePositionFromLine(s) != null) return false;
  return RECONNECTING_LINE_RES.some((r) => r.test(s));
}

/**
 * @param {string} line
 */
function isDisconnectedLine(line) {
  const s = line.trim();
  if (!s) return false;
  if (queuePositionFromLine(s) != null) return false;
  return DISCONNECTED_LINE_RES.some((r) => r.test(s));
}

/**
 * @param {string} line
 */
function isHardDisconnectLine(line) {
  const s = line.trim();
  if (!s) return false;
  if (queuePositionFromLine(s) != null) return false;
  if (isGraceDisconnectLine(s) || isFinalCrashLine(s)) return false;
  return isDisconnectedLine(s);
}

/**
 * @param {string} s
 */
function isPostQueueProgressLine(s) {
  const t = s.trim();
  if (!t) return false;
  if (queuePositionFromLine(t) != null) return false;
  return POST_QUEUE_PROGRESS_LINE_RES.some((r) => r.test(t));
}

/**
 * @param {string} data
 */
function tailHasPostQueueAfterLastQueueLine(data) {
  const lines = data.split(/\r?\n/);
  let lastQ = -1;
  for (let i = 0; i < lines.length; i++) {
    if (queuePositionFromLine(lines[i]) != null) lastQ = i;
  }
  if (lastQ < 0) return false;
  for (const line of lines.slice(lastQ + 1)) {
    if (isPostQueueProgressLine(line)) return true;
  }
  return false;
}

/**
 * @param {string} data
 * @returns {number|null} epoch seconds for the first post-queue progress line after the last queue line
 */
function parseFirstPostQueueEpochAfterLastQueueLine(data) {
  const lines = data.split(/\r?\n/);
  let lastQ = -1;
  for (let i = 0; i < lines.length; i++) {
    if (queuePositionFromLine(lines[i]) != null) lastQ = i;
  }
  if (lastQ < 0) return null;
  for (let i = lastQ + 1; i < lines.length; i++) {
    if (!isPostQueueProgressLine(lines[i])) continue;
    const t = parseLogTimestampEpoch(lines[i]);
    return t ?? (Date.now() / 1000);
  }
  return null;
}

/**
 * @param {string} data
 * @returns {{ kind: "disconnected"|"reconnecting"|"grace"|"queue"|"unknown", lastPos: number|null }}
 */
function classifyTailConnectionState(data) {
  /** @type {"disconnected"|"reconnecting"|"grace"|"queue"|"unknown"} */
  let lastKind = "unknown";
  /** @type {number|null} */
  let lastPos = null;

  for (const line of data.split(/\r?\n/)) {
    const s = line.trim();
    if (!s) continue;
    const pos = queuePositionFromLine(s);
    if (pos != null) {
      lastPos = pos;
      lastKind = "queue";
      continue;
    }
    if (isReconnectingLine(s)) {
      lastKind = "reconnecting";
      continue;
    }
    if (isFinalCrashLine(s)) {
      lastKind = "disconnected";
      continue;
    }
    if (isGraceDisconnectLine(s)) {
      lastKind = "grace";
      continue;
    }
    if (isHardDisconnectLine(s)) {
      lastKind = "disconnected";
      continue;
    }
  }

  return { kind: lastKind, lastPos };
}

/**
 * @param {string} data
 * @returns {{ lastPos: number|null, session: number }}
 */
function parseTailLastQueueReading(data) {
  /** @type {number|null} */
  let lastPos = null;
  const lines = data.split(/\r?\n/);
  const sessionBeforeLine = queueRunSessionBeforeLine(lines);
  let lastSess = 0;
  for (let i = 0; i < lines.length; i++) {
    const pos = queuePositionFromLine(lines[i]);
    if (pos == null) continue;
    lastPos = pos;
    lastSess = sessionBeforeLine[i] ?? lastSess;
  }
  return { lastPos, session: lastSess };
}

const TS_RE = /^\s*(\d{1,2})\.(\d{1,2})\.(\d{4})\s+(\d{2}):(\d{2}):(\d{2})\b/;

/**
 * @param {string} line
 * @returns {number|null} epoch seconds
 */
function parseLogTimestampEpoch(line) {
  const m = TS_RE.exec(line);
  if (!m) return null;
  const d = Number.parseInt(m[1], 10);
  const mo = Number.parseInt(m[2], 10);
  const y = Number.parseInt(m[3], 10);
  const hh = Number.parseInt(m[4], 10);
  const mm = Number.parseInt(m[5], 10);
  const ss = Number.parseInt(m[6], 10);
  if (![d, mo, y, hh, mm, ss].every(Number.isFinite)) return null;
  const dt = new Date(y, mo - 1, d, hh, mm, ss);
  const t = dt.getTime() / 1000;
  if (!Number.isFinite(t)) return null;
  return t;
}

/**
 * @param {string} data
 * @returns {number|null}
 */
function parseTailLastQueueLineEpoch(data) {
  /** @type {number|null} */
  let lastT = null;
  for (const line of data.split(/\r?\n/)) {
    if (queuePositionFromLine(line) == null) continue;
    const t = parseLogTimestampEpoch(line);
    lastT = t ?? (Date.now() / 1000);
  }
  return lastT;
}

/**
 * @param {string} data
 * @returns {number|null} epoch seconds for the first queue-position line in `data`
 */
function parseFirstQueueLineEpoch(data) {
  for (const line of data.split(/\r?\n/)) {
    if (queuePositionFromLine(line) == null) continue;
    const t = parseLogTimestampEpoch(line);
    return t ?? (Date.now() / 1000);
  }
  return null;
}

/**
 * Extract all queue position readings from a text chunk (usually a poll delta) in order.
 * This prevents the UI/graph from "skipping" when multiple queue updates land between polls.
 * @param {string} chunk
 * @returns {Array<{ pos: number, epoch: number|null }>}
 */
function extractQueueReadingsFromText(chunk) {
  if (!chunk) return [];
  /** @type {Array<{ pos: number, epoch: number|null }>} */
  const out = [];
  for (const line of chunk.split(/\r?\n/)) {
    const pos = queuePositionFromLine(line);
    if (pos == null) continue;
    out.push({ pos, epoch: parseLogTimestampEpoch(line) });
  }
  return out;
}

/**
 * Keep only the **current queue run** in a loaded chunk: same session model as {@link parseTailLastQueueReading}
 * (boundaries: reconnect, disconnect, main menu, new connection attempt, etc.). Works for a full file or a tail slice;
 * session indices are relative to the start of `data`.
 * @param {string} data
 */
function sliceLoadedLogToCurrentQueueRun(data) {
  if (!data) return data;
  const lines = data.split(/\r?\n/);
  if (lines.length === 0) return data;
  const sessionBeforeLine = queueRunSessionBeforeLine(lines);
  let lastQIdx = -1;
  for (let i = 0; i < lines.length; i++) {
    if (queuePositionFromLine(lines[i]) != null) lastQIdx = i;
  }
  if (lastQIdx < 0) return data;
  const targetSess = sessionBeforeLine[lastQIdx];
  let startIdx = 0;
  for (let i = 0; i < lines.length; i++) {
    if (sessionBeforeLine[i] === targetSess) {
      startIdx = i;
      break;
    }
  }
  return lines.slice(startIdx).join("\n");
}

/**
 * Same as {@link sliceLoadedLogToCurrentQueueRun}, but returns metadata so callers can detect
 * when the current run likely started *before* the loaded chunk (e.g. huge log).
 * @param {string} data
 * @returns {{ slice: string, startIdx: number, lastQIdx: number, lineCount: number }}
 */
function sliceLoadedLogToCurrentQueueRunMeta(data) {
  if (!data) return { slice: data, startIdx: 0, lastQIdx: -1, lineCount: 0 };
  const lines = data.split(/\r?\n/);
  if (lines.length === 0) return { slice: data, startIdx: 0, lastQIdx: -1, lineCount: 0 };
  const sessionBeforeLine = queueRunSessionBeforeLine(lines);
  let lastQIdx = -1;
  for (let i = 0; i < lines.length; i++) {
    if (queuePositionFromLine(lines[i]) != null) lastQIdx = i;
  }
  if (lastQIdx < 0) return { slice: data, startIdx: 0, lastQIdx: -1, lineCount: lines.length };
  const targetSess = sessionBeforeLine[lastQIdx];
  let startIdx = 0;
  for (let i = 0; i < lines.length; i++) {
    if (sessionBeforeLine[i] === targetSess) {
      startIdx = i;
      break;
    }
  }
  return { slice: lines.slice(startIdx).join("\n"), startIdx, lastQIdx, lineCount: lines.length };
}

/**
 * @param {string} raw
 * @returns {number[]}
 */
function parseAlertThresholds(raw) {
  const parts = raw.replaceAll(",", " ").split(/\s+/).map((s) => s.trim()).filter(Boolean);
  const out = [];
  for (const p of parts) {
    const n = Number.parseInt(p, 10);
    if (!Number.isFinite(n)) throw new Error("Warning thresholds must be numbers (e.g. 10, 5, 1).");
    if (n < 1) throw new Error(`Warning threshold ${n} must be >= 1.`);
    out.push(n);
  }
  if (out.length === 0) throw new Error("Add at least one warning threshold (e.g. 10, 5, 1).");
  const uniq = [...new Set(out)];
  uniq.sort((a, b) => b - a);
  return uniq;
}

// -----------------------------
// State + config
// -----------------------------

const STORAGE_KEY = "vsqm_web_config_v1";
const STORAGE_LAST_DIR_KEY = "vsqm_web_last_dir_v1";
/** Display metadata for the last successfully opened log (name + how it was chosen). Browsers do not expose real paths to pages. */
const STORAGE_LAST_LOG_META_KEY = "vsqm_last_log_meta_v1";
const IDB_HANDLES_NAME = "vsqm_handles_v1";
const IDB_HANDLES_STORE = "handles";
const IDB_LOG_FILE_KEY = "logFile";

// Debounced auto-save (mirrors the old app’s “save shortly after change” feel).
let _autosaveTimer = /** @type {number|null} */ (null);
function scheduleAutosave(note = "") {
  if (_autosaveTimer != null) window.clearTimeout(_autosaveTimer);
  _autosaveTimer = window.setTimeout(() => {
    _autosaveTimer = null;
    try {
      saveConfig();
      void syncSoundSummaries();
      if (note) showSettingsNote(note);
    } catch {
      // ignore
    }
  }, 450);
}

function applyFormToConfig() {
  const pollSec = Number.parseFloat(ui.inpPollSec.value.trim());
  const win = Number.parseInt(ui.inpWindowPoints.value.trim(), 10);
  // Validate thresholds but only throw if the user explicitly saves.
  config.pollSec = Number.isFinite(pollSec) ? pollSec : config.pollSec;
  config.windowPoints = Number.isFinite(win) ? win : config.windowPoints;
  if (ui.inpThresholds) config.thresholdsRaw = ui.inpThresholds.value.trim() || config.thresholdsRaw;
  config.logEveryChange = ui.chkLogEveryChange.checked;
  config.warnNotify = ui.chkWarnNotify.checked;
  config.warnSound = ui.chkWarnSound.checked;
  config.completionNotify = ui.chkCompletionNotify.checked;
  config.completionSound = ui.chkCompletionSound.checked;
  config.interruptNotify = ui.chkInterruptNotify.checked;
  config.interruptSound = ui.chkInterruptSound.checked;
  config.warnSoundUrl = ui.inpWarnSoundUrl.value.trim();
  config.completionSoundUrl = ui.inpCompletionSoundUrl.value.trim();
  config.interruptSoundUrl = ui.inpInterruptSoundUrl.value.trim();
  // graphLiveWindow is controlled by a button (not a form field).
  ui.kpiRateLabel.textContent = `RATE (AVG ${rollingWindowPoints()})`;
  if (ui.kpiStatusLabel) ui.kpiStatusLabel.textContent = `STATUS (${config.pollSec}s REFRESH)`;
}

/**
 * @typedef {{
 *   pollSec: number,
 *   thresholdsRaw: string,
 *   windowPoints: number,
 *   logEveryChange: boolean,
 *   warnNotify: boolean,
 *   warnSound: boolean,
 *   completionNotify: boolean,
 *   completionSound: boolean,
 *   interruptNotify: boolean,
 *   interruptSound: boolean,
 *   warnSoundUrl: string,
 *   warnSoundFileName: string,
 *   completionSoundUrl: string,
 *   completionSoundFileName: string,
 *   interruptSoundUrl: string,
 *   interruptSoundFileName: string,
 *   graphLogScale: boolean,
 *   graphLiveWindow: boolean
 * }} AppConfig
 */

/** @type {AppConfig} */
let config = {
  pollSec: 2,
  thresholdsRaw: "10, 5, 1",
  windowPoints: 10,
  logEveryChange: true,
  warnNotify: true,
  warnSound: true,
  completionNotify: true,
  completionSound: true,
  interruptNotify: true,
  interruptSound: true,
  warnSoundUrl: "",
  warnSoundFileName: "",
  completionSoundUrl: "",
  completionSoundFileName: "",
  interruptSoundUrl: "",
  interruptSoundFileName: "",
  graphLogScale: false,
  graphLiveWindow: true,
};

function loadConfig() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return;
    const obj = JSON.parse(raw);
    if (obj && typeof obj === "object") {
      config = {
        ...config,
        ...obj,
      };
    }
  } catch {
    // ignore
  }
}

function saveConfig() {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(config));
}

function syncConfigToForm() {
  ui.inpPollSec.value = String(config.pollSec);
  if (ui.inpThresholds) ui.inpThresholds.value = String(config.thresholdsRaw);
  ui.inpWindowPoints.value = String(config.windowPoints);
  ui.chkLogEveryChange.checked = !!config.logEveryChange;
  ui.chkWarnNotify.checked = !!config.warnNotify;
  ui.chkWarnSound.checked = !!config.warnSound;
  ui.chkCompletionNotify.checked = !!config.completionNotify;
  ui.chkCompletionSound.checked = !!config.completionSound;
  ui.chkInterruptNotify.checked = !!config.interruptNotify;
  ui.chkInterruptSound.checked = !!config.interruptSound;
  ui.inpWarnSoundUrl.value = config.warnSoundUrl ?? "";
  ui.inpCompletionSoundUrl.value = config.completionSoundUrl ?? "";
  ui.inpInterruptSoundUrl.value = config.interruptSoundUrl ?? "";
  ui.btnYScale.textContent = config.graphLogScale ? "Y → log" : "Y → linear";
  if (ui.btnGraphWindow) ui.btnGraphWindow.textContent = config.graphLiveWindow ? "Live view: on" : "Live view: off";
  ui.kpiRateLabel.textContent = `RATE (AVG ${config.windowPoints})`;
  if (ui.kpiStatusLabel) ui.kpiStatusLabel.textContent = `STATUS (${config.pollSec}s REFRESH)`;
}

function showSettingsNote(text, isError = false) {
  ui.settingsNote.textContent = text;
  ui.settingsNote.classList.toggle("danger", isError);
  if (text) setTimeout(() => showSettingsNote("", false), 4000);
}

// -----------------------------
// History + notifications + sound
// -----------------------------

/** @type {string[]} */
let history = [];

function nowStamp() {
  const d = new Date();
  const pad = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
}

function appendHistory(msg) {
  history.push(`[${nowStamp()}] ${msg}`);
  if (history.length > 600) history = history.slice(-600);
  ui.historyPre.textContent = history.join("\n");
  ui.historyPre.scrollTop = ui.historyPre.scrollHeight;
}

/** One-time capability warning so users know why OS banners didn't appear. */
let _desktopNotifyHintShown = false;
function desktopNotifyCapabilityHint() {
  if (_desktopNotifyHintShown) return;
  _desktopNotifyHintShown = true;
  try {
    if (!("Notification" in window)) {
      showToast("Desktop notifications unavailable", "This browser does not support system notifications.", "warn", { durationMs: 12000 });
      return;
    }
    const secure = typeof window !== "undefined" && "isSecureContext" in window ? window.isSecureContext : false;
    if (!secure) {
      appendNotifyDiagnostics("Notification blocked (origin):");
      showToast(
        "Desktop notifications are blocked here",
        "Browsers only allow system notifications on secure pages (https://) or localhost. Open this app via http://localhost (e.g. `python -m http.server 5173`, then visit http://localhost:5173) and click Enable notifications.",
        "warn",
        { durationMs: 16000 },
      );
      return;
    }
    if (Notification.permission === "denied") {
      appendNotifyDiagnostics("Notification blocked (denied):");
      showToast(
        "Desktop notifications blocked",
        "Unblock notifications in the browser’s site settings (lock icon in the address bar), then click Enable notifications again.",
        "warn",
        { durationMs: 16000 },
      );
      return;
    }
    if (Notification.permission !== "granted") {
      appendNotifyDiagnostics("Notification not enabled:");
      showToast(
        "Desktop notifications not enabled for this page",
        `Permission for this page is "${Notification.permission}". Click Enable notifications in the Info card to allow system notifications (toasts still work without this).`,
        "info",
        { durationMs: 14000 },
      );
    }
  } catch {
    // ignore
  }
}

/**
 * Desktop notification (optional). Toasts in `raiseAlert` / `maybeNotifyCompletion` work without permission.
 * @param {"threshold"|"completion"} kind
 * @param {string} title
 * @param {string} body
 */
function notifyDesktop(kind, title, body) {
  if (kind === "threshold" && !config.warnNotify) return;
  if (kind === "completion" && !config.completionNotify) return;
  if (kind === "interrupt" && !config.interruptNotify) return;
  // Do not spam capability toasts on alerts. We show a one-time hint on page load and keep the UI hint near the button.
  if (!("Notification" in window)) return;
  if (typeof window !== "undefined" && "isSecureContext" in window && !window.isSecureContext) return;
  if (Notification.permission !== "granted") return;
  const opts = {
    body: body ? `${body}\n\nClick to open VS Queue Monitor.` : "Click to open VS Queue Monitor.",
    silent: true,
    icon: NOTIFICATION_ICON_URL,
    tag:
      kind === "threshold"
        ? "vsqm-threshold"
        : kind === "completion"
          ? "vsqm-completion"
          : "vsqm-interrupt",
    renotify: true,
    requireInteraction: true,
    actions: [
      { action: "focus", title: "Open monitor" },
    ],
  };
  (async () => {
    try {
      const reg = await ensureServiceWorkerReady();
      if (reg && typeof reg.showNotification === "function") {
        // @ts-ignore options include requireInteraction in modern Chromium
        await reg.showNotification(title, opts);
        return;
      }
      // Fallback
      // @ts-ignore requireInteraction not in older libdefs.
      new Notification(title, opts);
    } catch (e) {
      appendNotifyDiagnostics("Notification delivery failed:");
      appendHistory(`Notification delivery failed: ${String(e)}`);
      showToast(
        "Desktop notification failed to deliver",
        "Permission is granted, but the browser/OS suppressed or blocked delivery. Check Windows notification settings for your browser (and Notification Center).",
        "warn",
        { durationMs: 16000 },
      );
    }
  })();
}

// One-time, non-spammy hint on page load (if notifications aren't ready).
(() => {
  const kick = () => desktopNotifyCapabilityHint();
  if (document.readyState === "complete") kick();
  else window.addEventListener("load", kick, { once: true });
})();

function appendNotifyDiagnostics(prefix) {
  try {
    const diag = {
      perm: "Notification" in window ? Notification.permission : "unsupported",
      secure: typeof window !== "undefined" && "isSecureContext" in window ? window.isSecureContext : false,
      proto: typeof location !== "undefined" ? location.protocol : "",
      vis: typeof document !== "undefined" ? document.visibilityState : "",
      focus: typeof document !== "undefined" ? document.hasFocus?.() : null,
    };
    appendHistory(`${prefix} ${JSON.stringify(diag)}`);
  } catch {
    // ignore
  }
}

/**
 * Test notifications are frequently suppressed while focused / by Windows settings.
 * Keep it minimal: send a single ping (same codepath as real alerts).
 */
function showTestDesktopNotification() {
  appendNotifyDiagnostics("Notification test:");
  notifyDesktop(
    "threshold",
    "VS Queue Monitor",
    "Test notification. If you don’t see a banner, open Notification Center and check Windows notification settings for your browser.",
  );
}

/** @type {AudioContext|null} */
let audioCtx = null;

/** @type {HTMLAudioElement|null} */
let previewAudioEl = null;
/** @type {string|null} */
let previewAudioObjectUrl = null;
/** @type {"warning"|"completion"|"interrupt"|null} */
let previewAudioKind = null;
let previewAudioNonce = 0;

function syncSoundPreviewButtons() {
  /** @param {"warning"|"completion"|"interrupt"} k */
  const isPlaying = (k) => previewAudioKind === k && previewAudioEl && !previewAudioEl.paused && !previewAudioEl.ended;
  const setBtn = (btn, k) => {
    const playing = isPlaying(k);
    btn.textContent = playing ? "Stop" : "Play";
    btn.classList.toggle("btn--stop", playing);
    btn.setAttribute("aria-pressed", playing ? "true" : "false");
    btn.title = playing ? "Stop preview" : "Play preview";
  };
  setBtn(ui.btnTestWarnSound, "warning");
  setBtn(ui.btnTestCompletionSound, "completion");
  setBtn(ui.btnTestInterruptSound, "interrupt");
}

function stopPreviewSound() {
  previewAudioNonce++;
  const a = previewAudioEl;
  previewAudioEl = null;
  previewAudioKind = null;
  if (a) {
    try {
      a.pause();
      a.currentTime = 0;
      a.src = "";
    } catch {
      // ignore
    }
  }
  if (previewAudioObjectUrl) {
    try {
      URL.revokeObjectURL(previewAudioObjectUrl);
    } catch {
      // ignore
    }
    previewAudioObjectUrl = null;
  }
  syncSoundPreviewButtons();
}

/** Soft sine chimes: used as fallback (and optional built-in sound). */
function beepBuiltin(kind) {
  try {
    audioCtx ??= new (window.AudioContext || window.webkitAudioContext)();
    const ctx = audioCtx;
    void ctx.resume();

    const master = ctx.createGain();
    master.gain.value = 0.72;
    master.connect(ctx.destination);

    const now = ctx.currentTime;
    /**
     * @param {number} freqHz
     * @param {number} t0
     * @param {number} durSec
     * @param {number} peak linear ~0..0.14
     */
    const tone = (freqHz, t0, durSec, peak) => {
      const o = ctx.createOscillator();
      const g = ctx.createGain();
      o.type = "sine";
      o.frequency.setValueAtTime(freqHz, t0);
      const atk = Math.min(0.022, durSec * 0.22);
      const rel = Math.min(0.12, durSec * 0.45);
      const peakT = t0 + atk;
      const endT = t0 + durSec;
      g.gain.setValueAtTime(0.0001, t0);
      g.gain.exponentialRampToValueAtTime(Math.max(peak, 0.0002), peakT);
      g.gain.exponentialRampToValueAtTime(0.0001, endT);
      o.connect(g);
      g.connect(master);
      o.start(t0);
      o.stop(endT + 0.04);
    };

    if (kind === "warning") {
      // Ascending perfect fifth (C5 → G5): clear, not harsh.
      tone(523.25, now, 0.12, 0.1);
      tone(783.99, now + 0.13, 0.14, 0.095);
    } else if (kind === "completion") {
      // C major arpeggio (C5–E5–G5–C6): short celebratory swell.
      tone(523.25, now, 0.2, 0.1);
      tone(659.25, now + 0.1, 0.22, 0.095);
      tone(783.99, now + 0.2, 0.24, 0.09);
      tone(1046.5, now + 0.3, 0.32, 0.085);
    } else {
      // Interrupt: descending minor third (E5 → C5): noticeable but not harsh.
      tone(659.25, now, 0.14, 0.1);
      tone(523.25, now + 0.16, 0.2, 0.095);
    }
  } catch {
    // ignore
  }
}

// -----------------------------
// File access
// -----------------------------

/** @type {FileSystemFileHandle|null} */
let logFileHandle = null;
/** @type {string|null} */
let sourceLabel = null;

const TAIL_BYTES = 128 * 1024;
/** First read after pick: load up to this many bytes for buffer + full graph replay (whole file if smaller). */
const INITIAL_FULL_READ_MAX_BYTES = 12 * 1024 * 1024;
const MAX_READ_BYTES_PER_POLL = 512 * 1024;
const BUFFER_MAX_CHARS = 400_000;

/** @type {number|null} */
let lastReadOffset = null;
/** @type {string|null} */
let pendingGraphReplayText = null;
/** Saved handle when read permission is still "prompt" after reload (browsers often require a user gesture). */
/** @type {FileSystemFileHandle|null} */
let pendingRestoreHandle = null;
/** @type {boolean} */
let restoreInProgress = false;
/** @type {string} */
let logBuffer = "";
const QUEUE_RESET_JUMP_THRESHOLD = 10;
/** Min seconds between threshold alerts (debounce duplicate polls; keep low enough to allow distinct milestones). */
const ALERT_MIN_INTERVAL_SEC = 5.0;
const COMPLETION_NOTIFY_MIN_INTERVAL_SEC = 2.0;
const QUEUE_UPDATE_INTERVAL_SEC = 30.0;
const QUEUE_STALE_TIMEOUT_MULT = 2.0;
const LOG_SILENCE_RECONNECT_SEC = 30.0;

/**
 * @param {ArrayBuffer} buf
 * @param {number} startOffset
 */
function decodeLogBytes(buf, startOffset) {
  if (!buf || buf.byteLength === 0) return "";
  const bytes = new Uint8Array(buf);
  const sample = bytes.slice(0, Math.min(4096, bytes.length));
  let nul = 0;
  for (const b of sample) if (b === 0) nul++;
  const nulRatio = nul / Math.max(1, sample.length);

  if (nulRatio > 0.05) {
    // Ensure 2-byte alignment if sliced mid-file
    let aligned = bytes;
    if (startOffset % 2 === 1 && aligned.length > 1) aligned = aligned.slice(1);
    for (const enc of ["utf-16le", "utf-16be", "utf-16"]) {
      try {
        return new TextDecoder(enc, { fatal: false }).decode(aligned);
      } catch {
        // continue
      }
    }
  }
  return new TextDecoder("utf-8", { fatal: false }).decode(bytes);
}

/**
 * @param {FileSystemFileHandle} handle
 * @param {number} tailBytes
 */
async function readLogRangeText(handle, start, end) {
  const file = await handle.getFile();
  const safeStart = Math.max(0, Math.min(start, file.size));
  const safeEnd = Math.max(safeStart, Math.min(end, file.size));
  const slice = file.slice(safeStart, safeEnd);
  const buf = await slice.arrayBuffer();
  return decodeLogBytes(buf, safeStart);
}

async function readLogTailText(handle, tailBytes) {
  const file = await handle.getFile();
  const size = file.size;
  const start = Math.max(0, size - tailBytes);
  return await readLogRangeText(handle, start, size);
}

/**
 * @param {FileSystemDirectoryHandle} dir
 * @param {string[]} names
 */
async function tryGetFirstExistingFile(dir, names) {
  for (const name of names) {
    try {
      const fh = await dir.getFileHandle(name);
      if (fh) return fh;
    } catch {
      // ignore
    }
  }
  return null;
}

/** Shell Link (.lnk) header: first DWORD is header size 0x0000004C. */
function fileHeadLooksLikeWindowsLnk(headBytes) {
  if (!headBytes || headBytes.byteLength < 4) return false;
  const u8 = new Uint8Array(headBytes);
  return u8[0] === 0x4c && u8[1] === 0 && u8[2] === 0 && u8[3] === 0;
}

/**
 * Windows "Create shortcut" makes a .lnk shell file, not a second path to the log bytes.
 * The File System Access API reads that tiny binary — queue detection sees garbage. Warn clearly.
 * @param {FileSystemFileHandle|null} handle
 */
async function warnIfPickedLogIsWindowsLnkShortcut(handle) {
  if (!handle) return;
  try {
    const file = await handle.getFile();
    const lower = file.name.toLowerCase();
    if (lower.endsWith(".lnk")) {
      showToast(
        "Wrong kind of shortcut",
        "This is a Windows .lnk shell shortcut, not the log. The app would read link metadata, not client-main.log. Delete it and use Copy, or run the ? command that uses mklink /H (hard link) in cmd.",
        "error",
        { actionLabel: "Guide", onAction: () => openHelp(), durationMs: 16000 },
      );
      appendHistory(
        "Picker: .lnk shortcuts do not work — use a hard link (mklink /H from Help) or copy client-main.log.",
      );
      return;
    }
    const head = await file.slice(0, 64).arrayBuffer();
    if (fileHeadLooksLikeWindowsLnk(head)) {
      showToast(
        "Wrong kind of shortcut",
        "This file is a Windows shell link (.lnk), even if renamed. Browsers cannot follow .lnk to the real log. Use mklink /H from ? (cmd) or copy the file.",
        "error",
        { actionLabel: "Guide", onAction: () => openHelp(), durationMs: 16000 },
      );
      appendHistory(
        "Picker: file header looks like .lnk — not plain log text. Use mklink /H or a file copy under Documents.",
      );
    }
  } catch {
    // ignore
  }
}

/**
 * @returns {Promise<IDBDatabase>}
 */
function openLogHandlesDb() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(IDB_HANDLES_NAME, 1);
    req.onupgradeneeded = () => {
      req.result.createObjectStore(IDB_HANDLES_STORE);
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

/**
 * @param {FileSystemFileHandle} handle
 */
async function idbPutLogFileHandle(handle) {
  const db = await openLogHandlesDb();
  await new Promise((resolve, reject) => {
    const tx = db.transaction(IDB_HANDLES_STORE, "readwrite");
    tx.oncomplete = () => resolve(undefined);
    tx.onerror = () => reject(tx.error);
    tx.objectStore(IDB_HANDLES_STORE).put(handle, IDB_LOG_FILE_KEY);
  });
  db.close();
}

/**
 * @returns {Promise<FileSystemFileHandle|undefined>}
 */
async function idbGetLogFileHandle() {
  const db = await openLogHandlesDb();
  const handle = await new Promise((resolve, reject) => {
    const tx = db.transaction(IDB_HANDLES_STORE, "readonly");
    const r = tx.objectStore(IDB_HANDLES_STORE).get(IDB_LOG_FILE_KEY);
    r.onsuccess = () => resolve(r.result);
    r.onerror = () => reject(r.error);
  });
  db.close();
  return handle;
}

async function idbDeleteLogFileHandle() {
  try {
    const db = await openLogHandlesDb();
    await new Promise((resolve, reject) => {
      const tx = db.transaction(IDB_HANDLES_STORE, "readwrite");
      tx.oncomplete = () => resolve(undefined);
      tx.onerror = () => reject(tx.error);
      tx.objectStore(IDB_HANDLES_STORE).delete(IDB_LOG_FILE_KEY);
    });
    db.close();
  } catch {
    // ignore
  }
}

const IDB_SOUNDS_NAME = "vsqm_sounds_v1";
const IDB_SOUNDS_STORE = "blobs";

/**
 * @returns {Promise<IDBDatabase>}
 */
function openSoundsDb() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(IDB_SOUNDS_NAME, 1);
    req.onupgradeneeded = () => {
      req.result.createObjectStore(IDB_SOUNDS_STORE);
    };
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

/**
 * @param {"warn"|"completion"} key
 * @param {Blob} blob
 */
async function idbPutSoundBlob(key, blob) {
  const db = await openSoundsDb();
  await new Promise((resolve, reject) => {
    const tx = db.transaction(IDB_SOUNDS_STORE, "readwrite");
    tx.oncomplete = () => resolve(undefined);
    tx.onerror = () => reject(tx.error);
    tx.objectStore(IDB_SOUNDS_STORE).put(blob, key);
  });
  db.close();
}

/**
 * @param {"warn"|"completion"} key
 * @returns {Promise<Blob|undefined>}
 */
async function idbGetSoundBlob(key) {
  try {
    const db = await openSoundsDb();
    const blob = await new Promise((resolve, reject) => {
      const tx = db.transaction(IDB_SOUNDS_STORE, "readonly");
      const r = tx.objectStore(IDB_SOUNDS_STORE).get(key);
      r.onsuccess = () => resolve(r.result);
      r.onerror = () => reject(r.error);
    });
    db.close();
    return /** @type {Blob|undefined} */ (blob);
  } catch {
    return undefined;
  }
}

/**
 * @param {"warn"|"completion"} key
 */
async function idbDeleteSoundBlob(key) {
  try {
    const db = await openSoundsDb();
    await new Promise((resolve, reject) => {
      const tx = db.transaction(IDB_SOUNDS_STORE, "readwrite");
      tx.oncomplete = () => resolve(undefined);
      tx.onerror = () => reject(tx.error);
      tx.objectStore(IDB_SOUNDS_STORE).delete(key);
    });
    db.close();
  } catch {
    // ignore
  }
}

/**
 * Best-effort: cache shipped default sounds in IndexedDB so they play reliably even
 * after reloads and in offline-ish scenarios. This does NOT autoplay audio.
 */
async function warmDefaultSoundsCache() {
  /**
   * @param {"warn"|"completion"|"interrupt"} key
   * @param {string} url
   */
  const ensure = async (key, url) => {
    const existing = await idbGetSoundBlob(key);
    if (existing) return;
    try {
      const r = await fetch(url, { cache: "force-cache" });
      if (!r.ok) return;
      const blob = await r.blob();
      if (!blob || blob.size < 16) return;
      await idbPutSoundBlob(key, blob);
    } catch {
      // ignore
    }
  };
  await Promise.all([
    ensure("warn", DEFAULT_WARN_SOUND_URL),
    ensure("completion", DEFAULT_COMPLETION_SOUND_URL),
    ensure("interrupt", DEFAULT_INTERRUPT_SOUND_URL),
  ]);
};

/**
 * @param {string} s
 * @param {number} [max]
 */
function truncateUrl(s, max = 56) {
  if (s.length <= max) return s;
  return s.slice(0, Math.max(0, max - 1)) + "…";
}

/**
 * @param {"warn"|"completion"|"interrupt"} kind
 * @param {Blob|undefined} blob
 */
function soundSummaryLine(kind, blob) {
  const fileName =
    kind === "warn" ? config.warnSoundFileName : kind === "completion" ? config.completionSoundFileName : config.interruptSoundFileName;
  const urlStr =
    kind === "warn" ? config.warnSoundUrl?.trim() : kind === "completion" ? config.completionSoundUrl?.trim() : config.interruptSoundUrl?.trim();
  const def =
    kind === "warn" ? DEFAULT_WARN_SOUND_URL : kind === "completion" ? DEFAULT_COMPLETION_SOUND_URL : DEFAULT_INTERRUPT_SOUND_URL;
  if (blob) return `Using: local file (${fileName || "saved in browser"})`;
  if (urlStr === "builtin") return "Using: built-in sine tones";
  if (!urlStr) return `Using: default clip (${def})`;
  return `Using: ${truncateUrl(urlStr)}`;
}

async function syncSoundSummaries() {
  const wBlob = await idbGetSoundBlob("warn");
  const cBlob = await idbGetSoundBlob("completion");
  const iBlob = await idbGetSoundBlob("interrupt");
  ui.warnSoundSummary.textContent = soundSummaryLine("warn", wBlob);
  ui.completionSoundSummary.textContent = soundSummaryLine("completion", cBlob);
  ui.interruptSoundSummary.textContent = soundSummaryLine("interrupt", iBlob);
  ui.btnClearWarnSoundFile.hidden = !wBlob && !config.warnSoundFileName;
  ui.btnClearCompletionSoundFile.hidden = !cBlob && !config.completionSoundFileName;
  ui.btnClearInterruptSoundFile.hidden = !iBlob && !config.interruptSoundFileName;
}

/**
 * @param {"warning"|"completion"|"interrupt"} kind
 * @param {{ force?: boolean, returnAudio?: boolean }} [opts]
 * @returns {Promise<{ audio: HTMLAudioElement, objectUrl: string|null } | null>}
 */
async function playSoundAsync(kind, opts = undefined) {
  const force = !!opts?.force;
  if (!force) {
    if (kind === "warning" && !config.warnSound) return;
    if (kind === "completion" && !config.completionSound) return;
    if (kind === "interrupt" && !config.interruptSound) return;
  }
  const key = kind === "warning" ? "warn" : kind === "completion" ? "completion" : "interrupt";
  const defaultUrl =
    kind === "warning" ? DEFAULT_WARN_SOUND_URL : kind === "completion" ? DEFAULT_COMPLETION_SOUND_URL : DEFAULT_INTERRUPT_SOUND_URL;
  try {
    const blob = await idbGetSoundBlob(key);
    if (blob) {
      const url = URL.createObjectURL(blob);
      const a = new Audio(url);
      await a.play();
      if (opts?.returnAudio) return { audio: a, objectUrl: url };
      a.onended = () => URL.revokeObjectURL(url);
      return null;
    }
    const urlStr =
      kind === "warning" ? config.warnSoundUrl?.trim() : kind === "completion" ? config.completionSoundUrl?.trim() : config.interruptSoundUrl?.trim();
    if (urlStr === "builtin") {
      beepBuiltin(kind);
      return null;
    }
    const src = urlStr || defaultUrl;
    const a = new Audio(src);
    await a.play();
    if (opts?.returnAudio) return { audio: a, objectUrl: null };
  } catch {
    beepBuiltin(kind);
  }
  return null;
}

/**
 * @param {"warning"|"completion"} kind
 */
function beep(kind) {
  void playSoundAsync(kind);
}

/**
 * Preview sound from Settings (ignores the enable toggles).
 * Click again to stop the preview.
 * @param {"warning"|"completion"|"interrupt"} kind
 */
function previewSound(kind) {
  const isPlaying = previewAudioKind === kind && previewAudioEl && !previewAudioEl.paused && !previewAudioEl.ended;
  if (isPlaying) {
    stopPreviewSound();
    return;
  }

  stopPreviewSound();
  syncSoundPreviewButtons();
  const myNonce = ++previewAudioNonce;
  void (async () => {
    const res = await playSoundAsync(kind, { force: true, returnAudio: true });
    if (myNonce !== previewAudioNonce) {
      if (res?.audio) {
        try {
          res.audio.pause();
          res.audio.currentTime = 0;
        } catch {
          // ignore
        }
      }
      if (res?.objectUrl) {
        try {
          URL.revokeObjectURL(res.objectUrl);
        } catch {
          // ignore
        }
      }
      return;
    }
    if (!res?.audio) {
      syncSoundPreviewButtons();
      return;
    }
    previewAudioEl = res.audio;
    previewAudioObjectUrl = res.objectUrl;
    previewAudioKind = kind;
    res.audio.onended = () => {
      if (previewAudioEl === res.audio) stopPreviewSound();
      else if (res.objectUrl) URL.revokeObjectURL(res.objectUrl);
    };
    syncSoundPreviewButtons();
  })();
}

/**
 * @param {FileSystemFileHandle} handle
 * @param {string} sourceLabel_
 * @param {{ name: string }} meta
 */
async function saveLastLogToStorage(handle, sourceLabel_, meta) {
  try {
    await idbPutLogFileHandle(handle);
  } catch {
    return;
  }
  try {
    localStorage.setItem(
      STORAGE_LAST_LOG_META_KEY,
      JSON.stringify({ name: meta.name, sourceLabel: sourceLabel_, savedAt: Date.now() }),
    );
  } catch {
    // ignore
  }
}

function hideRestoreBanner() {
  if (ui.restoreBanner) ui.restoreBanner.hidden = true;
}

/**
 * @param {string} [fileNameHint]
 */
function showRestoreBanner(fileNameHint) {
  if (!ui.restoreBanner || !ui.restoreBannerDetail) return;
  const extra = fileNameHint && String(fileNameHint).trim() ? ` (${String(fileNameHint).trim()})` : "";
  ui.restoreBannerDetail.textContent =
    `Chromium needs a click to allow reading the saved file again${extra}. The File System Access API does not grant read access from a page-load task without a user gesture.`;
  ui.restoreBanner.hidden = false;
}

async function clearSavedLogHandle() {
  pendingRestoreHandle = null;
  hideRestoreBanner();
  await idbDeleteLogFileHandle();
  try {
    localStorage.removeItem(STORAGE_LAST_LOG_META_KEY);
  } catch {
    // ignore
  }
}

/**
 * @param {FileSystemFileHandle} handle
 * @param {string} sourceLabel_
 * @param {{ historyLine?: string|null }} opts
 */
async function applyPickedLogHandle(handle, sourceLabel_, opts = {}) {
  pendingRestoreHandle = null;
  hideRestoreBanner();
  hideInterruptAdoptModal();
  const historyLine = opts.historyLine;
  logFileHandle = handle;
  sourceLabel = sourceLabel_;
  ui.infoSource.textContent = sourceLabel ?? "—";
  ui.infoResolved.textContent = logFileHandle ? (await logFileHandle.getFile()).name : "—";
  ui.btnStartStop.disabled = !logFileHandle;
  await warnIfPickedLogIsWindowsLnkShortcut(logFileHandle);
  if (historyLine) appendHistory(historyLine);
  lastReadOffset = null;
  pendingGraphReplayText = null;
  logBuffer = "";
  graphPoints = [];
  currentPoint = null;
  lastPosition = null;
  positionOneReachedAt = null;
  drawGraph();
  try {
    const f = await handle.getFile();
    await saveLastLogToStorage(handle, sourceLabel_, { name: f.name });
  } catch {
    await clearSavedLogHandle();
  }
}

/**
 * @param {FileSystemFileHandle} handle
 */
async function finishRestoreSavedLog(handle) {
  if (restoreInProgress) return;
  restoreInProgress = true;
  try {
    pendingRestoreHandle = null;
    let meta = null;
    try {
      const raw = localStorage.getItem(STORAGE_LAST_LOG_META_KEY);
      if (raw) meta = JSON.parse(raw);
    } catch {
      // ignore
    }
    const label = meta && typeof meta.sourceLabel === "string" ? meta.sourceLabel : "Saved log";
    const name = meta && typeof meta.name === "string" ? meta.name : (await handle.getFile()).name;
    await applyPickedLogHandle(handle, label, {
      historyLine: `Restored last log: ${name} (${label}).`,
    });
    if (!tutorialActive) startMonitoring();
  } finally {
    restoreInProgress = false;
  }
}

async function tryRestoreLastLogOnLoad() {
  if (typeof window !== "undefined" && "isSecureContext" in window && !window.isSecureContext) {
    appendHistory(
      "File picking is blocked in this context (not a secure origin). Open the app from http://localhost (or https://) so the browser can show the file picker.",
    );
    showToast(
      "Open via localhost",
      "Pick log requires a secure origin. Run `python -m http.server 5173`, open http://localhost:5173, then click Pick log file again.",
      "warn",
      { durationMs: 16000 },
    );
    return;
  }
  if (!window.showOpenFilePicker) {
    appendHistory(
      "File System Access API not available (`showOpenFilePicker`). Use Edge/Chrome and open the app from https:// or http://localhost (e.g. `python -m http.server 5173`). Some contexts (including file://) do not expose the picker.",
    );
    return;
  }
  /** @type {FileSystemFileHandle|undefined} */
  let handle;
  try {
    handle = await idbGetLogFileHandle();
  } catch {
    return;
  }
  if (!handle) return;

  try {
    const perm = await handle.queryPermission({ mode: "read" });
    if (perm === "denied") {
      await clearSavedLogHandle();
      return;
    }
    // If the browser already persisted read access for this handle, restore without a click.
    if (perm === "granted") {
      await finishRestoreSavedLog(handle);
      return;
    }
    // "prompt": do NOT call requestPermission() from the load task — Chromium ignores it without
    // a user activation. Show the bar + toast; the button/Allow run requestPermission in a click handler.
    pendingRestoreHandle = handle;
    let metaName = "";
    try {
      const raw = localStorage.getItem(STORAGE_LAST_LOG_META_KEY);
      if (raw) {
        const m = JSON.parse(raw);
        if (m && typeof m.name === "string") metaName = m.name;
      }
    } catch {
      // ignore
    }
    showRestoreBanner(metaName);
    showToast(
      "Resume last session",
      "Use Grant access & start in the green bar (or Allow here). The browser requires a click to reopen the file.",
      "info",
      {
        actionLabel: "Allow",
        onAction: async () => {
          try {
            const h = pendingRestoreHandle;
            if (!h) return;
            const p2 = await h.requestPermission({ mode: "read" });
            if (p2 !== "granted") {
              appendHistory("Last log not restored (permission denied).");
              return;
            }
            hideRestoreBanner();
            await finishRestoreSavedLog(h);
          } catch (e) {
            appendHistory(`Could not restore last log: ${String(e)}`);
          }
        },
        durationMs: 60000,
      },
    );
    appendHistory(
      "Saved log found — click **Grant access & start** (or Allow) so the browser can read the file again; then monitoring starts automatically.",
    );
  } catch (e) {
    appendHistory(`Could not restore last log: ${String(e)}`);
    await clearSavedLogHandle();
  }
}

async function pickLogFile() {
  if (typeof window !== "undefined" && "isSecureContext" in window && !window.isSecureContext) {
    appendHistory(
      "Pick log failed: this page is not a secure origin. Open via http://localhost (or https://) for the browser file picker to work.",
    );
    showToast(
      "Open via localhost",
      "Pick log requires a secure origin. Run `python -m http.server 5173`, open http://localhost:5173, then click Pick log file again.",
      "warn",
      { durationMs: 16000 },
    );
    return;
  }
  if (!window.showOpenFilePicker) {
    appendHistory("This browser does not support file picking. Use Edge or Chrome.");
    return;
  }
  // Proactive guidance: the picker UI can block “system” folders before we get a rejection.
  /** @type {{remove: ()=>void}|null} */
  let tipToast = null;
  try {
    const isFile = String(window.location && window.location.protocol) === "file:";
    const plat = String(navigator.platform || "").toLowerCase();
    const isWin = plat.includes("win");
    const isLinux = plat.includes("linux");
    if (isFile && (isWin || isLinux)) {
      appendHistory("Tip: if the picker says it can’t open files in a folder due to “system files”, the browser is blocking a protected location.");
      tipToast = showToast("Picker tip", "If you hit “system files” / protected folders, use the fix guide (mklink/ln -s).", "info", {
        actionLabel: "Open fix guide",
        onAction: () => openPickerFixGuide(),
        durationMs: Infinity,
      });
      if (isWin) {
        appendHistory("Windows: prefer a hard link to the log file — open ?, paste the full path to client-main.log, run the generated mklink /H in cmd.");
        appendHistory("Windows note: only mklink /H (hard link) to the log FILE is supported here — do not use folder links.");
      } else if (isLinux) {
        appendHistory("Linux workaround (symlink into ~/VSLogs):");
        appendHistory("  mkdir -p ~/VSLogs");
        appendHistory("  ln -s ~/.config/VintagestoryData/Logs/client-main.log ~/VSLogs/client-main.log");
        appendHistory("Then pick: ~/VSLogs/client-main.log");
      }
    }
  } catch {
    // ignore
  }
  /** @type {any} */
  let startIn = undefined;
  try {
    // `startIn` cannot be an arbitrary path (e.g. %APPDATA% or $HOME). Best-effort only.
    const last = localStorage.getItem(STORAGE_LAST_DIR_KEY);
    if (last) startIn = last;
  } catch {
    // ignore
  }
  if (!startIn) startIn = "documents";

  let handle;
  try {
    [handle] = await window.showOpenFilePicker({
      multiple: false,
      startIn,
      types: [
        {
          description: "Vintage Story log",
          accept: {
            "text/plain": [".log", ".txt"],
          },
        },
      ],
    });
  } catch (e) {
    tipToast?.remove();
    const msg = String(e && (e.message || e.name || e));
    const low = msg.toLowerCase();
    if (low.includes("abort") || low.includes("cancel")) {
      appendHistory("Pick log cancelled.");
      showToast(
        "Pick cancelled",
        "No file was selected. If you were trying to pick from AppData/protected folders and saw “system files”, the browser blocked it — use the fix guide.",
        "warn",
        {
          actionLabel: "Open fix guide",
          onAction: () => openPickerFixGuide(),
          durationMs: 12000,
        },
      );
      return;
    }
    const looksBlocked =
      low.includes("system files") ||
      low.includes("not allowed") ||
      low.includes("not permitted") ||
      low.includes("denied") ||
      low.includes("security") ||
      low.includes("permission");
    if (looksBlocked) {
      appendHistory("Browser blocked access to that folder/file (protected/system location).");
      showToast(
        "Picker blocked",
        "Browser denied access (protected/system location). Use the fix guide to expose the log under Documents/Home (mklink /H or ln -s).",
        "error",
        {
          actionLabel: "Open fix guide",
          onAction: () => openPickerFixGuide(),
          durationMs: 16000,
        },
      );
      appendHistory("Note: browsers do not reveal the exact filesystem path you attempted to pick, so we can’t auto-generate a command with the exact blocked path.");
      appendHistory('Tip: click "?" and paste the full path to client-main.log — the app generates mklink /H (hard link).');
      appendHistory("Linux workaround (symlink; source is the usual VS data dir under ~/.config):");
      appendHistory("  mkdir -p ~/VSLogs");
      appendHistory("  ln -s ~/.config/VintagestoryData/Logs/client-main.log ~/VSLogs/client-main.log");
      appendHistory("Explanation: this exposes the log under your home directory so the browser picker can access it.");
      appendHistory("Then pick: ~/VSLogs/client-main.log");
      return;
    }
    appendHistory(`Pick log failed: ${msg}`);
    showToast("Pick failed", msg, "error");
    return;
  }
  tipToast?.remove();
  if (!handle) return;
  const pickedName = (await handle.getFile()).name;
  await applyPickedLogHandle(handle, "Picked file", {
    historyLine: `Selected log file: ${pickedName}`,
  });
  // During the tutorial we require completing onboarding before monitoring starts.
  if (tutorialActive) {
    tutorialPickedDuringRun = true;
  } else {
    startMonitoringAfterSuccessfulPick();
  }

  // Best-effort: remember the last directory via well-known startIn token (not a real path).
  // Browsers do not expose a parent directory for a picked file handle.
  try {
    localStorage.setItem(STORAGE_LAST_DIR_KEY, String(startIn || "documents"));
  } catch {
    // ignore
  }
}

// -----------------------------
// Monitor engine (browser)
// -----------------------------

/** @typedef {[number, number]} GraphPoint */ // [epochSec, position]

/** @type {GraphPoint[]} */
let graphPoints = [];

/** Last draw layout for canvas hit-testing (queue graph). */
let lastGraphLayout = /** @type {null | { padL: number; padR: number; padT: number; padB: number; plotW: number; plotH: number; w: number; h: number; t1: number; span: number; minP: number; maxP: number }} */ (
  null
);
let graphCanvasHovering = false;
/** Canvas-space X for hover crosshair (null when pointer leaves). */
let graphHoverCanvasX = /** @type {number|null} */ (null);
/** Hover-snapped graph point (null when not hovering a point). */
let graphHoverPoint = /** @type {GraphPoint|null} */ (null);
let graphDrawRaf = 0;
function scheduleDrawGraph() {
  if (graphDrawRaf) return;
  graphDrawRaf = requestAnimationFrame(() => {
    graphDrawRaf = 0;
    drawGraph();
  });
}
/** @type {GraphPoint|null} */
let currentPoint = null;
/** @type {number|null} */
let lastPosition = null;
/** @type {number|null} */
let positionOneReachedAt = null;
/** @type {number|null} */
let connectPhaseStartedEpoch = null;
/** @type {number|null} */
let progressAtFrontEntry = null;
let leftConnectQueueDetected = false;
let running = false;
/** @type {number|null} */
let monitorStartEpoch = null;
/** @type {number|null} */
let pollTimer = null;
/** @type {number|null} */
let estimateTimer = null;
/** @type {number|null} */
let graphRealtimeTimer = null;
/** @type {number} */
let lastAlertEpoch = 0;
/** @type {Set<number>} */
let thresholdsFired = new Set();
/** Only animate warnings marquee briefly after a warning fires. */
let warningsMarqueeUntilEpoch = 0;
// Legacy: warnings used to have an explicit edit mode; now editing is via contextual popover.
/** @type {number} */
let lastCompletionNotifyEpoch = 0;
let completionNotifiedThisRun = false;
/** @type {number|null} */
let lastQueueRunSession = null;
/** Epoch seconds for the first queue line of the current run (best-effort). */
/** @type {number|null} */
let currentQueueRunStartEpoch = null;
/** @type {number|null} */
let lastQueueLineEpoch = null;
/** @type {{ size: number, mtime: number } | null} */
let lastLogStat = null;
/** @type {number|null} */
let lastLogGrowthEpoch = null;
let interruptedMode = false;
/** Session index (`parseTail`) at the moment we entered interrupted mode; `null` if unknown. */
/** @type {number|null} */
let sessionAtInterrupt = null;
/** User dismissed adopt for this session (suppress repeat prompts until session changes). */
/** @type {number|null} */
let interruptAdoptDeclinedSession = null;
/** @type {boolean} */
let interruptAdoptModalVisible = false;
/** @type {number|null} */
let interruptAdoptPendingSession = null;
/** @type {number|null} */
let interruptAdoptPendingPosition = null;
/** @type {number|null} */
let interruptedElapsedSec = null;
/** @type {[string, string] | null} */
let frozenRatesAtInterrupt = null;
/** @type {number|null} */
let lastQueuePositionChangeEpoch = null;
let predSpeedScale = 1.0;
let staleSlotsAccounted = 0;
/** @type {number|null} */
let mppFloorPosition = null;
/** @type {number|null} */
let mppFloorValue = null;

function setStatus(text, danger = false) {
  const statusTextEl = /** @type {HTMLElement|null} */ (document.getElementById("kpiStatusText"));
  if (statusTextEl) statusTextEl.textContent = text;
  else ui.kpiStatus.textContent = text;
  // legacy flag (still used by some callers)
  ui.kpiStatus.classList.toggle("danger", danger);

  const el = ui.kpiStatus;
  const cls = [
    "kpi__value--neutral",
    "kpi__value--info",
    "kpi__value--warn",
    "kpi__value--danger",
    "kpi__value--done",
    "kpi__value--ok",
  ];
  for (const c of cls) el.classList.remove(c);

  const t = String(text || "").toLowerCase();
  let state = "neutral";
  if (danger || t === "error" || t.includes("warning:") || t.includes("interrupted")) state = "danger";
  else if (t.includes("reconnecting") || t.includes("connecting") || t.includes("waiting for log")) state = "info";
  else if (t.includes("at front")) state = "warn";
  else if (t.includes("completed")) state = "done";
  else if (t.includes("monitoring")) state = "ok";

  el.classList.add(
    state === "ok"
      ? "kpi__value--ok"
      : state === "done"
        ? "kpi__value--done"
        : state === "warn"
          ? "kpi__value--warn"
          : state === "info"
            ? "kpi__value--info"
            : state === "danger"
              ? "kpi__value--danger"
              : "kpi__value--neutral",
  );
}

/**
 * @param {number|null} pos
 */
function setPositionDisplay(pos) {
  ui.kpiPosition.textContent = pos == null ? "—" : String(pos);
}

/**
 * @param {number} sec
 */
function formatDuration(sec) {
  const total = Math.max(0, Math.round(sec));
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  if (h > 0) return `${h}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
  return `${m}:${String(s).padStart(2, "0")}`;
}

/**
 * @param {number} sec
 */
function formatDurationRemaining(sec) {
  sec = Math.max(0, Number(sec));
  if (!Number.isFinite(sec) || sec <= 0) return "—";
  if (sec < 1) sec = 1;
  if (sec >= 3600) return formatDuration(sec);
  const m = Math.floor(sec / 60);
  const s = sec - m * 60;
  return `${m}:${s.toFixed(2).padStart(5, "0")}`;
}

function rollingWindowPoints() {
  const n = Math.max(2, Math.min(10000, Math.floor(config.windowPoints || 10)));
  return n;
}

function windowRecentPoints() {
  if (graphPoints.length < 2) return [];
  const n = rollingWindowPoints();
  return graphPoints.slice(-(n + 1));
}

function currentQueuePosition() {
  return lastPosition ?? (currentPoint ? currentPoint[1] : null);
}

function queueElapsedStartEpoch() {
  if (connectPhaseStartedEpoch != null) return connectPhaseStartedEpoch;
  if (graphPoints.length > 0) return graphPoints[0][0];
  return monitorStartEpoch;
}

function computeMovingAverageSpeedPosPerSec() {
  const pts = graphPoints;
  if (pts.length < 2) return { speed: null, n: 0, trail: pts.map((p) => p[1]) };
  const nWin = rollingWindowPoints();
  const recent = pts.slice(-(nWin + 1));
  const trail = recent.map((p) => p[1]);
  /** @type {number[]} */
  const rates = [];
  for (let i = 0; i < recent.length - 1; i++) {
    const [t0, p0] = recent[i];
    const [t1, p1] = recent[i + 1];
    const dt = t1 - t0;
    if (dt <= 0) continue;
    const improvement = p0 - p1;
    if (improvement <= 0) continue;
    rates.push(improvement / dt);
  }
  if (rates.length === 0) return { speed: null, n: 0, trail };
  if (rates.length < 3) return { speed: rates.reduce((a, b) => a + b, 0) / rates.length, n: rates.length, trail };
  rates.sort((a, b) => a - b);
  return { speed: rates[Math.floor(rates.length / 2)], n: rates.length, trail };
}

function computeWeightedSpeedPosPerSec() {
  const pts = graphPoints;
  if (pts.length < 2) return { speed: null, n: 0, trail: pts.map((p) => p[1]) };
  const nWin = rollingWindowPoints();
  const recent = pts.slice(-(nWin + 1));
  const trail = recent.map((p) => p[1]);
  let now = Date.now() / 1000;
  if (currentQueuePosition() === 0 && recent.length >= 2) now = recent[recent.length - 1][0];
  const TAU = 90.0;
  let wSum = 0;
  let rSum = 0;
  let nSeg = 0;
  for (let i = 0; i < recent.length - 1; i++) {
    const [t0, p0] = recent[i];
    const [t1, p1] = recent[i + 1];
    const dt = t1 - t0;
    if (dt <= 0) continue;
    const improvement = p0 - p1;
    if (improvement <= 0) continue;
    const rate = improvement / dt;
    const w = Math.exp(-Math.max(0, now - t1) / TAU);
    wSum += w;
    rSum += rate * w;
    nSeg += 1;
  }
  if (wSum <= 0 || nSeg < 1) return { speed: null, n: 0, trail };
  const speed = rSum / wSum;
  if (!(speed > 0)) return { speed: null, n: 0, trail };
  return { speed, n: nSeg, trail };
}

function computeEmpiricalPosPerSec() {
  const recent = windowRecentPoints();
  if (recent.length < 2) return null;
  const [t0, p0] = recent[0];
  const [t1, p1] = recent[recent.length - 1];
  const drop = p0 - p1;
  if (drop <= 0) return null;
  const pos = currentQueuePosition();
  const dt = running && pos !== 0 ? (Date.now() / 1000) - t0 : t1 - t0;
  if (dt <= 0) return null;
  return drop / dt;
}

function minutesPerPositionFromWindow() {
  const vEmp = computeEmpiricalPosPerSec();
  if (vEmp != null && vEmp > 0) return 1 / (vEmp * 60);
  const w = computeWeightedSpeedPosPerSec();
  if (w.speed != null && w.n > 0 && w.speed > 0) return 1 / (w.speed * predSpeedScale * 60);
  const ma = computeMovingAverageSpeedPosPerSec();
  if (ma.speed == null || ma.n <= 0 || !(ma.speed > 0)) return null;
  return 1 / (ma.speed * predSpeedScale * 60);
}

function minutesPerPositionCappedForDwell(mppRaw, pos) {
  if (mppRaw == null || pos == null || pos <= 1) return mppRaw;
  if (mppFloorPosition !== pos || mppFloorValue == null || !(mppFloorValue > 0)) return mppRaw;
  if (mppRaw <= mppFloorValue) return mppRaw;
  if (lastQueuePositionChangeEpoch == null) return mppFloorValue;
  const dwell = Math.max(0, (Date.now() / 1000) - lastQueuePositionChangeEpoch);
  if (dwell < mppFloorValue * 60) return mppFloorValue;
  return mppRaw;
}

function globalAvgMinutesPerPosition() {
  if (graphPoints.length < 2) return null;
  /** @type {number[]} */
  const mpps = [];
  for (let i = 0; i < graphPoints.length - 1; i++) {
    const [t0, p0] = graphPoints[i];
    const [t1, p1] = graphPoints[i + 1];
    const dt = t1 - t0;
    if (dt <= 0) continue;
    const improvement = p0 - p1;
    if (improvement <= 0) continue;
    const mpp = dt / 60 / improvement;
    if (Number.isFinite(mpp) && mpp > 0) mpps.push(mpp);
  }
  if (mpps.length === 0) return null;
  return mpps.reduce((a, b) => a + b, 0) / mpps.length;
}

function formatQueueRate(mpp) {
  if (mpp != null && mpp > 0) return `${mpp.toFixed(2)} min/pos`;
  return "—";
}

function bumpWarningsMarquee(sec = 10) {
  const now = Date.now() / 1000;
  warningsMarqueeUntilEpoch = Math.max(warningsMarqueeUntilEpoch, now + Math.max(2, sec));
  syncWarningsMarquee();
  window.setTimeout(() => {
    if (Date.now() / 1000 >= warningsMarqueeUntilEpoch - 0.05) syncWarningsMarquee();
  }, Math.ceil(sec * 1000) + 60);
}

function autoPanWarningsToLatestHit() {
  const viewport = ui.kpiWarnings?.querySelector(".kpiWarn__viewport");
  if (!viewport) return;
  const hits = viewport.querySelectorAll(".kpiWarn--hit");
  const el = hits.length ? /** @type {HTMLElement} */ (hits[hits.length - 1]) : null;
  if (!el) return;
  try {
    el.scrollIntoView({ behavior: "smooth", inline: "center", block: "nearest" });
  } catch {
    // ignore
  }
}

function syncWarningsMarquee() {
  const viewport = ui.kpiWarnings?.querySelector(".kpiWarn__viewport");
  const rail = ui.kpiWarningsRail;
  if (!viewport || !rail) return;
  viewport.classList.remove("kpiWarn__viewport--scroll");
  viewport.classList.remove("kpiWarn__viewport--overflow");
  ui.kpiWarnings?.classList.remove("kpiWarn--overflow");
  rail.classList.remove("kpiWarn__rail--marquee");
  rail.style.removeProperty("--kpi-warn-shift");
  rail.style.removeProperty("animation");

  queueMicrotask(() => {
    requestAnimationFrame(() => {
      const vw = viewport.clientWidth;
      const rw = rail.scrollWidth;
      if (rw <= vw + 2) return;
      viewport.classList.add("kpiWarn__viewport--overflow");
      ui.kpiWarnings?.classList.add("kpiWarn--overflow");
      syncWarningsArrowState();
      const now = Date.now() / 1000;
      if (!(now < warningsMarqueeUntilEpoch)) return;
      if (typeof window.matchMedia === "function" && window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
        return;
      }
      const shift = rw - vw;
      rail.style.setProperty("--kpi-warn-shift", `${shift}px`);
      const sec = Math.min(22, Math.max(7, 6 + shift / 28));
      rail.style.animation = `kpiWarnMarquee ${sec}s ease-in-out infinite alternate`;
      viewport.classList.add("kpiWarn__viewport--scroll");
      rail.classList.add("kpiWarn__rail--marquee");
      syncWarningsArrowState();
    });
  });
}

function syncWarningsArrowState() {
  const viewport = ui.kpiWarnings?.querySelector(".kpiWarn__viewport");
  if (!viewport || !ui.btnWarnScrollL || !ui.btnWarnScrollR) return;
  const max = Math.max(0, viewport.scrollWidth - viewport.clientWidth);
  const x = viewport.scrollLeft;
  ui.btnWarnScrollL.disabled = x <= 1;
  ui.btnWarnScrollR.disabled = x >= max - 1;
}

function refreshWarningsKpi() {
  let thresholds;
  try {
    thresholds = parseAlertThresholds(config.thresholdsRaw);
  } catch {
    if (ui.kpiWarningsRail) ui.kpiWarningsRail.textContent = "—";
    syncWarningsMarquee();
    return;
  }
  const pos = currentQueuePosition();
  const fired = thresholdsFired;
  const parts = [];
  for (const t of thresholds) {
    const passed = (pos != null && pos <= t) || fired.has(t);
    const cls = passed ? "kpiWarn--hit" : "kpiWarn--pending";
    parts.push(`<span class="kpiWarn__threshold ${cls}" data-threshold="${t}">${escapeHtml(String(t))}</span>`);
  }
  if (ui.kpiWarningsRail) {
    ui.kpiWarningsRail.innerHTML = parts.join('<span class="kpiWarn--sep"> · </span>');
  }
  syncWarningsMarquee();
}

function focusUpcomingWarningOnLoad() {
  const viewport = ui.kpiWarnings?.querySelector(".kpiWarn__viewport");
  if (!viewport) return;
  const rail = ui.kpiWarningsRail;
  if (!rail) return;
  // Upcoming = first pending threshold (not yet hit), left-to-right as displayed.
  const el = rail.querySelector(".kpiWarn--pending");
  if (!el) {
    viewport.scrollLeft = 0;
    syncWarningsArrowState();
    return;
  }
  try {
    /** @type {HTMLElement} */ (el).scrollIntoView({ behavior: "instant", inline: "center", block: "nearest" });
  } catch {
    // ignore
  }
  syncWarningsArrowState();
}

function estimateSecondsRemaining() {
  let pos = currentQueuePosition();
  if (pos == null || pos === 0) return null;
  const remainingPositions = pos === 1 ? 1 : Math.max(0, pos - 1);
  const vEmp = computeEmpiricalPosPerSec();
  let speed = null;
  if (vEmp != null && vEmp > 0) speed = vEmp;
  if (speed == null) {
    const w = computeWeightedSpeedPosPerSec();
    if (w.speed != null && w.n > 0 && w.speed > 0) speed = w.speed;
  }
  if (speed == null) {
    const ma = computeMovingAverageSpeedPosPerSec();
    if (ma.speed != null && ma.speed > 0) speed = ma.speed;
  }
  if (speed == null || !(speed > 0)) {
    if (pos === 1) return QUEUE_UPDATE_INTERVAL_SEC;
    return null;
  }

  const expectedSecPerPos = 1 / speed;
  const expectedUpdateSec = Math.max(QUEUE_UPDATE_INTERVAL_SEC, expectedSecPerPos);
  if (running && currentPoint && pos >= 1) {
    const dt = (Date.now() / 1000) - currentPoint[0];
    if (dt >= expectedUpdateSec) {
      const missed = Math.floor(dt / expectedUpdateSec);
      if (missed > staleSlotsAccounted) {
        const extra = missed - staleSlotsAccounted;
        predSpeedScale *= Math.pow(0.92, extra);
        predSpeedScale = Math.max(0.05, predSpeedScale);
        staleSlotsAccounted = missed;
      }
    } else {
      staleSlotsAccounted = 0;
    }
    const vEff = speed * predSpeedScale;
    const base = remainingPositions / vEff;
    return Math.max(1, base - dt);
  }
  return remainingPositions / (speed * predSpeedScale);
}

function updateTimeEstimates() {
  ui.kpiRateLabel.textContent = `RATE (AVG ${rollingWindowPoints()})`;
  const pos = currentQueuePosition();

  if (interruptedElapsedSec != null) {
    ui.kpiElapsed.textContent = formatDuration(interruptedElapsedSec);
    ui.kpiRemaining.textContent = "—";
    if (frozenRatesAtInterrupt) {
      ui.kpiRate.textContent = frozenRatesAtInterrupt[0];
      ui.infoGlobalRate.textContent = frozenRatesAtInterrupt[1];
    } else {
      const mppRaw = minutesPerPositionFromWindow();
      const mpp = minutesPerPositionCappedForDwell(mppRaw, pos);
      ui.kpiRate.textContent = formatQueueRate(mpp);
      ui.infoGlobalRate.textContent = formatQueueRate(globalAvgMinutesPerPosition());
    }
    ui.progressFill.style.width = "0%";
    ui.progressFill.title = "Progress: 0% (interrupted)";
    ui.progressFill.setAttribute("aria-label", "Progress: 0% (interrupted)");
    if (ui.progressBar) ui.progressBar.title = "Progress: 0% (interrupted)";
    if (ui.kpiProgressLabel) ui.kpiProgressLabel.textContent = "PROGRESS (0%)";
    return;
  }

  if (running && pos != null && pos > 1) positionOneReachedAt = null;

  const startT = queueElapsedStartEpoch();
  let elapsedSec = null;
  if (running && monitorStartEpoch != null) {
    if (startT == null) ui.kpiElapsed.textContent = "—";
    else if (pos != null && pos <= 1 && positionOneReachedAt != null) {
      elapsedSec = Math.max(0, positionOneReachedAt - startT);
      ui.kpiElapsed.textContent = formatDuration(elapsedSec);
    } else {
      elapsedSec = Math.max(0, (Date.now() / 1000) - startT);
      ui.kpiElapsed.textContent = formatDuration(elapsedSec);
    }
  } else if (!running && positionOneReachedAt != null && graphPoints.length >= 1) {
    elapsedSec = Math.max(0, positionOneReachedAt - graphPoints[0][0]);
    ui.kpiElapsed.textContent = formatDuration(elapsedSec);
  } else if (graphPoints.length >= 2) {
    const startT2 = graphPoints[0][0];
    const endT = currentPoint ? currentPoint[0] : graphPoints[graphPoints.length - 1][0];
    elapsedSec = Math.max(0, endT - startT2);
    ui.kpiElapsed.textContent = formatDuration(elapsedSec);
  } else {
    ui.kpiElapsed.textContent = "—";
  }

  const mppRaw = minutesPerPositionFromWindow();
  const mpp = minutesPerPositionCappedForDwell(mppRaw, pos);
  ui.kpiRate.textContent = formatQueueRate(mpp);
  ui.infoGlobalRate.textContent = formatQueueRate(globalAvgMinutesPerPosition());

  let secRem = estimateSecondsRemaining();
  if (secRem == null && pos != null && mpp != null && mpp > 0) {
    if (pos > 1) secRem = Math.max(0, (pos - 1) * mpp * 60);
    else if (pos === 1) secRem = Math.max(0, mpp * 60);
  }
  ui.kpiRemaining.textContent = secRem == null ? "—" : formatDurationRemaining(secRem);

  let progress = 0;
  if (pos != null && pos <= 1) {
    progress = leftConnectQueueDetected ? 100 : Math.min(99, progressAtFrontEntry ?? 90);
  } else if (elapsedSec != null && secRem != null) {
    const total = elapsedSec + Math.max(0, secRem);
    progress = total > 1e-6 ? Math.min(100, Math.max(0, (100 * elapsedSec) / total)) : 0;
  } else {
    progress = 0;
  }
  const pct = Math.min(100, Math.max(0, progress));
  ui.progressFill.style.width = `${pct.toFixed(1)}%`;
  const pctText = `${pct.toFixed(1)}%`;
  const posText = pos != null ? ` — position ${pos}` : "";
  ui.progressFill.title = `Progress: ${pctText}${posText}`;
  ui.progressFill.setAttribute("aria-label", `Progress: ${pctText}${posText}`);
  if (ui.progressBar) ui.progressBar.title = `Progress: ${pctText}${posText}`;
  if (ui.kpiProgressLabel) ui.kpiProgressLabel.textContent = `PROGRESS (${pctText})`;
}

/**
 * @param {number} position
 * @param {number|null} lineEpoch
 */
function appendGraphPoint(position, lineEpoch) {
  let t = lineEpoch ?? (Date.now() / 1000);
  // Store every queue reading (even if position didn't change) so hover can snap to “minor” updates.
  // Ensure time is strictly increasing to avoid zero-width segments when logs repeat timestamps.
  const lastT = graphPoints.length ? graphPoints[graphPoints.length - 1][0] : null;
  if (lastT != null && t <= lastT) t = lastT + 0.001;

  currentPoint = [t, position];
  lastPosition = position;
  predSpeedScale = 1.0;
  staleSlotsAccounted = 0;
  graphPoints.push(currentPoint);
  if (graphPoints.length > 5000) graphPoints = graphPoints.slice(-5000);
  drawGraph();
}

/**
 * Rebuild graph points from a full log snapshot (first load / truncate resync), matching live poll semantics.
 * @param {string} fullText
 */
function replayQueueGraphFromText(fullText) {
  // Only graph the *current* queue run (avoid cluttering with older reconnect runs).
  const text = sliceLoadedLogToCurrentQueueRun(fullText);
  if (!text) {
    graphPoints = [];
    currentPoint = null;
    lastPosition = null;
    drawGraph();
    return;
  }
  const lines = text.split(/\r?\n/);
  const sessionBeforeLine = queueRunSessionBeforeLine(lines);

  graphPoints = [];
  currentPoint = null;
  lastPosition = null;
  /** @type {number|null} */
  let sessionAtLastEmit = null;

  let lastQueueIdx = -1;
  /** @type {number|null} */
  let lastQueuePos = null;
  /** @type {number|null} */
  let lastQueueEpoch = null;
  /** @type {number|null} */
  let lastQueueSess = null;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (isQueueRunBoundaryLine(line)) continue;

    const rawPos = queuePositionFromLine(line);
    if (rawPos == null) continue;

    lastQueueIdx = i;
    lastQueuePos = rawPos;
    lastQueueEpoch = parseLogTimestampEpoch(line);
    lastQueueSess = sessionBeforeLine[i] ?? lastQueueSess;

    const sess = lastQueueSess;
    let pos = rawPos;

    const prevPos = lastPosition;
    if (
      prevPos != null &&
      sessionAtLastEmit != null &&
      sess != null &&
      sess === sessionAtLastEmit &&
      pos > prevPos &&
      pos - prevPos >= QUEUE_RESET_JUMP_THRESHOLD
    ) {
      pos = prevPos;
    }

    const t = lastQueueEpoch ?? Date.now() / 1000;
    let tt = t;
    const lastT = graphPoints.length ? graphPoints[graphPoints.length - 1][0] : null;
    if (lastT != null && tt <= lastT) tt = lastT + 0.001;
    currentPoint = [tt, pos];
    graphPoints.push(currentPoint);
    if (graphPoints.length > 5000) graphPoints = graphPoints.slice(-5000);
    lastPosition = pos;
    sessionAtLastEmit = sess;
  }

  // If the tail indicates we left the queue after the last queue reading, append a final "0" point once.
  if (lastQueueIdx >= 0 && lastQueuePos != null && lastQueuePos <= 1) {
    let postIdx = -1;
    for (let i = lastQueueIdx + 1; i < lines.length; i++) {
      if (isPostQueueProgressLine(lines[i])) {
        postIdx = i;
        break;
      }
    }
    if (postIdx >= 0) {
      let t0 = parseLogTimestampEpoch(lines[postIdx]);
      if (t0 == null) t0 = (lastQueueEpoch ?? Date.now() / 1000) + 0.25;
      const lastT = graphPoints.length ? graphPoints[graphPoints.length - 1][0] : null;
      if (lastT != null && t0 <= lastT) t0 = lastT + 0.001;
      currentPoint = [t0, 0];
      graphPoints.push(currentPoint);
      if (graphPoints.length > 5000) graphPoints = graphPoints.slice(-5000);
      lastPosition = 0;
    }
  }

  const { session } = parseTailLastQueueReading(text);
  lastQueueRunSession = session;
  drawGraph();
}

/**
 * @param {number|null} prevPos
 * @param {number} currPos
 * @returns {{ should: boolean, reason: string }}
 */
function computeAlert(prevPos, currPos) {
  let thresholds;
  try {
    thresholds = parseAlertThresholds(config.thresholdsRaw);
  } catch {
    return { should: false, reason: "" };
  }
  if (prevPos == null) return { should: false, reason: "" };
  if (prevPos <= 1 && currPos <= 1) return { should: false, reason: "" };
  const jumpUp = currPos - prevPos;
  if (jumpUp >= QUEUE_RESET_JUMP_THRESHOLD) {
    const marginalSpikeFromFront = prevPos <= 1 && jumpUp === QUEUE_RESET_JUMP_THRESHOLD;
    if (!marginalSpikeFromFront) thresholdsFired.clear();
  }
  const crossed = [];
  for (const t of thresholds) {
    if (prevPos > t && currPos <= t && !thresholdsFired.has(t)) {
      crossed.push(t);
      thresholdsFired.add(t);
    }
  }
  if (crossed.length === 0) return { should: false, reason: "" };
  crossed.sort((a, b) => b - a);
  return { should: true, reason: `reached ${crossed.map((t) => `≤${t}`).join(", ")}` };
}

/**
 * @param {number} position
 * @param {string} reason
 */
function raiseAlert(position, reason) {
  const now = Date.now() / 1000;
  if (lastAlertEpoch > 0 && now - lastAlertEpoch < ALERT_MIN_INTERVAL_SEC) return;
  lastAlertEpoch = now;
  if (document.visibilityState !== "visible") setAttentionBadge("!");
  bumpWarningsMarquee(12);
  // If the thresholds overflow the KPI cell, pan to the newly-hit milestone.
  autoPanWarningsToLatestHit();
  const secRem = estimateSecondsRemaining();
  const etaDisplay = secRem == null ? "—" : formatDurationRemaining(secRem);
  const etaPart = secRem == null ? "" : ` Est. remaining ${etaDisplay}.`;
  ui.infoLastAlert.textContent = `${nowStamp()} · pos ${position} · ${reason}`;
  appendHistory(`Threshold alert: position ${position} (${reason})${secRem == null ? "" : `; est. remaining ${etaDisplay}`}`);
  beep("warning");
  if (config.warnNotify) {
    showToast(
      "Threshold reached",
      `Position ${position}. ${reason}.${etaPart}`,
      "warn",
      { durationMs: 9000 },
    );
    notifyDesktop(
      "threshold",
      "Threshold reached",
      secRem == null
        ? `Position ${position}. ${reason}.`
        : `Position ${position}. ${reason}. About ${etaDisplay} left.`,
    );
  }
}

/**
 * @param {number} position
 * @param {string} tailText
 */
function maybeNotifyCompletion(position, tailText) {
  if (position !== 0) return;
  if (!tailHasPostQueueAfterLastQueueLine(tailText)) return;
  if (completionNotifiedThisRun) return;
  const now = Date.now() / 1000;
  if (lastCompletionNotifyEpoch > 0 && now - lastCompletionNotifyEpoch < COMPLETION_NOTIFY_MIN_INTERVAL_SEC) return;
  const wantSound = !!config.completionSound;
  const wantPopup = !!config.completionNotify;
  if (!wantSound && !wantPopup) return;
  completionNotifiedThisRun = true;
  lastCompletionNotifyEpoch = now;
  appendHistory("Queue completion: past queue wait — connecting (position 0).");
  ui.infoLastAlert.textContent = `${nowStamp()} · queue complete`;
  if (document.visibilityState !== "visible") setAttentionBadge("✓");
  beep("completion");
  if (wantPopup) {
    const msg = "Past queue wait detected — connecting or loading.";
    showToast("Queue complete", msg, "ok", { durationMs: 14000 });
    notifyDesktop("completion", "Queue complete", msg);
  }
}

function hideInterruptAdoptModal() {
  if (!ui.interruptAdoptOverlay) return;
  interruptAdoptModalVisible = false;
  ui.interruptAdoptOverlay.hidden = true;
}

function showInterruptAdoptModal() {
  if (!ui.interruptAdoptOverlay || !ui.interruptAdoptDetail) return;
  interruptAdoptModalVisible = true;
  const s = interruptAdoptPendingSession;
  const p = interruptAdoptPendingPosition;
  ui.interruptAdoptDetail.textContent = `A new connect-queue run appears in the log (session ${s ?? "?"}, position ${p ?? "—"}). Adopt it to clear the graph and reset alerts for this run, or stay interrupted to keep the previous graph until you decide.`;
  ui.interruptAdoptOverlay.hidden = false;
}

/**
 * @param {number} session
 * @param {number|null} lastPos
 */
function offerInterruptAdoptIfNeeded(session, lastPos) {
  if (interruptAdoptModalVisible) return;
  if (interruptAdoptDeclinedSession === session) return;
  interruptAdoptPendingSession = session;
  interruptAdoptPendingPosition = lastPos;
  showInterruptAdoptModal();
}

/**
 * @param {number} session
 */
function applyInterruptAdopt(session) {
  hideInterruptAdoptModal();
  interruptedMode = false;
  interruptedElapsedSec = null;
  frozenRatesAtInterrupt = null;
  sessionAtInterrupt = null;
  interruptAdoptDeclinedSession = null;
  thresholdsFired.clear();
  positionOneReachedAt = null;
  connectPhaseStartedEpoch = null;
  progressAtFrontEntry = null;
  leftConnectQueueDetected = false;
  completionNotifiedThisRun = false;
  lastQueuePositionChangeEpoch = Date.now() / 1000;
  mppFloorPosition = null;
  mppFloorValue = null;
  graphPoints = [];
  currentPoint = null;
  lastPosition = null;
  pendingGraphReplayText = null;
  const slice = sliceLoadedLogToCurrentQueueRun(logBuffer);
  replayQueueGraphFromText(slice);
  lastQueueRunSession = session;
  setStatus("Monitoring");
  appendHistory("Adopted new queue run after interrupt — graph and alerts re-seeded for this run.");
  drawGraph();
  refreshWarningsKpi();
  updateTimeEstimates();
}

/**
 * @param {string} detail
 */
function enterInterruptedState(detail) {
  if (interruptedMode) return;
  interruptedMode = true;
  sessionAtInterrupt = lastQueueRunSession;
  interruptedElapsedSec = snapshotElapsedSecondsAtInterrupt();
  frozenRatesAtInterrupt = [ui.kpiRate.textContent, ui.infoGlobalRate.textContent];
  setStatus("Interrupted", true);
  appendHistory(`Queue interrupted; still watching the log. (${detail})`);

  // Separate alert channel for disconnects/interrupts.
  if (document.visibilityState !== "visible") setAttentionBadge("×");
  notifyDesktop("interrupt", "VS Queue Monitor — interrupted", detail);
  beep("interrupt");
}

function snapshotElapsedSecondsAtInterrupt() {
  const startT = queueElapsedStartEpoch();
  if (startT == null) return null;
  const pos = currentQueuePosition();
  if (pos != null && pos <= 1 && positionOneReachedAt != null) return Math.max(0, positionOneReachedAt - startT);
  return Math.max(0, (Date.now() / 1000) - startT);
}

async function bumpLogActivityIfChanged() {
  if (!logFileHandle) return;
  try {
    const f = await logFileHandle.getFile();
    const size = f.size;
    const mtime = f.lastModified;
    const key = { size, mtime };
    if (!lastLogStat || lastLogStat.size !== key.size || lastLogStat.mtime !== key.mtime) {
      lastLogStat = key;
      lastLogGrowthEpoch = Date.now() / 1000;
    } else if (lastLogGrowthEpoch == null) {
      lastLogGrowthEpoch = Date.now() / 1000;
    }
  } catch {
    // ignore
  }
}

function appendToLogBuffer(text) {
  if (!text) return;
  logBuffer += text;
  if (logBuffer.length > BUFFER_MAX_CHARS) logBuffer = logBuffer.slice(-BUFFER_MAX_CHARS);
}

async function readNewLogText(handle) {
  const file = await handle.getFile();
  const size = file.size;

  // First read: load full file when reasonable so we can replay the full queue graph; then set offset to EOF.
  if (lastReadOffset == null) {
    let seed;
    if (size <= INITIAL_FULL_READ_MAX_BYTES) {
      seed = await readLogRangeText(handle, 0, size);
    } else {
      // Large logs: start with a tail window, but walk backward a little if the current queue run
      // appears to start before the loaded chunk (e.g. you started at 47 but the tail begins later).
      const maxWalkBack = Math.max(INITIAL_FULL_READ_MAX_BYTES * 3, 32 * 1024 * 1024); // cap extra reads
      let start = Math.max(0, size - INITIAL_FULL_READ_MAX_BYTES);
      let span = size - start;
      seed = await readLogRangeText(handle, start, size);
      appendHistory(
        `Large log (${(size / (1024 * 1024)).toFixed(1)} MB); loaded last ${(INITIAL_FULL_READ_MAX_BYTES / (1024 * 1024)).toFixed(0)} MB for history and graph.`,
      );
      // If the current run slice begins at the chunk start, we likely missed earlier lines for this run.
      // Walk back (up to a cap) to capture the beginning of the active run.
      for (let attempts = 0; attempts < 3; attempts++) {
        const meta = sliceLoadedLogToCurrentQueueRunMeta(seed);
        if (meta.lastQIdx < 0) break;
        if (meta.startIdx > 0) break;
        if (start <= 0) break;
        const add = Math.min(INITIAL_FULL_READ_MAX_BYTES, maxWalkBack - span);
        if (add <= 0) break;
        const newStart = Math.max(0, start - add);
        if (newStart === start) break;
        start = newStart;
        span = size - start;
        seed = await readLogRangeText(handle, start, size);
      }
    }
    const rawLen = seed.length;
    const meta = sliceLoadedLogToCurrentQueueRunMeta(seed);
    seed = meta.slice;
    if (seed.length < rawLen) appendHistory("Graph: current queue run only (older reconnect runs omitted).");
    lastReadOffset = size;
    pendingGraphReplayText = seed;
    return seed;
  }

  // Truncation / rotation: file got smaller, reset and reload window for replay.
  if (size < lastReadOffset) {
    let seed;
    if (size <= INITIAL_FULL_READ_MAX_BYTES) {
      seed = await readLogRangeText(handle, 0, size);
    } else {
      const start = Math.max(0, size - INITIAL_FULL_READ_MAX_BYTES);
      seed = await readLogRangeText(handle, start, size);
    }
    appendHistory("Log file size decreased (truncated/rotated). Resynced tail.");
    const rawLenT = seed.length;
    const metaT = sliceLoadedLogToCurrentQueueRunMeta(seed);
    seed = metaT.slice;
    if (seed.length < rawLenT) appendHistory("Graph: current queue run only (older reconnect runs omitted).");
    lastReadOffset = size;
    pendingGraphReplayText = seed;
    return seed;
  }

  if (size === lastReadOffset) return "";

  // Read only appended bytes, with a cap to avoid huge spikes.
  const start = lastReadOffset;
  const end = Math.min(size, start + MAX_READ_BYTES_PER_POLL);
  const chunk = await readLogRangeText(handle, start, end);
  lastReadOffset = end;

  if (end < size) {
    appendHistory(
      `Log grew quickly; read ${MAX_READ_BYTES_PER_POLL} bytes this poll and will continue next poll.`,
    );
  }
  return chunk;
}

async function pollOnce() {
  if (!running) return;
  if (!logFileHandle) {
    setStatus("Waiting for log file", false);
    return;
  }

  try {
    updateTimeEstimates();
    await bumpLogActivityIfChanged();
    const newText = await readNewLogText(logFileHandle);
    const replayChunk = pendingGraphReplayText;
    pendingGraphReplayText = null;
    if (newText) appendToLogBuffer(newText);
    if (newText && /[\r\n]/.test(newText)) pulseLogActivityLed();
    if (replayChunk != null) replayQueueGraphFromText(replayChunk);
    const viewRaw = logBuffer || "";
    // Always reason about the current queue run only (avoid spanning multiple reconnect sessions).
    const view = sliceLoadedLogToCurrentQueueRun(viewRaw);
    const { kind } = classifyTailConnectionState(view);
    const { lastPos, session } = parseTailLastQueueReading(view);
    const lastLineEpoch = parseTailLastQueueLineEpoch(view);
    if (lastLineEpoch != null) lastQueueLineEpoch = lastLineEpoch;
    const left = tailHasPostQueueAfterLastQueueLine(view);
    const now = Date.now() / 1000;
    const logSilent = lastLogGrowthEpoch != null && now - lastLogGrowthEpoch >= LOG_SILENCE_RECONNECT_SEC;
    const staleLimit = QUEUE_UPDATE_INTERVAL_SEC * QUEUE_STALE_TIMEOUT_MULT;

    if (interruptedMode) {
      if (lastQueueLineEpoch != null && now - lastQueueLineEpoch <= staleLimit && kind === "queue" && lastPos != null) {
        if (sessionAtInterrupt === null) {
          interruptedMode = false;
          interruptedElapsedSec = null;
          frozenRatesAtInterrupt = null;
          sessionAtInterrupt = null;
          interruptAdoptDeclinedSession = null;
          hideInterruptAdoptModal();
          setStatus("Monitoring");
          appendHistory("Recovered from interrupted state (queue lines resumed).");
        } else if (session > sessionAtInterrupt) {
          offerInterruptAdoptIfNeeded(session, lastPos);
          return;
        } else {
          interruptedMode = false;
          interruptedElapsedSec = null;
          frozenRatesAtInterrupt = null;
          sessionAtInterrupt = null;
          interruptAdoptDeclinedSession = null;
          hideInterruptAdoptModal();
          setStatus("Monitoring");
          appendHistory("Recovered from interrupted state (queue lines resumed).");
        }
      } else {
        return;
      }
    }

    if (!interruptedMode && kind === "disconnected") {
      enterInterruptedState("Connection lost (final teardown).");
      leftConnectQueueDetected = false;
      positionOneReachedAt = null;
      connectPhaseStartedEpoch = null;
      setPositionDisplay(null);
      lastPosition = null;
      return;
    }

    if (!interruptedMode && (kind === "reconnecting" || kind === "grace" || logSilent) && !(lastPos != null && lastPos <= 1)) {
      // Do not wipe rate/progress history just because the tail is temporarily in a connecting/reconnecting phase.
      // We still want ETA/rate/progress to remain stable using existing graphPoints until we truly detect a new run or a disconnect.
      setStatus(logSilent || kind === "grace" ? "Reconnecting…" : "Connecting…");
      setPositionDisplay(lastPosition);
      return;
    }

    if (!interruptedMode && lastPos != null && (!logSilent || lastPos <= 1)) {
      const prevPos = lastPosition;
      let pos = lastPos;

      if (prevPos != null && pos > prevPos && pos - prevPos >= QUEUE_RESET_JUMP_THRESHOLD) {
        pos = prevPos;
      }

      if (pos <= 1 && left) pos = 0;

      // Ensure we don't span multiple queue runs: if the *start* of the current-run slice moves forward,
      // treat it as a new run even if the session counter didn't increment.
      const runStart = parseFirstQueueLineEpoch(view);
      if (currentQueueRunStartEpoch == null) currentQueueRunStartEpoch = runStart;
      else if (runStart != null && runStart > currentQueueRunStartEpoch + 1) {
        thresholdsFired.clear();
        positionOneReachedAt = null;
        connectPhaseStartedEpoch = null;
        progressAtFrontEntry = null;
        leftConnectQueueDetected = false;
        completionNotifiedThisRun = false;
        lastQueuePositionChangeEpoch = now;
        mppFloorPosition = null;
        mppFloorValue = null;
        graphPoints = [];
        currentPoint = null;
        lastPosition = null;
        pendingGraphReplayText = null;
        appendHistory("New queue run detected — graph and alerts reset for this run.");

        replayQueueGraphFromText(view);
        lastQueueRunSession = session;
        currentQueueRunStartEpoch = runStart;
        refreshWarningsKpi();
        updateTimeEstimates();
        return;
      }

      if (pos > 1) {
        leftConnectQueueDetected = false;
        progressAtFrontEntry = null;
        completionNotifiedThisRun = false;
        if (prevPos == null || pos !== prevPos) {
          lastQueuePositionChangeEpoch = now;
        } else if (lastQueuePositionChangeEpoch == null) {
          lastQueuePositionChangeEpoch = now;
        }

        if (lastQueueLineEpoch == null || now - lastQueueLineEpoch > staleLimit) {
          enterInterruptedState(`No new queue log lines for ~${staleLimit.toFixed(0)}s (stale).`);
          return;
        }
      } else {
        lastQueuePositionChangeEpoch = null;
      }

      if (prevPos != null && prevPos > 1 && pos <= 1) {
        const w = Number.parseFloat(String(ui.progressFill.style.width || "").replace("%", ""));
        progressAtFrontEntry = Number.isFinite(w) ? Math.min(99, Math.max(0, w)) : 95;
      }

      if (pos === 0) leftConnectQueueDetected = true;
      else if (pos <= 1) leftConnectQueueDetected = false;

      // New run detection: session counter in tail (best-effort)
      if (lastQueueRunSession != null && session > lastQueueRunSession) {
        thresholdsFired.clear();
        positionOneReachedAt = null;
        connectPhaseStartedEpoch = null;
        progressAtFrontEntry = null;
        leftConnectQueueDetected = false;
        completionNotifiedThisRun = false;
        lastQueuePositionChangeEpoch = now;
        mppFloorPosition = null;
        mppFloorValue = null;
        // Clear graph/rate history so window-based metrics don't span runs.
        graphPoints = [];
        currentPoint = null;
        lastPosition = null;
        pendingGraphReplayText = null;
        appendHistory("New queue run (from log) — graph and alerts reset for this run.");

        // Reseed the graph from the current run slice so the user sees immediate context.
        replayQueueGraphFromText(view);
        lastQueueRunSession = session;
        currentQueueRunStartEpoch = runStart;
        refreshWarningsKpi();
        updateTimeEstimates();
        return;
      }
      lastQueueRunSession = session;

      if (pos === 0) setStatus("Completed");
      else if (pos <= 1) setStatus("At front");
      else setStatus("Monitoring");

      setPositionDisplay(pos);
      if (pos <= 1 && positionOneReachedAt == null) positionOneReachedAt = lastLineEpoch ?? now;

      // If multiple queue readings arrived since the last poll, append them all so the graph doesn't "jump".
      const deltaReadings = newText ? extractQueueReadingsFromText(newText) : [];
      if (deltaReadings.length >= 2) {
        let lastEpoch = graphPoints.length ? graphPoints[graphPoints.length - 1][0] : null;
        let lastAppendedPos = graphPoints.length ? graphPoints[graphPoints.length - 1][1] : null;
        for (const r of deltaReadings) {
          let t = r.epoch;
          if (t == null) t = (lastEpoch != null ? lastEpoch + 0.25 : Date.now() / 1000);
          // Ensure monotonic times for the segment builder.
          if (lastEpoch != null && t <= lastEpoch) t = lastEpoch + 0.001;
          appendGraphPoint(r.pos, t);
          lastEpoch = t;
          lastAppendedPos = r.pos;
        }

        // Ensure the *final* point matches the computed current position (e.g. 0 when post-queue is detected).
        if (pos !== lastAppendedPos) {
          const tFinal =
            pos === 0
              ? (parseFirstPostQueueEpochAfterLastQueueLine(view) ?? lastLineEpoch ?? now)
              : (lastLineEpoch ?? now);
          appendGraphPoint(pos, tFinal);
        }
      } else {
        appendGraphPoint(pos, lastLineEpoch);
      }
      try {
        updateTimeEstimates();

        if (pos !== prevPos) {
          ui.infoLastChange.textContent = nowStamp();
          mppFloorPosition = pos;
          mppFloorValue = minutesPerPositionFromWindow();
          if (config.logEveryChange) {
            if (prevPos == null) appendHistory(`Queue position: ${pos}`);
            else appendHistory(`Queue changed: ${prevPos} → ${pos}`);
          }
        }

        const { should, reason } = computeAlert(prevPos, pos);
        if (should) raiseAlert(pos, reason);
        maybeNotifyCompletion(pos, view);
        refreshWarningsKpi();
      } catch (e) {
        appendHistory(`Non-fatal: ${String(e)}`);
      }
      return;
    }

    setStatus("Warning: no queue detected", true);
  } catch (e) {
    setStatus("Error", true);
    appendHistory(`Error: ${String(e)}`);
  }
}

/** After a successful file/folder pick: begin (or restart) tailing the new handle. */
function startMonitoringAfterSuccessfulPick() {
  if (running) stopMonitoring();
  startMonitoring();
}

/** @param {boolean} isRunning */
function setLogActivityMonitoring(on) {
  const w = ui.logActivityWrap;
  const led = ui.logActivityLed;
  if (!w || !led) return;
  if (on) {
    w.hidden = false;
    led.classList.add("logActivityLed--armed");
  } else {
    w.hidden = true;
    led.classList.remove("logActivityLed--armed", "logActivityLed--pulse");
  }
}

function pulseLogActivityLed() {
  const el = ui.logActivityLed;
  if (!el || !running) return;
  // The graph scrolls each tick; keep the indicator subtle (no pulse).
}

function setStartStopButtonLook(isRunning) {
  ui.btnStartStop.textContent = isRunning ? "Stop" : "Start";
  ui.btnStartStop.classList.toggle("btn--primary", !isRunning);
  ui.btnStartStop.classList.toggle("btn--stop", isRunning);
  ui.btnStartStop.setAttribute("aria-pressed", isRunning ? "true" : "false");
  ui.btnStartStop.title = isRunning ? "Stop tailing the log" : "Start tailing the log";
}

function startMonitoring() {
  if (!logFileHandle) return;
  if (running) return;
  running = true;
  monitorStartEpoch = Date.now() / 1000;
  setStatus("Monitoring");
  setStartStopButtonLook(true);
  ui.btnPickLog.disabled = true;
  thresholdsFired.clear();
  completionNotifiedThisRun = false;
  interruptedMode = false;
  interruptedElapsedSec = null;
  frozenRatesAtInterrupt = null;
  sessionAtInterrupt = null;
  interruptAdoptDeclinedSession = null;
  hideInterruptAdoptModal();
  lastQueueRunSession = null;
  appendHistory("Monitoring started.");
  setLogActivityMonitoring(true);

  if (pollTimer != null) window.clearInterval(pollTimer);
  pollTimer = window.setInterval(() => pollOnce(), Math.max(200, config.pollSec * 1000));
  if (estimateTimer != null) window.clearInterval(estimateTimer);
  estimateTimer = window.setInterval(() => updateTimeEstimates(), 100);
  if (graphRealtimeTimer != null) window.clearInterval(graphRealtimeTimer);
  graphRealtimeTimer = window.setInterval(() => {
    if (running && config.graphLiveWindow && graphPoints.length > 0) scheduleDrawGraph();
  }, 250);
  pollOnce();
}

function stopMonitoring() {
  running = false;
  setLogActivityMonitoring(false);
  setStartStopButtonLook(false);
  ui.btnPickLog.disabled = false;
  if (pollTimer != null) window.clearInterval(pollTimer);
  pollTimer = null;
  if (estimateTimer != null) window.clearInterval(estimateTimer);
  estimateTimer = null;
  if (graphRealtimeTimer != null) window.clearInterval(graphRealtimeTimer);
  graphRealtimeTimer = null;
  hideInterruptAdoptModal();
  setStatus(leftConnectQueueDetected ? "Completed" : "Stopped", false);
  appendHistory("Monitoring stopped.");
}

// -----------------------------
// Graph (canvas)
// -----------------------------

function graphHintDefaultText() {
  if (graphPoints.length < 1) {
    return "Pick a log file to start monitoring. The graph will fill as queue positions change.";
  }
  return config.graphLogScale ? "Y scale: log" : "Y scale: linear";
}

/**
 * @param {number} tSec
 */
function formatGraphHoverTime(tSec) {
  try {
    return new Date(tSec * 1000).toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  } catch {
    return String(tSec);
  }
}

/** Short time for X-axis ticks (Grafana-style compact axis). */
function formatGraphXTick(tSec) {
  try {
    return new Date(tSec * 1000).toLocaleTimeString(undefined, {
      hour: "2-digit",
      minute: "2-digit",
      second: "2-digit",
    });
  } catch {
    return "";
  }
}

/**
 * @param {number} clientX
 * @param {number} clientY
 * @returns {GraphPoint|null}
 */
function hitTestGraphPoint(clientX, clientY) {
  const layout = lastGraphLayout;
  if (!layout || graphPoints.length < 1) return null;
  const canvas = ui.graphCanvas;
  const rect = canvas.getBoundingClientRect();
  const scaleX = canvas.width / rect.width;
  const scaleY = canvas.height / rect.height;
  const mx = (clientX - rect.left) * scaleX;
  const my = (clientY - rect.top) * scaleY;
  const { padL, padR, padT, padB, plotW, plotH, w, h, t1, span } = layout;
  if (mx < padL || mx > w - padR || my < padT || my > h - padB) return null;
  const xOf = (t) => padL + ((t - t1 + span) / span) * plotW;
  /** @type {GraphPoint|null} */
  let best = null;
  let bestD = Infinity;
  for (let i = 0; i < graphPoints.length; i++) {
    const d = Math.abs(xOf(graphPoints[i][0]) - mx);
    if (d < bestD) {
      bestD = d;
      best = graphPoints[i];
    }
  }
  // No snapping: only “pick up” a point when the cursor is actually near a real update.
  // `bestD` is in *canvas* pixels; use a CSS-pixel radius and scale it so hover works on HiDPI.
  const HIT_CSS_PX = 8;
  const HIT_PX = HIT_CSS_PX * Math.max(1, Math.min(scaleX, scaleY));
  if (best && bestD <= HIT_PX) return best;
  return null;
}

function graphYMap(pos, minP, maxP, h) {
  const padTop = 22;
  const padBot = 46;
  const plotH = h - padTop - padBot;
  const clamp = (v) => Math.max(0, Math.min(1, v));
  if (config.graphLogScale) {
    const p = Math.max(0, pos);
    const a = Math.log1p(Math.max(0, minP));
    const b = Math.log1p(Math.max(0, maxP));
    const v = Math.log1p(p);
    const t = b - a <= 1e-9 ? 0.5 : clamp((v - a) / (b - a));
    return padTop + (1 - t) * plotH;
  }
  const t = maxP - minP <= 1e-9 ? 0.5 : Math.max(0, Math.min(1, (pos - minP) / (maxP - minP)));
  return padTop + (1 - t) * plotH;
}

function drawGraph() {
  const c = ui.graphCanvas;
  const ctx = c.getContext("2d");
  if (!ctx) return;
  const w = c.width;
  const h = c.height;

  ctx.clearRect(0, 0, w, h);
  const bgGrad = ctx.createLinearGradient(0, 0, 0, h);
  bgGrad.addColorStop(0, "rgba(18,22,32,0.98)");
  bgGrad.addColorStop(0.55, "rgba(10,13,20,0.98)");
  bgGrad.addColorStop(1, "rgba(6,8,12,0.99)");
  ctx.fillStyle = bgGrad;
  ctx.fillRect(0, 0, w, h);

  if (graphPoints.length < 1) {
    lastGraphLayout = null;
    ui.graphHint.textContent = graphHintDefaultText();
    return;
  }
  if (!graphCanvasHovering) ui.graphHint.textContent = graphHintDefaultText();

  const padL = 56;
  const padR = 20;
  const padT = 22;
  const padB = 46;
  const plotW = w - padL - padR;
  const plotH = h - padT - padB;
  const plotBottom = padT + plotH;

  // Time range
  const tLast = graphPoints[graphPoints.length - 1][0];
  const tNow = Date.now() / 1000;
  // Live view = keep the X-axis advancing so the full-history timeline keeps stretching (constant motion).
  const t1 = config.graphLiveWindow && running ? Math.max(tLast, tNow) : tLast;
  const span = Math.max(60, t1 - graphPoints[0][0]);
  const t0 = t1 - span;
  const xOf = (t) => padL + ((t - t0) / span) * plotW;

  // Range: always full-history (live view only affects X-axis motion).
  const positions = graphPoints.map((p) => p[1]);
  let minP = Math.min(...positions);
  let maxP = Math.max(...positions);
  if (!Number.isFinite(minP) || !Number.isFinite(maxP)) {
    lastGraphLayout = null;
    return;
  }
  if (minP === maxP) {
    minP = Math.max(0, minP - 1);
    maxP = maxP + 1;
  }

  const mono = getComputedStyle(document.documentElement).getPropertyValue("--mono").trim() || "ui-monospace, monospace";

  // Grids (horizontal + vertical, Grafana-style readability)
  const yTickCount = 5;
  const xTickCount = 5;
  ctx.lineWidth = 1;

  // Horizontal gridlines + Y labels that match the active scale.
  const yTicks = [];
  if (config.graphLogScale) {
    const a = Math.log1p(Math.max(0, minP));
    const b = Math.log1p(Math.max(0, maxP));
    for (let i = 0; i <= yTickCount; i++) {
      const frac = i / yTickCount; // 0 top → 1 bottom
      const v = Math.expm1(b - frac * (b - a));
      yTicks.push(Math.max(0, Math.round(v)));
    }
  } else {
    for (let i = 0; i <= yTickCount; i++) {
      const frac = i / yTickCount; // 0 top → 1 bottom
      const v = maxP - frac * (maxP - minP);
      yTicks.push(Math.round(v));
    }
  }
  // De-dupe while keeping order (log rounding can create repeats).
  const seen = new Set();
  const yTickVals = yTicks.filter((v) => {
    if (seen.has(v)) return false;
    seen.add(v);
    return true;
  });

  ctx.strokeStyle = "rgba(55,65,82,0.36)";
  for (let i = 0; i < yTickVals.length; i++) {
    const val = yTickVals[i];
    const y = graphYMap(val, minP, maxP, h);
    const strong = i === 0 || i === yTickVals.length - 1;
    ctx.strokeStyle = strong ? "rgba(55,65,82,0.62)" : "rgba(55,65,82,0.36)";
    ctx.beginPath();
    ctx.moveTo(padL, y);
    ctx.lineTo(w - padR, y);
    ctx.stroke();
  }

  // Y-axis tick labels (every other tick, plus ends).
  ctx.fillStyle = "rgba(155,165,176,0.92)";
  ctx.font = "12px " + mono;
  ctx.textAlign = "right";
  ctx.textBaseline = "middle";
  for (let i = 0; i < yTickVals.length; i++) {
    if (!(i === 0 || i === yTickVals.length - 1 || i % 2 === 0)) continue;
    const val = yTickVals[i];
    const y = graphYMap(val, minP, maxP, h);
    ctx.fillText(String(val), padL - 8, y);
  }

  for (let i = 0; i <= xTickCount; i++) {
    const x = padL + (i / xTickCount) * plotW;
    ctx.strokeStyle = i === 0 || i === xTickCount ? "rgba(55,65,82,0.42)" : "rgba(55,65,82,0.2)";
    ctx.beginPath();
    ctx.moveTo(x, padT);
    ctx.lineTo(x, plotBottom);
    ctx.stroke();
  }

  // Panel frame
  ctx.strokeStyle = "rgba(46,55,66,0.95)";
  ctx.lineWidth = 1;
  ctx.strokeRect(padL - 0.5, padT - 0.5, plotW + 1, plotH + 1);

  // Y-axis title
  ctx.save();
  ctx.fillStyle = "rgba(130,140,155,0.85)";
  ctx.font = "10px " + mono;
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  ctx.translate(12, padT + plotH / 2);
  ctx.rotate(-Math.PI / 2);
  ctx.fillText("Position", 0, 0);
  ctx.restore();

  function traceStepLine() {
    for (let i = 0; i < graphPoints.length; i++) {
      const [t, p] = graphPoints[i];
      const x = xOf(t);
      const y = graphYMap(p, minP, maxP, h);
      if (i === 0) ctx.moveTo(x, y);
      else {
        const [, pPrev] = graphPoints[i - 1];
        const yPrev = graphYMap(pPrev, minP, maxP, h);
        ctx.lineTo(x, yPrev);
        ctx.lineTo(x, y);
      }
    }
  }

  // Gradient area under the step series
  if (graphPoints.length >= 2) {
    const gradFill = ctx.createLinearGradient(0, padT, 0, plotBottom);
    gradFill.addColorStop(0, "rgba(100,168,255,0.24)");
    gradFill.addColorStop(1, "rgba(100,168,255,0.03)");
    const [t0, p0] = graphPoints[0];
    const x0 = xOf(t0);
    const y0 = graphYMap(p0, minP, maxP, h);
    ctx.beginPath();
    ctx.moveTo(x0, plotBottom);
    ctx.lineTo(x0, y0);
    for (let i = 1; i < graphPoints.length; i++) {
      const [t, p] = graphPoints[i];
      const [, pPrev] = graphPoints[i - 1];
      const x = xOf(t);
      const y = graphYMap(p, minP, maxP, h);
      const yPrev = graphYMap(pPrev, minP, maxP, h);
      ctx.lineTo(x, yPrev);
      ctx.lineTo(x, y);
    }
    const xLast = xOf(graphPoints[graphPoints.length - 1][0]);
    ctx.lineTo(xLast, plotBottom);
    ctx.closePath();
    ctx.fillStyle = gradFill;
    ctx.fill();
  }

  ctx.strokeStyle = "rgba(100,168,255,0.92)";
  ctx.lineWidth = 2;
  ctx.beginPath();
  traceStepLine();
  ctx.stroke();

  // Current marker
  const last = graphPoints[graphPoints.length - 1];
  const xm = xOf(last[0]);
  const ym = graphYMap(last[1], minP, maxP, h);
  ctx.fillStyle = "rgba(130,200,255,0.98)";
  ctx.beginPath();
  ctx.arc(xm, ym, 4.5, 0, Math.PI * 2);
  ctx.fill();

  // Hover marker (snaps to nearest point)
  if (graphCanvasHovering && graphHoverPoint) {
    const xh = xOf(graphHoverPoint[0]);
    const yh = graphYMap(graphHoverPoint[1], minP, maxP, h);
    ctx.fillStyle = "rgba(255,255,255,0.92)";
    ctx.beginPath();
    ctx.arc(xh, yh, 3.6, 0, Math.PI * 2);
    ctx.fill();
    ctx.strokeStyle = "rgba(100,168,255,0.85)";
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.arc(xh, yh, 5.2, 0, Math.PI * 2);
    ctx.stroke();
  }

  // Hover crosshair (vertical, scoped to plot)
  if (graphCanvasHovering && graphHoverCanvasX != null) {
    const cx = Math.max(padL, Math.min(w - padR, graphHoverCanvasX));
    ctx.strokeStyle = "rgba(200,210,230,0.4)";
    ctx.lineWidth = 1;
    ctx.setLineDash([3, 4]);
    ctx.beginPath();
    ctx.moveTo(cx, padT);
    ctx.lineTo(cx, plotBottom);
    ctx.stroke();
    ctx.setLineDash([]);
  }

  // X-axis time ticks
  ctx.fillStyle = "rgba(130,140,155,0.88)";
  ctx.font = "10px " + mono;
  ctx.textAlign = "center";
  ctx.textBaseline = "top";
  for (let i = 0; i <= xTickCount; i++) {
    const frac = i / xTickCount;
    const tTick = t0 + frac * span;
    const x = padL + frac * plotW;
    ctx.fillText(formatGraphXTick(tTick), x, plotBottom + 4);
  }

  lastGraphLayout = { padL, padR, padT, padB, plotW, plotH, w, h, t1, span, minP, maxP };
}

// -----------------------------
// Wire up UI
// -----------------------------

loadConfig();
syncConfigToForm();
void syncSoundSummaries();
void warmDefaultSoundsCache();
setStatus("Idle");
refreshWarningsKpi();
// On first paint, center the next upcoming (pending) threshold.
queueMicrotask(() => requestAnimationFrame(() => focusUpcomingWarningOnLoad()));
appendHistory(
  "VS Queue Monitor (web) ready. Pick your client log to start monitoring (or use Stop / Start to pause and resume). The last session can restore automatically when permitted.",
);
window.addEventListener(
  "load",
  () => {
    queueMicrotask(() => void tryRestoreLastLogOnLoad());
  },
  { once: true },
);
wireHelpOverlay();
wireSettingsOverlay();
startUpdateCheckLoop();

// Tutorial wiring (first run).
(() => {
  ui.btnTutorialHelp?.addEventListener("click", () => openPickerFixGuide());
  ui.btnTutorialSkip?.addEventListener("click", () => closeTutorial(true));
  ui.btnTutorialBack?.addEventListener("click", () => tutorialSetStep(tutorialStepIdx - 1));
  ui.btnTutorialNext?.addEventListener("click", () => {
    if (tutorialStepIdx === 4) {
      // Complete tutorial: start monitoring now (if a log was selected).
      if (tutorialHasLogSelected()) startMonitoringAfterSuccessfulPick();
      closeTutorial(true);
      showToast("Tutorial complete", "Monitoring started. You can adjust WARNINGS and RATE any time.", "ok", { durationMs: 8000 });
      return;
    }
    tutorialSetStep(tutorialStepIdx + 1);
  });

  // Auto-open on first run.
  try {
    if (!isTutorialDone()) {
      // If a log is already restored automatically (rare), still show tutorial but allow skipping.
      openTutorial(true);
    }
  } catch {
    // ignore
  }
})();

(() => {
  const viewport = ui.kpiWarnings?.querySelector(".kpiWarn__viewport");
  if (!viewport || typeof ResizeObserver === "undefined") return;
  const ro = new ResizeObserver(() => syncWarningsMarquee());
  ro.observe(viewport);
})();

// Warnings: allow side-scroll on wheel/trackpad when hovered.
(() => {
  const viewport = ui.kpiWarnings?.querySelector(".kpiWarn__viewport");
  if (!viewport) return;
  viewport.addEventListener("scroll", () => syncWarningsArrowState(), { passive: true });
  viewport.addEventListener(
    "wheel",
    (e) => {
      // Prefer explicit horizontal deltas when present; otherwise map vertical wheel to horizontal pan.
      const dx = Math.abs(e.deltaX) > 0.5 ? e.deltaX : e.deltaY;
      if (!dx) return;
      const before = viewport.scrollLeft;
      viewport.scrollLeft += dx;
      if (viewport.scrollLeft !== before) e.preventDefault();
      syncWarningsArrowState();
    },
    { passive: false },
  );
})();

(() => {
  const viewport = ui.kpiWarnings?.querySelector(".kpiWarn__viewport");
  if (!viewport) return;
  const step = () => Math.max(80, Math.round(viewport.clientWidth * 0.55));
  ui.btnWarnScrollL?.addEventListener("click", () => {
    viewport.scrollBy({ left: -step(), behavior: "smooth" });
    window.setTimeout(() => syncWarningsArrowState(), 220);
  });
  ui.btnWarnScrollR?.addEventListener("click", () => {
    viewport.scrollBy({ left: step(), behavior: "smooth" });
    window.setTimeout(() => syncWarningsArrowState(), 220);
  });
})();

let _warningsEditorPrev = "";
function openWarningsAddPopover() {
  if (!ui.warningsAddPopover) return;
  _warningsEditorPrev = String(config.thresholdsRaw || "");
  ui.inpWarningsAdd.value = _warningsEditorPrev;
  ui.warningsAddPopover.hidden = false;
  try {
    ui.inpWarningsAdd.focus();
    ui.inpWarningsAdd.select();
  } catch {
    // ignore
  }
}

function closeWarningsAddPopover() {
  if (!ui.warningsAddPopover) return;
  ui.warningsAddPopover.hidden = true;
}

// Warnings editor is a simple CSV input popover (see index.html).

function updateThresholdsFromList(list) {
  const uniq = [...new Set(list.filter((n) => Number.isFinite(n) && n >= 1))];
  uniq.sort((a, b) => b - a);
  config.thresholdsRaw = uniq.join(", ");
  if (ui.inpThresholds) ui.inpThresholds.value = config.thresholdsRaw;
  saveConfig();
  refreshWarningsKpi();
}

function normalizeThresholdInput(raw) {
  const s = String(raw ?? "").replaceAll(",", " ");
  const parts = s.split(/\s+/).map((x) => x.trim()).filter(Boolean);
  /** @type {number[]} */
  const out = [];
  for (const p of parts) {
    const n = Number.parseInt(p, 10);
    if (!Number.isFinite(n)) continue;
    if (n >= 1) out.push(n);
  }
  const uniq = [...new Set(out)];
  uniq.sort((a, b) => b - a);
  return { list: uniq, normalized: uniq.join(", ") };
}

ui.btnWarningsEdit?.addEventListener("click", (e) => {
  e.preventDefault();
  if (!ui.warningsAddPopover) return;
  ui.warningsAddPopover.hidden ? openWarningsAddPopover() : closeWarningsAddPopover();
});

ui.btnWarningsAddCancel?.addEventListener("click", () => {
  ui.inpWarningsAdd.value = _warningsEditorPrev;
  closeWarningsAddPopover();
});

ui.btnWarningsAddOk?.addEventListener("click", () => {
  const { list: next, normalized } = normalizeThresholdInput(ui.inpWarningsAdd.value);
  if (next.length === 0) {
    showToast("Invalid thresholds", "Enter one or more whole numbers ≥ 1 (comma- or space-separated).", "warn", { durationMs: 8000 });
    return;
  }
  updateThresholdsFromList(next);
  ui.inpWarningsAdd.value = normalized;
  closeWarningsAddPopover();
});

ui.inpWarningsAdd?.addEventListener("keydown", (e) => {
  if (e.key === "Enter") {
    e.preventDefault();
    ui.btnWarningsAddOk.click();
  } else if (e.key === "Escape") {
    e.preventDefault();
    ui.btnWarningsAddCancel.click();
  }
});

ui.inpWarningsAdd?.addEventListener("blur", () => {
  const { normalized } = normalizeThresholdInput(ui.inpWarningsAdd.value);
  if (normalized) ui.inpWarningsAdd.value = normalized;
});


ui.btnResumeLastLog.addEventListener("click", async () => {
  const h = pendingRestoreHandle;
  if (!h) return;
  try {
    const p = await h.requestPermission({ mode: "read" });
    if (p !== "granted") {
      appendHistory("Permission not granted.");
      return;
    }
    hideRestoreBanner();
    await finishRestoreSavedLog(h);
  } catch (e) {
    appendHistory(`Resume failed: ${String(e)}`);
  }
});
ui.btnDismissRestoreBanner.addEventListener("click", () => {
  pendingRestoreHandle = null;
  hideRestoreBanner();
  appendHistory("Resume dismissed — pick the log file or reload to try again.");
});

ui.btnInterruptAdoptConfirm.addEventListener("click", () => {
  const s = interruptAdoptPendingSession;
  if (s == null) return;
  applyInterruptAdopt(s);
});
ui.btnInterruptAdoptNotNow.addEventListener("click", () => {
  interruptAdoptDeclinedSession = interruptAdoptPendingSession;
  hideInterruptAdoptModal();
  appendHistory("Keeping interrupted state — adopt the new run when ready (dialog will show again if the session changes).");
});

// Folder picking removed (confusing UX). Keep only “Pick log file…”.

function focusAndReveal(el) {
  try {
    el.scrollIntoView({ block: "center", behavior: "smooth" });
  } catch {
    // ignore
  }
  try {
    el.focus({ preventScroll: true });
  } catch {
    try {
      el.focus();
    } catch {
      // ignore
    }
  }
}

function flashInput(el) {
  el.classList.add("flash");
  window.setTimeout(() => el.classList.remove("flash"), 700);
}

function openSettingsAndEditRollingWindow() {
  openSettings();
  // Wait a frame so the modal is visible before scrolling/focusing.
  requestAnimationFrame(() => {
    focusAndReveal(ui.inpWindowPoints);
    try {
      ui.inpWindowPoints.select();
    } catch {
      // ignore
    }
    flashInput(ui.inpWindowPoints);
  });
}

let rateWindowEditOpen = false;
let rateWindowPrev = "";
function openRateWindowPopover() {
  if (!ui.rateWindowPopover || !ui.inpRateWindowPoints) return;
  rateWindowEditOpen = true;
  ui.rateWindowPopover.hidden = false;
  rateWindowPrev = String(config.windowPoints ?? "");
  ui.inpRateWindowPoints.value = String(config.windowPoints ?? rollingWindowPoints());
  try {
    ui.inpRateWindowPoints.focus();
    ui.inpRateWindowPoints.select?.();
  } catch {
    // ignore
  }
}
function closeRateWindowPopover() {
  if (!ui.rateWindowPopover) return;
  rateWindowEditOpen = false;
  ui.rateWindowPopover.hidden = true;
}
function commitRateWindowPopover() {
  if (!ui.inpRateWindowPoints) return;
  const raw = String(ui.inpRateWindowPoints.value || "").trim();
  const n = Number.parseInt(raw, 10);
  if (!Number.isFinite(n) || n < 2) {
    showToast("Invalid AVG window", "Enter a whole number ≥ 2.", "warn", { durationMs: 7000 });
    try {
      ui.inpRateWindowPoints.focus();
      ui.inpRateWindowPoints.select?.();
    } catch {
      // ignore
    }
    return;
  }
  config.windowPoints = n;
  saveConfig();
  syncConfigToForm();
  updateTimeEstimates();
  closeRateWindowPopover();
}

let statusRefreshEditOpen = false;
let statusRefreshPrev = "";
function openStatusRefreshPopover() {
  if (!ui.statusRefreshPopover || !ui.inpStatusRefreshSec) return;
  statusRefreshEditOpen = true;
  ui.statusRefreshPopover.hidden = false;
  statusRefreshPrev = String(config.pollSec ?? "");
  ui.inpStatusRefreshSec.value = String(config.pollSec ?? 2);
  try {
    ui.inpStatusRefreshSec.focus();
    ui.inpStatusRefreshSec.select?.();
  } catch {
    // ignore
  }
}
function closeStatusRefreshPopover() {
  if (!ui.statusRefreshPopover) return;
  statusRefreshEditOpen = false;
  ui.statusRefreshPopover.hidden = true;
}
function commitStatusRefreshPopover() {
  if (!ui.inpStatusRefreshSec) return;
  const raw = String(ui.inpStatusRefreshSec.value || "").trim();
  const n = Number.parseFloat(raw);
  if (!Number.isFinite(n) || n < 0.2) {
    showToast("Invalid refresh", "Enter a number ≥ 0.2 seconds.", "warn", { durationMs: 7000 });
    try {
      ui.inpStatusRefreshSec.focus();
      ui.inpStatusRefreshSec.select?.();
    } catch {
      // ignore
    }
    return;
  }
  config.pollSec = n;
  saveConfig();
  syncConfigToForm();
  if (running) {
    if (pollTimer != null) window.clearInterval(pollTimer);
    pollTimer = window.setInterval(() => pollOnce(), Math.max(200, config.pollSec * 1000));
    appendHistory(`Updated poll interval: ${config.pollSec}s`);
  }
  closeStatusRefreshPopover();
}

// Inline-edit affordances: click KPI to jump to the relevant setting.
ui.kpiWarnings.title = "Scroll to pan thresholds left/right. Click to edit warning thresholds.";
ui.kpiWarnings.style.cursor = "pointer";
ui.kpiWarnings.addEventListener("click", () => {
  if (warningsEditMode) return;
  focusAndReveal(ui.inpThresholds);
  try {
    ui.inpThresholds.select();
  } catch {
    // ignore
  }
  flashInput(ui.inpThresholds);
});

ui.kpiRateLabel.title = "Click to edit AVG window (points)";
ui.kpiRateLabel.style.cursor = "pointer";
ui.kpiRateLabel.addEventListener("click", () => {
  if (rateWindowEditOpen) return;
  openRateWindowPopover();
});

ui.kpiRate.title = "Click to edit AVG window (points)";
ui.kpiRate.style.cursor = "pointer";
ui.kpiRate.addEventListener("click", () => {
  if (rateWindowEditOpen) return;
  openRateWindowPopover();
});

ui.btnRateEdit?.addEventListener("click", (e) => {
  e.preventDefault();
  if (rateWindowEditOpen) closeRateWindowPopover();
  else openRateWindowPopover();
});

ui.btnRateWindowOk?.addEventListener("click", () => commitRateWindowPopover());
ui.btnRateWindowCancel?.addEventListener("click", () => {
  if (ui.inpRateWindowPoints) ui.inpRateWindowPoints.value = rateWindowPrev;
  closeRateWindowPopover();
});
ui.inpRateWindowPoints?.addEventListener("keydown", (e) => {
  if (e.key === "Escape") {
    e.preventDefault();
    if (ui.inpRateWindowPoints) ui.inpRateWindowPoints.value = rateWindowPrev;
    closeRateWindowPopover();
  } else if (e.key === "Enter") {
    e.preventDefault();
    commitRateWindowPopover();
  }
});

document.addEventListener("click", (e) => {
  if (!rateWindowEditOpen) return;
  const pop = ui.rateWindowPopover;
  const host = ui.kpiRate?.closest(".kpi--rate");
  const t = /** @type {any} */ (e.target);
  if (pop && (pop === t || pop.contains(t))) return;
  if (host && (host === t || host.contains(t))) return;
  closeRateWindowPopover();
});

ui.kpiStatusLabel?.addEventListener("click", () => {
  if (statusRefreshEditOpen) return;
  openStatusRefreshPopover();
});
ui.btnStatusRefreshEdit?.addEventListener("click", (e) => {
  e.preventDefault();
  if (statusRefreshEditOpen) closeStatusRefreshPopover();
  else openStatusRefreshPopover();
});
ui.btnStatusRefreshOk?.addEventListener("click", () => commitStatusRefreshPopover());
ui.btnStatusRefreshCancel?.addEventListener("click", () => {
  if (ui.inpStatusRefreshSec) ui.inpStatusRefreshSec.value = statusRefreshPrev;
  closeStatusRefreshPopover();
});
ui.inpStatusRefreshSec?.addEventListener("keydown", (e) => {
  if (e.key === "Escape") {
    e.preventDefault();
    if (ui.inpStatusRefreshSec) ui.inpStatusRefreshSec.value = statusRefreshPrev;
    closeStatusRefreshPopover();
  } else if (e.key === "Enter") {
    e.preventDefault();
    commitStatusRefreshPopover();
  }
});
document.addEventListener("click", (e) => {
  if (!statusRefreshEditOpen) return;
  const pop = ui.statusRefreshPopover;
  const host = ui.kpiStatus?.closest(".kpi--status");
  const t = /** @type {any} */ (e.target);
  if (pop && (pop === t || pop.contains(t))) return;
  if (host && (host === t || host.contains(t))) return;
  closeStatusRefreshPopover();
});

ui.btnPickLog.addEventListener("click", async () => {
  try {
    await pickLogFile();
  } catch (e) {
    appendHistory(`Pick log cancelled/failed: ${String(e)}`);
  }
});

ui.btnStartStop.addEventListener("click", async () => {
  if (!running) startMonitoring();
  else stopMonitoring();
});

ui.btnYScale.addEventListener("click", () => {
  config.graphLogScale = !config.graphLogScale;
  ui.btnYScale.textContent = config.graphLogScale ? "Y → log" : "Y → linear";
  saveConfig();
  drawGraph();
});

ui.btnGraphWindow?.addEventListener("click", () => {
  config.graphLiveWindow = !config.graphLiveWindow;
  ui.btnGraphWindow.textContent = config.graphLiveWindow ? "Live view: on" : "Live view: off";
  saveConfig();
  drawGraph();
});

ui.btnClear.addEventListener("click", () => {
  graphPoints = [];
  currentPoint = null;
  lastPosition = null;
  positionOneReachedAt = null;
  connectPhaseStartedEpoch = null;
  progressAtFrontEntry = null;
  leftConnectQueueDetected = false;
  thresholdsFired.clear();
  completionNotifiedThisRun = false;
  ui.infoLastChange.textContent = "—";
  ui.infoLastAlert.textContent = "—";
  setPositionDisplay(null);
  ui.kpiElapsed.textContent = "—";
  ui.kpiRemaining.textContent = "—";
  ui.kpiRate.textContent = "—";
  ui.infoGlobalRate.textContent = "—";
  ui.progressFill.style.width = "0%";
  history = [];
  ui.historyPre.textContent = "";
  appendHistory("Cleared.");
  drawGraph();
});

ui.btnCopyHistory.addEventListener("click", async () => {
  try {
    await navigator.clipboard.writeText(ui.historyPre.textContent || "");
    appendHistory("History copied to clipboard.");
  } catch {
    appendHistory("Could not copy history (clipboard permission).");
  }
});

function canvasToPngBlob(canvas) {
  return new Promise((resolve) => {
    try {
      canvas.toBlob((b) => resolve(b), "image/png");
    } catch {
      resolve(null);
    }
  });
}

function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.rel = "noreferrer";
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 2000);
}

ui.btnCopyGraph?.addEventListener("click", async () => {
  const canvas = ui.graphCanvas;
  const blob = await canvasToPngBlob(canvas);
  if (!blob) {
    showToast("Copy failed", "Could not capture the canvas image.", "error");
    return;
  }

  const fileName = `vs-queue-graph-${new Date().toISOString().replace(/[:.]/g, "-")}.png`;
  try {
    // Clipboard image write is not supported everywhere; require a user gesture (this click).
    if (!navigator.clipboard || typeof window.ClipboardItem !== "function") throw new Error("Clipboard image write not supported");
    const item = new ClipboardItem({ "image/png": blob });
    await navigator.clipboard.write([item]);
    showToast("Copied", "Graph snapshot copied to clipboard (PNG).");
    appendHistory("Graph snapshot copied to clipboard.");
  } catch {
    downloadBlob(blob, fileName);
    showToast("Downloaded", "Clipboard image copy isn't available here, so the snapshot was downloaded instead.", "info", {
      durationMs: 9000,
    });
    appendHistory(`Graph snapshot downloaded: ${fileName}`);
  }
});

ui.btnRequestNotify.addEventListener("click", async () => {
  if (!("Notification" in window)) {
    appendHistory("Notifications are not supported in this browser.");
    showToast("Not supported", "This browser does not support desktop notifications.", "warn", { durationMs: 7000 });
    return;
  }
  if (typeof window !== "undefined" && "isSecureContext" in window && !window.isSecureContext) {
    appendHistory("Desktop notifications are blocked in this context (not a secure origin).");
    showToast(
      "Open via localhost",
      "Desktop notifications require a secure origin. Run `python -m http.server 5173`, open http://localhost:5173, then click Enable notifications again.",
      "warn",
      { durationMs: 16000 },
    );
    return;
  }
  if (Notification.permission === "granted") {
    showTestDesktopNotification();
    appendHistory("Desktop notifications: permission already granted — sent a test notification.");
    showToast(
      "Test sent",
      "If you don’t see a banner, open Notification Center and check Windows notification settings for your browser. Banners are often suppressed while this tab is focused—try another window and watch for the next ping.",
      "info",
      { durationMs: 14000 },
    );
    syncNotifyButtonUi();
    syncNotifyPill();
    return;
  }
  if (Notification.permission === "denied") {
    appendHistory("Notifications are blocked for this site — change the permission in the browser (lock icon / site settings).");
    showToast(
      "Notifications blocked",
      "Unblock this site in the browser’s site settings (address bar) if you want desktop alerts.",
      "warn",
      { durationMs: 12000 },
    );
    return;
  }
  const p = await Notification.requestPermission();
  appendHistory(`Notification permission: ${p}`);
  if (p === "granted") {
    showTestDesktopNotification();
    showToast(
      "Notifications enabled",
      "You should see up to 3 test notifications. If not, open Notification Center and ensure Windows allows notifications for your browser.",
      "info",
      { durationMs: 16000 },
    );
  } else {
    showToast("Notifications not granted", "Desktop alerts stay off until you allow them in the browser.", "warn", { durationMs: 9000 });
  }
  syncNotifyButtonUi();
  syncNotifyPill();
});

ui.btnNotifyPill?.addEventListener("click", () => {
  try {
    if (ui.btnRequestNotify && !ui.btnRequestNotify.disabled) ui.btnRequestNotify.click();
    else desktopNotifyCapabilityHint();
  } catch {
    // ignore
  }
});

ui.btnSaveSettings.addEventListener("click", () => {
  try {
    const pollSec = Number.parseFloat(ui.inpPollSec.value.trim());
    if (!(pollSec >= 0.2)) throw new Error("Poll (s) must be >= 0.2.");
    const win = Number.parseInt(ui.inpWindowPoints.value.trim(), 10);
    if (!Number.isFinite(win) || win < 2) throw new Error("Rolling window (points) must be >= 2.");
    parseAlertThresholds(config.thresholdsRaw);

    config.pollSec = pollSec;
    config.windowPoints = win;
    // thresholdsRaw is edited inline from WARNINGS (not in this dialog)
    applyFormToConfig();
    saveConfig();
    syncConfigToForm();
    void syncSoundSummaries();
    refreshWarningsKpi();
    updateTimeEstimates();
    showSettingsNote("Saved.");

    if (running) {
      if (pollTimer != null) window.clearInterval(pollTimer);
      pollTimer = window.setInterval(() => pollOnce(), Math.max(200, config.pollSec * 1000));
      appendHistory(`Updated poll interval: ${config.pollSec}s`);
    }
  } catch (e) {
    showSettingsNote(String(e), true);
  }
});

ui.btnCancelSettings?.addEventListener("click", () => {
  // Discard in-progress edits (autosave may already have persisted, but this restores the form view).
  try {
    syncConfigToForm();
    void syncSoundSummaries();
  } catch {
    // ignore
  }
  closeSettings();
});

function bindEnterToSave(input) {
  input.addEventListener("keydown", (e) => {
    if (e.key !== "Enter") return;
    e.preventDefault();
    ui.btnSaveSettings.click();
  });
}

bindEnterToSave(ui.inpPollSec);
if (ui.inpThresholds) bindEnterToSave(ui.inpThresholds);
bindEnterToSave(ui.inpWindowPoints);
bindEnterToSave(ui.inpWarnSoundUrl);
bindEnterToSave(ui.inpCompletionSoundUrl);
bindEnterToSave(ui.inpInterruptSoundUrl);

// Auto-save on change (debounced). This is the primary persistence mechanism.
for (const el of [
  ui.inpPollSec,
  ui.inpThresholds,
  ui.inpWindowPoints,
  ui.inpWarnSoundUrl,
  ui.inpCompletionSoundUrl,
  ui.inpInterruptSoundUrl,
  ui.chkLogEveryChange,
  ui.chkWarnNotify,
  ui.chkWarnSound,
  ui.chkCompletionNotify,
  ui.chkCompletionSound,
  ui.chkInterruptNotify,
  ui.chkInterruptSound,
].filter(Boolean)) {
  el.addEventListener("input", () => {
    applyFormToConfig();
    scheduleAutosave();
    refreshWarningsKpi();
    updateTimeEstimates();
    if (running) {
      if (pollTimer != null) window.clearInterval(pollTimer);
      pollTimer = window.setInterval(() => pollOnce(), Math.max(200, config.pollSec * 1000));
    }
  });
  el.addEventListener("change", () => {
    applyFormToConfig();
    scheduleAutosave();
    refreshWarningsKpi();
    updateTimeEstimates();
    if (running) {
      if (pollTimer != null) window.clearInterval(pollTimer);
      pollTimer = window.setInterval(() => pollOnce(), Math.max(200, config.pollSec * 1000));
    }
  });
}

ui.btnPickWarnSound.addEventListener("click", () => ui.fileWarnSound.click());
ui.btnPickCompletionSound.addEventListener("click", () => ui.fileCompletionSound.click());
ui.btnPickInterruptSound.addEventListener("click", () => ui.fileInterruptSound.click());

ui.fileWarnSound.addEventListener("change", async (e) => {
  const f = e.target.files?.[0];
  if (!f) return;
  try {
    await idbPutSoundBlob("warn", f);
    config.warnSoundFileName = f.name;
    saveConfig();
    ui.fileWarnSound.value = "";
    await syncSoundSummaries();
  } catch {
    showSettingsNote("Could not save warning sound file.", true);
  }
});

ui.fileCompletionSound.addEventListener("change", async (e) => {
  const f = e.target.files?.[0];
  if (!f) return;
  try {
    await idbPutSoundBlob("completion", f);
    config.completionSoundFileName = f.name;
    saveConfig();
    ui.fileCompletionSound.value = "";
    await syncSoundSummaries();
  } catch {
    showSettingsNote("Could not save completion sound file.", true);
  }
});

ui.fileInterruptSound.addEventListener("change", async (e) => {
  const f = e.target.files?.[0];
  if (!f) return;
  try {
    await idbPutSoundBlob("interrupt", f);
    config.interruptSoundFileName = f.name;
    saveConfig();
    ui.fileInterruptSound.value = "";
    await syncSoundSummaries();
  } catch {
    showSettingsNote("Could not save interrupt sound file.", true);
  }
});

ui.btnClearWarnSoundFile.addEventListener("click", async () => {
  await idbDeleteSoundBlob("warn");
  config.warnSoundFileName = "";
  saveConfig();
  await syncSoundSummaries();
});

ui.btnClearCompletionSoundFile.addEventListener("click", async () => {
  await idbDeleteSoundBlob("completion");
  config.completionSoundFileName = "";
  saveConfig();
  await syncSoundSummaries();
});

ui.btnClearInterruptSoundFile.addEventListener("click", async () => {
  await idbDeleteSoundBlob("interrupt");
  config.interruptSoundFileName = "";
  saveConfig();
  await syncSoundSummaries();
});

ui.btnWarnBuiltin.addEventListener("click", () => {
  ui.inpWarnSoundUrl.value = "builtin";
  applyFormToConfig();
  scheduleAutosave();
  void syncSoundSummaries();
});

ui.btnCompletionBuiltin.addEventListener("click", () => {
  ui.inpCompletionSoundUrl.value = "builtin";
  applyFormToConfig();
  scheduleAutosave();
  void syncSoundSummaries();
});

ui.btnInterruptBuiltin.addEventListener("click", () => {
  ui.inpInterruptSoundUrl.value = "builtin";
  applyFormToConfig();
  scheduleAutosave();
  void syncSoundSummaries();
});

ui.btnWarnDefaultUrl.addEventListener("click", () => {
  ui.inpWarnSoundUrl.value = "";
  applyFormToConfig();
  scheduleAutosave();
  void syncSoundSummaries();
});

ui.btnCompletionDefaultUrl.addEventListener("click", () => {
  ui.inpCompletionSoundUrl.value = "";
  applyFormToConfig();
  scheduleAutosave();
  void syncSoundSummaries();
});

ui.btnInterruptDefaultUrl.addEventListener("click", () => {
  ui.inpInterruptSoundUrl.value = "";
  applyFormToConfig();
  scheduleAutosave();
  void syncSoundSummaries();
});

ui.btnTestWarnSound.addEventListener("click", () => {
  previewSound("warning");
});

ui.btnTestCompletionSound.addEventListener("click", () => {
  previewSound("completion");
});

ui.btnTestInterruptSound.addEventListener("click", () => {
  previewSound("interrupt");
});

// Resize canvas for crisp rendering on HiDPI (keep CSS size fixed)
function resizeCanvasToDisplaySize() {
  const canvas = ui.graphCanvas;
  const rect = canvas.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;
  const w = Math.max(600, Math.round(rect.width * dpr));
  const h = Math.max(280, Math.round(rect.height * dpr));
  if (canvas.width !== w || canvas.height !== h) {
    canvas.width = w;
    canvas.height = h;
    drawGraph();
  }
}
window.addEventListener("resize", () => resizeCanvasToDisplaySize());
resizeCanvasToDisplaySize();

// Allow vertical resizing of the graph card: redraw when the canvas box changes.
try {
  const ro = new ResizeObserver(() => resizeCanvasToDisplaySize());
  ro.observe(ui.graphCanvas);
} catch {
  // ignore (older browsers)
}

ui.graphCanvas.addEventListener("mouseenter", () => {
  graphCanvasHovering = true;
});
ui.graphCanvas.addEventListener("mouseleave", () => {
  graphCanvasHovering = false;
  graphHoverCanvasX = null;
  graphHoverPoint = null;
  ui.graphHint.textContent = graphHintDefaultText();
  scheduleDrawGraph();
});
ui.graphCanvas.addEventListener("mousemove", (e) => {
  const canvas = ui.graphCanvas;
  const rect = canvas.getBoundingClientRect();
  const scaleX = canvas.width / rect.width;
  graphHoverCanvasX = (e.clientX - rect.left) * scaleX;
  const pt = hitTestGraphPoint(e.clientX, e.clientY);
  graphHoverPoint = pt;
  if (pt) ui.graphHint.textContent = `${formatGraphHoverTime(pt[0])} — position ${pt[1]}`;
  else ui.graphHint.textContent = graphHintDefaultText();
  scheduleDrawGraph();
});

drawGraph();

