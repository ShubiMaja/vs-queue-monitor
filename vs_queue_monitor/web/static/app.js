/* global WebSocket, fetch, document, window, localStorage */
(function () {
  "use strict";

  const SINGLE_POINT_SPAN = 60;
  const GRAPH_LOG_GAMMA = 1.15;
  const PAD_L = 46;
  const PAD_R = 22;
  const PAD_T = 12;
  const PAD_B = 32;

  let lastAlertPrev = "";

  function $(id) {
    return document.getElementById(id);
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

  function graphTimeRange(points, liveView, running) {
    if (!points.length) return [0, 1];
    if (points.length === 1) {
      const mid = points[0][0];
      const half = SINGLE_POINT_SPAN / 2;
      return [mid - half, mid + half];
    }
    let t0 = points[0][0];
    let t1 = points[points.length - 1][0];
    if (t1 <= t0) t1 = t0 + 1e-6;
    if (liveView && running) {
      t1 = Math.max(t1, Date.now() / 1000);
    }
    return [t0, t1];
  }

  function drawGraph(canvas, state) {
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    const w = canvas.width;
    const h = canvas.height;
    ctx.fillStyle = "#11161c";
    ctx.fillRect(0, 0, w, h);

    const points = state.graph_points || [];
    const liveView = !!state.graph_live_view;
    const running = !!state.running;
    const logScale = !!state.graph_log_scale;

    const plotW = Math.max(1, w - PAD_L - PAD_R);
    const plotH = Math.max(1, h - PAD_T - PAD_B);
    const x0 = PAD_L;
    const y0 = PAD_T;
    const x1 = PAD_L + plotW;
    const y1 = PAD_T + plotH;

    ctx.fillStyle = "#11161c";
    ctx.fillRect(x0, y0, plotW, plotH);

    if (!points.length) {
      ctx.fillStyle = "#6e7680";
      ctx.font = "14px system-ui";
      ctx.fillText("No data yet", x0 + 8, y0 + 20);
      return;
    }

    const [t0, t1] = graphTimeRange(points, liveView, running);
    const vals = points.map(function (p) {
      return p[1];
    });
    let vmin = Math.min.apply(null, vals);
    let vmax = Math.max.apply(null, vals);
    if (vmax === vmin) vmax = vmin + 1;
    vmin = Math.max(0, vmin);

    function xOf(t) {
      return x0 + ((t - t0) / (t1 - t0)) * plotW;
    }
    function yOf(v) {
      const vv = Math.max(vmin, Math.min(vmax, v));
      if (!logScale) {
        const frac = (vmax - vv) / Math.max(1, vmax - vmin);
        return y0 + frac * plotH;
      }
      const lvmin = Math.log(vmin + 1);
      const lvmax = Math.log(vmax + 1);
      const lv = Math.log(vv + 1);
      let frac = lvmax <= lvmin ? 0 : (lvmax - lv) / (lvmax - lvmin);
      frac = Math.max(0, Math.min(1, frac));
      frac = Math.pow(frac, GRAPH_LOG_GAMMA);
      return y0 + frac * plotH;
    }

    ctx.strokeStyle = "#2a3340";
    ctx.beginPath();
    ctx.moveTo(x0, y0);
    ctx.lineTo(x0, y1);
    ctx.lineTo(x1, y1);
    ctx.stroke();

    ctx.fillStyle = "#c7d0d9";
    ctx.font = "11px system-ui";
    ctx.fillText("min " + vmin + "  max " + vmax, x0 + 6, y0 + 14);

    const stepVerts = [];
    for (let i = 0; i < points.length; i++) {
      const t = points[i][0];
      const p = points[i][1];
      if (i === 0) {
        stepVerts.push([t, p]);
        continue;
      }
      const tPrev = points[i - 1][0];
      const pPrev = points[i - 1][1];
      if (t <= tPrev) continue;
      if (p !== pPrev) {
        stepVerts.push([t, pPrev]);
      }
      stepVerts.push([t, p]);
    }

    ctx.strokeStyle = "#73bf69";
    ctx.lineWidth = 2;
    ctx.beginPath();
    let first = true;
    for (let j = 0; j < stepVerts.length; j++) {
      const xx = xOf(stepVerts[j][0]);
      const yy = yOf(stepVerts[j][1]);
      if (first) {
        ctx.moveTo(xx, yy);
        first = false;
      } else {
        ctx.lineTo(xx, yy);
      }
    }
    if (points.length === 1) {
      const lx = xOf(points[0][0]);
      const ly = yOf(points[0][1]);
      ctx.moveTo(x0, ly);
      ctx.lineTo(lx, ly);
    }
    ctx.stroke();

    const marker = state.current_point || points[points.length - 1];
    if (marker) {
      const lx = xOf(marker[0]);
      const ly = yOf(marker[1]);
      ctx.fillStyle = "#ff9830";
      ctx.beginPath();
      ctx.arc(lx, ly, 5, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = "#c7d0d9";
      ctx.font = "12px system-ui";
      ctx.fillText(String(marker[1]), lx + 10, ly + 4);
    }

    canvas._drawState = { points: points, t0: t0, t1: t1, x0: x0, x1: x1, y0: y0, y1: y1, plotW: plotW, plotH: plotH, yOf: yOf, logScale: logScale, vmin: vmin, vmax: vmax };
  }

  function applyState(s) {
    $("kpiPos").textContent = s.position || "—";
    $("kpiStatus").textContent = s.status || "—";
    var rh = $("kpiRateHdr");
    if (rh) rh.textContent = s.rate_header || "RATE";
    $("kpiRate").textContent = s.queue_rate || "—";
    $("kpiElapsed").textContent = s.elapsed || "—";
    $("kpiRem").textContent = s.remaining || "—";
    const prog = Math.max(0, Math.min(100, s.progress || 0));
    $("kpiProgFill").style.width = prog + "%";
    $("kpiProgTxt").textContent = Math.round(prog) + "%";

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
    if (!w.length) kw.textContent = "—";

    $("infoLastCh").textContent = s.last_change || "—";
    $("infoLastAl").textContent = s.last_alert || "—";
    $("infoPath").textContent = s.resolved_path || "—";
    $("infoGlo").textContent = s.global_rate || "—";

    const la = s.last_alert || "";
    if (la && la !== lastAlertPrev) {
      toast(la, "warn");
    }
    lastAlertPrev = la;

    $("inpPath").value = s.source_path || "";

    $("btnYScale").textContent = s.graph_log_scale ? "Y → log" : "Y → linear";
    $("btnLive").textContent = s.graph_live_view ? "Live view: on" : "Live view: off";

    $("btnStartStop").textContent = s.running ? "Stop" : "Start";
    $("btnStartStop").className = s.running ? "btn btn--danger" : "btn btn--primary";

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

    const c = $("graphCanvas");
    drawGraph(c, s);

    resizeCanvas();
  }

  function resizeCanvas() {
    if (!window._lastState) return;
    const c = $("graphCanvas");
    const wrap = c.parentElement;
    if (!wrap) return;
    const dpr = window.devicePixelRatio || 1;
    const rect = wrap.getBoundingClientRect();
    const w = Math.max(400, Math.floor(rect.width - 4));
    const h = 280;
    c.width = w * dpr;
    c.height = h * dpr;
    c.style.width = w + "px";
    c.style.height = h + "px";
    const ctx = c.getContext("2d");
    if (ctx) ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    if (window._lastState) drawGraph(c, window._lastState);
  }

  window._lastState = null;

  function connectWs() {
    const proto = location.protocol === "https:" ? "wss:" : "ws:";
    const ws = new WebSocket(proto + "//" + location.host + "/ws");
    ws.onmessage = function (ev) {
      try {
        const s = JSON.parse(ev.data);
        window._lastState = s;
        applyState(s);
      } catch (e) {}
    };
    ws.onclose = function () {
      setTimeout(connectWs, 1500);
    };
  }

  function setupTour() {
    const steps = [
      { title: "Welcome", body: "This local web UI uses the same engine as the desktop app. No data leaves your machine.", sel: null },
      { title: "Logs folder", body: "Paste your Vintage Story Logs folder (or data path), then Start.", sel: ".topbar__path" },
      { title: "KPI row", body: "Use ✎ next to STATUS, RATE, or WARNINGS for inline edits (poll, rolling window, thresholds).", sel: "#secKpi" },
      { title: "Chart", body: "Hover for time/position. Copy as PNG or TSV for spreadsheets.", sel: "#graphCanvas" },
      { title: "Info & history", body: "Details below the chart; session log at the bottom.", sel: ".info" },
      { title: "Done", body: "Open ⚙ for more toggles. Enjoy!", sel: null },
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
      const step = steps[idx];
      title.textContent = step.title;
      body.textContent = step.body;
      stepNum.textContent = idx + 1 + " / " + steps.length;
      btnBack.style.display = idx ? "inline-block" : "none";
      btnNext.textContent = idx === steps.length - 1 ? "Done" : "Next";
      placeCard();
    }

    function hide() {
      overlay.classList.add("hidden");
      overlay.classList.remove("active");
      card.style.transform = "";
      postConfig({ tutorial_done: true }).catch(function () {});
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

  function setupPopovers() {
    $("btnEditPoll").onclick = function (e) {
      e.stopPropagation();
      $("popPoll").classList.toggle("hidden");
      $("popWindow").classList.add("hidden");
      $("popWarn").classList.add("hidden");
      $("inpPoll").value = window._lastState ? window._lastState.poll_sec : "2";
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
      $("popWindow").classList.toggle("hidden");
      $("popPoll").classList.add("hidden");
      $("popWarn").classList.add("hidden");
      $("inpWindow").value = window._lastState ? window._lastState.avg_window : "12";
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

    $("btnEditWarn").onclick = function (e) {
      e.stopPropagation();
      $("popWarn").classList.toggle("hidden");
      $("popPoll").classList.add("hidden");
      $("popWindow").classList.add("hidden");
      $("inpWarn").value = window._lastState ? window._lastState.alert_thresholds : "10, 5, 1";
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

    document.body.addEventListener("click", function () {
      $("popPoll").classList.add("hidden");
      $("popWindow").classList.add("hidden");
      $("popWarn").classList.add("hidden");
    });
    ["popPoll", "popWindow", "popWarn"].forEach(function (id) {
      const el = $(id);
      if (el)
        el.addEventListener("click", function (e) {
          e.stopPropagation();
        });
    });
  }

  function setupGraphCanvas() {
    const c = $("graphCanvas");
    let hover = null;
    c.addEventListener("mousemove", function (ev) {
      const st = c._drawState;
      if (!st || !st.points.length) return;
      const rect = c.getBoundingClientRect();
      const scaleX = c.width / rect.width;
      const mx = (ev.clientX - rect.left) * scaleX;
      const padL = PAD_L;
      const plotW = st.plotW;
      const x = Math.max(padL, Math.min(padL + plotW, mx));
      const t0 = st.t0;
      const t1 = st.t1;
      const targetT = t0 + ((x - padL) / plotW) * (t1 - t0);
      let best = st.points[0];
      let bestDt = Math.abs(best[0] - targetT);
      for (let i = 1; i < st.points.length; i++) {
        const dt = Math.abs(st.points[i][0] - targetT);
        if (dt < bestDt) {
          bestDt = dt;
          best = st.points[i];
        }
      }
      hover = best;
      const d = new Date(best[0] * 1000);
      $("graphHint").textContent =
        d.toLocaleString() + " · pos " + best[1];
    });
    c.addEventListener("mouseleave", function () {
      $("graphHint").textContent = "Move the mouse over the chart for time and position.";
    });
  }

  function setupChrome() {
    $("btnStartStop").onclick = function () {
      postToggle().catch(function (e) {
        toast(String(e), "warn");
      });
    };
    $("btnYScale").onclick = function () {
      const g = window._lastState && window._lastState.graph_log_scale;
      postConfig({ graph_log_scale: !g }).catch(function (e) {
        toast(String(e), "warn");
      });
    };
    $("btnLive").onclick = function () {
      const g = window._lastState && window._lastState.graph_live_view;
      postConfig({ graph_live_view: !g }).catch(function (e) {
        toast(String(e), "warn");
      });
    };
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
      const pts = (window._lastState && window._lastState.graph_points) || [];
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

    $("btnHelp").onclick = function () {
      fetch("/api/meta")
        .then(function (r) {
          return r.json();
        })
        .then(function (m) {
          $("helpCfgPath").textContent = "Config: " + (m.config_path || "");
          $("modalHelp").classList.remove("hidden");
        })
        .catch(function () {
          $("modalHelp").classList.remove("hidden");
        });
    };
    $("btnSettings").onclick = function () {
      $("modalSettings").classList.remove("hidden");
    };
    document.querySelectorAll("[data-close]").forEach(function (el) {
      el.addEventListener("click", function () {
        $("modalHelp").classList.add("hidden");
        $("modalSettings").classList.add("hidden");
      });
    });
    $("btnSaveSettings").onclick = function () {
      postConfig({
        show_every_change: $("chkEvery").checked,
        popup_enabled: $("chkPop").checked,
        sound_enabled: $("chkSnd").checked,
        completion_popup: $("chkCompPop").checked,
        completion_sound: $("chkCompSnd").checked,
      })
        .then(function () {
          $("modalSettings").classList.add("hidden");
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

    $("inpPath").addEventListener(
      "change",
      function () {
        postConfig({ source_path: $("inpPath").value.trim() }).catch(function (e) {
          toast(String(e.message || e), "warn");
        });
      },
    );
  }

  window.addEventListener("resize", resizeCanvas);

  setupChrome();
  setupPopovers();
  setupGraphCanvas();
  setupTour();
  connectWs();
  fetch("/api/meta")
    .then(function (r) {
      return r.json();
    })
    .then(function (m) {
      $("helpCfgPath").textContent = "Config: " + (m.config_path || "");
    })
    .catch(function () {});

  /** Fix Start button class — add btn--danger style */
  const st = document.createElement("style");
  st.textContent = ".btn--danger{background:#cf222e;border-color:#cf222e;}";
  document.head.appendChild(st);
})();
