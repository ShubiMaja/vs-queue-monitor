/* global WebSocket, fetch, document, window, localStorage */
(function () {
  "use strict";

  window._graphTheme = null;
  window._graphHover = null;

  var lastAlertSeq = null;
  var lastCompletionSeq = null;
  var LS_PATH = "vs_queue_monitor_web_last_path";
  var LS_PATH_LEGACY = "vsqm_web_last_path";
  var LS_SESSION = "vs_queue_monitor_selected_session_v1";
  var LS_SESSION_LEGACY = "vsqm_selected_session_v1";
  var selectedSessionKey = "latest";
  var _sessionDropdownInited = false;
  var _restoreOnce = false;
  /** True after we POST saved local path because the engine had no source_path (sync with localStorage). */
  var _pathRehydratePosted = false;
  var notifySyncHint = null;

  function lsGetPath() {
    try {
      var v = localStorage.getItem(LS_PATH);
      if (v != null && v !== "") return v;
      return localStorage.getItem(LS_PATH_LEGACY);
    } catch (e) {
      return null;
    }
  }
  function lsSetPath(val) {
    try {
      localStorage.setItem(LS_PATH, val);
      localStorage.removeItem(LS_PATH_LEGACY);
    } catch (e) {}
  }
  function lsGetSession() {
    try {
      var v = localStorage.getItem(LS_SESSION);
      if (v != null && v !== "") return v;
      return localStorage.getItem(LS_SESSION_LEGACY);
    } catch (e) {
      return null;
    }
  }
  function lsSetSession(val) {
    try {
      localStorage.setItem(LS_SESSION, val);
      localStorage.removeItem(LS_SESSION_LEGACY);
    } catch (e) {}
  }

  function $(id) {
    return document.getElementById(id);
  }

  /** True while a modal, tour, or restore banner is visible — block global single-key shortcuts. */
  function uiBlockingLayerOpen() {
    var ids = ["modalNewQueue", "modalPath", "modalHelp", "modalSettings", "tourOverlay"];
    var i;
    for (i = 0; i < ids.length; i++) {
      var el = $(ids[i]);
      if (el && !el.classList.contains("hidden")) return true;
    }
    var rb = $("restoreBanner");
    return !!(rb && !rb.classList.contains("hidden"));
  }

  function focusElSoon(el) {
    if (!el) return;
    setTimeout(function () {
      try {
        el.focus();
      } catch (e) {}
    }, 0);
  }

  function showEl(el) {
    if (!el) return;
    el.classList.remove("hidden");
    el.setAttribute("aria-hidden", "false");
  }

  function hideEl(el) {
    if (!el) return;
    el.classList.add("hidden");
    el.setAttribute("aria-hidden", "true");
  }

  function closeHelpModal() {
    var mh = $("modalHelp");
    if (!mh || mh.classList.contains("hidden")) return;
    hideEl(mh);
    focusElSoon($("btnHelp"));
  }

  function closeSettingsModal() {
    var ms = $("modalSettings");
    if (!ms || ms.classList.contains("hidden")) return;
    hideEl(ms);
    focusElSoon($("btnSettings"));
  }

  /** Header shows only whether a path is configured; the full path is in Info and in tooltip / aria-label. */
  function syncPathDisplay() {
    var inp = $("inpPath");
    var tx = $("pathSummaryText");
    var btn = $("pathSummary");
    var raw = inp ? String(inp.value || "").trim() : "";
    if (tx) tx.textContent = raw ? "Path set" : "Not set";
    if (btn) btn.classList.toggle("path-summary--empty", !raw);
    if (btn) {
      btn.title = raw ? raw : "Click to paste path, or use the folder / file icons";
      btn.setAttribute(
        "aria-label",
        raw
          ? "Log source path set. Full path: " + raw + ". Click to edit."
          : "Log source not set. Click to paste path.",
      );
    }
  }

  /** Before the first WebSocket snapshot, show the last saved path so the header is not blank. */
  function hydratePathFromStorageEarly() {
    var inp = $("inpPath");
    if (!inp) return;
    if (String(inp.value || "").trim()) return;
    var saved = "";
    try {
      saved = (lsGetPath() || "").trim();
    } catch (e) {}
    if (saved) {
      inp.value = saved;
      syncPathDisplay();
    }
  }

  function toast(msg, kind) {
    const host = $("toastHost");
    if (!host) return;
    const el = document.createElement("div");
    el.className = "toast" + (kind === "warn" ? " toast--warn" : "");
    el.textContent = msg;
    host.appendChild(el);
    setTimeout(function () {
      try {
        el.remove();
      } catch (e) {}
    }, 6500);
  }

  var NOTIFY_ICON_PATH = "/notify-icon.svg";

  function notifyIconUrl() {
    try {
      return new URL(NOTIFY_ICON_PATH, location.href).href;
    } catch (e) {
      return NOTIFY_ICON_PATH;
    }
  }

  /**
   * Richer desktop notifications: app icon, badge, timestamp; pass tag to control deduplication in the OS.
   */
  function desktopNotify(title, extra) {
    var o = {
      icon: notifyIconUrl(),
      badge: notifyIconUrl(),
      timestamp: Date.now(),
      lang: "en",
    };
    if (extra && typeof extra === "object") {
      var k;
      for (k in extra) {
        if (Object.prototype.hasOwnProperty.call(extra, k)) o[k] = extra[k];
      }
    }
    return new Notification(title, o);
  }

  function postConfig(patch) {
    return fetch("/api/config", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(patch),
    }).then(function (r) {
      return r.json().then(function (j) {
        if (!r.ok) throw new Error(j.error || r.statusText);
        return j;
      });
    });
  }

  function postToggle() {
    return fetch("/api/monitoring/toggle", { method: "POST" }).then(function (r) {
      return r.json();
    });
  }

  function postReset() {
    return fetch("/api/reset_defaults", { method: "POST" }).then(function (r) {
      return r.json();
    });
  }

  function postNewQueue(accept) {
    return fetch("/api/new_queue", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ accept: !!accept }),
    }).then(function (r) {
      return r.json().then(function (j) {
        if (!r.ok) throw new Error(j.error || r.statusText);
        return j;
      });
    });
  }

  /** Native folder/file dialog via Python (Tk) on the machine running the app. */
  function pickPath(mode) {
    return fetch("/api/pick_path", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ mode: mode }),
    }).then(function (r) {
      return r.json().then(function (j) {
        if (!r.ok) throw new Error(j.error || r.statusText);
        return j;
      });
    });
  }

  function applyChromeTheme(chrome) {
    if (!chrome || typeof chrome !== "object") {
      return;
    }
    var root = document.documentElement;
    Object.keys(chrome).forEach(function (k) {
      root.style.setProperty(k, chrome[k]);
    });
  }

  function drawGraph(canvas, state) {
    if (!window.VsQueueMonitorGraph) {
      return;
    }
    var ctx = canvas.getContext("2d");
    if (!ctx) {
      return;
    }
    VsQueueMonitorGraph.draw(ctx, canvas, state, window._graphTheme, window._graphHover, window._graphZoom);
  }

  function redrawGraphOnly() {
    resizeCanvas();
  }

  /** Duration for stats (H:MM:SS or M:SS), same logic as legacy web UI. */
  function formatDurationHms(totalSeconds) {
    if (totalSeconds == null || !Number.isFinite(totalSeconds) || totalSeconds < 0) {
      return "—";
    }
    var s = Math.floor(totalSeconds);
    var h = Math.floor(s / 3600);
    var m = Math.floor((s % 3600) / 60);
    var ss = s % 60;
    if (h > 0) {
      return h + ":" + String(m).padStart(2, "0") + ":" + String(ss).padStart(2, "0");
    }
    return m + ":" + String(ss).padStart(2, "0");
  }

  /** Graph tooltip: sub-second as N.NNs, otherwise same as stats (e.g. 1:33, 1:05:02). */
  function formatTooltipDuration(sec) {
    if (sec == null || !Number.isFinite(sec) || sec < 0) {
      return "—";
    }
    if (sec < 1) {
      return sec.toFixed(2) + "s";
    }
    return formatDurationHms(sec);
  }

  /**
   * Stats for the currently displayed graph (same scope as Session / Copy graph TSV).
   * Ported from feature/change-to-web-ui computeSelectedSessionStats.
   */
  function computeGraphSessionStats() {
    var pts = (window._displayState && window._displayState.graph_points) || [];
    if (!pts.length) {
      return {
        startPos: null,
        endPos: null,
        cleared: null,
        seconds: null,
        minutes: null,
        avgMinPerPos: null,
      };
    }
    var startPos = null;
    var startT = null;
    var i;
    for (i = 0; i < pts.length; i++) {
      if (pts[i][1] > 1) {
        startPos = pts[i][1];
        startT = pts[i][0];
        break;
      }
    }
    if (startPos == null) {
      startPos = pts[0][1];
      startT = pts[0][0];
    }
    var endPos = pts[pts.length - 1][1];
    var endT = pts[pts.length - 1][0];
    var seconds = startT != null && endT != null ? Math.max(0, endT - startT) : null;
    var minutes = seconds != null ? seconds / 60 : null;
    var cleared = startPos != null && endPos != null ? Math.max(0, startPos - endPos) : null;
    var avgMinPerPos =
      minutes != null && minutes > 0 && cleared != null && cleared > 0 ? minutes / cleared : null;
    return { startPos: startPos, endPos: endPos, cleared: cleared, seconds: seconds, minutes: minutes, avgMinPerPos: avgMinPerPos };
  }

  function renderSessionStats() {
    var stats = computeGraphSessionStats();
    var elS = $("infoStatStart");
    var elE = $("infoStatEnd");
    var elC = $("infoStatCleared");
    var elSp = $("infoStatSpan");
    var elA = $("infoStatAvg");
    if (elS) elS.textContent = stats.startPos == null ? "—" : String(stats.startPos);
    if (elE) elE.textContent = stats.endPos == null ? "—" : String(stats.endPos);
    if (elC) elC.textContent = stats.cleared == null ? "—" : String(stats.cleared);
    if (elSp) elSp.textContent = formatDurationHms(stats.seconds);
    if (elA) {
      elA.textContent =
        stats.avgMinPerPos == null ? "—" : stats.avgMinPerPos.toFixed(2) + " min/pos";
    }
  }

  function copyStatsToClipboard() {
    var stats = computeGraphSessionStats();
    var text =
      "Start Pos: " + (stats.startPos == null ? "—" : stats.startPos) + "\n" +
      "End Pos: " + (stats.endPos == null ? "—" : stats.endPos) + "\n" +
      "Pos Delta: " + (stats.cleared == null ? "—" : stats.cleared) + "\n" +
      "Duration: " +
      (stats.minutes == null ? "—" : stats.minutes.toFixed(1) + " min") +
      "\n" +
      "Avg Rate: " +
      (stats.avgMinPerPos == null ? "—" : stats.avgMinPerPos.toFixed(2) + " min/pos") +
      "\n";
    navigator.clipboard.writeText(text).then(
      function () {
        toast("Stats copied");
      },
      function () {
        toast("Could not copy stats (clipboard permission)", "warn");
      },
    );
  }

  function copyHistoryToClipboard() {
    var hp = $("historyPre");
    var txt = hp ? hp.textContent || "" : "";
    if (!txt.trim()) {
      toast("No history to copy", "warn");
      return;
    }
    navigator.clipboard.writeText(txt).then(
      function () {
        toast("Session history copied");
      },
      function () {
        toast("Clipboard failed", "warn");
      },
    );
  }

  function formatSessionStart(epoch) {
    if (epoch == null || !isFinite(epoch)) {
      return "—";
    }
    if (typeof dayjs === "function") {
      return dayjs.unix(epoch).format("YYYY-MM-DD HH:mm:ss");
    }
    return new Date(epoch * 1000).toLocaleString();
  }

  function buildDisplayState(s) {
    var out = {};
    var k;
    for (k in s) {
      if (Object.prototype.hasOwnProperty.call(s, k)) {
        out[k] = s[k];
      }
    }
    var key = selectedSessionKey || "latest";
    if (key === "latest" || !s.queue_sessions || !s.queue_sessions.length) {
      return out;
    }
    var sess = null;
    var i;
    for (i = 0; i < s.queue_sessions.length; i++) {
      if (s.queue_sessions[i].key === key) {
        sess = s.queue_sessions[i];
        break;
      }
    }
    if (!sess && key.indexOf("t:") === 0) {
      var m = /^t:(\d+)/.exec(key);
      var ep = m ? parseInt(m[1], 10) : NaN;
      if (isFinite(ep)) {
        for (i = 0; i < s.queue_sessions.length; i++) {
          var se = s.queue_sessions[i].start_epoch;
          if (se != null && Math.floor(se) === ep) {
            sess = s.queue_sessions[i];
            break;
          }
        }
      }
    }
    if (!sess || !sess.points || !sess.points.length) {
      return out;
    }
    out.graph_points = sess.points;
    var last = sess.points[sess.points.length - 1];
    out.current_point = [last[0], last[1]];
    return out;
  }

  function rebuildSessionDropdown(s) {
    var sel = $("selSession");
    if (!sel) {
      return;
    }
    var sessions = s.queue_sessions || [];
    sel.innerHTML = "";
    var opt0 = document.createElement("option");
    opt0.value = "latest";
    opt0.textContent = "Latest session (auto)";
    opt0.title = "Live engine graph for the current queue run.";
    sel.appendChild(opt0);
    var i;
    for (i = 0; i < sessions.length; i++) {
      var o = document.createElement("option");
      o.value = sessions[i].key;
      o.textContent = (sessions[i].label || "Session") + " — " + formatSessionStart(sessions[i].start_epoch);
      o.title =
        "Start: " +
        formatSessionStart(sessions[i].start_epoch) +
        "\nEnd: " +
        formatSessionStart(sessions[i].end_epoch) +
        "\nPoints: " +
        (sessions[i].points ? sessions[i].points.length : 0);
      sel.appendChild(o);
    }
    if (!_sessionDropdownInited) {
      _sessionDropdownInited = true;
      try {
        var saved = (lsGetSession() || "").trim();
        if (saved) {
          selectedSessionKey = saved;
        }
      } catch (e) {}
    }
    var valid = selectedSessionKey === "latest";
    if (!valid) {
      for (i = 0; i < sessions.length; i++) {
        if (sessions[i].key === selectedSessionKey) {
          valid = true;
          break;
        }
      }
    }
    if (!valid) {
      selectedSessionKey = "latest";
    }
    sel.value = selectedSessionKey;
    if (sel.value !== selectedSessionKey) {
      sel.value = "latest";
      selectedSessionKey = "latest";
    }
    try {
      lsSetSession(selectedSessionKey);
    } catch (e) {}
    sel.title =
      sessions.length > 0
        ? "Plot a past queue run from the log tail; KPIs above stay live."
        : "More queue sessions appear here when the log has more than one run in the saved tail.";
    updateSessionBadge();
  }

  function updateSessionBadge() {
    var badge = $("sessionScopeBadge");
    if (!badge) return;
    if (selectedSessionKey && selectedSessionKey !== "latest") {
      badge.classList.remove("hidden");
    } else {
      badge.classList.add("hidden");
    }
  }

  function setupSessionSelect() {
    var sel = $("selSession");
    if (!sel) {
      return;
    }
    sel.addEventListener("change", function () {
      selectedSessionKey = sel.value || "latest";
      try {
        lsSetSession(selectedSessionKey);
      } catch (e) {}
      updateSessionBadge();
      if (window._lastState) {
        window._displayState = buildDisplayState(window._lastState);
        redrawGraphOnly();
        renderSessionStats();
      }
    });
  }

  function tryRestoreBanner(s) {
    var rb = $("restoreBanner");
    if (!rb) return;
    if (_pathRehydratePosted) {
      rb.classList.add("hidden");
      return;
    }
    var saved = "";
    try {
      saved = (lsGetPath() || "").trim();
    } catch (e) {}
    var cur = (s.source_path || "").trim();
    if (!saved || cur) {
      rb.classList.add("hidden");
      return;
    }
    $("restoreBannerDetail").textContent = "Resume last folder path? " + saved;
    rb.classList.remove("hidden");
    focusElSoon($("btnResumePath"));
  }

  function setKpiMetric(el, raw, emptyTitle) {
    if (!el) return;
    var t = raw == null || raw === "" ? "—" : String(raw);
    el.textContent = t;
    if (t === "—") {
      el.classList.add("kpi__val--empty");
      if (emptyTitle) el.title = emptyTitle;
    } else {
      el.classList.remove("kpi__val--empty");
      el.removeAttribute("title");
    }
  }

  function applyState(s) {
    setKpiMetric(
      $("kpiPos"),
      s.position,
      "No queue position in the log yet — start monitoring or check the log path.",
    );
    setKpiMetric($("kpiStatus"), s.status, "Engine status — idle until monitoring starts.");
    var rh = $("kpiRateHdr");
    if (rh) rh.textContent = s.rate_header || "RATE";
    setKpiMetric(
      $("kpiRate"),
      s.queue_rate,
      "No rate yet — need more queue movement in the rolling window.",
    );
    setKpiMetric($("kpiElapsed"), s.elapsed, "Timer starts once queue timing is available.");
    setKpiMetric(
      $("kpiRem"),
      s.remaining,
      "No ETA yet — need more samples or movement in the log.",
    );
    const prog = Math.max(0, Math.min(100, s.progress || 0));
    $("kpiProgFill").style.width = prog + "%";
    var pp = $("kpiProgPct");
    if (pp) {
      var pctText = Math.round(prog) + "%";
      pp.textContent = pctText;
      if (prog === 0) pp.classList.add("kpi__val--empty");
      else pp.classList.remove("kpi__val--empty");
    }

    const w = s.warnings || [];
    const kw = $("kpiWarnings");
    kw.innerHTML = "";
    w.forEach(function (row, i) {
      if (i) kw.appendChild(document.createTextNode(" · "));
      const sp = document.createElement("span");
      sp.textContent = row.t;
      sp.className = row.passed ? "warn-off" : "warn-on";
      kw.appendChild(sp);
    });
    if (!w.length) {
      kw.textContent = "—";
      kw.classList.add("kpi__val--empty");
      kw.title =
        "Threshold positions — configure under Settings; values show when the queue crosses them.";
    } else {
      kw.classList.remove("kpi__val--empty");
      kw.removeAttribute("title");
    }

    $("infoLastCh").textContent = s.last_change || "—";
    $("infoLastAl").textContent = s.last_alert || "—";
    $("infoPath").textContent = s.resolved_path || "—";
    $("infoGlo").textContent = s.global_rate || "—";

    const aseq = typeof s.last_alert_seq === "number" ? s.last_alert_seq : 0;
    const alertMsg = (s.last_alert_message || "").trim();
    if (
      lastAlertSeq !== null &&
      aseq > lastAlertSeq &&
      alertMsg &&
      alertMsg !== "—"
    ) {
      toast(alertMsg, "warn");
      if (
        s.popup_enabled &&
        typeof Notification !== "undefined" &&
        Notification.permission === "granted"
      ) {
        try {
          var posStr =
            s.position != null && String(s.position).trim() !== ""
              ? String(s.position).trim()
              : null;
          var statStr =
            s.status != null && String(s.status).trim() !== ""
              ? String(s.status).trim()
              : null;
          var detail = [];
          if (posStr != null) detail.push("Position " + posStr);
          if (statStr) detail.push(statStr);
          var threshBody = alertMsg;
          if (detail.length) threshBody = alertMsg + "\n\n" + detail.join(" · ");
          desktopNotify("Threshold crossed", {
            body: threshBody,
            tag: "vsqm-threshold-" + aseq,
          });
        } catch (e) {
          toast(
            "Could not show a desktop notification (check Windows Settings → System → Notifications for this app).",
            "warn",
          );
        }
      }
    }
    lastAlertSeq = aseq;

    const cseq = typeof s.completion_notify_seq === "number" ? s.completion_notify_seq : 0;
    if (lastCompletionSeq !== null && cseq > lastCompletionSeq) {
      toast("Past queue wait — connecting (position 0).", "");
      if (
        s.completion_popup &&
        typeof Notification !== "undefined" &&
        Notification.permission === "granted"
      ) {
        try {
          desktopNotify("Queue wait finished", {
            body:
              "Past queue wait — connecting (position 0).\n\nThe in-queue wait is over; the app shows live connection status.",
            tag: "vsqm-completion-" + cseq,
          });
        } catch (e) {
          toast(
            "Could not show a desktop notification (check Windows Settings → System → Notifications for this app).",
            "warn",
          );
        }
      }
    }
    lastCompletionSeq = cseq;

    var srvPath = (s.source_path || "").trim();
    var lsPath = "";
    try {
      lsPath = (lsGetPath() || "").trim();
    } catch (e) {}
    var inpPathEl = $("inpPath");
    if (!_pathRehydratePosted && !srvPath && lsPath && inpPathEl) {
      _pathRehydratePosted = true;
      inpPathEl.value = lsPath;
      syncPathDisplay();
      postConfig({ source_path: lsPath }).catch(function (err) {
        toast(String(err.message || err), "warn");
      });
    } else if (inpPathEl) {
      if (srvPath) {
        inpPathEl.value = srvPath;
        syncPathDisplay();
      } else if (!_pathRehydratePosted) {
        inpPathEl.value = "";
        syncPathDisplay();
      }
    }
    try {
      var pth = (inpPathEl && String(inpPathEl.value || "").trim()) || (s.source_path || "").trim();
      if (pth) lsSetPath(pth);
    } catch (e) {}

    var chkGL = $("chkGraphLog");
    if (chkGL) chkGL.checked = !!s.graph_log_scale;
    var chkGV = $("chkGraphLive");
    if (chkGV) chkGV.checked = !!s.graph_live_view;

    var btnSS = $("btnStartStop");
    if (btnSS) {
      btnSS.textContent = s.running ? "Stop" : "Start";
      btnSS.className = s.running ? "btn btn--danger" : "btn btn--primary";
      btnSS.title = s.running ? "Stop monitoring" : "Start monitoring";
      btnSS.setAttribute("aria-label", s.running ? "Stop monitoring" : "Start monitoring");
    }

    const logEl = $("lblLogAct");
    if (logEl) {
      if (!s.running) logEl.textContent = "";
      else {
        const g = s.last_log_growth_epoch;
        const now = Date.now() / 1000;
        if (g == null) logEl.textContent = "Log: waiting for file activity";
        else if (now - g >= 30) logEl.textContent = "Log quiet ≥30s (reconnecting or idle)";
        else logEl.textContent = "Log active (" + Math.round(now - g) + "s since growth)";
      }
    }

    const hp = $("historyPre");
    if (hp && s.history_tail) {
      hp.textContent = s.history_tail.join("\n");
      hp.scrollTop = hp.scrollHeight;
    }

    $("chkEvery").checked = !!s.show_every_change;
    $("chkPop").checked = !!s.popup_enabled;
    $("chkSnd").checked = !!s.sound_enabled;
    $("chkCompPop").checked = !!s.completion_popup;
    $("chkCompSnd").checked = !!s.completion_sound;

    var iws = $("inpSetWarnSound");
    if (iws) iws.value = s.alert_sound_path || "";
    var ics = $("inpSetCompSound");
    if (ics) ics.value = s.completion_sound_path || "";

    var mnq = $("modalNewQueue");
    if (mnq) {
      if (s.pending_new_queue_session != null && s.pending_new_queue_session !== undefined) {
        showEl(mnq);
        var nb = $("modalNewQueueBody");
        if (nb)
          nb.innerHTML =
            "<p>A new queue session was detected in the log while you were in <strong>Interrupted</strong> state.</p>" +
            "<p>Session id <strong>" +
            String(s.pending_new_queue_session) +
            "</strong>. Load it? This resets the chart and threshold alerts for the new run.</p>";
        focusElSoon($("btnNewQueueYes"));
      } else {
        hideEl(mnq);
      }
    }

    if (!_restoreOnce) {
      _restoreOnce = true;
      tryRestoreBanner(s);
    }

    rebuildSessionDropdown(s);
    window._displayState = buildDisplayState(s);
    renderSessionStats();
    var fv = $("footerVersion");
    if (fv) {
      var bf = s.build_fingerprint || "";
      fv.textContent = "v" + (s.version || "") + (bf ? " (" + bf + ")" : "");
    }

    var kh = $("kpiHint");
    if (kh) {
      var noPath = !(s.source_path || "").trim();
      if (!s.running && noPath) {
        kh.textContent = "Set the Vintage Story logs folder above, then click Start.";
        kh.classList.remove("hidden");
      } else if (s.running && typeof s.status === "string" && s.status.indexOf("Waiting") === 0) {
        kh.textContent = "Monitoring started — looking for client-main.log in the selected folder.";
        kh.classList.remove("hidden");
      } else {
        kh.classList.add("hidden");
      }
    }

    if (notifySyncHint) notifySyncHint();
    resizeCanvas();
  }

  function resizeCanvas() {
    if (!window._displayState) return;
    const c = $("graphCanvas");
    const wrap = c.parentElement;
    if (!wrap) return;
    const dpr = window.devicePixelRatio || 1;
    const rect = wrap.getBoundingClientRect();
    const w = Math.max(1, Math.floor(rect.width));
    const h = window._graphH || 280;
    c.width = w * dpr;
    c.height = h * dpr;
    c.style.width = w + "px";
    c.style.height = h + "px";
    const ctx = c.getContext("2d");
    if (ctx) ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    if (window._displayState) drawGraph(c, window._displayState);
  }

  window._lastState = null;
  window._displayState = null;
  window._graphH = parseInt(localStorage.getItem('vsqm_graph_h') || '', 10) || 280;
  window._graphZoom = null;

  var _wsEverConnected = false;
  var _disconnectOverlayShown = false;

  function _showDisconnectOverlay() {
    if (_disconnectOverlayShown) return;
    _disconnectOverlayShown = true;
    var overlay = document.getElementById("serverStoppedOverlay");
    if (!overlay) return;
    overlay.classList.remove("hidden");
    var btn = document.getElementById("btnCloseTab");
    if (btn) btn.addEventListener("click", function () { window.close(); });
  }

  function _hideDisconnectOverlay() {
    if (!_disconnectOverlayShown) return;
    _disconnectOverlayShown = false;
    var overlay = document.getElementById("serverStoppedOverlay");
    if (overlay) overlay.classList.add("hidden");
  }

  function connectWs() {
    const proto = location.protocol === "https:" ? "wss:" : "ws:";
    const ws = new WebSocket(proto + "//" + location.host + "/ws");
    ws.onmessage = function (ev) {
      _wsEverConnected = true;
      _hideDisconnectOverlay();
      try {
        const s = JSON.parse(ev.data);
        window._lastState = s;
        applyState(s);
      } catch (e) {}
    };
    ws.onopen = function () {
      _wsEverConnected = true;
      _hideDisconnectOverlay();
    };
    ws.onclose = function () {
      if (_wsEverConnected) _showDisconnectOverlay();
      setTimeout(connectWs, 1500);
    };
  }

  function setupTour() {
    const steps = [
      {
        title: "Welcome",
        html:
          '<p class="tutorial-lead"><strong>~2 minutes</strong> — set your logs folder, tune warnings and rolling window, then start.</p>' +
          "<ul class=\"tutorial-list\"><li>Paste the <strong>folder</strong> that contains <code>client-main.log</code> (Python reads the disk; nothing is uploaded).</li>" +
          "<li>Warnings default to <strong>10, 5, 1</strong> (alerts on downward crossings).</li>" +
          "<li>Rolling window defaults to <strong>10</strong> points.</li></ul>",
        sel: null,
      },
      {
        title: "Log source",
        html:
          '<p>Paste your <strong>VintagestoryData</strong> or <strong>Logs</strong> path, or use the <strong>folder</strong> / <strong>log file</strong> icons for a system dialog on this PC.</p>' +
          "<p class=\"muted\">Typical: Windows <code>%APPDATA%\\\\VintagestoryData</code> · macOS <code>~/Library/Application Support/VintagestoryData</code> · Linux <code>~/.config/VintagestoryData</code></p>" +
          '<p class="muted">Open <strong>?</strong> for paths and where the config file lives.</p>',
        sel: ".topbar__path",
      },
      {
        title: "Warnings",
        html:
          "<p>Milestones that trigger alerts as you approach the front.</p>" +
          '<p>Use <strong>+</strong> to add one threshold or <strong>✎</strong> to edit the full list.</p>',
        sel: "#kpiWarnRail",
      },
      {
        title: "Rolling rate",
        html:
          "<p><strong>✎</strong> on the RATE header edits the rolling window (points). Larger = smoother ETA, slower to react.</p>",
        sel: "#kpiRateLabel",
      },
      {
        title: "Session stats",
        html:
          "<p><strong>Stats</strong> summarize the <strong>same graph</strong> as the Session dropdown (per queue run).</p>" +
          "<p>Use <strong>Copy stats</strong> and <strong>Copy history</strong> for plain-text clipboard export.</p>",
        sel: "#infoStatsRows",
      },
      {
        title: "Chart & alerts",
        html:
          "<p>Use <strong>Session</strong> to plot an earlier queue run from the log tail (KPIs stay live).</p>" +
          "<p><strong>⚙ Settings</strong> sets log/linear <strong>Y</strong> and <strong>live view</strong>. Tap or hover the chart for a <strong>tooltip</strong>. <strong>Copy PNG / TSV</strong> for sharing.</p>" +
          "<p>Use the <strong>notification switch</strong> in the header to allow browser alerts or turn them off; <strong>Send test notification</strong> in Settings checks banners.</p>" +
          "<p>Open <strong>⚙</strong> for sounds and history verbosity. You’re ready — <strong>Start</strong> when the path is set.</p>",
        sel: "#graphCanvas",
      },
    ];
    let idx = 0;
    const overlay = $("tourOverlay");
    const spotlight = $("tourSpotlight");
    const card = $("tourCard");
    if (card)
      card.addEventListener("click", function (e) {
        e.stopPropagation();
      });
    const title = $("tourTitle");
    const body = $("tourBody");
    const stepNum = $("tourStepNum");
    const btnNext = $("tourNext");
    const btnBack = $("tourBack");
    const btnSkip = $("tourSkip");

    function placeCard() {
      const step = steps[idx];
      if (step.sel) {
        const el = document.querySelector(step.sel);
        if (el) {
          const r = el.getBoundingClientRect();
          spotlight.style.display = "block";
          spotlight.style.left = r.left - 6 + "px";
          spotlight.style.top = r.top - 6 + "px";
          spotlight.style.width = r.width + 12 + "px";
          spotlight.style.height = r.height + 12 + "px";
          overlay.classList.add("active");
          card.style.transform = "";
          card.style.left = Math.min(window.innerWidth - 400, r.left) + "px";
          card.style.top = Math.min(window.innerHeight - 220, r.bottom + 16) + "px";
        } else {
          overlay.classList.remove("active");
          spotlight.style.display = "none";
          card.style.left = "50%";
          card.style.top = "40%";
          card.style.transform = "translate(-50%, -50%)";
        }
      } else {
        overlay.classList.remove("active");
        spotlight.style.display = "none";
        card.style.left = "50%";
        card.style.top = "40%";
        card.style.transform = "translate(-50%, -50%)";
      }
    }

    function show() {
      overlay.classList.remove("hidden");
      overlay.setAttribute("aria-hidden", "false");
      const step = steps[idx];
      title.textContent = step.title;
      body.innerHTML = step.html || "";
      stepNum.textContent = idx + 1 + " / " + steps.length;
      btnBack.style.display = idx ? "inline-block" : "none";
      btnNext.textContent = idx === steps.length - 1 ? "Done" : "Next";
      placeCard();
      focusElSoon($("tourNext"));
    }

    function hide() {
      overlay.classList.add("hidden");
      overlay.setAttribute("aria-hidden", "true");
      overlay.classList.remove("active");
      card.style.transform = "";
      postConfig({ tutorial_done: true }).catch(function () {});
      focusElSoon($("btnTour"));
    }

    btnNext.onclick = function () {
      if (idx >= steps.length - 1) {
        hide();
        return;
      }
      idx++;
      show();
    };
    btnBack.onclick = function () {
      if (idx > 0) idx--;
      show();
    };
    btnSkip.onclick = hide;
    $("btnTour").onclick = function () {
      idx = 0;
      show();
    };
    window.addEventListener("resize", function () {
      if (!overlay.classList.contains("hidden")) placeCard();
    });

    fetch("/api/state")
      .then(function (r) {
        return r.json();
      })
      .then(function (s) {
        if (!s.tutorial_done) {
          idx = 0;
          show();
        }
      })
      .catch(function () {});
  }

  function positionKpiPopover(popEl, anchorEl) {
    if (!popEl || !anchorEl) {
      return;
    }
    var margin = 8;
    popEl.classList.remove("hidden");
    requestAnimationFrame(function () {
      var pr = popEl.getBoundingClientRect();
      var ar = anchorEl.getBoundingClientRect();
      var w = pr.width;
      var h = pr.height;
      var left = ar.left;
      var top = ar.bottom + margin;
      var vw = window.innerWidth;
      var vh = window.innerHeight;
      if (left + w > vw - margin) {
        left = Math.max(margin, vw - w - margin);
      }
      if (top + h > vh - margin) {
        top = Math.max(margin, ar.top - h - margin);
      }
      if (left < margin) {
        left = margin;
      }
      if (top < margin) {
        top = margin;
      }
      popEl.style.left = left + "px";
      popEl.style.top = top + "px";
    });
  }

  function repositionOpenKpiPopovers() {
    if (!$("popPoll").classList.contains("hidden")) {
      positionKpiPopover($("popPoll"), $("btnEditPoll"));
    }
    if (!$("popWindow").classList.contains("hidden")) {
      positionKpiPopover($("popWindow"), $("btnEditWindow"));
    }
    if (!$("popWarn").classList.contains("hidden")) {
      positionKpiPopover($("popWarn"), $("btnEditWarn"));
    }
    if (!$("popWarnAdd").classList.contains("hidden")) {
      positionKpiPopover($("popWarnAdd"), $("btnAddWarn"));
    }
  }

  function setupPopovers() {
    $("btnEditPoll").onclick = function (e) {
      e.stopPropagation();
      $("popWindow").classList.add("hidden");
      $("popWarn").classList.add("hidden");
      $("popWarnAdd").classList.add("hidden");
      $("popPoll").classList.toggle("hidden");
      if (!$("popPoll").classList.contains("hidden")) {
        $("inpPoll").value = window._lastState ? window._lastState.poll_sec : "2";
        positionKpiPopover($("popPoll"), $("btnEditPoll"));
        requestAnimationFrame(function () { $("inpPoll").focus(); });
      }
    };
    $("btnPollOk").onclick = function () {
      postConfig({ poll_sec: $("inpPoll").value.trim() })
        .then(function () {
          $("popPoll").classList.add("hidden");
        })
        .catch(function (err) {
          toast(String(err.message || err), "warn");
        });
    };
    $("btnPollCancel").onclick = function () {
      $("popPoll").classList.add("hidden");
    };

    $("btnEditWindow").onclick = function (e) {
      e.stopPropagation();
      $("popPoll").classList.add("hidden");
      $("popWarn").classList.add("hidden");
      $("popWarnAdd").classList.add("hidden");
      $("popWindow").classList.toggle("hidden");
      if (!$("popWindow").classList.contains("hidden")) {
        $("inpWindow").value = window._lastState ? window._lastState.avg_window : "12";
        positionKpiPopover($("popWindow"), $("btnEditWindow"));
        requestAnimationFrame(function () { $("inpWindow").focus(); });
      }
    };
    $("btnWindowOk").onclick = function () {
      postConfig({ avg_window: $("inpWindow").value.trim() })
        .then(function () {
          $("popWindow").classList.add("hidden");
        })
        .catch(function (err) {
          toast(String(err.message || err), "warn");
        });
    };
    $("btnWindowCancel").onclick = function () {
      $("popWindow").classList.add("hidden");
    };

    $("btnAddWarn").onclick = function (e) {
      e.stopPropagation();
      $("popPoll").classList.add("hidden");
      $("popWindow").classList.add("hidden");
      $("popWarn").classList.add("hidden");
      $("popWarnAdd").classList.toggle("hidden");
      if (!$("popWarnAdd").classList.contains("hidden")) {
        $("inpWarnAdd").value = "";
        positionKpiPopover($("popWarnAdd"), $("btnAddWarn"));
        requestAnimationFrame(function () { $("inpWarnAdd").focus(); });
      }
    };
    $("btnEditWarn").onclick = function (e) {
      e.stopPropagation();
      $("popPoll").classList.add("hidden");
      $("popWindow").classList.add("hidden");
      $("popWarnAdd").classList.add("hidden");
      $("popWarn").classList.toggle("hidden");
      if (!$("popWarn").classList.contains("hidden")) {
        $("inpWarn").value = window._lastState ? window._lastState.alert_thresholds : "10, 5, 1";
        positionKpiPopover($("popWarn"), $("btnEditWarn"));
        requestAnimationFrame(function () { $("inpWarn").focus(); });
      }
    };
    $("btnWarnOk").onclick = function () {
      postConfig({ alert_thresholds: $("inpWarn").value.trim() })
        .then(function () {
          $("popWarn").classList.add("hidden");
        })
        .catch(function (err) {
          toast(String(err.message || err), "warn");
        });
    };
    $("btnWarnCancel").onclick = function () {
      $("popWarn").classList.add("hidden");
    };

    function mergeAlertThresholdsString(raw, addN) {
      const set = {};
      function addToken(part) {
        const p = (part || "").trim();
        if (!p) return;
        const rm = /^(\d+)\s*-\s*(\d+)$/.exec(p);
        if (rm) {
          const a = parseInt(rm[1], 10);
          const b = parseInt(rm[2], 10);
          if (isFinite(a) && isFinite(b) && a >= 1 && b >= 1) {
            const step = a <= b ? 1 : -1;
            let x = a;
            while ((step > 0 && x <= b) || (step < 0 && x >= b)) {
              set[x] = true;
              x += step;
            }
          }
          return;
        }
        const n = parseInt(p, 10);
        if (!isNaN(n) && n >= 1) set[n] = true;
      }
      (raw || "")
        .replace(/,/g, " ")
        .split(/\s+/)
        .forEach(function (p) {
          addToken(p);
        });
      if (!isNaN(addN) && addN >= 1) set[addN] = true;
      const arr = Object.keys(set)
        .map(Number)
        .sort(function (a, b) {
          return b - a;
        });
      if (!arr.length) throw new Error("Add at least one threshold (e.g. 10, 5, 1).");
      return arr.join(", ");
    }
    $("btnWarnAddOk").onclick = function () {
      const n = parseInt(($("inpWarnAdd").value || "").trim(), 10);
      if (isNaN(n) || n < 1) {
        toast("Enter a queue position ≥ 1", "warn");
        return;
      }
      const raw = window._lastState ? window._lastState.alert_thresholds : "10, 5, 1";
      let merged;
      try {
        merged = mergeAlertThresholdsString(raw, n);
      } catch (err) {
        toast(String(err.message || err), "warn");
        return;
      }
      postConfig({ alert_thresholds: merged })
        .then(function () {
          $("popWarnAdd").classList.add("hidden");
        })
        .catch(function (err) {
          toast(String(err.message || err), "warn");
        });
    };
    $("btnWarnAddCancel").onclick = function () {
      $("popWarnAdd").classList.add("hidden");
    };

    document.body.addEventListener("click", function () {
      ["popPoll", "popWindow", "popWarn", "popWarnAdd"].forEach(function (id) {
        var p = $(id);
        if (p) {
          p.classList.add("hidden");
          p.style.left = "";
          p.style.top = "";
        }
      });
    });
    ["popPoll", "popWindow", "popWarn", "popWarnAdd"].forEach(function (id) {
      const el = $(id);
      if (el)
        el.addEventListener("click", function (e) {
          e.stopPropagation();
        });
    });

    window.addEventListener(
      "resize",
      function () {
        repositionOpenKpiPopovers();
      },
      { passive: true },
    );
    window.addEventListener(
      "scroll",
      function () {
        repositionOpenKpiPopovers();
      },
      true,
    );
  }

  function nearestPointIndexByTime(pts, targetT) {
    var n = pts.length;
    if (!n) {
      return -1;
    }
    var lo = 0;
    var hi = n;
    while (lo < hi) {
      var mid = (lo + hi) >> 1;
      if (pts[mid][0] < targetT) {
        lo = mid + 1;
      } else {
        hi = mid;
      }
    }
    var i = lo;
    var candidates = [];
    if (i < n) {
      candidates.push(i);
    }
    if (i > 0) {
      candidates.push(i - 1);
    }
    var best = candidates[0];
    var bestDt = Math.abs(pts[best][0] - targetT);
    var k;
    for (k = 1; k < candidates.length; k++) {
      var j = candidates[k];
      var dt = Math.abs(pts[j][0] - targetT);
      if (dt < bestDt) {
        bestDt = dt;
        best = j;
      }
    }
    return best;
  }

  function formatGraphTooltipHint(pt, idx, series) {
    var ts = VsQueueMonitorGraph.fmtTooltipTs(pt[0]);
    var posStr = String(pt[1]);
    var lines = [ts + "  ·  pos " + posStr];
    if (idx > 0) {
      var prev = series[idx - 1];
      var dt = pt[0] - prev[0];
      var dp = pt[1] - prev[1];
      if (dt > 1e-6) {
        var dpStr = (dp >= 0 ? "+" : "") + dp;
        var extra = dp !== 0 ? "  (" + (dp / dt).toFixed(3) + "/s)" : "";
        lines.push(
          "vs prev: " + dpStr + "  ·  position length: " + formatTooltipDuration(dt) + extra,
        );
      } else {
        lines.push("vs prev: " + (dp >= 0 ? "+" : "") + dp);
      }
    }
    return lines.join("\n");
  }

  function hideGraphTooltip() {
    var tt = $("graphTooltip");
    if (!tt) {
      return;
    }
    tt.classList.add("hidden");
    tt.textContent = "";
    tt.setAttribute("aria-hidden", "true");
  }

  function showGraphTooltip(ev, text) {
    var tt = $("graphTooltip");
    if (!tt) {
      return;
    }
    tt.textContent = text;
    tt.classList.remove("hidden");
    tt.setAttribute("aria-hidden", "false");
    var pad = 14;
    tt.style.left = ev.clientX + pad + "px";
    tt.style.top = ev.clientY + pad + "px";
    requestAnimationFrame(function () {
      var r = tt.getBoundingClientRect();
      var x = ev.clientX + pad;
      var y = ev.clientY + pad;
      if (x + r.width > window.innerWidth - 8) {
        x = window.innerWidth - r.width - 8;
      }
      if (y + r.height > window.innerHeight - 8) {
        y = window.innerHeight - r.height - 8;
      }
      if (x < 8) {
        x = 8;
      }
      if (y < 8) {
        y = 8;
      }
      tt.style.left = x + "px";
      tt.style.top = y + "px";
    });
  }

  function setupGraphCanvas() {
    const c = $("graphCanvas");
    c.addEventListener("mousemove", function (ev) {
      const st = c._drawState;
      const series = (st && st.rawPoints && st.rawPoints.length ? st.rawPoints : st && st.drawn) || [];
      if (!st || !series.length) {
        hideGraphTooltip();
        return;
      }
      const rect = c.getBoundingClientRect();
      const mxCss = ev.clientX - rect.left;
      const padL = st.x0;
      const plotW = st.plotW;
      const x = Math.max(padL, Math.min(padL + plotW, mxCss));
      const t0 = st.t0;
      const t1 = st.t1;
      const targetT = t0 + ((x - padL) / plotW) * (t1 - t0);
      const idx = nearestPointIndexByTime(series, targetT);
      if (idx < 0) {
        hideGraphTooltip();
        return;
      }
      const best = series[idx];
      showGraphTooltip(ev, formatGraphTooltipHint(best, idx, series));
      window._graphHover = [best[0], best[1]];
      redrawGraphOnly();
    });
    c.addEventListener("mouseleave", function () {
      hideGraphTooltip();
      window._graphHover = null;
      redrawGraphOnly();
    });
  }

  function setupRestoreBanner() {
    var dismiss = $("btnDismissRestore");
    var resume = $("btnResumePath");
    if (dismiss)
      dismiss.onclick = function () {
        var rb = $("restoreBanner");
        if (rb) rb.classList.add("hidden");
        focusElSoon($("pathSummary"));
      };
    if (resume)
      resume.onclick = function () {
        var saved = "";
        try {
          saved = (lsGetPath() || "").trim();
        } catch (e) {}
        if (!saved) return;
        var wasRunning = window._lastState && window._lastState.running;
        $("inpPath").value = saved;
        syncPathDisplay();
        postConfig({ source_path: saved })
          .then(function () {
            var rb = $("restoreBanner");
            if (rb) rb.classList.add("hidden");
            if (!wasRunning) {
              return postToggle().then(function () {
                focusElSoon($("btnStartStop"));
              });
            }
            focusElSoon($("btnStartStop"));
          })
          .catch(function (err) {
            toast(String(err.message || err), "warn");
          });
      };
  }

  function setupNewQueueModal() {
    var yes = $("btnNewQueueYes");
    var no = $("btnNewQueueNo");
    var bd = $("modalNewQueueBackdrop");
    function submit(accept) {
      postNewQueue(accept)
        .then(function () {
          setTimeout(function () {
            focusElSoon($("btnStartStop"));
          }, 0);
        })
        .catch(function (err) {
          toast(String(err.message || err), "warn");
        });
    }
    if (yes) yes.onclick = function () {
      submit(true);
    };
    if (no) no.onclick = function () {
      submit(false);
    };
    if (bd) bd.onclick = function () {
      submit(false);
    };
  }

  var _notifUnsupported = false;
  var _notifEverAsked = !!localStorage.getItem("vsqm_notif_asked");

  function setupNotifications() {
    var btn = $("btnNotify");

    function syncHint() {
      var popOn =
        window._lastState == null || window._lastState.popup_enabled !== false;
      var st = "pending";
      var label = "Desktop notifications — click to allow in the browser";
      var hint = "Notifications pending — click to allow the browser prompt";
      if (typeof Notification === "undefined" || _notifUnsupported ||
          (typeof Notification !== "undefined" && Notification.permission === "denied")) {
        var bannerNote = (typeof Notification === "undefined" || _notifUnsupported)
          ? " (banners need a browser tab)"
          : " (banners blocked — allow in browser settings)";
        if (popOn) {
          st = "live";
          label = "Sound alerts on — click to turn off" + bannerNote;
          hint = "Sound alerts on" + bannerNote;
        } else {
          st = "off";
          label = "Sound alerts off — click to turn on" + bannerNote;
          hint = "Sound alerts off — click to turn on";
        }
      } else if (!popOn) {
        st = "off";
        if (Notification.permission === "granted") {
          label = "Desktop notifications off — click to turn on";
          hint = "Notifications off — click to turn desktop alerts back on";
        } else {
          label = "Desktop notifications off — click to turn on and allow browser notifications";
          hint = "Click to enable Warning popup and allow the browser prompt";
        }
      } else if (Notification.permission === "granted") {
        st = "live";
        label = "Desktop notifications on — click to turn off";
        hint = "Notifications on — click to turn off desktop alerts";
      } else {
        st = "pending";
        label = "Desktop notifications — click to allow in the browser";
        hint = "Notifications pending — click to allow the browser prompt";
      }
      if (btn) {
        btn.setAttribute("data-state", st);
        btn.setAttribute("aria-checked", st === "live" ? "true" : "false");
        btn.setAttribute("aria-label", label);
        btn.title = hint;
      }
    }
    notifySyncHint = syncHint;

    /** Standard web API only: Notification.requestPermission() + new Notification() */
    function requestPermissionFlow() {
      if (typeof Notification === "undefined") {
        _notifUnsupported = true;
        syncHint();
        toast("Desktop banners aren't supported here — open in a browser for that. Sound alerts still work.", "warn");
        return;
      }
      if (Notification.permission === "denied" && !_notifEverAsked) {
        _notifUnsupported = true;
        syncHint();
        toast("Desktop banners aren't available in this window. Sound alerts still work. Open in a browser to enable banners.", "warn");
        return;
      }
      var t0 = Date.now();
      try {
        localStorage.setItem("vsqm_notif_asked", "1");
        _notifEverAsked = true;
        var req = Notification.requestPermission();
        if (req && typeof req.then === "function") {
          req
            .then(function (p) {
              syncHint();
              if (p === "granted") {
                try {
                  desktopNotify("Notifications enabled", {
                    body:
                      "VS Queue Monitor can show desktop banners when queue thresholds are crossed.\n\nText matches the in-app toast for each alert.",
                    tag: "vsqm-setup-grant",
                  });
                } catch (e) {}
                toast("Notifications enabled.");
              } else if (p === "denied") {
                if (Date.now() - t0 < 300) {
                  _notifUnsupported = true;
                  toast("Desktop banners aren't available in this window. Sound alerts still work. Open in a browser to enable banners.", "warn");
                } else {
                  toast("Notifications were denied in the browser.", "warn");
                }
                syncHint();
              }
            })
            .catch(function () {
              syncHint();
              toast("Could not request notification permission.", "warn");
            });
        } else {
          syncHint();
          if (Notification.permission === "granted") {
            try {
              desktopNotify("Notifications enabled", {
                body:
                  "VS Queue Monitor can show desktop banners when queue thresholds are crossed.\n\nText matches the in-app toast for each alert.",
                tag: "vsqm-setup-grant",
              });
            } catch (e) {}
            toast("Notifications enabled.");
          }
        }
      } catch (e) {
        _notifUnsupported = true;
        syncHint();
        toast("Desktop banners aren't available in this window. Sound alerts still work.", "warn");
      }
    }

    function bumpPopupEnabled(on) {
      if (window._lastState) window._lastState.popup_enabled = !!on;
    }

    /** Same sample copy as after first granting permission — confirms OS banners when turning alerts back on. */
    function showExampleDesktopNotification() {
      try {
        desktopNotify("Threshold alerts active", {
          body:
            "When a threshold is crossed, you'll see a banner like this with the alert text, your position, and status.",
          tag: "vsqm-example-" + Date.now(),
        });
      } catch (e) {}
    }

    function _isBannerUnsupported() {
      return _notifUnsupported || typeof Notification === "undefined";
    }

    function _notifBannersBlocked() {
      return typeof Notification !== "undefined" && Notification.permission === "denied";
    }

    function onNotifyClick() {
      var popOn =
        window._lastState == null || window._lastState.popup_enabled !== false;

      if (_isBannerUnsupported()) {
        if (popOn) {
          postConfig({ popup_enabled: false })
            .then(function () { bumpPopupEnabled(false); toast("Alerts off."); syncHint(); })
            .catch(function (e) { toast(String(e.message || e), "warn"); });
        } else {
          postConfig({ popup_enabled: true })
            .then(function () {
              bumpPopupEnabled(true);
              toast("Sound alerts on. Desktop banners aren't available in this window — open in a browser for those.");
              syncHint();
            })
            .catch(function (e) { toast(String(e.message || e), "warn"); });
        }
        return;
      }

      if (_notifBannersBlocked()) {
        if (!popOn) {
          fetch("/api/clear_notification_permission", { method: "POST" })
            .then(function () {
              toast("Notification permission reset — reopen VS Queue Monitor to grant access.", "warn");
            })
            .catch(function () {
              toast("Could not reset notification permission. Try reinstalling the app.", "warn");
            });
        } else {
          postConfig({ popup_enabled: false })
            .then(function () { bumpPopupEnabled(false); toast("Alerts off."); syncHint(); })
            .catch(function (e) { toast(String(e.message || e), "warn"); });
        }
        return;
      }

      var perm = Notification.permission;
      if (perm === "granted") {
        if (popOn) {
          postConfig({ popup_enabled: false })
            .then(function () {
              bumpPopupEnabled(false);
              toast("Desktop notifications off.");
              syncHint();
            })
            .catch(function (e) {
              toast(String(e.message || e), "warn");
            });
        } else {
          postConfig({ popup_enabled: true })
            .then(function () {
              bumpPopupEnabled(true);
              showExampleDesktopNotification();
              toast("Desktop notifications on.");
              syncHint();
            })
            .catch(function (e) {
              toast(String(e.message || e), "warn");
            });
        }
        return;
      }
      if (!popOn) {
        postConfig({ popup_enabled: true })
          .then(function () {
            bumpPopupEnabled(true);
            syncHint();
            requestPermissionFlow();
          })
          .catch(function (e) {
            toast(String(e.message || e), "warn");
          });
        return;
      }
      requestPermissionFlow();
    }
    if (btn) {
      btn.addEventListener("click", onNotifyClick);
    }
    var btnTest = $("btnTestNotify");
    if (btnTest) {
      btnTest.addEventListener("click", function () {
        if (_isBannerUnsupported()) {
          toast("Desktop banners aren't available in this window — open in a browser to test them.", "warn");
          return;
        }
        var pOn =
          window._lastState == null || window._lastState.popup_enabled !== false;
        if (!pOn) {
          toast("Turn on Warning popup first (same setting as the header switch).", "warn");
          return;
        }
        if (Notification.permission !== "granted") {
          toast("Allow notifications from the header switch first.", "warn");
          return;
        }
        try {
          desktopNotify("Test notification", {
            body:
              "If you see this, desktop alerts are working.\n\nReal alerts repeat the in-app message and add queue context.",
            tag: "vsqm-test",
          });
        } catch (e) {}
        toast("Test sent — check the system tray if you see no banner.");
      });
    }
    syncHint();
  }

  function setupHelpCmd() {
    $("btnHelp").onclick = function () {
      fetch("/api/meta")
        .then(function (r) {
          return r.json();
        })
        .then(function (m) {
          $("helpCfgPath").textContent = "Config: " + (m.config_path || "");
          showEl($("modalHelp"));
          focusElSoon($("btnHelpOk"));
        })
        .catch(function () {
          showEl($("modalHelp"));
          focusElSoon($("btnHelpOk"));
        });
    };
  }

  function setupPathModal() {
    var modal = $("modalPath");
    var inpHidden = $("inpPath");
    var inpModal = $("inpPathModal");
    var ps = $("pathSummary");

    function closePathModal() {
      if (modal) hideEl(modal);
      if (ps) ps.focus();
    }

    function applyPathModal() {
      var v = inpModal ? String(inpModal.value || "").trim() : "";
      if (inpHidden) inpHidden.value = v;
      syncPathDisplay();
      if (modal) hideEl(modal);
      postConfig({ source_path: v }).catch(function (e) {
        toast(String(e.message || e), "warn");
      });
      if (ps) ps.focus();
    }

    if (ps) {
      ps.onclick = function () {
        if (inpModal && inpHidden) inpModal.value = inpHidden.value;
        if (modal) showEl(modal);
        if (inpModal) {
          setTimeout(function () {
            inpModal.focus();
            try {
              inpModal.select();
            } catch (e) {}
          }, 0);
        }
      };
    }
    var ok = $("btnPathOk");
    if (ok) ok.onclick = function () {
      applyPathModal();
    };
    var cancel = $("btnPathCancel");
    if (cancel) cancel.onclick = function () {
      closePathModal();
    };
    var bd = $("modalPathBackdrop");
    if (bd) bd.onclick = function () {
      closePathModal();
    };
    if (inpModal) {
      inpModal.addEventListener("keydown", function (ev) {
        if (ev.key === "Enter") {
          ev.preventDefault();
          applyPathModal();
        }
      });
    }
  }

  /** Keep Tab cycling within an open dialog (WCAG-friendly). */
  function setupModalTabTrap() {
    var modalIds = ["modalNewQueue", "modalPath", "modalHelp", "modalSettings", "tourOverlay"];
    document.addEventListener(
      "keydown",
      function (ev) {
        if (ev.key !== "Tab") return;
        var ae = document.activeElement;
        if (!ae || !ae.closest) return;
        var i;
        var root = null;
        for (i = 0; i < modalIds.length; i++) {
          var m = $(modalIds[i]);
          if (m && !m.classList.contains("hidden") && m.contains(ae)) {
            root = m;
            break;
          }
        }
        if (!root) return;
        var nodes = root.querySelectorAll(
          'button:not([disabled]), [href], input:not([disabled]):not([type="hidden"]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])',
        );
        var focusables = [];
        var j;
        for (j = 0; j < nodes.length; j++) {
          var el = nodes[j];
          var st = window.getComputedStyle(el);
          if (st.visibility === "hidden" || st.display === "none") continue;
          focusables.push(el);
        }
        if (focusables.length === 0) return;
        var first = focusables[0];
        var last = focusables[focusables.length - 1];
        if (ev.shiftKey) {
          if (ae === first) {
            ev.preventDefault();
            last.focus();
          }
        } else if (ae === last) {
          ev.preventDefault();
          first.focus();
        }
      },
      true,
    );
  }

  function setupModalEscape() {
    document.addEventListener(
      "keydown",
      function (ev) {
        if (ev.key !== "Escape") return;
        var nq = $("modalNewQueue");
        if (nq && !nq.classList.contains("hidden")) {
          ev.preventDefault();
          var no = $("btnNewQueueNo");
          if (no) no.click();
          return;
        }
        var mp = $("modalPath");
        if (mp && !mp.classList.contains("hidden")) {
          ev.preventDefault();
          var bd = $("modalPathBackdrop");
          if (bd) bd.click();
          return;
        }
        if ($("modalHelp") && !$("modalHelp").classList.contains("hidden")) {
          ev.preventDefault();
          closeHelpModal();
          return;
        }
        if ($("modalSettings") && !$("modalSettings").classList.contains("hidden")) {
          ev.preventDefault();
          closeSettingsModal();
          return;
        }
        var tour = $("tourOverlay");
        if (tour && !tour.classList.contains("hidden")) {
          ev.preventDefault();
          var sk = $("tourSkip");
          if (sk) sk.click();
        }
      },
      true,
    );
  }

  function setupChrome() {
    $("btnStartStop").onclick = function () {
      postToggle().catch(function (e) {
        toast(String(e), "warn");
      });
    };
    var bf = $("btnBrowseFolder");
    if (bf) {
      bf.onclick = function () {
        pickPath("folder")
          .then(function (j) {
            if (j.cancelled) return;
            if (!j.path) return;
            $("inpPath").value = j.path;
            syncPathDisplay();
            return postConfig({ source_path: $("inpPath").value.trim() });
          })
          .then(function () {
            if ($("inpPath").value.trim()) toast("Path set from folder picker");
          })
          .catch(function (e) {
            toast(String(e.message || e), "warn");
          });
      };
    }
    var bfile = $("btnBrowseFile");
    if (bfile) {
      bfile.onclick = function () {
        pickPath("file")
          .then(function (j) {
            if (j.cancelled) return;
            if (!j.path) return;
            $("inpPath").value = j.path;
            syncPathDisplay();
            return postConfig({ source_path: $("inpPath").value.trim() });
          })
          .then(function () {
            if ($("inpPath").value.trim()) toast("Path set from file picker");
          })
          .catch(function (e) {
            toast(String(e.message || e), "warn");
          });
      };
    }
    $("btnCopyPng").onclick = function () {
      const c = $("graphCanvas");
      c.toBlob(function (blob) {
        if (!blob || !navigator.clipboard || !navigator.clipboard.write) {
          toast("PNG: copy not supported — use right-click Save image on canvas", "warn");
          return;
        }
        navigator.clipboard
          .write([new ClipboardItem({ "image/png": blob })])
          .then(function () {
            toast("Graph PNG copied to clipboard");
          })
          .catch(function () {
            toast("Could not copy PNG (browser permission)", "warn");
          });
      });
    };
    $("btnCopyTsv").onclick = function () {
      const pts = (window._displayState && window._displayState.graph_points) || [];
      if (!pts.length) {
        toast("No graph data yet", "warn");
        return;
      }
      const lines = ["epoch_seconds\tposition"].concat(
        pts.map(function (p) {
          return p[0] + "\t" + p[1];
        }),
      );
      navigator.clipboard.writeText(lines.join("\n")).then(
        function () {
          toast("TSV copied");
        },
        function () {
          toast("Clipboard failed", "warn");
        },
      );
    };

    var bs = $("btnCopyStats");
    if (bs) {
      bs.onclick = function () {
        copyStatsToClipboard();
      };
    }
    var bh = $("btnCopyHistory");
    if (bh) {
      bh.onclick = function () {
        copyHistoryToClipboard();
      };
    }

    $("btnSettings").onclick = function () {
      showEl($("modalSettings"));
      focusElSoon($("chkEvery"));
    };
    document.querySelectorAll("[data-close]").forEach(function (el) {
      el.addEventListener("click", function () {
        var helpWas = $("modalHelp") && !$("modalHelp").classList.contains("hidden");
        var setWas = $("modalSettings") && !$("modalSettings").classList.contains("hidden");
        hideEl($("modalHelp"));
        hideEl($("modalSettings"));
        if (helpWas) focusElSoon($("btnHelp"));
        else if (setWas) focusElSoon($("btnSettings"));
      });
    });
    $("btnSaveSettings").onclick = function () {
      var patch = {
        show_every_change: $("chkEvery").checked,
        popup_enabled: $("chkPop").checked,
        sound_enabled: $("chkSnd").checked,
        completion_popup: $("chkCompPop").checked,
        completion_sound: $("chkCompSnd").checked,
        graph_log_scale: $("chkGraphLog").checked,
        graph_live_view: $("chkGraphLive").checked,
      };
      var iws = $("inpSetWarnSound");
      var ics = $("inpSetCompSound");
      if (iws) patch.alert_sound_path = iws.value.trim();
      if (ics) patch.completion_sound_path = ics.value.trim();
      postConfig(patch)
        .then(function () {
          hideEl($("modalSettings"));
          focusElSoon($("btnSettings"));
          toast("Settings saved");
        })
        .catch(function (e) {
          toast(String(e.message || e), "warn");
        });
    };
    $("btnReset").onclick = function () {
      postReset()
        .then(function () {
          toast("Defaults reset");
        })
        .catch(function (e) {
          toast(String(e), "warn");
        });
    };

  }

  window.addEventListener("resize", resizeCanvas);

  function zoomGraph(factor, centerT) {
    var c = $("graphCanvas");
    var ds = c && c._drawState;
    if (!ds || !ds.rawPoints || !ds.rawPoints.length) return;
    var rawT0 = ds.rawPoints[0][0];
    var rawT1 = ds.rawPoints[ds.rawPoints.length - 1][0];
    var fullSpan = rawT1 - rawT0;
    if (fullSpan <= 0) return;
    var curT0 = window._graphZoom ? window._graphZoom[0] : rawT0;
    var curT1 = window._graphZoom ? window._graphZoom[1] : rawT1;
    if (centerT == null) centerT = (curT0 + curT1) / 2;
    var newSpan = Math.max(10, (curT1 - curT0) * factor);
    var newT0 = centerT - newSpan / 2;
    var newT1 = centerT + newSpan / 2;
    if (newT0 < rawT0) { newT0 = rawT0; newT1 = rawT0 + newSpan; }
    if (newT1 > rawT1) { newT1 = rawT1; newT0 = rawT1 - newSpan; }
    newT0 = Math.max(newT0, rawT0);
    newT1 = Math.min(newT1, rawT1);
    window._graphZoom = (newT1 - newT0 >= fullSpan * 0.999) ? null : [newT0, newT1];
    redrawGraphOnly();
    updateZoomResetBtn();
  }

  function updateZoomResetBtn() {
    var btn = $("btnZoomReset");
    if (!btn) return;
    if (window._graphZoom) btn.classList.remove("hidden");
    else btn.classList.add("hidden");
  }

  function setupGraphZoom() {
    var btnIn = $("btnZoomIn");
    var btnOut = $("btnZoomOut");
    var btnReset = $("btnZoomReset");
    if (btnIn) btnIn.onclick = function () { zoomGraph(0.5, null); };
    if (btnOut) btnOut.onclick = function () { zoomGraph(2, null); };
    if (btnReset) btnReset.onclick = function () { window._graphZoom = null; redrawGraphOnly(); updateZoomResetBtn(); };
    var c = $("graphCanvas");
    if (!c) return;
    c.addEventListener("wheel", function (e) {
      var ds = c._drawState;
      if (!ds || !ds.rawPoints || !ds.rawPoints.length) return;
      var rect = c.getBoundingClientRect();
      var mxCss = e.clientX - rect.left;
      var centerT = (mxCss >= ds.x0 && mxCss <= ds.x0 + ds.plotW)
        ? ds.t0 + ((mxCss - ds.x0) / ds.plotW) * (ds.t1 - ds.t0)
        : (ds.t0 + ds.t1) / 2;
      zoomGraph(e.deltaY > 0 ? 1.5 : 1 / 1.5, centerT);
      e.preventDefault();
    }, { passive: false });
  }

  function setupGraphResize() {
    var handle = $("graphResizeHandle");
    if (!handle) return;
    var startY, startH;
    function beginDrag(clientY) {
      startY = clientY;
      startH = window._graphH;
    }
    function moveDrag(clientY) {
      window._graphH = Math.max(120, Math.min(800, startH + (clientY - startY)));
      resizeCanvas();
    }
    function endDrag() {
      localStorage.setItem("vsqm_graph_h", String(window._graphH));
    }
    handle.addEventListener("mousedown", function (e) {
      beginDrag(e.clientY);
      function onMove(e) { moveDrag(e.clientY); }
      function onUp() { endDrag(); document.removeEventListener("mousemove", onMove); document.removeEventListener("mouseup", onUp); }
      document.addEventListener("mousemove", onMove);
      document.addEventListener("mouseup", onUp);
      e.preventDefault();
    });
    handle.addEventListener("touchstart", function (e) {
      beginDrag(e.touches[0].clientY);
      function onMove(e) { moveDrag(e.touches[0].clientY); e.preventDefault(); }
      function onUp() { endDrag(); document.removeEventListener("touchmove", onMove); document.removeEventListener("touchend", onUp); }
      document.addEventListener("touchmove", onMove, { passive: false });
      document.addEventListener("touchend", onUp);
      e.preventDefault();
    }, { passive: false });
  }

  function setupInfoHistoryResize() {
    var handle = $("ihResizeHandle");
    var section = document.querySelector(".info-history");
    if (!handle || !section) return;
    var saved = parseFloat(localStorage.getItem("vsqm_ih_pct") || "");
    if (!isNaN(saved)) applyIhSplit(section, saved);
    function applyIhSplit(sec, pct) {
      var rect = sec.getBoundingClientRect();
      var handleW = 10;
      var avail = rect.width - handleW;
      var px = Math.max(avail * 0.2, Math.min(avail * 0.8, avail * pct / 100));
      sec.style.setProperty("--ih-main-w", px + "px");
    }
    function getPct(sec, clientX) {
      var rect = sec.getBoundingClientRect();
      var handleW = 10;
      var avail = rect.width - handleW;
      return Math.max(20, Math.min(80, ((clientX - rect.left) / avail) * 100));
    }
    handle.addEventListener("mousedown", function (e) {
      function onMove(e) { var p = getPct(section, e.clientX); applyIhSplit(section, p); }
      function onUp(e) {
        var p = getPct(section, e.clientX);
        applyIhSplit(section, p);
        localStorage.setItem("vsqm_ih_pct", String(p));
        document.removeEventListener("mousemove", onMove);
        document.removeEventListener("mouseup", onUp);
      }
      document.addEventListener("mousemove", onMove);
      document.addEventListener("mouseup", onUp);
      e.preventDefault();
    });
    handle.addEventListener("touchstart", function (e) {
      function onMove(e) { var p = getPct(section, e.touches[0].clientX); applyIhSplit(section, p); e.preventDefault(); }
      function onUp(e) {
        var p = getPct(section, (e.changedTouches[0] || e.touches[0]).clientX);
        applyIhSplit(section, p);
        localStorage.setItem("vsqm_ih_pct", String(p));
        document.removeEventListener("touchmove", onMove);
        document.removeEventListener("touchend", onUp);
      }
      document.addEventListener("touchmove", onMove, { passive: false });
      document.addEventListener("touchend", onUp);
      e.preventDefault();
    }, { passive: false });
  }

  function setupKeyboardShortcuts() {
    document.addEventListener("keydown", function (ev) {
      const t = ev.target;
      const tag = t && t.tagName ? String(t.tagName) : "";
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || (t && t.isContentEditable)) {
        return;
      }
      if (uiBlockingLayerOpen()) return;
      if (ev.code === "Space") {
        ev.preventDefault();
        postToggle().catch(function (e) {
          toast(String(e), "warn");
        });
        return;
      }
      if (ev.key === "F1") {
        ev.preventDefault();
        $("btnHelp").click();
        return;
      }
      if (ev.key === "o" || ev.key === "O") {
        if (!ev.ctrlKey && !ev.metaKey && !ev.altKey) {
          ev.preventDefault();
          showEl($("modalSettings"));
          focusElSoon($("chkEvery"));
        }
        return;
      }
      if (ev.key === "c" && !ev.ctrlKey && !ev.metaKey && !ev.altKey) {
        ev.preventDefault();
        $("btnCopyTsv").click();
        return;
      }
      if (ev.key === "v" && !ev.ctrlKey && !ev.metaKey && !ev.altKey) {
        ev.preventDefault();
        copyHistoryToClipboard();
        return;
      }
      if ((ev.key === "+" || ev.key === "=") && !ev.ctrlKey && !ev.metaKey && !ev.altKey) {
        ev.preventDefault();
        zoomGraph(0.5, null);
        return;
      }
      if (ev.key === "-" && !ev.ctrlKey && !ev.metaKey && !ev.altKey) {
        ev.preventDefault();
        zoomGraph(2, null);
        return;
      }
      if (ev.key === "0" && !ev.ctrlKey && !ev.metaKey && !ev.altKey) {
        ev.preventDefault();
        window._graphZoom = null;
        redrawGraphOnly();
        updateZoomResetBtn();
        return;
      }
    });
  }

  setupChrome();
  setupPopovers();
  setupSessionSelect();
  setupGraphCanvas();
  setupGraphZoom();
  setupGraphResize();
  setupInfoHistoryResize();
  setupRestoreBanner();
  setupNewQueueModal();
  setupNotifications();
  setupHelpCmd();
  setupPathModal();
  setupModalTabTrap();
  setupModalEscape();
  setupKeyboardShortcuts();
  setupTour();
  hydratePathFromStorageEarly();
  fetch("/api/state")
    .then(function (r) {
      return r.json();
    })
    .then(function (s) {
      window._lastState = s;
      applyState(s);
    })
    .catch(function () {});
  connectWs();
  fetch("/api/meta")
    .then(function (r) {
      return r.json();
    })
    .then(function (m) {
      window._graphTheme = m.graph_theme || null;
      applyChromeTheme(m.chrome_theme);
      $("helpCfgPath").textContent = "Config: " + (m.config_path || "");
      var fv2 = $("footerVersion");
      if (fv2) {
        var bf2 = m.build_fingerprint || "";
        fv2.textContent = "v" + (m.version || "") + (bf2 ? " (" + bf2 + ")" : "");
      }
      if (window._lastState) {
        window._displayState = buildDisplayState(window._lastState);
        redrawGraphOnly();
        renderSessionStats();
      }
    })
    .catch(function () {});
})();
