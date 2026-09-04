export default function Controls({ status, sendCommand }) {
  const running  = status?.running  ?? false;
  const modelOn  = status?.model_on ?? false;

  return (
    <div className="controls glass-card">
      {/* Start */}
      <button
        id="btn-start"
        className={`controls__btn controls__btn--start ${running ? 'active' : ''}`}
        onClick={() => sendCommand('start')}
        disabled={!modelOn}
      >
        <span className="controls__btn-icon">▶</span>
        START
      </button>

      {/* Stop */}
      <button
        id="btn-stop"
        className={`controls__btn controls__btn--stop ${!running ? 'active' : ''}`}
        onClick={() => sendCommand('stop')}
        disabled={!modelOn || !running}
      >
        <span className="controls__btn-icon">■</span>
        STOP
      </button>

      {/* AI Model Toggle */}
      <div className="controls__toggle-group">
        <span className="controls__toggle-label">AI MODEL</span>

        <span className={`toggle-state ${modelOn ? 'on' : 'off'}`}>
          {modelOn ? 'ON' : ''}
        </span>

        <div
          id="toggle-model"
          className={`toggle ${modelOn ? 'on' : ''}`}
          role="switch"
          aria-checked={modelOn}
          tabIndex={0}
          onClick={() => sendCommand('set_model', { on: !modelOn })}
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault();
              sendCommand('set_model', { on: !modelOn });
            }
          }}
        >
          <div className="toggle__knob" />
        </div>

        <span className={`toggle-state ${!modelOn ? 'off' : ''}`}>
          {!modelOn ? 'OFF' : ''}
        </span>
      </div>

    </div>
  );
}
