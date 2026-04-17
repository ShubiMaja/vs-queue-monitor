const APP_VERSION = "2.0.1";

const $ = (id) => /** @type {HTMLElement} */ (document.getElementById(id));

const ui = {
  btnPickLog: $("btnPickLog"),
  btnPickFolder: $("btnPickFolder"),
  btnHelp: $("btnHelp"),
  btnHelpClose: $("btnHelpClose"),
  btnStartStop: $("btnStartStop"),
  btnYScale: $("btnYScale"),
  btnClear: $("btnClear"),
  btnCopyHistory: $("btnCopyHistory"),
  btnRequestNotify: $("btnRequestNotify"),
  btnSaveSettings: $("btnSaveSettings"),
  toastHost: $("toastHost"),
  helpOverlay: $("helpOverlay"),
  inpHelpSourcePath: /** @type {HTMLInputElement} */ ($("inpHelpSourcePath")),
  btnHelpCopyCmd: $("btnHelpCopyCmd"),
  preHelpCmd: $("preHelpCmd"),
  graphCanvas: /** @type {HTMLCanvasElement} */ ($("graphCanvas")),
  graphHint: $("graphHint"),

  kpiPosition: $("kpiPosition"),
  kpiStatus: $("kpiStatus"),
  kpiRateLabel: $("kpiRateLabel"),
  kpiRate: $("kpiRate"),
  kpiWarnings: $("kpiWarnings"),
  kpiElapsed: $("kpiElapsed"),
  kpiRemaining: $("kpiRemaining"),
  progressFill: $("progressFill"),

  infoSource: $("infoSource"),
  infoResolved: $("infoResolved"),
  infoLastChange: $("infoLastChange"),
  infoLastAlert: $("infoLastAlert"),
  infoGlobalRate: $("infoGlobalRate"),

  inpPollSec: /** @type {HTMLInputElement} */ ($("inpPollSec")),
  inpThresholds: /** @type {HTMLInputElement} */ ($("inpThresholds")),
  inpWindowPoints: /** @type {HTMLInputElement} */ ($("inpWindowPoints")),
  chkLogEveryChange: /** @type {HTMLInputElement} */ ($("chkLogEveryChange")),
  chkWarnNotify: /** @type {HTMLInputElement} */ ($("chkWarnNotify")),
  chkWarnSound: /** @type {HTMLInputElement} */ ($("chkWarnSound")),
  chkCompletionNotify: /** @type {HTMLInputElement} */ ($("chkCompletionNotify")),
  chkCompletionSound: /** @type {HTMLInputElement} */ ($("chkCompletionSound")),
  settingsNote: $("settingsNote"),
  historyPre: $("historyPre"),
  footerVersion: $("footerVersion"),
};

ui.footerVersion.textContent = `v${APP_VERSION}`;

function showToast(title, body = "", kind = "info") {
  const host = ui.toastHost;
  if (!host) return;
  const el = document.createElement("div");
  el.className = `toast ${kind === "error" ? "toast--error" : ""}`.trim();
  el.innerHTML =
    `<div class="toast__title">${escapeHtml(String(title))}</div>` +
    (body ? `<div class="toast__body">${escapeHtml(String(body))}</div>` : "");
  host.appendChild(el);
  window.setTimeout(() => {
    try {
      el.remove();
    } catch {
      // ignore
    }
  }, 2400);
}

