/* ============================================================
   Canvas drawing utilities for waveforms, level meters, sparklines
   — Sahara Warm Theme (cream backgrounds, warm tones)
   ============================================================ */

/**
 * Draw a waveform on a canvas from an array of floats (-1..1).
 * Renders as vertical bars from center (audio visualization style)
 * with a soft glow effect.
 */
export function drawWaveform(canvas, buffer, color, glowColor) {
  const ctx = canvas.getContext('2d');
  const w = canvas._cssW || canvas.width;
  const h = canvas._cssH || canvas.height;
  const len = buffer.length;

  ctx.clearRect(0, 0, w, h);

  // Grid lines (warm cream tones)
  drawGrid(ctx, w, h);

  if (len === 0) {
    // Center line when idle
    ctx.strokeStyle = 'rgba(154, 144, 136, 0.15)';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(0, h / 2);
    ctx.lineTo(w, h / 2);
    ctx.stroke();
    return;
  }

  const mid = h / 2;
  const barWidth = Math.max(1, w / len);

  // Glow layer (wider, blurry bars)
  ctx.save();
  ctx.shadowBlur = 14;
  ctx.shadowColor = glowColor;
  ctx.globalAlpha = 0.35;
  ctx.fillStyle = color;
  for (let i = 0; i < len; i++) {
    const x = (i / len) * w;
    const amp = buffer[i] * mid * 0.9;
    ctx.fillRect(x, mid - Math.abs(amp), barWidth + 0.5, Math.abs(amp) * 2);
  }
  ctx.restore();

  // Solid bars
  ctx.save();
  ctx.shadowBlur = 4;
  ctx.shadowColor = glowColor;
  ctx.globalAlpha = 0.85;
  for (let i = 0; i < len; i++) {
    const x = (i / len) * w;
    const amp = buffer[i] * mid * 0.9;
    const absAmp = Math.abs(amp);

    // Color intensity based on amplitude
    const intensity = Math.min(1, absAmp / (mid * 0.5));
    ctx.globalAlpha = 0.4 + intensity * 0.55;
    ctx.fillStyle = color;
    ctx.fillRect(x, mid - absAmp, barWidth + 0.3, absAmp * 2);
  }
  ctx.restore();

  // Bright center line (signal trace)
  ctx.save();
  ctx.strokeStyle = color;
  ctx.lineWidth = 1;
  ctx.globalAlpha = 0.5;
  ctx.shadowBlur = 6;
  ctx.shadowColor = glowColor;
  ctx.beginPath();
  for (let i = 0; i < len; i++) {
    const x = (i / len) * w + barWidth / 2;
    const y = mid - buffer[i] * mid * 0.9;
    if (i === 0) ctx.moveTo(x, y);
    else ctx.lineTo(x, y);
  }
  ctx.stroke();
  ctx.restore();
}

function drawGrid(ctx, w, h) {
  ctx.save();
  ctx.strokeStyle = 'rgba(154, 144, 136, 0.08)';
  ctx.lineWidth = 0.5;
  // Horizontal
  for (let i = 0; i <= 8; i++) {
    const y = (i / 8) * h;
    ctx.beginPath();
    ctx.moveTo(0, y);
    ctx.lineTo(w, y);
    ctx.stroke();
  }
  // Vertical
  const vLines = Math.max(1, Math.floor(w / 50));
  for (let i = 0; i <= vLines; i++) {
    const x = (i / vLines) * w;
    ctx.beginPath();
    ctx.moveTo(x, 0);
    ctx.lineTo(x, h);
    ctx.stroke();
  }
  ctx.restore();
}

/**
 * Draw a vertical level meter.
 * `dbLevel` is in range [-60, 0].
 */
