# SIH26052 — UI ↔ Model WebSocket Contract

This is the agreed "language" between the **React UI** (frontend) and the
**Python audio engine** (backend). If both sides follow this document, the UI
will connect to the real model with no changes.

> **Important:** All audio stays inside Python. The browser never captures the
> microphone and never plays audio. The UI only **displays data** and **sends
> button commands**. This is deliberate — it keeps the demo simple and reliable.

---

## 1. Connection

- **Transport:** WebSocket
- **URL (localhost only):** `ws://127.0.0.1:8000/ws`
- **Message format:** JSON text frames (one JSON object per message)
- Every message has a `"type"` field that says what it is.
- The UI can connect at any time. It should auto-reconnect if the socket drops.

During development, the UI connects to the **mock server** (same URL, same
messages, fake data). For the demo it connects to the **real engine**. The UI
code is identical for both.

---

## 2. Messages: Python → React (data to display)

The backend pushes these to the UI. The UI only reads them.

### 2.1 `status` — sent once on connect, and whenever state changes

```json
{
  "type": "status",
  "running": false,
  "model_on": true,
  "sample_rate": 48000,
  "block_ms": 100,
  "message": "idle"
}
```

| Field         | Type    | Meaning                                             |
|---------------|---------|-----------------------------------------------------|
| `running`     | bool    | Is the audio pipeline currently capturing?          |
| `model_on`    | bool    | Is noise cancellation ON (true) or bypassed (false)?|
| `sample_rate` | int     | Audio sample rate in Hz (always 48000)              |
| `block_ms`    | int     | Processing block size in ms (informational)         |
| `message`     | string  | Human-readable status for display, e.g. "idle"      |

### 2.2 `waveform` — sent continuously while running (~10–20 times per second)

Two short arrays of floats to plot: the noisy input and the cleaned output.
Values are already downsampled for display (NOT raw audio). Range roughly -1.0
to 1.0.

```json
{
  "type": "waveform",
  "t": 12.34,
  "noisy": [0.01, -0.03, 0.05, 0.12, -0.08, ...],
  "clean": [0.01, -0.02, 0.03, 0.04, -0.02, ...]
}
```

| Field   | Type            | Meaning                                          |
|---------|-----------------|--------------------------------------------------|
| `t`     | float           | Seconds since the pipeline started (for x-axis)  |
| `noisy` | array of float  | Downsampled input waveform (~200 points)         |
| `clean` | array of float  | Downsampled enhanced waveform, same length       |

> When `model_on` is `false`, `clean` will look the same as `noisy` (model is
> bypassed). That is expected and is the "before" state of the demo.

### 2.3 `metrics` — sent a few times per second while running

The numbers that prove the model is working.

```json
{
  "type": "metrics",
  "t": 12.34,
  "snr_in_db": -3.2,
  "snr_out_db": 8.1,
  "snr_improvement_db": 11.3,
  "dnsmos": 3.42,
  "latency_ms": 120.0,
  "rtf": 0.22
}
```

| Field                | Type   | Meaning                                            |
|----------------------|--------|----------------------------------------------------|
| `snr_in_db`          | float  | Estimated SNR of the noisy input                   |
| `snr_out_db`         | float  | Estimated SNR of the cleaned output                |
| `snr_improvement_db` | float  | `snr_out_db - snr_in_db` (the headline number)     |
| `dnsmos`             | float  | Speech-quality score, ~1.0 (bad) to ~5.0 (great)   |
| `latency_ms`         | float  | Current end-to-end processing latency              |
| `rtf`                | float  | Real-time factor; < 1.0 means keeping up with live |

> Any metric may be `null` if not available yet. The UI should handle `null`
> gracefully (show "—" or a blank).

### 2.4 `error` — sent if something goes wrong

```json
{
  "type": "error",
  "message": "No microphone found"
}
```

---

## 3. Messages: React → Python (commands)

The UI sends these when the user clicks a button. Each is a small JSON object.

### 3.1 Start the pipeline
```json
{ "type": "command", "action": "start" }
```

### 3.2 Stop the pipeline
```json
{ "type": "command", "action": "stop" }
```

### 3.3 Toggle noise cancellation on/off (the live "before vs after")
```json
{ "type": "command", "action": "set_model", "on": true }
```
`"on": false` bypasses the model (judges hear the raw noisy audio).
`"on": true` enables noise cancellation (judges hear the cleaned audio).

After handling any command, the backend replies with an updated `status`
message (2.1) so the UI can reflect the new state.

---

## 4. What the UI should render

Minimum for the demo:

1. **Start / Stop** button → sends `start` / `stop`.
2. **Model ON/OFF** toggle → sends `set_model`. This is the key demo moment.
3. **Two waveforms** side by side (or stacked): `noisy` vs `clean`.
4. **Metrics panel:** SNR improvement (big), DNSMOS, latency.
5. A small **connection indicator** (connected / reconnecting).

Everything else (styling, layout, animations) is the UI's freedom.

---

## 5. Rules of thumb (so integration is painless)

- The UI must **never assume audio**. It only draws arrays and shows numbers.
- The UI must **tolerate missing fields** (`null` metrics, empty arrays).
- The UI must **auto-reconnect** if the WebSocket closes.
- Field names and message `type` values are fixed by this document. If either
  side needs a change, update THIS FILE first, then both sides adapt.
- Same URL, same messages for mock and real engine — do not special-case them.