function escapeHtml(s) {
  return String(s)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function openHelp() {
  if (!ui.helpOverlay) return;
  ui.helpOverlay.hidden = false;
  try {
    // Set a sensible default in the generator if empty.
    if (ui.inpHelpSourcePath && !ui.inpHelpSourcePath.value) {
      const plat = String(navigator.platform || "").toLowerCase();
      if (plat.includes("win")) ui.inpHelpSourcePath.value = "%APPDATA%\\VintagestoryData";
      else if (plat.includes("linux")) ui.inpHelpSourcePath.value = "~/.config/VintagestoryData/Logs/client-main.log";
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

function closeHelp() {
  if (!ui.helpOverlay) return;
  ui.helpOverlay.hidden = true;
  try {
    ui.btnHelp?.focus();
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

function normalizeSlashes(s) {
  return String(s).trim().replaceAll("\r", "").replaceAll("\n", "");
}

function renderHelpCommandPreview() {
  if (!ui.preHelpCmd || !ui.inpHelpSourcePath) return;
  const raw = normalizeSlashes(ui.inpHelpSourcePath.value);
  const plat = String(navigator.platform || "").toLowerCase();
  const isWin = plat.includes("win");
  const isLinux = plat.includes("linux");
  const wantsFile = /[\\/](client-main\.log|client\.log)$/i.test(raw) || /\.log$/i.test(raw);
  const logName = /client\.log$/i.test(raw) ? "client.log" : "client-main.log";

  if (isWin) {
    const src = raw || "%APPDATA%\\VintagestoryData";
    const dest = '%USERPROFILE%\\Documents\\VintagestoryData';
    ui.preHelpCmd.textContent =
      `mkdir "${dest}"\n` +
      `mklink /J "${dest}" "${src}"\n` +
      `\nThen pick: ${dest}\\Logs\\${logName}`;
    return;
  }

  if (isLinux) {
    if (wantsFile) {
      const srcFile = raw || "~/.config/VintagestoryData/Logs/client-main.log";
      ui.preHelpCmd.textContent =
        `mkdir -p ~/VSLogs\n` +
        `ln -s ${srcFile} ~/VSLogs/${logName}\n` +
        `\nThen pick: ~/VSLogs/${logName}`;
      return;
    }
    const srcDir = raw || "~/.config/VintagestoryData";
    ui.preHelpCmd.textContent =
      `mkdir -p ~/VSLogs\n` +
      `ln -s ${srcDir}/Logs/${logName} ~/VSLogs/${logName}\n` +
      `\nThen pick: ~/VSLogs/${logName}`;
    return;
  }

  ui.preHelpCmd.textContent =
    "Open this app in Edge/Chrome.\n" +
    "If the picker is blocked, paste your real VS data/log path above to generate a junction/symlink command.";
}

// -----------------------------
// Parsing (ported from core.py)
// -----------------------------

const QUEUE_RE = new RegExp(
  "(?:" +
    "client\\s+is\\s+in\\s+connect\\s+queue\\s+at\\s+position" +
    "|your\\s+position\\s+in\\s+the\\s+queue\\s+is" +
    ")\\D*(\\d+)",
  "i",
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

const QUEUE_RUN_BOUNDARY_RES = [
  /\breconnect(?:ing|ed)?\b/i,
  /\b(?:connection|connect)\s+(?:to\s+(?:the\s+)?)?(?:server\s+)?(?:lost|closed|failed|aborted|reset|refused|timed\s*out)\b/i,
  /\b(?:lost|closed)\s+connection\b/i,
  /\bdisconnect(?:ed|ing)?\b/i,
  /\bopening\s+connection\b/i,
  /\bconnecting\s+to\s+/i,
  /\binitialized\s+server\s+connection\b/i,
  /\btrying\s+to\s+connect\b/i,
  /\breturned\s+to\s+(?:the\s+)?main\s+menu\b/i,
  /\b(?:server|client)\s+shut\s+down\b/i,
];

/**
 * @param {string} line
 */
function isQueueRunBoundaryLine(line) {
  const s = line.trim();
  if (!s) return false;
  if (queuePositionFromLine(s) != null) return false;
  return QUEUE_RUN_BOUNDARY_RES.some((r) => r.test(s));
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
  let session = 0;
  let lastSess = 0;
  for (const line of data.split(/\r?\n/)) {
    if (isQueueRunBoundaryLine(line)) {
      session += 1;
      continue;
    }
    const pos = queuePositionFromLine(line);
    if (pos == null) continue;
    lastPos = pos;
    lastSess = session;
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

// Debounced auto-save (mirrors the old app’s “save shortly after change” feel).
let _autosaveTimer = /** @type {number|null} */ (null);
function scheduleAutosave(note = "") {
  if (_autosaveTimer != null) window.clearTimeout(_autosaveTimer);
  _autosaveTimer = window.setTimeout(() => {
    _autosaveTimer = null;
    try {
      saveConfig();
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
  config.thresholdsRaw = ui.inpThresholds.value.trim() || config.thresholdsRaw;
  config.logEveryChange = ui.chkLogEveryChange.checked;
  config.warnNotify = ui.chkWarnNotify.checked;
  config.warnSound = ui.chkWarnSound.checked;
  config.completionNotify = ui.chkCompletionNotify.checked;
  config.completionSound = ui.chkCompletionSound.checked;
  ui.kpiRateLabel.textContent = `RATE (Rolling ${rollingWindowPoints()})`;
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
 *   graphLogScale: boolean
 * }} AppConfig
 */

/** @type {AppConfig} */
let config = {
  pollSec: 2,
  thresholdsRaw: "10, 5, 1",
  windowPoints: 10,
  logEveryChange: false,
  warnNotify: true,
  warnSound: true,
  completionNotify: true,
  completionSound: true,
  graphLogScale: false,
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
  ui.inpThresholds.value = String(config.thresholdsRaw);
  ui.inpWindowPoints.value = String(config.windowPoints);
  ui.chkLogEveryChange.checked = !!config.logEveryChange;
  ui.chkWarnNotify.checked = !!config.warnNotify;
  ui.chkWarnSound.checked = !!config.warnSound;
  ui.chkCompletionNotify.checked = !!config.completionNotify;
  ui.chkCompletionSound.checked = !!config.completionSound;
  ui.btnYScale.textContent = config.graphLogScale ? "Y → log" : "Y → linear";
  ui.kpiRateLabel.textContent = `RATE (Rolling ${config.windowPoints})`;
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

/**
 * @param {string} title
 * @param {string} body
 */
function notify(title, body) {
  if (!config.warnNotify && title.startsWith("⚠")) return;
  if (!config.completionNotify && title.startsWith("🎉")) return;
  if (!("Notification" in window)) return;
  if (Notification.permission !== "granted") return;
  try {
    new Notification(title, { body, silent: true });
  } catch {
    // ignore
  }
}

/** @type {AudioContext|null} */
let audioCtx = null;

function beep(kind) {
  if (kind === "warning" && !config.warnSound) return;
  if (kind === "completion" && !config.completionSound) return;
  try {
    audioCtx ??= new (window.AudioContext || window.webkitAudioContext)();
    const ctx = audioCtx;
    const o = ctx.createOscillator();
    const g = ctx.createGain();
    const now = ctx.currentTime;
    const base = kind === "completion" ? 880 : 520;
    o.type = kind === "completion" ? "triangle" : "square";
    o.frequency.setValueAtTime(base, now);
    o.frequency.exponentialRampToValueAtTime(base * 1.12, now + 0.12);
    g.gain.setValueAtTime(0.0001, now);
    g.gain.exponentialRampToValueAtTime(0.07, now + 0.01);
    g.gain.exponentialRampToValueAtTime(0.0001, now + 0.22);
    o.connect(g);
    g.connect(ctx.destination);
    o.start(now);
    o.stop(now + 0.25);
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
const QUEUE_RESET_JUMP_THRESHOLD = 10;
const ALERT_MIN_INTERVAL_SEC = 12.0;
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
async function readLogTailText(handle, tailBytes) {
  const file = await handle.getFile();
  const size = file.size;
  const start = Math.max(0, size - tailBytes);
  const slice = file.slice(start, size);
  const buf = await slice.arrayBuffer();
  return decodeLogBytes(buf, start);
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

async function pickLogFile() {
  if (!window.showOpenFilePicker) {
    appendHistory("This browser does not support file picking. Use Edge or Chrome.");
    return;
  }
  // Proactive guidance: the picker UI can block “system” folders before we get a rejection.
  try {
    const isFile = String(window.location && window.location.protocol) === "file:";
    const plat = String(navigator.platform || "").toLowerCase();
    const isWin = plat.includes("win");
    const isLinux = plat.includes("linux");
    if (isFile && (isWin || isLinux)) {
      appendHistory("Tip: if the picker says it can’t open files in a folder due to “system files”, the browser is blocking a protected location.");
      showToast("Picker tip", "If blocked by “system files”, click ? for workaround.");
      if (isWin) {
        appendHistory("Windows workaround (junction via Documents):");
        appendHistory('  mkdir "%USERPROFILE%\\Documents\\VintagestoryData"');
        appendHistory('  mklink /J "%USERPROFILE%\\Documents\\VintagestoryData" "%APPDATA%\\VintagestoryData"');
        appendHistory("Then pick: %USERPROFILE%\\Documents\\VintagestoryData\\Logs\\client-main.log");
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
    const msg = String(e && (e.message || e.name || e));
    const low = msg.toLowerCase();
    if (low.includes("abort") || low.includes("cancel")) {
      appendHistory("Pick log cancelled.");
      showToast("Pick cancelled", "No file was selected.");
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
      showToast("Picker blocked", "Browser denied access (protected/system location). Click ? for help.", "error");
      appendHistory("Note: browsers do not reveal the exact filesystem path you attempted to pick, so we can’t auto-generate a command with the exact blocked path.");
      appendHistory('Tip: click "?" and paste your real VS data/log path to generate an exact junction/symlink command.');
      appendHistory("Windows workaround (junction; source is the usual VS data dir under %APPDATA%):");
      appendHistory('  mkdir "%USERPROFILE%\\Documents\\VintagestoryData"');
      appendHistory('  mklink /J "%USERPROFILE%\\Documents\\VintagestoryData" "%APPDATA%\\VintagestoryData"');
      appendHistory("Explanation: this exposes %APPDATA%\\VintagestoryData under Documents so the browser picker can access it.");
      appendHistory("Then pick: %USERPROFILE%\\Documents\\VintagestoryData\\Logs\\client-main.log");
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
  logFileHandle = handle ?? null;
  sourceLabel = "Picked file";
  ui.infoSource.textContent = sourceLabel ?? "—";
  ui.infoResolved.textContent = logFileHandle ? (await logFileHandle.getFile()).name : "—";
  ui.btnStartStop.disabled = !logFileHandle;
  appendHistory(`Selected log file: ${(await logFileHandle.getFile()).name}`);

  // Best-effort: remember the last directory via well-known startIn token (not a real path).
  // Browsers do not expose a parent directory for a picked file handle.
  try {
    localStorage.setItem(STORAGE_LAST_DIR_KEY, String(startIn || "documents"));
  } catch {
    // ignore
  }
}

async function pickFolder() {
  if (!window.showDirectoryPicker) {
    appendHistory("Folder picking is not available here. Pick the log file directly (recommended).");
    return;
  }
  let dir;
  try {
    dir = await window.showDirectoryPicker({ mode: "read" });
  } catch (e) {
    // Chrome/Edge can block protected folders (and users can cancel).
    const msg = String(e && (e.message || e.name || e));
    if (msg.toLowerCase().includes("abort") || msg.toLowerCase().includes("cancel")) {
      appendHistory("Pick folder cancelled.");
      showToast("Pick cancelled", "No folder was selected.");
      return;
    }
    appendHistory("Could not open that folder. Pick the log file directly (recommended), or choose a non-system folder such as your Vintage Story data/Logs folder.");
    showToast("Pick failed", "Folder access was blocked. Pick the log file instead.", "error");
    return;
  }
  const file = await tryGetFirstExistingFile(dir, ["client-main.log", "client.log"]);
  if (!file) {
    appendHistory("Selected folder, but no client-main.log/client.log found at the top level. Pick the log file directly, or choose the Logs folder.");
    sourceLabel = "Picked folder (no log yet)";
    ui.infoSource.textContent = sourceLabel;
    ui.infoResolved.textContent = "—";
    logFileHandle = null;
    ui.btnStartStop.disabled = true;
    return;
  }
  logFileHandle = file;
  sourceLabel = "Picked folder";
  ui.infoSource.textContent = sourceLabel;
  ui.infoResolved.textContent = (await logFileHandle.getFile()).name;
  ui.btnStartStop.disabled = false;
  appendHistory(`Selected folder; resolved log file: ${(await logFileHandle.getFile()).name}`);
}

// -----------------------------
// Monitor engine (browser)
// -----------------------------

/** @typedef {[number, number]} GraphPoint */ // [epochSec, position]

/** @type {GraphPoint[]} */
let graphPoints = [];
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
/** @type {number} */
let lastAlertEpoch = 0;
/** @type {Set<number>} */
let thresholdsFired = new Set();
/** @type {number} */
let lastCompletionNotifyEpoch = 0;
let completionNotifiedThisRun = false;
/** @type {number|null} */
let lastQueueRunSession = null;
/** @type {number|null} */
let lastQueueLineEpoch = null;
/** @type {{ size: number, mtime: number } | null} */
let lastLogStat = null;
/** @type {number|null} */
let lastLogGrowthEpoch = null;
let interruptedMode = false;
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
  ui.kpiStatus.textContent = text;
  ui.kpiStatus.classList.toggle("danger", danger);
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

function refreshWarningsKpi() {
  let thresholds;
  try {
    thresholds = parseAlertThresholds(config.thresholdsRaw);
  } catch {
    ui.kpiWarnings.textContent = "—";
    return;
  }
  const pos = currentQueuePosition();
  const fired = thresholdsFired;
  const parts = [];
  for (const t of thresholds) {
    const passed = (pos != null && pos <= t) || fired.has(t);
    parts.push(passed ? String(t) : String(t));
  }
  ui.kpiWarnings.textContent = thresholds.join(" · ");
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
  ui.kpiRateLabel.textContent = `RATE (Rolling ${rollingWindowPoints()})`;
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
  ui.progressFill.style.width = `${progress.toFixed(1)}%`;
}

/**
 * @param {number} position
 * @param {number|null} lineEpoch
 */
function appendGraphPoint(position, lineEpoch) {
  const t = lineEpoch ?? (Date.now() / 1000);
  if (currentPoint && currentPoint[1] === position) return;
  currentPoint = [t, position];
  lastPosition = position;
  predSpeedScale = 1.0;
  staleSlotsAccounted = 0;
  graphPoints.push(currentPoint);
  if (graphPoints.length > 5000) graphPoints = graphPoints.slice(-5000);
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
  return { should: true, reason: `crossed threshold(s): ${crossed.join(", ")}` };
}

/**
 * @param {number} position
 * @param {string} reason
 */
function raiseAlert(position, reason) {
  const now = Date.now() / 1000;
  if (lastAlertEpoch > 0 && now - lastAlertEpoch < ALERT_MIN_INTERVAL_SEC) return;
  lastAlertEpoch = now;
  ui.infoLastAlert.textContent = nowStamp();
  const secRem = estimateSecondsRemaining();
  const etaDisplay = secRem == null ? "—" : formatDurationRemaining(secRem);
  const extra = secRem == null ? "" : `; est. remaining ${etaDisplay}`;
  appendHistory(`Threshold alert: position ${position} (${reason})${extra}`);
  beep("warning");
  notify("⚠ Threshold alert", `Position ${position} (${reason}). ETA: ${etaDisplay}`);
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
  beep("completion");
  notify("🎉 Queue completed", "Past queue wait detected in the log tail (connecting/loading).");
}

/**
 * @param {string} detail
 */
function enterInterruptedState(detail) {
  if (interruptedMode) return;
  interruptedMode = true;
  interruptedElapsedSec = snapshotElapsedSecondsAtInterrupt();
  frozenRatesAtInterrupt = [ui.kpiRate.textContent, ui.infoGlobalRate.textContent];
  setStatus("Interrupted", true);
  appendHistory(`Queue interrupted; still watching the log. (${detail})`);
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

async function pollOnce() {
  if (!running) return;
  if (!logFileHandle) {
    setStatus("Waiting for log file", false);
    return;
  }

  try {
    updateTimeEstimates();
    await bumpLogActivityIfChanged();
    const tail = await readLogTailText(logFileHandle, TAIL_BYTES);
    const { kind } = classifyTailConnectionState(tail);
    const { lastPos, session } = parseTailLastQueueReading(tail);
    const lastLineEpoch = parseTailLastQueueLineEpoch(tail);
    if (lastLineEpoch != null) lastQueueLineEpoch = lastLineEpoch;
    const left = tailHasPostQueueAfterLastQueueLine(tail);
    const now = Date.now() / 1000;
    const logSilent = lastLogGrowthEpoch != null && now - lastLogGrowthEpoch >= LOG_SILENCE_RECONNECT_SEC;
    const staleLimit = QUEUE_UPDATE_INTERVAL_SEC * QUEUE_STALE_TIMEOUT_MULT;

    if (interruptedMode) {
      // Minimal: keep interrupted until the queue looks healthy again (new queue lines).
      if (lastQueueLineEpoch != null && now - lastQueueLineEpoch <= staleLimit && kind === "queue" && lastPos != null) {
        interruptedMode = false;
        interruptedElapsedSec = null;
        frozenRatesAtInterrupt = null;
        setStatus("Monitoring");
        appendHistory("Recovered from interrupted state (queue lines resumed).");
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
      leftConnectQueueDetected = false;
      progressAtFrontEntry = null;
      positionOneReachedAt = null;
      connectPhaseStartedEpoch = null;
      setStatus(logSilent || kind === "grace" ? "Reconnecting…" : "Connecting…");
      setPositionDisplay(null);
      lastPosition = null;
      return;
    }

    if (lastPos != null && (!logSilent || lastPos <= 1)) {
      const prevPos = lastPosition;
      let pos = lastPos;

      if (prevPos != null && pos > prevPos && pos - prevPos >= QUEUE_RESET_JUMP_THRESHOLD) {
        pos = prevPos;
      }

      if (pos <= 1 && left) pos = 0;

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
        appendHistory("New queue run (from log).");
      }
      lastQueueRunSession = session;

      if (pos === 0) setStatus("Completed");
      else if (pos <= 1) setStatus("At front");
      else setStatus("Monitoring");

      setPositionDisplay(pos);
      if (pos <= 1 && positionOneReachedAt == null) positionOneReachedAt = lastLineEpoch ?? now;

      appendGraphPoint(pos, lastLineEpoch);
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
      maybeNotifyCompletion(pos, tail);
      refreshWarningsKpi();
      return;
    }

    setStatus("Warning: no queue detected", true);
  } catch (e) {
    setStatus("Error", true);
    appendHistory(`Error: ${String(e)}`);
  }
}

function startMonitoring() {
  if (!logFileHandle) return;
  running = true;
  monitorStartEpoch = Date.now() / 1000;
  setStatus("Monitoring");
  ui.btnStartStop.textContent = "Stop";
  ui.btnPickLog.disabled = true;
  ui.btnPickFolder.disabled = true;
  thresholdsFired.clear();
  completionNotifiedThisRun = false;
  interruptedMode = false;
  interruptedElapsedSec = null;
  frozenRatesAtInterrupt = null;
  lastQueueRunSession = null;
  appendHistory("Monitoring started.");

  if (pollTimer != null) window.clearInterval(pollTimer);
  pollTimer = window.setInterval(() => pollOnce(), Math.max(200, config.pollSec * 1000));
  if (estimateTimer != null) window.clearInterval(estimateTimer);
  estimateTimer = window.setInterval(() => updateTimeEstimates(), 100);
  pollOnce();
}

function stopMonitoring() {
  running = false;
  ui.btnStartStop.textContent = "Start";
  ui.btnPickLog.disabled = false;
  ui.btnPickFolder.disabled = false;
  if (pollTimer != null) window.clearInterval(pollTimer);
  pollTimer = null;
  if (estimateTimer != null) window.clearInterval(estimateTimer);
  estimateTimer = null;
  setStatus(leftConnectQueueDetected ? "Completed" : "Stopped", false);
  appendHistory("Monitoring stopped.");
}

// -----------------------------
// Graph (canvas)
// -----------------------------

function graphYMap(pos, minP, maxP, h) {
  const padTop = 18;
  const padBot = 26;
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
  ctx.fillStyle = "rgba(13,15,18,0.95)";
  ctx.fillRect(0, 0, w, h);

  if (graphPoints.length < 1) {
    ui.graphHint.textContent = "Pick a log and press Start. The graph will fill as queue positions change.";
    return;
  }
  ui.graphHint.textContent = config.graphLogScale ? "Y scale: log" : "Y scale: linear";

  const padL = 54;
  const padR = 20;
  const padT = 18;
  const padB = 26;
  const plotW = w - padL - padR;
  const plotH = h - padT - padB;

  // Range
  const positions = graphPoints.map((p) => p[1]);
  let minP = Math.min(...positions);
  let maxP = Math.max(...positions);
  if (!Number.isFinite(minP) || !Number.isFinite(maxP)) return;
  if (minP === maxP) {
    minP = Math.max(0, minP - 1);
    maxP = maxP + 1;
  }

  // Time range
  const t0 = graphPoints[0][0];
  const t1 = graphPoints[graphPoints.length - 1][0];
  const span = Math.max(60, t1 - t0);
  const xOf = (t) => padL + ((t - t1 + span) / span) * plotW;

  // Grid
  ctx.strokeStyle = "rgba(46,55,66,0.7)";
  ctx.lineWidth = 1;
  for (let i = 0; i <= 6; i++) {
    const y = padT + (i / 6) * plotH;
    ctx.beginPath();
    ctx.moveTo(padL, y);
    ctx.lineTo(w - padR, y);
    ctx.stroke();
  }

  // Axes labels (simple)
  ctx.fillStyle = "rgba(159,167,179,0.95)";
  ctx.font = "12px " + getComputedStyle(document.documentElement).getPropertyValue("--mono");
  ctx.textAlign = "right";
  ctx.textBaseline = "middle";
  const yLabels = [maxP, Math.round((maxP + minP) / 2), minP];
  for (const val of yLabels) {
    const y = graphYMap(val, minP, maxP, h);
    ctx.fillText(String(val), padL - 8, y);
  }

  // Series (step plot)
  ctx.strokeStyle = "rgba(87,148,242,0.95)";
  ctx.lineWidth = 2;
  ctx.beginPath();
  for (let i = 0; i < graphPoints.length; i++) {
    const [t, p] = graphPoints[i];
    const x = xOf(t);
    const y = graphYMap(p, minP, maxP, h);
    if (i === 0) ctx.moveTo(x, y);
    else {
      const [tPrev, pPrev] = graphPoints[i - 1];
      const xPrev = xOf(tPrev);
      const yPrev = graphYMap(pPrev, minP, maxP, h);
      ctx.lineTo(x, yPrev);
      ctx.lineTo(x, y);
    }
  }
  ctx.stroke();

  // Current marker
  const last = graphPoints[graphPoints.length - 1];
  const xm = xOf(last[0]);
  const ym = graphYMap(last[1], minP, maxP, h);
  ctx.fillStyle = "rgba(107,155,214,1)";
  ctx.beginPath();
  ctx.arc(xm, ym, 4.5, 0, Math.PI * 2);
  ctx.fill();
}

// -----------------------------
// Wire up UI
// -----------------------------

loadConfig();
syncConfigToForm();
setStatus("Idle");
refreshWarningsKpi();
appendHistory("VS Queue Monitor (web) ready. Pick your client log and press Start.");
wireHelpOverlay();

// Hide folder picking when unsupported (common under file:// or non-Chromium).
try {
  const isFile = String(window.location && window.location.protocol) === "file:";
  if (isFile || !window.showDirectoryPicker) ui.btnPickFolder.style.display = "none";
} catch {
  // ignore
}

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

// Inline-edit affordances: click KPI to jump to the relevant setting.
ui.kpiWarnings.title = "Click to edit warning thresholds";
ui.kpiWarnings.style.cursor = "pointer";
ui.kpiWarnings.addEventListener("click", () => {
  focusAndReveal(ui.inpThresholds);
  try {
    ui.inpThresholds.select();
  } catch {
    // ignore
  }
  flashInput(ui.inpThresholds);
});

ui.kpiRateLabel.title = "Click to edit rolling window (points)";
ui.kpiRateLabel.style.cursor = "pointer";
ui.kpiRateLabel.addEventListener("click", () => {
  focusAndReveal(ui.inpWindowPoints);
  try {
    ui.inpWindowPoints.select();
  } catch {
    // ignore
  }
  flashInput(ui.inpWindowPoints);
});

ui.kpiRate.title = "Click to edit rolling window (points)";
ui.kpiRate.style.cursor = "pointer";
ui.kpiRate.addEventListener("click", () => {
  focusAndReveal(ui.inpWindowPoints);
  try {
    ui.inpWindowPoints.select();
  } catch {
    // ignore
  }
  flashInput(ui.inpWindowPoints);
});

ui.btnPickLog.addEventListener("click", async () => {
  try {
    await pickLogFile();
  } catch (e) {
    appendHistory(`Pick log cancelled/failed: ${String(e)}`);
  }
});

ui.btnPickFolder.addEventListener("click", async () => {
  try {
    await pickFolder();
  } catch (e) {
    appendHistory(`Pick folder cancelled/failed: ${String(e)}`);
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

ui.btnRequestNotify.addEventListener("click", async () => {
  if (!("Notification" in window)) {
    appendHistory("Notifications are not supported in this browser.");
    return;
  }
  const p = await Notification.requestPermission();
  appendHistory(`Notification permission: ${p}`);
});

ui.btnSaveSettings.addEventListener("click", () => {
  try {
    const pollSec = Number.parseFloat(ui.inpPollSec.value.trim());
    if (!(pollSec >= 0.2)) throw new Error("Poll (s) must be >= 0.2.");
    const win = Number.parseInt(ui.inpWindowPoints.value.trim(), 10);
    if (!Number.isFinite(win) || win < 2) throw new Error("Rolling window (points) must be >= 2.");
    parseAlertThresholds(ui.inpThresholds.value);

    config.pollSec = pollSec;
    config.windowPoints = win;
    config.thresholdsRaw = ui.inpThresholds.value.trim();
    config.logEveryChange = ui.chkLogEveryChange.checked;
    config.warnNotify = ui.chkWarnNotify.checked;
    config.warnSound = ui.chkWarnSound.checked;
    config.completionNotify = ui.chkCompletionNotify.checked;
    config.completionSound = ui.chkCompletionSound.checked;
    saveConfig();
    syncConfigToForm();
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

function bindEnterToSave(input) {
  input.addEventListener("keydown", (e) => {
    if (e.key !== "Enter") return;
    e.preventDefault();
    ui.btnSaveSettings.click();
  });
}

bindEnterToSave(ui.inpPollSec);
bindEnterToSave(ui.inpThresholds);
bindEnterToSave(ui.inpWindowPoints);

// Auto-save on change (debounced). This is the primary persistence mechanism.
for (const el of [
  ui.inpPollSec,
  ui.inpThresholds,
  ui.inpWindowPoints,
  ui.chkLogEveryChange,
  ui.chkWarnNotify,
  ui.chkWarnSound,
  ui.chkCompletionNotify,
  ui.chkCompletionSound,
]) {
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
drawGraph();

