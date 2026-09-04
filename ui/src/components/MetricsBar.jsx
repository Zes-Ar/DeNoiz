import { useRef, useEffect } from 'react';
import { drawSparkline } from '../utils/drawWave.js';

const MAX_HISTORY = 40; // sparkline data points

const CARDS = [
  {
    id: 'snr',
    title: 'SNR IMPROVEMENT',
    field: 'snr_improvement_db',
    unit: 'dB',
    sign: '+',
    desc: 'Noise reduction achieved',
    color: '#39ff14',
    cssClass: 'metric-card--snr',
  },
  {
    id: 'dnsmos',
    title: 'DNSMOS SCORE',
    field: 'dnsmos',
    unit: '/ 5.00',
    sign: '',
    desc: 'Perceptual quality score',
    color: '#00e5ff',
    cssClass: 'metric-card--dnsmos',
  },
  {
    id: 'latency',
    title: 'LATENCY',
    field: 'latency_ms',
    unit: 'ms',
    sign: '',
    desc: 'End-to-end processing time',
    color: '#b266ff',
    cssClass: 'metric-card--latency',
  },
  {
    id: 'rtf',
    title: 'REAL-TIME FACTOR',
    field: 'rtf',
    unit: 'x',
    sign: '',
    desc: 'Speed ratio (< 1.0 = real-time)',
    color: '#ff9800',
    cssClass: 'metric-card--rtf',
  },
];

export default function MetricsBar({ metrics }) {
  return (
    <div className="metrics-bar">
      {/* Left header */}
      <div className="metrics-bar__header glass-card">
        <div className="metrics-bar__header-icon">📊</div>
        <div>
          <div className="metrics-bar__header-title">METRICS</div>
          <div className="metrics-bar__header-sub">Real-time Performance<br />Analytics</div>
        </div>
      </div>

      {/* Cards */}
      {CARDS.map((card) => (
        <MetricCard key={card.id} card={card} metrics={metrics} />
      ))}
    </div>
  );
}

function MetricCard({ card, metrics }) {
  const historyRef = useRef([]);
  const sparkRef = useRef(null);

  const rawValue = metrics?.[card.field];
  const value = rawValue != null ? rawValue : null;

  // Append to history
  useEffect(() => {
    if (value != null) {
      historyRef.current.push(value);
      if (historyRef.current.length > MAX_HISTORY) {
        historyRef.current.shift();
      }
    }
  }, [value]);

  // Draw sparkline
  useEffect(() => {
    const canvas = sparkRef.current;
    if (!canvas) return;
    const rect = canvas.getBoundingClientRect();
    canvas.width = rect.width * window.devicePixelRatio;
    canvas.height = rect.height * window.devicePixelRatio;
    const ctx = canvas.getContext('2d');
    ctx.scale(window.devicePixelRatio, window.devicePixelRatio);
    drawSparkline(canvas, historyRef.current, card.color);
  }, [value, card.color]);

  const display = value != null
    ? `${card.sign}${typeof value === 'number' ? value.toFixed(card.id === 'rtf' ? 3 : 1) : value}`
    : '—';

  return (
    <div className={`metric-card glass-card ${card.cssClass}`}>
      <div className="metric-card__top">
        <span className="metric-card__title">{card.title}</span>
        <span className="metric-card__info" title={card.desc}>ⓘ</span>
      </div>
      <div className="metric-card__value">
        {display}
        <span className="metric-card__unit">{value != null ? ` ${card.unit}` : ''}</span>
      </div>
      <div className="metric-card__desc">{card.desc}</div>
      <div className="metric-card__sparkline">
        <canvas ref={sparkRef} />
      </div>
    </div>
  );
}
