/* global window */
/**
 * Queue graph drawing — Canvas 2D parity with the historical Tk graph (theme via GET /api/meta).
 * Theme numbers/colors come from GET /api/meta ``graph_theme`` (vs_queue_monitor.core).
 */
(function (global) {
  "use strict";

  var DEFAULT_THEME = {
    max_draw_points: 5000,
    single_point_graph_span_sec: 60,
    graph_log_gamma: 1.15,
    pad_left: 46,
    pad_right: 22,
    pad_top: 22,
    pad_bottom: 32,
    ui_graph_bg: "#0d0f12",
    ui_graph_plot: "#141820",
    ui_graph_grid: "#1e232c",
    ui_graph_axis: "#4a5260",
    ui_graph_text: "#9fa7b3",
    ui_graph_line: "#5794f2",
    ui_graph_marker: "#6b9bd6",
    ui_graph_hover_cursor: "#f0f4f8",
    ui_graph_minor_tick: "#3a4250",
    ui_graph_empty: "#9fa7b3",
  };

  function mergeTheme(t) {
    var o = {};
    var k;
    for (k in DEFAULT_THEME) {
      if (Object.prototype.hasOwnProperty.call(DEFAULT_THEME, k)) {
        o[k] = DEFAULT_THEME[k];
      }
    }
    if (t && typeof t === "object") {
      for (k in t) {
        if (Object.prototype.hasOwnProperty.call(t, k)) {
          o[k] = t[k];
        }
      }
    }
    return o;
  }

  function downsamplePoints(points, maxN) {
    if (!points.length || points.length <= maxN) {
      return points.slice();
    }
    var step = Math.max(1, Math.floor(points.length / maxN));
    var out = [];
    var i;
    for (i = 0; i < points.length; i += step) {
      out.push(points[i]);
    }
    var last = points[points.length - 1];
    var tail = out[out.length - 1];
    if (!tail || tail[0] !== last[0]) {
      out.push(last);
    }
    return out;
  }

  function terminalCutoffIndex(points) {
    var i;
    for (i = 0; i < points.length; i++) {
      if (points[i][1] <= 0) {
        return i;
      }
    }
    return -1;
  }

  function graphPlotTimeRange(points, extendToNow, singleSpan) {
    if (!points.length) {
      return [0, 1];
    }
    if (points.length === 1) {
      var mid = points[0][0];
      var half = singleSpan / 2;
      return [mid - half, mid + half];
    }
    var t0 = points[0][0];
    var t1 = points[points.length - 1][0];
    if (t1 <= t0) {
      t1 = t0 + 1e-6;
    }
    if (extendToNow) {
      var span = Math.max(1e-6, t1 - t0);
      var rightPad = Math.max(4, span * 0.04);
      t1 += rightPad;
      t1 = Math.max(t1, Date.now() / 1000);
    }
    return [t0, t1];
  }

  function buildStepVertices(points) {
    var normalized = [];
    var stepVertices = [];
    var i;
    for (i = 0; i < points.length; i++) {
      var rawT = points[i][0];
      var rawP = points[i][1];
      if (!normalized.length) {
        normalized.push([rawT, rawP]);
        continue;
      }
      var prevNorm = normalized[normalized.length - 1];
      if (rawT < prevNorm[0]) {
        continue;
      }
      if (rawT === prevNorm[0]) {
        normalized[normalized.length - 1] = [rawT, rawP];
        continue;
      }
      normalized.push([rawT, rawP]);
    }
    for (i = 0; i < normalized.length; i++) {
      var t = normalized[i][0];
      var p = normalized[i][1];
      if (i === 0) {
        stepVertices.push([t, p]);
        continue;
      }
      var tPrev = normalized[i - 1][0];
      var pPrev = normalized[i - 1][1];
      if (t <= tPrev) {
        continue;
      }
      if (p !== pPrev) {
        stepVertices.push([t, pPrev]);
      }
      stepVertices.push([t, p]);
    }
    return stepVertices;
  }

  function drawGraphEventMarker(ctx, kind, x, y) {
    var color = kind === "warning" ? "#c89b3c" : kind === "connect" ? "#2e8b57" : kind === "disconnect" ? "#b4545c" : null;
    if (!color) return;
    ctx.save();
    ctx.beginPath();
    ctx.arc(x, y, 5, 0, Math.PI * 2);
    ctx.fillStyle = color;
    ctx.fill();
    ctx.strokeStyle = "rgba(12, 15, 18, 0.78)";
    ctx.lineWidth = 1;
    ctx.stroke();
    ctx.restore();
  }

  function pad2(n) {
    return String(n).padStart(2, "0");
  }

  function fmtRelativeTime(tSec, baseSec, includeSeconds) {
    var delta = Math.max(0, Math.round(tSec - baseSec));
    var h = Math.floor(delta / 3600);
    var m = Math.floor((delta % 3600) / 60);
    var s = delta % 60;
    if (includeSeconds || h > 0) {
      return h > 0
        ? (h + ":" + pad2(m) + ":" + pad2(s))
        : (m + ":" + pad2(s));
    }
    return h > 0 ? (h + ":" + pad2(m)) : String(m) + "m";
  }

  function fmtTooltipTs(tSec, mode, baseSec) {
    if (mode === "relative") {
      return fmtRelativeTime(tSec, baseSec == null ? tSec : baseSec, true);
    }
    var dj =
      typeof global !== "undefined" && global.dayjs
        ? global.dayjs
        : typeof window !== "undefined" && window.dayjs
          ? window.dayjs
          : null;
    if (dj) {
      return dj.unix(tSec).format("YYYY-MM-DD HH:mm:ss");
    }
    var d = new Date(tSec * 1000);
    return (
      d.getFullYear() +
      "-" +
      pad2(d.getMonth() + 1) +
      "-" +
      pad2(d.getDate()) +
      " " +
      pad2(d.getHours()) +
      ":" +
      pad2(d.getMinutes()) +
      ":" +
      pad2(d.getSeconds())
    );
  }

  function formatOverlayDuration(totalSeconds) {
    if (totalSeconds == null || !isFinite(totalSeconds) || totalSeconds < 0) {
      return "-";
    }
    var whole = Math.floor(totalSeconds);
    var h = Math.floor(whole / 3600);
    var m = Math.floor((whole % 3600) / 60);
    var s = whole % 60;
    if (h > 0) {
      return h + ":" + pad2(m) + ":" + pad2(s);
    }
    return m + ":" + pad2(s);
  }

  function computeOverlayStats(points) {
    if (!points || !points.length) {
      return null;
    }
    var startPos = null;
    var startT = null;
    var i;
    for (i = 0; i < points.length; i++) {
      if (points[i][1] > 1) {
        startPos = points[i][1];
        startT = points[i][0];
        break;
      }
    }
    if (startPos == null) {
      startPos = points[0][1];
      startT = points[0][0];
    }
    var endPos = points[points.length - 1][1];
    var endT = points[points.length - 1][0];
    var cleared = startPos != null && endPos != null ? Math.max(0, startPos - endPos) : null;
    var seconds = startT != null && endT != null ? Math.max(0, endT - startT) : null;
    var avgMinPerPos =
      seconds != null && seconds > 0 && cleared != null && cleared > 0
        ? (seconds / 60) / cleared
        : null;
    var vals = points.map(function (p) {
      return p[1];
    });
    return {
      min: Math.min.apply(null, vals),
      max: Math.max.apply(null, vals),
      startPos: startPos,
      endPos: endPos,
      cleared: cleared,
      seconds: seconds,
      avgMinPerPos: avgMinPerPos,
      samples: points.length,
    };
  }

  /**
   * @param {CanvasRenderingContext2D} ctx
   * @param {HTMLCanvasElement} canvas
   * @param {object} state — snapshot from /ws
   * @param {object|null} theme — from /api/meta graph_theme
   * @param {number[]|null} hoverPoint — [tSec, pos] or null
   */
  function draw(ctx, canvas, state, theme, hoverPoint, viewRange) {
    var th = mergeTheme(theme);
    var dpr = window.devicePixelRatio || 1;
    var width = canvas.width / dpr;
    var height = canvas.height / dpr;

    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.fillStyle = th.ui_graph_bg;
    ctx.fillRect(0, 0, width, height);

    if (width <= 10 || height <= 10) {
      return;
    }

    var padLeft = th.pad_left;
    var padRight = th.pad_right;
    var padTop = th.pad_top;
    var padBottom = th.pad_bottom;
    var plotW = Math.max(1, width - padLeft - padRight);
    var plotH = Math.max(1, height - padTop - padBottom);
    var x0 = padLeft;
    var y0 = padTop;
    var x1 = padLeft + plotW;
    var y1 = padTop + plotH;

    var rawPoints = state.graph_points || [];
    var liveView = !!state.graph_live_view;
    var running = !!state.running;
    var progress = typeof state.progress === "number" ? state.progress : 0;
    var terminalCutoff = liveView ? terminalCutoffIndex(rawPoints) : -1;
    if (terminalCutoff >= 0) {
      rawPoints = rawPoints.slice(0, terminalCutoff + 1);
    }
    var points = downsamplePoints(rawPoints, th.max_draw_points);
    var extendToNow = liveView && running && progress < 1.0;
    var logScale = !!state.graph_log_scale;
    var timeMode = state.graph_time_mode || "relative";
    var gamma = th.graph_log_gamma;

    ctx.fillStyle = th.ui_graph_plot;
    ctx.fillRect(x0, y0, plotW, plotH);

    if (!points.length) {
      var cx = x0 + plotW / 2;
      var cy = y0 + plotH / 2;
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      var emptyLine1, emptyLine2;
      if (!state.running && !(state.source_path || "").trim()) {
        emptyLine1 = "Queue data will appear here";
        emptyLine2 = "← Set a log folder above, then click Start";
      } else if (state.running && (state.source_path || "").trim()) {
        emptyLine1 = "Waiting for queue data…";
        emptyLine2 = "Join a server queue and position changes will plot here.";
      } else {
        emptyLine1 = "No data yet";
        emptyLine2 = "Queue position will plot here from the log.";
      }
      ctx.fillStyle = th.ui_graph_empty;
      ctx.font = "15px system-ui,Segoe UI,sans-serif";
      ctx.fillText(emptyLine1, cx, cy - 10);
      ctx.fillStyle = th.ui_graph_axis;
      ctx.font = "12px system-ui,Segoe UI,sans-serif";
      ctx.fillText(emptyLine2, cx, cy + 12);
      ctx.textAlign = "start";
      ctx.textBaseline = "alphabetic";
      canvas._drawState = {
        points: [],
        drawn: [],
        rawPoints: [],
        t0: 0,
        t1: 1,
        x0: x0,
        x1: x1,
        y0: y0,
        y1: y1,
        plotW: plotW,
        plotH: plotH,
        logScale: false,
        theme: th,
      };
      return;
    }

    var rangePts = rawPoints.length ? rawPoints : points;
    var fullTr = graphPlotTimeRange(rangePts, extendToNow, th.single_point_graph_span_sec);
    var tr;
    if (viewRange && viewRange.length === 2) {
      tr = [viewRange[0], viewRange[1]];
    } else {
      tr = fullTr;
    }
    var t0 = tr[0];
    var t1 = tr[1];
    var span = t1 - t0;
    if (span <= 0) {
      span = 1;
    }

    var viewPts = (viewRange && viewRange.length === 2)
      ? points.filter(function (p) { return p[0] >= t0 && p[0] <= t1; })
      : points;
    if (!viewPts.length) viewPts = points;
    var vals = viewPts.map(function (p) {
      return p[1];
    });
    var vmin = Math.min.apply(null, vals);
    var vmax = Math.max.apply(null, vals);
    var axisVmin = Math.max(0, vmin);
    var axisVmax = vmax;
    if (axisVmax === axisVmin) {
      axisVmax = axisVmin + 1;
    }
    var drawVmin = axisVmin;
    var drawVmax = axisVmax;

    function xOf(t) {
      return x0 + ((t - t0) / (t1 - t0)) * plotW;
    }

    function yOf(v) {
      var vv = Math.max(drawVmin, Math.min(drawVmax, v));
      if (!logScale) {
        var frac = (drawVmax - vv) / Math.max(1, drawVmax - drawVmin);
        return y0 + frac * plotH;
      }
      var lvmin = Math.log(drawVmin + 1);
      var lvmax = Math.log(drawVmax + 1);
      var lv = Math.log(vv + 1);
      var frac = lvmax <= lvmin ? 0 : (lvmax - lv) / (lvmax - lvmin);
      frac = Math.max(0, Math.min(1, frac));
      frac = Math.pow(frac, gamma);
      return y0 + frac * plotH;
    }

    var axisColor = th.ui_graph_axis;
    var textColor = th.ui_graph_text;
    ctx.strokeStyle = axisColor;
    ctx.beginPath();
    ctx.moveTo(x0, y0);
    ctx.lineTo(x0, y1);
    ctx.moveTo(x0, y1);
    ctx.lineTo(x1, y1);
    ctx.stroke();

    var tickStep = 5;
    var start = Math.floor(axisVmin / tickStep) * tickStep;
    var end = Math.ceil((axisVmax + tickStep - 1) / tickStep) * tickStep;
    var tickVals = [];
    var val;
    for (val = start; val <= end; val += tickStep) {
      if (axisVmin <= val && val <= axisVmax) {
        if (val === 0 && axisVmin > 0) {
          continue;
        }
        tickVals.push(val);
      }
    }
    if (axisVmin <= 5 && 5 <= axisVmax) {
      tickVals.push(1, 2, 3, 4, 5);
    }
    tickVals.push(axisVmin, axisVmax);
    tickVals = Array.from(new Set(tickVals)).sort(function (a, b) {
      return b - a;
    });

    var lastYLabel = null;
    var minLabelDy = 16;
    var idx;
    for (idx = 0; idx < tickVals.length; idx++) {
      val = tickVals[idx];
      var y = yOf(val);
      ctx.beginPath();
      ctx.moveTo(x0 - 4, y);
      ctx.lineTo(x0, y);
      ctx.strokeStyle = axisColor;
      ctx.stroke();
      if (lastYLabel === null || Math.abs(y - lastYLabel) >= minLabelDy) {
        ctx.fillStyle = textColor;
        ctx.font = "11px system-ui,Segoe UI,sans-serif";
        ctx.textAlign = "right";
        ctx.textBaseline = "middle";
        ctx.fillText(String(val), x0 - 6, y);
        lastYLabel = y;
      }
      if (idx > 0 && idx < tickVals.length - 1) {
        ctx.strokeStyle = th.ui_graph_grid;
        ctx.beginPath();
        ctx.moveTo(x0, y);
        ctx.lineTo(x1, y);
        ctx.stroke();
      }
    }

    // Draw event icons ON the axis line before time labels so labels render over them.
    var graphEvents = state.graph_events || [];
    if (graphEvents.length) {
      for (j = 0; j < graphEvents.length; j++) {
        var event = graphEvents[j];
        if (!event || !isFinite(event.t) || !isFinite(event.pos)) {
          continue;
        }
        if (event.t < t0 - 1e-6 || event.t > t1 + 1e-6) {
          continue;
        }
        var ex = xOf(event.t);
        drawGraphEventMarker(ctx, event.kind, ex, y1);
      }
    }

    var candidates = [5, 10, 15, 30, 60, 300, 600, 900, 1800, 3600, 7200, 21600];
    var targetTicks = 6;
    var interval = candidates[candidates.length - 1];
    var ci;
    for (ci = 0; ci < candidates.length; ci++) {
      if (span / candidates[ci] <= targetTicks) {
        interval = candidates[ci];
        break;
      }
    }
    var fmt = interval < 3600 ? "hms" : "hm";
    var firstTick = Math.ceil(t0 / interval) * interval;
    var lastTick = Math.floor(t1 / interval) * interval;
    var tickTimes = [];
    var t = firstTick;
    while (t <= lastTick + 1e-6) {
      tickTimes.push(t);
      t += interval;
    }
    if (!tickTimes.length || tickTimes[0] - t0 > interval * 0.4) {
      tickTimes.unshift(t0);
    }
    if (Math.abs(tickTimes[tickTimes.length - 1] - t1) > 1e-6) {
      tickTimes.push(t1);
    }
    var dedup = [];
    tickTimes
      .slice()
      .sort(function (a, b) {
        return a - b;
      })
      .forEach(function (tv) {
        var xv = xOf(tv);
        if (!dedup.length || Math.abs(xv - xOf(dedup[dedup.length - 1])) > 2) {
          dedup.push(tv);
        }
      });
    if (!dedup.length || Math.abs(dedup[dedup.length - 1] - t1) > 1e-6) {
      dedup.push(t1);
    } else {
      dedup[dedup.length - 1] = t1;
    }
    tickTimes = dedup;

    var minLabelDx = Math.max(76, Math.min(130, plotW / 7.5));
    var lastXLabel = null;
    for (idx = 0; idx < tickTimes.length; idx++) {
      t = tickTimes[idx];
      var x = xOf(t);
      var d = new Date(t * 1000);
      var label;
      if (timeMode === "relative") {
        label = fmtRelativeTime(t, rangePts[0][0], fmt === "hms");
      } else {
        label =
          fmt === "hms"
            ? pad2(d.getHours()) + ":" + pad2(d.getMinutes()) + ":" + pad2(d.getSeconds())
            : pad2(d.getHours()) + ":" + pad2(d.getMinutes());
      }
      ctx.strokeStyle = axisColor;
      ctx.beginPath();
      ctx.moveTo(x, y1);
      ctx.lineTo(x, y1 + 4);
      ctx.stroke();
      var isLast = idx === tickTimes.length - 1;
      if (isLast || lastXLabel === null || Math.abs(x - lastXLabel) >= minLabelDx) {
        ctx.font = "11px system-ui,Segoe UI,sans-serif";
        ctx.textBaseline = "top";
        var lx = isLast ? x + 2 : x;
        var lw = ctx.measureText(label).width;
        var lbgX = isLast ? lx - lw - 2 : lx - lw / 2 - 2;
        ctx.fillStyle = th.ui_graph_bg;
        ctx.fillRect(lbgX, y1 + 13, lw + 4, 13);
        ctx.fillStyle = textColor;
        ctx.textAlign = isLast ? "right" : "center";
        ctx.fillText(label, lx, y1 + 14);
        lastXLabel = x;
      }
      if (idx > 0 && idx < tickTimes.length - 1) {
        ctx.strokeStyle = th.ui_graph_grid;
        ctx.beginPath();
        ctx.moveTo(x, y0);
        ctx.lineTo(x, y1);
        ctx.stroke();
      }
    }

    var spanSec = t1 - t0;
    if (spanSec > 1e-6) {
      var majorXs = tickTimes.map(function (tv) {
        return xOf(tv);
      });
      var minorCandidates = [60, 120, 300, 600, 900, 1800, 3600, 7200];
      var minorStepSec = 60;
      var brokeMinor = false;
      var si;
      for (si = 0; si < minorCandidates.length; si++) {
        minorStepSec = minorCandidates[si];
        var nDivs = spanSec / minorStepSec;
        if (nDivs < 1.5) {
          continue;
        }
        var pxPerDiv = plotW / nDivs;
        if (pxPerDiv >= 5) {
          brokeMinor = true;
          break;
        }
      }
      if (!brokeMinor) {
        minorStepSec = Math.max(60, spanSec / Math.max(1, plotW / 5));
      }
      var majorClearPx = 6;

      function tooCloseToMajor(xm) {
        var j;
        for (j = 0; j < majorXs.length; j++) {
          if (Math.abs(xm - majorXs[j]) <= majorClearPx) {
            return true;
          }
        }
        return false;
      }

      var mStart = Math.ceil(t0 / minorStepSec) * minorStepSec;
      var m = mStart;
      var lastMinorX = null;
      while (m <= t1 + 1e-6) {
        var xm = xOf(m);
        if (x0 <= xm && xm <= x1 && !tooCloseToMajor(xm)) {
          if (lastMinorX === null || Math.abs(xm - lastMinorX) >= 4) {
            ctx.strokeStyle = th.ui_graph_minor_tick;
            ctx.lineWidth = 1;
            ctx.beginPath();
            ctx.moveTo(xm, y1);
            ctx.lineTo(xm, y1 + 3);
            ctx.stroke();
            lastMinorX = xm;
          }
        }
        m += minorStepSec;
      }
    }

    var overlayStats = null;
    try {
      overlayStats = computeOverlayStats(viewPts);
    } catch (_overlayErr) {
      overlayStats = null;
    }
    if (overlayStats) {
      var overlayLines = [
        "Start pos: " + overlayStats.startPos,
        "Current pos: " + overlayStats.endPos,
      ];
      if (
        overlayStats.min !== overlayStats.endPos ||
        overlayStats.max !== overlayStats.startPos
      ) {
        overlayLines.push("Min pos: " + overlayStats.min);
        overlayLines.push("Max pos: " + overlayStats.max);
      }
      overlayLines.push(
        "Pos Change: " + (overlayStats.cleared == null ? "-" : overlayStats.cleared)
      );
      overlayLines.push(
        "Duration: " + formatOverlayDuration(overlayStats.seconds)
      );
      overlayLines.push(
        "Full Rate: " +
          (overlayStats.avgMinPerPos == null
            ? "-"
            : overlayStats.avgMinPerPos.toFixed(2) + " m/p")
      );
      ctx.font = "11px system-ui,Segoe UI,sans-serif";
      ctx.textBaseline = "top";
      ctx.textAlign = "left";
      var overlayPadX = 8;
      var overlayPadY = 6;
      var overlayLineH = 14;
      var overlayW = 0;
      var oi;
      for (oi = 0; oi < overlayLines.length; oi++) {
        overlayW = Math.max(overlayW, ctx.measureText(overlayLines[oi]).width);
      }
      var boxW = overlayW + overlayPadX * 2;
      var boxH = overlayLines.length * overlayLineH + overlayPadY * 2 - 2;
      var boxX = x1 - boxW - 8;
      var boxY = y0 + 8;
      ctx.fillStyle = "rgba(20, 24, 32, 0.82)";
      ctx.fillRect(boxX, boxY, boxW, boxH);
      ctx.strokeStyle = th.ui_graph_grid;
      ctx.strokeRect(boxX + 0.5, boxY + 0.5, boxW - 1, boxH - 1);
      ctx.fillStyle = textColor;
      for (oi = 0; oi < overlayLines.length; oi++) {
        ctx.fillText(
          overlayLines[oi],
          boxX + overlayPadX,
          boxY + overlayPadY + oi * overlayLineH
        );
      }
    }

    var stepVertices = buildStepVertices(points);
    var line = [];
    var j;
    for (j = 0; j < stepVertices.length; j++) {
      line.push(xOf(stepVertices[j][0]), yOf(stepVertices[j][1]));
    }

    ctx.strokeStyle = th.ui_graph_line;
    ctx.lineWidth = 2;
    ctx.lineJoin = "miter";
    ctx.save();
    ctx.beginPath();
    ctx.rect(x0, y0, plotW, plotH);
    ctx.clip();
    if (line.length >= 4) {
      ctx.beginPath();
      ctx.moveTo(line[0], line[1]);
      for (j = 2; j < line.length; j += 2) {
        ctx.lineTo(line[j], line[j + 1]);
      }
      ctx.stroke();
    } else if (points.length === 1 && stepVertices.length) {
      var ts0 = stepVertices[0][0];
      var pv0 = stepVertices[0][1];
      var lx0 = xOf(ts0);
      var ly0 = yOf(pv0);
      ctx.beginPath();
      ctx.moveTo(x0, ly0);
      ctx.lineTo(lx0, ly0);
      ctx.stroke();
    }
    ctx.restore();

    var visibleMarker = viewPts.length ? viewPts[viewPts.length - 1] : null;
    var marker =
      (viewRange && viewRange.length === 2)
        ? (visibleMarker || points[points.length - 1])
        : (terminalCutoff >= 0 ? points[points.length - 1] : (state.current_point || points[points.length - 1]));
    if (marker) {
      var lastT = marker[0];
      var lastV = marker[1];
      var lx = xOf(lastT);
      var ly = yOf(lastV);
      var isHistorical = !running || progress >= 1.0;
      var terminalMarkerKind = null;
      if (isHistorical && graphEvents.length) {
        var lastEvent = null;
        for (var ei = graphEvents.length - 1; ei >= 0; ei--) {
          var ge = graphEvents[ei];
          if (
            ge &&
            ge.kind !== "warning" &&
            isFinite(ge.t) &&
            ge.t >= t0 - 1e-6 &&
            ge.t <= t1 + 1e-6
          ) {
            lastEvent = ge;
            break;
          }
        }
        if (lastEvent) terminalMarkerKind = lastEvent.kind;
      }

      if (!terminalMarkerKind) {
        ctx.fillStyle = th.ui_graph_marker;
        ctx.beginPath();
        ctx.arc(lx, ly, 5, 0, Math.PI * 2);
        ctx.fill();
      } else {
        drawGraphEventMarker(ctx, terminalMarkerKind, lx, ly);
      }
      ctx.fillStyle = textColor;
      ctx.font = "12px system-ui,Segoe UI,sans-serif";
      var markerText = String(lastV);
      var markerTextW = ctx.measureText(markerText).width;
      ctx.textBaseline = "middle";
      if (lx + 10 + markerTextW <= x1 - 2) {
        ctx.textAlign = "left";
        ctx.fillText(markerText, lx + 10, ly);
      } else {
        ctx.textAlign = "right";
        ctx.fillText(markerText, lx - 8, ly);
      }
    }

    if (hoverPoint && hoverPoint.length >= 2) {
      var ht = hoverPoint[0];
      var hv = hoverPoint[1];
      var hx = xOf(ht);
      var hy = yOf(hv);
      ctx.strokeStyle = th.ui_graph_hover_cursor;
      ctx.lineWidth = 1;
      ctx.beginPath();
      ctx.moveTo(hx, y0);
      ctx.lineTo(hx, y1);
      ctx.stroke();
      ctx.fillStyle = th.ui_graph_plot;
      ctx.beginPath();
      ctx.arc(hx, hy, 5, 0, Math.PI * 2);
      ctx.fill();
      ctx.strokeStyle = th.ui_graph_line;
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(hx, hy, 5, 0, Math.PI * 2);
      ctx.stroke();
    }

    canvas._drawState = {
      points: points,
      drawn: points,
      rawPoints: viewPts,
      t0: t0,
      t1: t1,
      fullT0: fullTr[0],
      fullT1: fullTr[1],
      x0: x0,
      x1: x1,
      y0: y0,
      y1: y1,
      plotW: plotW,
      plotH: plotH,
      logScale: logScale,
      vmin: vmin,
      vmax: vmax,
      yOf: yOf,
      xOf: xOf,
      theme: th,
      fmtTooltipTs: fmtTooltipTs,
    };
  }

  global.VsQueueMonitorGraph = {
    draw: draw,
    mergeTheme: mergeTheme,
    fmtTooltipTs: fmtTooltipTs,
    graphPlotTimeRange: graphPlotTimeRange,
    downsamplePoints: downsamplePoints,
  };
})(typeof window !== "undefined" ? window : this);
