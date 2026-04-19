/* global window */
/**
 * Queue graph drawing — Canvas 2D parity with the historical Tk graph (theme via GET /api/meta).
 * Theme numbers/colors come from GET /api/meta ``graph_theme`` (vs_queue_monitor.core).
 */
(function (global) {
  "use strict";

  var DEFAULT_THEME = {
    max_draw_points: 1200,
    single_point_graph_span_sec: 60,
    graph_log_gamma: 1.15,
    pad_left: 46,
    pad_right: 22,
    pad_top: 12,
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
    ui_graph_empty: "#6e7680",
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

  function graphPlotTimeRange(points, liveView, running, singleSpan) {
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
    if (liveView && running) {
      t1 = Math.max(t1, Date.now() / 1000);
    }
    return [t0, t1];
  }

  function buildStepVertices(points) {
    var stepVertices = [];
    var i;
    for (i = 0; i < points.length; i++) {
      var t = points[i][0];
      var p = points[i][1];
      if (i === 0) {
        stepVertices.push([t, p]);
        continue;
      }
      var tPrev = points[i - 1][0];
      var pPrev = points[i - 1][1];
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

  function pad2(n) {
    return String(n).padStart(2, "0");
  }

  function fmtTooltipTs(tSec) {
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

  /**
   * @param {CanvasRenderingContext2D} ctx
   * @param {HTMLCanvasElement} canvas
   * @param {object} state — snapshot from /ws
   * @param {object|null} theme — from /api/meta graph_theme
   * @param {number[]|null} hoverPoint — [tSec, pos] or null
   */
  function draw(ctx, canvas, state, theme, hoverPoint) {
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
    var points = downsamplePoints(rawPoints, th.max_draw_points);
    var liveView = !!state.graph_live_view;
    var running = !!state.running;
    var logScale = !!state.graph_log_scale;
    var gamma = th.graph_log_gamma;

    ctx.fillStyle = th.ui_graph_plot;
    ctx.fillRect(x0, y0, plotW, plotH);

    if (!points.length) {
      ctx.fillStyle = th.ui_graph_empty;
      ctx.font = "14px system-ui,Segoe UI,sans-serif";
      ctx.fillText("No data yet", x0 + 6, y0 + 20);
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
    var tr = graphPlotTimeRange(rangePts, liveView, running, th.single_point_graph_span_sec);
    var t0 = tr[0];
    var t1 = tr[1];
    var span = t1 - t0;
    if (span <= 0) {
      span = 1;
    }

    var vals = points.map(function (p) {
      return p[1];
    });
    var vmin = Math.min.apply(null, vals);
    var vmax = Math.max.apply(null, vals);
    if (vmax === vmin) {
      vmax = vmin + 1;
    }
    vmin = Math.max(0, vmin);

    function xOf(t) {
      return x0 + ((t - t0) / (t1 - t0)) * plotW;
    }

    function yOf(v) {
      var vv = Math.max(vmin, Math.min(vmax, v));
      if (!logScale) {
        var frac = (vmax - vv) / Math.max(1, vmax - vmin);
        return y0 + frac * plotH;
      }
      var lvmin = Math.log(vmin + 1);
      var lvmax = Math.log(vmax + 1);
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
    var start = Math.floor(vmin / tickStep) * tickStep;
    var end = Math.ceil((vmax + tickStep - 1) / tickStep) * tickStep;
    var tickVals = [];
    var val;
    for (val = start; val <= end; val += tickStep) {
      if (vmin <= val && val <= vmax) {
        if (val === 0 && vmin > 0) {
          continue;
        }
        tickVals.push(val);
      }
    }
    if (vmin <= 5 && 5 <= vmax) {
      tickVals.push(1, 2, 3, 4, 5);
    }
    tickVals.push(vmin, vmax);
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
    if (tickTimes[tickTimes.length - 1] < t1 - interval * 0.4) {
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
    tickTimes = dedup;

    var minLabelDx = Math.max(76, Math.min(130, plotW / 7.5));
    var lastXLabel = null;
    for (idx = 0; idx < tickTimes.length; idx++) {
      t = tickTimes[idx];
      var x = xOf(t);
      var d = new Date(t * 1000);
      var label =
        fmt === "hms"
          ? pad2(d.getHours()) + ":" + pad2(d.getMinutes()) + ":" + pad2(d.getSeconds())
          : pad2(d.getHours()) + ":" + pad2(d.getMinutes());
      ctx.strokeStyle = axisColor;
      ctx.beginPath();
      ctx.moveTo(x, y1);
      ctx.lineTo(x, y1 + 4);
      ctx.stroke();
      if (lastXLabel === null || Math.abs(x - lastXLabel) >= minLabelDx) {
        ctx.fillStyle = textColor;
        ctx.font = "11px system-ui,Segoe UI,sans-serif";
        ctx.textAlign = "center";
        ctx.textBaseline = "top";
        ctx.fillText(label, x, y1 + 14);
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

    ctx.fillStyle = textColor;
    ctx.font = "11px system-ui,Segoe UI,sans-serif";
    ctx.textAlign = "left";
    ctx.textBaseline = "top";
    ctx.fillText("min " + vmin + "  max " + vmax, x0 + 6, y0 + 6);

    var stepVertices = buildStepVertices(points);
    var line = [];
    var j;
    for (j = 0; j < stepVertices.length; j++) {
      line.push(xOf(stepVertices[j][0]), yOf(stepVertices[j][1]));
    }

    ctx.strokeStyle = th.ui_graph_line;
    ctx.lineWidth = 2;
    ctx.lineJoin = "miter";
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

    var marker = state.current_point || points[points.length - 1];
    if (marker) {
      var lastT = marker[0];
      var lastV = marker[1];
      var lx = xOf(lastT);
      var ly = yOf(lastV);
      ctx.fillStyle = th.ui_graph_marker;
      ctx.beginPath();
      ctx.arc(lx, ly, 4, 0, Math.PI * 2);
      ctx.fill();
      ctx.fillStyle = textColor;
      ctx.font = "12px system-ui,Segoe UI,sans-serif";
      ctx.textAlign = "left";
      ctx.textBaseline = "middle";
      ctx.fillText(String(lastV), lx + 10, ly);
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
      rawPoints: rawPoints,
      t0: t0,
      t1: t1,
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

  global.VSQMGraph = {
    draw: draw,
    mergeTheme: mergeTheme,
    fmtTooltipTs: fmtTooltipTs,
    graphPlotTimeRange: graphPlotTimeRange,
    downsamplePoints: downsamplePoints,
  };
})(typeof window !== "undefined" ? window : this);
