import React from 'react';
import { useSocket } from './hooks/useSocket.js';
import Header from './components/Header.jsx';
import ControlsPanel from './components/ControlsPanel.jsx';
import VisualizersDeck from './components/VisualizersDeck.jsx';
import Footer from './components/Footer.jsx';

export default function App() {
  const { status, waveform, metrics, error, connState, sendCommand } = useSocket();
  // connState: "connected" | "reconnecting" | "disconnected" — from useSocket

  return (
    <>
      <Header status={status} />

      <main className="flex-1 max-w-[1800px] w-full mx-auto px-6 sm:px-10 lg:px-16 py-8 sm:py-10 flex flex-col gap-8">
        
        {/* Error banner */}
        {error && (
          <div className="bg-error-container text-on-error-container px-4 py-3 rounded-2xl border border-error-container flex items-center gap-3">
            <span className="material-symbols-outlined text-[20px]">error</span>
            <span className="text-sm font-medium">{error.message}</span>
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
          <ControlsPanel status={status} connState={connState} sendCommand={sendCommand} />
          <VisualizersDeck status={status} waveform={waveform} metrics={metrics} />
        </div>

        {/* Full-width Metrics Row */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4" data-purpose="metrics-grid">
          {/* Metric Card 1: SNR Improvement */}
          <div className="bg-transparent border border-outline-variant/70 rounded-2xl p-4 shadow-warm-card hover:shadow-warm-hover transition-all">
            <div className="flex items-center justify-between text-on-surface-variant mb-1.5">
              <span className="text-[10px] uppercase font-bold tracking-wider">SNR Improvement</span>
              <button className="text-secondary hover:text-on-surface transition" title="Signal-to-Noise Ratio Gain">
                <span className="material-symbols-outlined text-[15px]">info</span>
              </button>
            </div>
            <div className="flex items-baseline gap-1.5">
              <span className="text-2xl font-black tracking-tight text-olive-600 font-mono">
                {status?.running && metrics?.snr_improvement_db != null ? `+${metrics.snr_improvement_db.toFixed(1)}` : '-.-'}
              </span>
              <span className="text-xs font-bold text-olive-600">dB</span>
            </div>
            <div className="mt-2.5 flex items-center justify-between text-[11px] text-on-surface-variant">
              <span>Noise reduced</span>
              <span className="text-olive-600 font-semibold font-mono">▲ High gain</span>
            </div>
            <div className="w-full bg-secondary-container h-1 rounded-full mt-2 overflow-hidden">
              <div className="bg-olive-500 h-1 rounded-full transition-all duration-300" style={{ width: `${status?.running ? Math.min(100, Math.max(0, ((metrics?.snr_improvement_db || 0) / 30) * 100)) : 0}%` }}></div>
            </div>
          </div>
          
          {/* Metric Card 2: DNSMOS Score */}
          <div className="bg-transparent border border-outline-variant/70 rounded-2xl p-4 shadow-warm-card hover:shadow-warm-hover transition-all">
            <div className="flex items-center justify-between text-on-surface-variant mb-1.5">
              <span className="text-[10px] uppercase font-bold tracking-wider">DNSMOS Score</span>
              <button className="text-secondary hover:text-on-surface transition" title="Deep Noise Suppression Mean Opinion Score">
                <span className="material-symbols-outlined text-[15px]">info</span>
              </button>
            </div>
            <div className="flex items-baseline gap-1.5">
              <span className="text-2xl font-black tracking-tight text-on-surface font-mono">
                {status?.running && metrics?.dnsmos ? metrics.dnsmos.toFixed(2) : '-.--'}
              </span>
              <span className="text-xs font-semibold text-secondary">/ 5.0</span>
            </div>
            <div className="mt-2.5 flex items-center justify-between text-[11px] text-on-surface-variant">
              <span>Perceptual rating</span>
              <span className="text-primary font-bold">Excellent</span>
            </div>
            <div className="w-full bg-secondary-container h-1 rounded-full mt-2 overflow-hidden">
              <div className="bg-primary h-1 rounded-full transition-all duration-300" style={{ width: `${status?.running ? Math.min(100, Math.max(0, ((metrics?.dnsmos || 0) / 5) * 100)) : 0}%` }}></div>
            </div>
          </div>
          
          {/* Metric Card 3: Algorithmic Latency */}
          <div className="bg-transparent border border-outline-variant/70 rounded-2xl p-4 shadow-warm-card hover:shadow-warm-hover transition-all">
            <div className="flex items-center justify-between text-on-surface-variant mb-1.5">
              <span className="text-[10px] uppercase font-bold tracking-wider">End-to-End Latency</span>
              <button className="text-secondary hover:text-on-surface transition" title="Processing delay">
                <span className="material-symbols-outlined text-[15px]">info</span>
              </button>
            </div>
            <div className="flex items-baseline gap-1.5">
              <span className="text-2xl font-black tracking-tight text-on-surface font-mono">
                {status?.running && metrics?.latency_ms ? metrics.latency_ms.toFixed(1) : '-.-'}
              </span>
              <span className="text-xs font-bold text-secondary">ms</span>
            </div>
            <div className="mt-2.5 flex items-center justify-between text-[11px] text-on-surface-variant">
              <span>Frame: 10ms</span>
              <span className="text-olive-600 font-semibold font-mono">Ultra-low</span>
            </div>
            <div className="w-full bg-secondary-container h-1 rounded-full mt-2 overflow-hidden">
              <div className="bg-olive-500 h-1 rounded-full transition-all duration-300" style={{ width: `${status?.running ? Math.min(100, Math.max(0, ((metrics?.latency_ms || 0) / 200) * 100)) : 0}%` }}></div>
            </div>
          </div>
          
          {/* Metric Card 4: Real-Time Factor (RTF) */}
          <div className="bg-transparent border border-outline-variant/70 rounded-2xl p-4 shadow-warm-card hover:shadow-warm-hover transition-all">
            <div className="flex items-center justify-between text-on-surface-variant mb-1.5">
              <span className="text-[10px] uppercase font-bold tracking-wider">Real-Time Factor</span>
              <button className="text-secondary hover:text-on-surface transition" title="Processing speed relative to real-time (target < 1.0)">
                <span className="material-symbols-outlined text-[15px]">info</span>
              </button>
            </div>
            <div className="flex items-baseline gap-1.5">
              <span className="text-2xl font-black tracking-tight text-on-surface font-mono">
                {status?.running && metrics?.rtf ? metrics.rtf.toFixed(2) : '-.--'}
              </span>
              <span className="text-xs font-bold text-secondary">RTF</span>
            </div>
            <div className="mt-2.5 flex items-center justify-between text-[11px] text-on-surface-variant">
              <span>Speed &lt; 1.0 = RT</span>
              <span className="text-on-surface font-bold font-mono">5.5x Fast</span>
            </div>
            <div className="w-full bg-secondary-container h-1 rounded-full mt-2 overflow-hidden">
              <div className="bg-on-surface h-1 rounded-full transition-all duration-300" style={{ width: `${status?.running ? Math.min(100, Math.max(0, ((metrics?.rtf || 0) / 1.0) * 100)) : 0}%` }}></div>
            </div>
          </div>
        </div>
      </main>

      <Footer />
    </>
  );
}
