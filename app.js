// Bump `index.html` script src `?v=` when changing version (cache bust for ./app.js).
const APP_VERSION = "2.0.43";

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
  restoreBanner: $("restoreBanner"),
  restoreBannerDetail: $("restoreBannerDetail"),
  btnResumeLastLog: $("btnResumeLastLog"),
  btnDismissRestoreBanner: $("btnDismissRestoreBanner"),
  interruptAdoptOverlay: $("interruptAdoptOverlay"),
  interruptAdoptDetail: $("interruptAdoptDetail"),
  btnInterruptAdoptConfirm: $("btnInterruptAdoptConfirm"),
  btnInterruptAdoptNotNow: $("btnInterruptAdoptNotNow"),
  helpOverlay: $("helpOverlay"),
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
    kind === "error" ? "toast--error" : kind === "warn" ? "toast--warn" : kind === "ok" ? "toast--ok" : "";
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
    const logsRoot = findWindowsLogsFolderRoot(srcIn);

    // Hard link the log file into Documents (no admin on same volume). Single file under vs-queue-monitor — no subfolder.
    if (looksLikeLogFile) {
      const destFile = winHardLinkExposedLogPath(srcIn);
      let txt =
        `REM mklink /H is for FILES only (not folders). Second path must be your real client-main.log file.\n` +
        `if not exist "%USERPROFILE%\\Documents\\vs-queue-monitor" mkdir "%USERPROFILE%\\Documents\\vs-queue-monitor"\n` +
        `mklink /H "${destFile}" "${srcIn}"`;
      if (logsRoot) {
        const leafJ = linkFolderName("logs", logsRoot);
        const destJ = `%USERPROFILE%\\Documents\\vs-queue-monitor\\${leafJ}`;
        let pickSuffix = logName;
        const rel = winPathRelativeBelowLogs(srcIn, logsRoot);
        if (rel !== null && rel.length > 0) pickSuffix = rel;
        txt +=
          `\n\n` +
          `REM If mklink /H fails (file must exist; same drive as Documents), use a folder junction — /J for folders, not /H:\n` +
          `REM if not exist "%USERPROFILE%\\Documents\\vs-queue-monitor" mkdir "%USERPROFILE%\\Documents\\vs-queue-monitor"\n` +
          `REM mklink /J "${destJ}" "${logsRoot}"\n` +
          `REM Then pick: ${destJ}\\${pickSuffix}`;
      }
      ui.preHelpCmd.textContent = txt;
      setPick(destFile);
      return;
    }

    // Folder junction: Logs directory or data root (no .log file pasted).
    if (logsRoot) {
      const leaf = linkFolderName("logs", logsRoot);
      const dest = `%USERPROFILE%\\Documents\\vs-queue-monitor\\${leaf}`;
      ui.preHelpCmd.textContent =
        `REM Folders: use mklink /J only. Do not use mklink /H on a directory (that causes an error).\n` +
        `if not exist "%USERPROFILE%\\Documents\\vs-queue-monitor" mkdir "%USERPROFILE%\\Documents\\vs-queue-monitor"\n` +
        `mklink /J "${dest}" "${logsRoot}"`;
      setPick(`${dest}\\${logName}`);
      return;
    }

    const srcDir = srcIn;
    const leaf = linkFolderName("data", srcDir);
    const dest = `%USERPROFILE%\\Documents\\vs-queue-monitor\\${leaf}`;
    ui.preHelpCmd.textContent =
      `REM Folders: mklink /J only. For a single log file under Documents, paste the .log path to get mklink /H instead.\n` +
      `if not exist "%USERPROFILE%\\Documents\\vs-queue-monitor" mkdir "%USERPROFILE%\\Documents\\vs-queue-monitor"\n` +
      `mklink /J "${dest}" "${srcDir}"`;
    setPick(`${dest}\\Logs\\${logName}`);
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
    "If the picker is blocked, paste your real VS data/log path above to generate a junction/symlink command.";
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
 * Keep only the **current queue run** in a loaded chunk: same session model as {@link parseTailLastQueueReading}
 * (boundaries: reconnect, disconnect, main menu, new connection attempt, etc.). Works for a full file or a tail slice;
 * session indices are relative to the start of `data`.
 * @param {string} data
 */
