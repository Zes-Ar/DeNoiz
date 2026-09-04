import React from 'react';
import WaveformPanel from './WaveformPanel.jsx';

export default function VisualizersDeck({ status, waveform, metrics }) {
  const isRunning = status?.running ?? false;

  return (
    <section className="lg:col-span-8 flex flex-col gap-5 h-full" data-purpose="audio-visualizers-and-metrics">
      {/* 1. NOISY INPUT VISUALIZER PANEL */}
      <WaveformPanel 
        variant="noisy" 
        data={waveform?.noisy} 
        running={isRunning} 
        metrics={metrics} 
      />
      
      {/* 2. CLEAN OUTPUT VISUALIZER PANEL */}
      <WaveformPanel 
        variant="clean" 
        data={waveform?.clean} 
        running={isRunning} 
        metrics={metrics} 
      />
    </section>
  );
}
