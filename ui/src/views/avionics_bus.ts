/**
 * Avionics Bus & Protocol Inspector.
 * Displays real-time ARINC 429 digital words (32-bit binary & hex decoding)
 * and NMEA 0183 sentences.
 */

import { FullTelemetry } from '../types';

export class AvionicsBusView {
  private container: HTMLElement;

  constructor(container: HTMLElement) {
    this.container = container;
  }

  public render(telemetry: FullTelemetry) {
    const bus = telemetry.arinc429_bus || [];
    const nmea = telemetry.nmea_0183 || { GGA: '', RMC: '', GSA: '' };

    const arincRowsHtml = bus.map(w => {
      const isNormal = w.ssm_name === 'NORMAL_OPERATION';
      const ssmBadgeClass = isNormal ? 'badge-green' : 'badge-amber';
      return `
        <tr>
          <td class="font-mono text-cyan">${w.label_octal}</td>
          <td class="font-bold text-slate">${w.parameter || 'GENERIC'}</td>
          <td class="font-mono">${w.sdi}</td>
          <td class="font-mono text-xs text-slate-muted">${w.data_bits}</td>
          <td><span class="badge ${ssmBadgeClass}">${w.ssm_name}</span></td>
          <td class="font-mono">${w.parity}</td>
          <td class="font-mono text-amber font-bold">${w.raw_hex}</td>
          <td class="font-mono text-green">${w.decoded_value !== undefined ? `${w.decoded_value} ${w.units || ''}` : '---'}</td>
        </tr>
      `;
    }).join('');

    this.container.innerHTML = `
      <div class="avionics-bus-panel">
        <div class="panel-section-title">
          <span>⚡ ARINC 429 AVIONICS DIGITAL BUS (32-BIT ENCODING)</span>
          <span class="text-xs text-slate-muted">SPEED: High-Speed 100 kbps | ODD PARITY</span>
        </div>

        <div class="table-container">
          <table class="arinc-table">
            <thead>
              <tr>
                <th>LBL (OCT)</th>
                <th>PARAMETER</th>
                <th>SDI</th>
                <th>DATA BITS (19-BIT)</th>
                <th>SSM</th>
                <th>PAR</th>
                <th>HEX WORD</th>
                <th>DECODED VALUE</th>
              </tr>
            </thead>
            <tbody>
              ${arincRowsHtml || '<tr><td colspan="8" class="text-center py-2">No active bus words</td></tr>'}
            </tbody>
          </table>
        </div>

        <div class="panel-section-title mt-3">
          <span>🛰️ NMEA 0183 HIGH-PRECISION GNSS TELEMETRY STREAM</span>
          <span class="text-xs text-slate-muted">BAUD: 4800 / 38400 | IEC 61162-1</span>
        </div>

        <div class="nmea-terminal">
          <div class="nmea-line"><span class="nmea-prompt">&gt;</span> <span class="nmea-text">${nmea.GGA || 'Waiting for GGA...'}</span></div>
          <div class="nmea-line"><span class="nmea-prompt">&gt;</span> <span class="nmea-text">${nmea.RMC || 'Waiting for RMC...'}</span></div>
          <div class="nmea-line"><span class="nmea-prompt">&gt;</span> <span class="nmea-text">${nmea.GSA || 'Waiting for GSA...'}</span></div>
        </div>
      </div>
    `;
  }
}