function sliceLoadedLogToCurrentQueueRun(data) {
  if (!data) return data;
  const lines = data.split(/\r?\n/);
  if (lines.length === 0) return data;
  const sessionBeforeLine = new Array(lines.length);
  let s = 0;
  for (let i = 0; i < lines.length; i++) {
    sessionBeforeLine[i] = s;
    if (isQueueRunBoundaryLine(lines[i])) s++;
  }
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
 * Desktop notification (optional). Toasts in `raiseAlert` / `maybeNotifyCompletion` work without permission.
 * @param {"threshold"|"completion"} kind
 * @param {string} title
 * @param {string} body
 */
function notifyDesktop(kind, title, body) {
  if (kind === "threshold" && !config.warnNotify) return;
  if (kind === "completion" && !config.completionNotify) return;
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

/** Soft sine chimes: warning = two-step attention; completion = short major arpeggio. */
function beep(kind) {
  if (kind === "warning" && !config.warnSound) return;
  if (kind === "completion" && !config.completionSound) return;
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
    } else {
      // C major arpeggio (C5–E5–G5–C6): short celebratory swell.
      tone(523.25, now, 0.2, 0.1);
      tone(659.25, now + 0.1, 0.22, 0.095);
      tone(783.99, now + 0.2, 0.24, 0.09);
      tone(1046.5, now + 0.3, 0.32, 0.085);
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
    startMonitoring();
  } finally {
    restoreInProgress = false;
  }
}

async function tryRestoreLastLogOnLoad() {
  if (!window.showOpenFilePicker) {
    appendHistory(
      "File System Access API not available (`showOpenFilePicker`). Use Edge/Chrome and open the app from http://localhost (npm run dev) or https:// — not all contexts expose the picker.",
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
      tipToast = showToast("Picker tip", "If blocked by “system files”, open the guide for a workaround.", "info", {
        actionLabel: "Guide",
        onAction: () => openHelp(),
        durationMs: Infinity,
      });
      if (isWin) {
        appendHistory("Windows: prefer a hard link to the log file — open ?, paste the full path to client-main.log, run the generated mklink /H in cmd.");
        appendHistory("Folder junctions to AppData often still fail in the picker; /H on the file under Documents usually works.");
        appendHistory("Older fallback (junction): mkdir + mklink /J from ? when you paste a folder path, or see README.");
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
      showToast("Pick cancelled", "No file was selected.", "warn", {
        actionLabel: "Guide",
        onAction: () => openHelp(),
        durationMs: 7000,
      });
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
      showToast("Picker blocked", "Browser denied access (protected/system location).", "error", {
        actionLabel: "Guide",
        onAction: () => openHelp(),
        durationMs: 9000,
      });
      appendHistory("Note: browsers do not reveal the exact filesystem path you attempted to pick, so we can’t auto-generate a command with the exact blocked path.");
      appendHistory('Tip: click "?" and paste the full path to client-main.log — the app generates mklink /H (hard link), which usually works when folder junctions do not.');
      appendHistory("Windows fallback (junction; may still be blocked by the picker):");
      appendHistory('  mkdir "%USERPROFILE%\\Documents\\VintagestoryData"');
      appendHistory('  mklink /J "%USERPROFILE%\\Documents\\VintagestoryData" "%APPDATA%\\VintagestoryData"');
      appendHistory("Explanation: exposes VintagestoryData under Documents; Edge/Chrome may still treat it as a system path.");
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
  tipToast?.remove();
  if (!handle) return;
  const pickedName = (await handle.getFile()).name;
  await applyPickedLogHandle(handle, "Picked file", {
    historyLine: `Selected log file: ${pickedName}`,
  });
  startMonitoringAfterSuccessfulPick();

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
      showToast("Pick cancelled", "No folder was selected.", "warn", {
        actionLabel: "Guide",
        onAction: () => openHelp(),
        durationMs: 7000,
      });
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
  const pickedName = (await file.getFile()).name;
  await applyPickedLogHandle(file, "Picked folder", {
    historyLine: `Selected folder; resolved log file: ${pickedName}`,
  });
  startMonitoringAfterSuccessfulPick();
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
    const cls = passed ? "kpiWarn--hit" : "kpiWarn--pending";
    parts.push(`<span class="${cls}">${escapeHtml(String(t))}</span>`);
  }
  ui.kpiWarnings.innerHTML = parts.join('<span class="kpiWarn--sep"> · </span>');
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
 * Rebuild graph points from a full log snapshot (first load / truncate resync), matching live poll semantics.
 * @param {string} fullText
 */
function replayQueueGraphFromText(fullText) {
  const text = sliceLoadedLogToCurrentQueueRun(fullText);
  if (!text) {
    graphPoints = [];
    currentPoint = null;
    lastPosition = null;
    drawGraph();
    return;
  }
  const lines = text.split(/\r?\n/);
  const sessionBeforeLine = new Array(lines.length);
  let s = 0;
  for (let i = 0; i < lines.length; i++) {
    sessionBeforeLine[i] = s;
    if (isQueueRunBoundaryLine(lines[i])) s++;
  }

  graphPoints = [];
  currentPoint = null;
  lastPosition = null;
  /** @type {number|null} */
  let sessionAtLastEmit = null;

  let lastQIdx = -1;
  let lastQueuePos = /** @type {number|null} */ (null);
  let lastQueueEpoch = /** @type {number|null} */ (null);

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];
    if (isQueueRunBoundaryLine(line)) continue;

    const rawPos = queuePositionFromLine(line);
    if (rawPos != null) {
      lastQIdx = i;
      lastQueuePos = rawPos;
      lastQueueEpoch = parseLogTimestampEpoch(line);
    }

    if (lastQIdx < 0 || lastQueuePos == null) continue;

    const sess = sessionBeforeLine[lastQIdx];
    let pos = lastQueuePos;

    let left = false;
    for (let j = lastQIdx + 1; j <= i; j++) {
      if (isPostQueueProgressLine(lines[j])) {
        left = true;
        break;
      }
    }

    const prevPos = lastPosition;
    if (
      prevPos != null &&
      sessionAtLastEmit != null &&
      sess === sessionAtLastEmit &&
      pos > prevPos &&
      pos - prevPos >= QUEUE_RESET_JUMP_THRESHOLD
    ) {
      pos = prevPos;
    }

    if (pos <= 1 && left) pos = 0;

    const t = lastQueueEpoch ?? Date.now() / 1000;

    if (!currentPoint || currentPoint[1] !== pos) {
      currentPoint = [t, pos];
      graphPoints.push(currentPoint);
      if (graphPoints.length > 5000) graphPoints = graphPoints.slice(-5000);
      lastPosition = pos;
      sessionAtLastEmit = sess;
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
      const start = Math.max(0, size - INITIAL_FULL_READ_MAX_BYTES);
      seed = await readLogRangeText(handle, start, size);
      appendHistory(
        `Large log (${(size / (1024 * 1024)).toFixed(1)} MB); loaded last ${(INITIAL_FULL_READ_MAX_BYTES / (1024 * 1024)).toFixed(0)} MB for history and graph.`,
      );
    }
    const rawLen = seed.length;
    seed = sliceLoadedLogToCurrentQueueRun(seed);
    if (seed.length < rawLen) {
      appendHistory("Using current queue session only (earlier reconnects omitted from this load).");
    }
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
    seed = sliceLoadedLogToCurrentQueueRun(seed);
    if (seed.length < rawLenT) {
      appendHistory("Using current queue session only (earlier reconnects omitted from this load).");
    }
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
    if (replayChunk != null) replayQueueGraphFromText(replayChunk);
    const view = logBuffer || "";
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
      leftConnectQueueDetected = false;
      progressAtFrontEntry = null;
      positionOneReachedAt = null;
      connectPhaseStartedEpoch = null;
      setStatus(logSilent || kind === "grace" ? "Reconnecting…" : "Connecting…");
      setPositionDisplay(null);
      lastPosition = null;
      return;
    }

    if (!interruptedMode && lastPos != null && (!logSilent || lastPos <= 1)) {
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
  ui.btnPickFolder.disabled = true;
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

  if (pollTimer != null) window.clearInterval(pollTimer);
  pollTimer = window.setInterval(() => pollOnce(), Math.max(200, config.pollSec * 1000));
  if (estimateTimer != null) window.clearInterval(estimateTimer);
  estimateTimer = window.setInterval(() => updateTimeEstimates(), 100);
  pollOnce();
}

function stopMonitoring() {
  running = false;
  setStartStopButtonLook(false);
  ui.btnPickLog.disabled = false;
  ui.btnPickFolder.disabled = false;
  if (pollTimer != null) window.clearInterval(pollTimer);
  pollTimer = null;
  if (estimateTimer != null) window.clearInterval(estimateTimer);
  estimateTimer = null;
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
  return best;
}

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
  if (!Number.isFinite(minP) || !Number.isFinite(maxP)) {
    lastGraphLayout = null;
    return;
  }
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
  ctx.strokeStyle = "rgba(55,65,82,0.55)";
  ctx.lineWidth = 1;
  for (let i = 0; i <= 6; i++) {
    const y = padT + (i / 6) * plotH;
    ctx.beginPath();
    ctx.moveTo(padL, y);
    ctx.lineTo(w - padR, y);
    ctx.stroke();
  }

  // Axes labels (simple)
  ctx.fillStyle = "rgba(155,165,176,0.92)";
  ctx.font = "12px " + getComputedStyle(document.documentElement).getPropertyValue("--mono");
  ctx.textAlign = "right";
  ctx.textBaseline = "middle";
  const yLabels = [maxP, Math.round((maxP + minP) / 2), minP];
  for (const val of yLabels) {
    const y = graphYMap(val, minP, maxP, h);
    ctx.fillText(String(val), padL - 8, y);
  }

  // Series (step plot)
  ctx.strokeStyle = "rgba(100,168,255,0.92)";
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
  ctx.fillStyle = "rgba(130,200,255,0.98)";
  ctx.beginPath();
  ctx.arc(xm, ym, 4.5, 0, Math.PI * 2);
  ctx.fill();

  lastGraphLayout = { padL, padR, padT, padB, plotW, plotH, w, h, t1, span, minP, maxP };
}

// -----------------------------
// Wire up UI
// -----------------------------

loadConfig();
syncConfigToForm();
setStatus("Idle");
refreshWarningsKpi();
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

ui.graphCanvas.addEventListener("mouseenter", () => {
  graphCanvasHovering = true;
});
ui.graphCanvas.addEventListener("mouseleave", () => {
  graphCanvasHovering = false;
  ui.graphHint.textContent = graphHintDefaultText();
});
ui.graphCanvas.addEventListener("mousemove", (e) => {
  const pt = hitTestGraphPoint(e.clientX, e.clientY);
  if (pt) {
    ui.graphHint.textContent = `${formatGraphHoverTime(pt[0])} — position ${pt[1]}`;
  } else {
    ui.graphHint.textContent = graphHintDefaultText();
  }
});

drawGraph();