export function drawLevelMeter(canvas, dbLevel, color, glowColor) {
  const ctx = canvas.getContext('2d');
  const w = canvas._cssW || canvas.width;
  const h = canvas._cssH || canvas.height;

  ctx.clearRect(0, 0, w, h);

  // Background (warm cream tint instead of dark)
  ctx.fillStyle = 'rgba(236, 230, 220, 0.5)';
  ctx.beginPath();
  ctx.roundRect(0, 0, w, h, 4);
  ctx.fill();

  // dB labels (warm dark text)
  const dbSteps = [0, -10, -20, -30, -40, -50, -60];
  ctx.fillStyle = 'rgba(58, 48, 42, 0.8)';
  ctx.font = `bold ${Math.min(9, w * 0.28)}px "JetBrains Mono", monospace`;
  ctx.textAlign = 'right';

  const barX = 2;
  const barW = Math.max(4, w - 20);
  const barPad = 6;
  const barH = h - barPad * 2;

  for (const db of dbSteps) {
    const frac = 1 - (db + 60) / 60;
    const y = barPad + frac * barH;
    ctx.fillText(db.toString(), w - 1, y + 3);
  }

  // Segments
  const segs = 35;
  const segGap = 1.2;
  const segH = (barH - (segs - 1) * segGap) / segs;
  const level = Math.max(0, Math.min(1, (dbLevel + 60) / 60));
  const litSegs = Math.round(level * segs);

  ctx.shadowBlur = 0;
  for (let i = 0; i < segs; i++) {
    const segIndex = segs - 1 - i; // bottom=0, top=segs-1
    const y = barPad + i * (segH + segGap);
    const isLit = segIndex < litSegs;

    if (isLit) {
      const frac = segIndex / (segs - 1);
      let c;
      if (frac < 0.45) c = color;
      else if (frac < 0.7) c = '#e08850';
      else c = '#c0392b';

      ctx.fillStyle = c;
      ctx.shadowBlur = 3;
      ctx.shadowColor = c;
    } else {
      // Unlit segments: warm cream tinted
      ctx.fillStyle = 'rgba(216, 208, 200, 0.35)';
      ctx.shadowBlur = 0;
    }

    ctx.fillRect(barX, y, barW, segH);
  }
  ctx.shadowBlur = 0;
}

/**
 * Draw a sparkline from an array of values.
 */
export function drawSparkline(canvas, data, color) {
  const ctx = canvas.getContext('2d');
  const w = canvas._cssW || canvas.width;
  const h = canvas._cssH || canvas.height;

  ctx.clearRect(0, 0, w, h);

  if (!data || data.length < 2) return;

  const min = Math.min(...data);
  const max = Math.max(...data);
  const range = max - min || 1;
  const pad = 3;

  // Map data to x/y points
  const pts = data.map((v, i) => ({
    x: (i / (data.length - 1)) * w,
    y: h - ((v - min) / range) * (h - pad * 2) - pad,
  }));

  ctx.save();

  // --- Smooth curve using Catmull-Rom → cubic bezier ---
  ctx.strokeStyle = color;
  ctx.lineWidth = 2;
  ctx.lineJoin = 'round';
  ctx.lineCap = 'round';
  ctx.shadowBlur = 6;
  ctx.shadowColor = color;
  ctx.globalAlpha = 0.9;

  ctx.beginPath();
  ctx.moveTo(pts[0].x, pts[0].y);

  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = pts[i - 1] || pts[0];
    const p1 = pts[i];
    const p2 = pts[i + 1];
    const p3 = pts[i + 2] || pts[pts.length - 1];

    // Catmull-Rom to cubic bezier control points (tension = 0.35)
    const t = 0.35;
    const cp1x = p1.x + (p2.x - p0.x) * t;
    const cp1y = p1.y + (p2.y - p0.y) * t;
    const cp2x = p2.x - (p3.x - p1.x) * t;
    const cp2y = p2.y - (p3.y - p1.y) * t;

    ctx.bezierCurveTo(cp1x, cp1y, cp2x, cp2y, p2.x, p2.y);
  }
  ctx.stroke();

  // --- Gradient fill under the curve ---
  ctx.globalAlpha = 0.12;
  ctx.shadowBlur = 0;
  ctx.lineTo(w, h);
  ctx.lineTo(0, h);
  ctx.closePath();

  const grad = ctx.createLinearGradient(0, 0, 0, h);
  grad.addColorStop(0, color);
  grad.addColorStop(1, 'transparent');
  ctx.fillStyle = grad;
  ctx.fill();

  // --- Bright dot on the last data point ---
  const last = pts[pts.length - 1];
  ctx.globalAlpha = 1;
  ctx.shadowBlur = 8;
  ctx.shadowColor = color;
  ctx.fillStyle = color;
  ctx.beginPath();
  ctx.arc(last.x, last.y, 2.5, 0, Math.PI * 2);
  ctx.fill();

  ctx.restore();
}
