import React, { useRef, useEffect, useCallback } from 'react';
import { drawWaveform, drawLevelMeter } from '../utils/drawWave.js';

const BUFFER_SIZE = 1500; // ~5 seconds of display at 15fps × 200pts rolling

export default function WaveformPanel({ variant, data, running, metrics }) {
  const canvasRef = useRef(null);
  const meterRef = useRef(null);
  const bufferRef = useRef([]);
  const rafRef = useRef(null);

  const isNoisy = variant === 'noisy';
  const color = isNoisy ? '#c2652a' : '#4f7a55';
  const glowColor = isNoisy ? 'rgba(194, 101, 42, 0.4)' : 'rgba(79, 122, 85, 0.35)';
  const label = isNoisy ? 'Noisy Input' : 'Clean Output';
  const subtitle = isNoisy ? 'Raw Unprocessed Environmental Feed' : 'AI Denoised Vocal Pristine Stream';

  // Append new data to rolling buffer
  useEffect(() => {
    if (!data || data.length === 0) return;
    const buf = bufferRef.current;
    buf.push(...data);
    // Trim to max size
    if (buf.length > BUFFER_SIZE) {
      buf.splice(0, buf.length - BUFFER_SIZE);
    }
  }, [data]);

  // Clear buffer when stopping
  useEffect(() => {
    if (!running) {
      bufferRef.current = [];
    }
  }, [running]);

  // Resize canvas to match CSS size (for sharp rendering)
  const resizeCanvas = useCallback(() => {
    const canvas = canvasRef.current;
    const meter = meterRef.current;
    if (canvas) {
      const rect = canvas.getBoundingClientRect();
      canvas.width = rect.width * window.devicePixelRatio;
      canvas.height = rect.height * window.devicePixelRatio;
      const ctx = canvas.getContext('2d');
      ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
      canvas._cssW = rect.width;
      canvas._cssH = rect.height;
    }
    if (meter) {
      const rect = meter.getBoundingClientRect();
      meter.width = rect.width * window.devicePixelRatio;
      meter.height = rect.height * window.devicePixelRatio;
      const ctx = meter.getContext('2d');
      ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
      meter._cssW = rect.width;
      meter._cssH = rect.height;
    }
  }, []);

  useEffect(() => {
    resizeCanvas();
    window.addEventListener('resize', resizeCanvas);
    return () => window.removeEventListener('resize', resizeCanvas);
  }, [resizeCanvas]);

  // Animation loop
  useEffect(() => {
    let lastT = 0;

    const animate = (t) => {
      rafRef.current = requestAnimationFrame(animate);

      // Throttle to ~30fps for perf
      if (t - lastT < 33) return;
      lastT = t;

      const canvas = canvasRef.current;
      const meter = meterRef.current;
      if (!canvas || !meter) return;

      const w = canvas._cssW || canvas.getBoundingClientRect().width;
      const h = canvas._cssH || canvas.getBoundingClientRect().height;

      const buf = bufferRef.current;

      // If not running, draw idle animation
      if (!running && buf.length === 0) {
        const ctx = canvas.getContext('2d');
        ctx.clearRect(0, 0, w, h);
        // Subtle idle wave
        const idleBuf = [];
        const now = performance.now() / 1000;
        for (let i = 0; i < 200; i++) {
          idleBuf.push(0.03 * Math.sin((i / 200) * Math.PI * 6 + now * 2));
        }
        drawWaveform(canvas, idleBuf, color, glowColor);
        drawLevelMeter(meter, -55, color, glowColor);
        return;
      }

      drawWaveform(canvas, buf, color, glowColor);

      // Level meter: compute RMS of last 200 samples
      const tail = buf.slice(-200);
      if (tail.length > 0) {
        const rms = Math.sqrt(tail.reduce((s, v) => s + v * v, 0) / tail.length);
        const db = rms > 0 ? 20 * Math.log10(rms) : -60;
        drawLevelMeter(meter, Math.max(-60, Math.min(0, db)), color, glowColor);
      }
    };

    rafRef.current = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(rafRef.current);
  }, [running, color, glowColor]);

  return (
    <div className="bg-transparent border border-outline-variant/70 rounded-3xl p-5 sm:p-6 shadow-warm-card relative overflow-hidden flex flex-col flex-1">
      {/* Waveform Card Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          {/* Glyph */}
          <div className={`w-10 h-10 rounded-2xl flex items-center justify-center shadow-sm border ${isNoisy ? 'bg-sienna-50 border-primary/20' : 'bg-olive-50 border-olive-500/25'}`}>
            <span className={`material-symbols-outlined text-[20px] ${isNoisy ? 'text-primary' : 'text-olive-600'}`}>
              {isNoisy ? 'equalizer' : 'graphic_eq'}
            </span>
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className={`text-xs uppercase font-extrabold tracking-wider ${isNoisy ? 'text-primary' : 'text-olive-600'}`}>{label}</h3>
              <span className={`inline-flex items-center gap-1 text-[10px] font-bold px-2 py-0.5 rounded-full border ${isNoisy ? 'bg-primary/10 text-primary border-primary/20' : 'bg-olive-50 text-olive-600 border-olive-500/25'}`}>
                <span className={`w-1.5 h-1.5 rounded-full animate-pulse ${isNoisy ? 'bg-primary' : 'bg-olive-500'}`}></span>
                {isNoisy ? 'LIVE MIC' : 'FILTERED'}
              </span>
            </div>
            <p className="text-xs text-on-surface font-semibold">{subtitle}</p>
          </div>
        </div>

      </div>
      
      {/* Oscilloscope & VU Meter Group */}
      <div className="grid grid-cols-12 gap-3 items-stretch flex-1 min-h-[8rem]">
        {/* Waveform Canvas Display Area */}
        <div className="col-span-11 relative rounded-2xl bg-surface-container-low/70 border border-outline-variant/70 sahara-audio-grid overflow-hidden flex items-center shadow-warm-inner">
          {/* Center Axis Marker */}
          <div className="absolute inset-x-0 top-1/2 h-px bg-outline-variant pointer-events-none"></div>
          {/* Time Scale Indicators */}
          <div className="absolute bottom-1.5 inset-x-3 flex justify-between text-[9px] font-mono text-on-surface font-bold select-none pointer-events-none z-10">
            <span>-2.0s</span>
            <span>-1.5s</span>
            <span>-1.0s</span>
            <span>-0.5s</span>
            <span className={`${isNoisy ? 'text-primary' : 'text-olive-600'} font-bold`}>0.0s (Now)</span>
          </div>
          <canvas ref={canvasRef} className="absolute inset-0 w-full h-full" />
        </div>
        
        {/* Vertical dB VU Meter */}
        <div className="col-span-1 rounded-2xl bg-surface-container-low/70 border border-outline-variant/70 flex flex-col justify-between items-center py-2 px-1 relative shadow-warm-inner min-h-0">
          <span className="text-[9px] font-mono text-on-surface font-bold">0</span>
          <div className="w-full flex-1 mx-auto my-1 flex flex-col justify-start items-center min-h-0 relative">
            <canvas ref={meterRef} className="absolute inset-0 w-full h-full block" />
          </div>
          <span className="text-[9px] font-mono text-on-surface font-bold">-60</span>
        </div>
      </div>
    </div>
  );
}
