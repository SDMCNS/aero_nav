/**
 * Dedicated Digital DME Interrogator Unit.
 * High-visibility LED segmented readouts for Distance (NM),
 * Groundspeed (KTS), and Time-to-Station (MIN), plus RF channel metrics.
 */

import { FullTelemetry } from '../types';

export class DmeDisplay {
  private container: HTMLElement;

  constructor(container: HTMLElement) {
    this.container = container;
  }

  public render(telemetry: FullTelemetry) {
    const dme = telemetry.dme1;
    const ev = dme?.evaluation;
    const isLocked = ev && ev.is_received;

    const distStr = isLocked ? ev.slant_range_nm.toFixed(1) : '---.-';
    const gsStr = isLocked ? ev.groundspeed_readout_kts.toFixed(0) : '---';
    const ttsStr = isLocked ? ev.time_to_station_min.toFixed(0) : '--';
    const stationId = dme?.station?.id || '---';
    const channel = ev?.channel || dme?.station?.channel || '80X';

    this.container.innerHTML = `
      <div class="dme-unit">
        <div class="dme-header">
          <div class="dme-brand">KING / BENDIX DME 890</div>
          <div class="dme-annunciators">
            <span class="dme-led ${isLocked ? 'led-active-green' : 'led-dim'}">LOCKED</span>
            <span class="dme-led ${!isLocked && ev ? 'led-active-amber' : 'led-dim'}">SEARCH</span>
          </div>
        </div>

        <div class="dme-readouts-grid">
          <div class="dme-readout-cell">
            <span class="readout-label">DISTANCE (NM)</span>
            <div class="digital-display text-green">${distStr}</div>
          </div>
          <div class="dme-readout-cell">
            <span class="readout-label">GROUND SPEED</span>
            <div class="digital-display text-amber">${gsStr} <span class="unit">KT</span></div>
          </div>
          <div class="dme-readout-cell">
            <span class="readout-label">TIME TO STA</span>
            <div class="digital-display text-cyan">${ttsStr} <span class="unit">MIN</span></div>
          </div>
        </div>

        <div class="dme-footer-info">
          <span>STN: <b>${stationId}</b> (CH ${channel})</span>
          <span>PULSE: ${ev?.pulse_spacing_us || 12} µs</span>
          <span>TX DELAY: 50.0 µs</span>
          <span>RSSI: ${ev?.signal_strength_dbm ? ev.signal_strength_dbm.toFixed(0) + ' dBm' : '---'}</span>
        </div>
      </div>
    `;
  }
}

