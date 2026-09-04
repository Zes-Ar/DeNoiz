import React from 'react';

export default function ControlsPanel({ status, connState, sendCommand }) {
  // Engine is the source of truth. Drive UI from status messages, not local state.
  const isRunning = status?.running ?? false;
  const modelOn = status?.model_on ?? true;   // engine defaults to model ON
  const isConnected = connState === 'connected';

  return (
    <aside className="lg:col-span-4 flex flex-col gap-5 h-full" data-purpose="audio-controls-panel">
      
      {/* 1. Connection Status Container — reflects the real WebSocket state */}
      <div className="bg-transparent border border-outline-variant/70 rounded-3xl p-5 px-6 shadow-warm-card flex items-center justify-between relative overflow-hidden">
        <div className="absolute -right-10 -top-10 w-32 h-32 bg-[#175133]/50 rounded-full blur-2xl pointer-events-none"></div>
        <div className="flex items-center gap-2.5 relative z-10">
          <span className={`w-2.5 h-2.5 rounded-full shadow-sm ${isConnected ? 'bg-olive-500 shadow-olive-500/40' : 'bg-outline'}`}></span>
          <h2 className="text-xs uppercase font-extrabold tracking-wider text-on-surface">Processing Engine</h2>
        </div>
        <span className={`relative z-10 inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-[11px] font-bold border transition-colors ${isConnected ? 'bg-olive-50 text-olive-600 border-olive-500/25' : 'bg-surface-container text-on-surface border-outline-variant/60'}`}>
          <span className={`w-1.5 h-1.5 rounded-full transition-colors ${isConnected ? 'bg-olive-500' : 'bg-on-surface-variant'}`}></span>
          {isConnected ? 'Connected' : (connState === 'reconnecting' ? 'Reconnecting' : 'Disconnected')}
        </span>
      </div>

      {/* 2. Main Controls Container */}
      <div className="bg-transparent border border-outline-variant/70 rounded-3xl p-6 shadow-warm-card">
        {/* Action Buttons (Start / Stop) — send start/stop per the contract */}
        <div className="grid grid-cols-2 gap-3 mb-6">
          {/* Start capture */}
          <button 
            onClick={() => sendCommand('start')}
            disabled={!isConnected || isRunning}
            className={`group flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl text-xs shadow-sm transition-all border border-transparent ${(!isConnected || isRunning) ? 'opacity-50 cursor-not-allowed bg-surface-container-low text-on-surface font-semibold' : 'bg-on-surface text-surface-container-lowest hover:bg-on-surface/90 font-semibold'}`}
          >
            <span className={`material-symbols-outlined text-[16px] group-hover:scale-110 transition-transform ${isRunning ? 'material-symbols-fill text-olive-500' : ''}`}>play_arrow</span>
            <span className="font-semibold">Start</span>
          </button>
          
          {/* Stop capture */}
          <button 
            onClick={() => sendCommand('stop')}
            disabled={!isConnected || !isRunning}
            className={`group flex items-center justify-center gap-2 py-2.5 px-4 rounded-xl text-xs transition-all ${(!isConnected || !isRunning) ? 'opacity-50 cursor-not-allowed bg-surface-container-low text-on-surface font-semibold' : 'bg-[#175133] text-white font-semibold shadow-sm hover:bg-[#175133]/90'}`}
          >
            <span className="material-symbols-outlined text-[15px] group-hover:scale-110 transition-transform">stop</span>
            <span className="font-semibold">Stop</span>
          </button>
        </div>
        
        {/* AI Model Suppression — THE before/after toggle. Sends set_model {on}. */}
        <div className="p-4 rounded-2xl bg-surface-container-low border border-outline-variant/60 transition-all flex items-center justify-between">
          <div className="flex flex-col">
            <span className="text-xs font-bold text-on-surface uppercase tracking-wide">AI Model Suppression</span>
            <span className="text-[10px] text-on-surface-variant mt-0.5">{modelOn ? 'ON — hearing cleaned audio' : 'OFF — hearing raw noise'}</span>
          </div>
          {/* Toggle: checked = model ON. Reflects engine status.model_on. */}
          <label className={`relative inline-flex items-center ${isConnected ? 'cursor-pointer' : 'cursor-not-allowed opacity-50'}`}>
            <input 
              type="checkbox" 
              className="sr-only peer" 
              checked={modelOn} 
              disabled={!isConnected}
              onChange={(e) => sendCommand('set_model', { on: e.target.checked })} 
            />
            <div className="w-11 h-6 bg-surface-container-highest peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all after:shadow-sm peer-checked:bg-[#175133]"></div>
          </label>
        </div>
      </div>
      
      {/* 3. Audio Routing Container */}
      <div className="bg-transparent border border-outline-variant/70 rounded-3xl p-5 px-6 shadow-warm-card flex-1 flex flex-col justify-start">
        <div className="flex items-center justify-between mb-3">
          <div className="text-[11px] uppercase tracking-wider font-extrabold text-on-surface">Audio Routing</div>
          <span className="text-[9px] text-on-surface-variant">set on engine</span>
        </div>
        
        {/* Input Device (display only — engine picks via --input) */}
        <div className="mb-3">
          <label className="block text-xs font-bold text-on-surface mb-1 flex items-center justify-between">
            <span>Audio Input</span>
            <span className="text-[10px] text-[#0ce079] font-bold font-mono">Mono</span>
          </label>
          <div className="relative">
            <select disabled className="w-full text-xs font-medium bg-surface-container-low border border-outline-variant/80 rounded-xl py-2 pl-3 pr-8 text-on-surface opacity-80 cursor-not-allowed transition">
              <option>Microphone Array (default)</option>
            </select>
          </div>
        </div>
        
        {/* Output Device (display only — engine picks via --output) */}
        <div>
          <label className="block text-xs font-bold text-on-surface mb-1 flex items-center justify-between">
            <span>Filtered Output</span>
            <span className="text-[10px] text-olive-600 font-semibold">Headphones</span>
          </label>
          <div className="relative">
            <select disabled className="w-full text-xs font-medium bg-surface-container-low border border-outline-variant/80 rounded-xl py-2 pl-3 pr-8 text-on-surface opacity-80 cursor-not-allowed transition">
              <option>Headphones (default)</option>
            </select>
          </div>
        </div>
      </div>
      
    </aside>
  );
}
