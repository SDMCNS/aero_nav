/**
 * Airborne Radio Receiver Reception Matrix.
 * Scans all available ground navigation aids in the Irish FIR,
 * evaluating real-time signal strength, line-of-sight status, and operational validity.
 */

import { FullTelemetry, ReceptionMatrixItem } from '../types';
import { api } from '../api';

export class ReceiverMatrixView {
  private container: HTMLElement;

  constructor(container: HTMLElement) {
    this.container = container;
  }

  public render(telemetry: FullTelemetry) {
    const list: ReceptionMatrixItem[] = telemetry.reception_matrix || [];

    const rowsHtml = list.map(item => {
      let statusBadge = '<span class="badge badge-gray">OUT OF RANGE</span>';
      if (item.in_cone) {
        statusBadge = '<span class="badge badge-red">CONE OF CONFUSION</span>';
      } else if (item.restricted) {
        statusBadge = '<span class="badge badge-amber">TERRAIN BLOCKED</span>';
      } else if (item.received) {
        statusBadge = '<span class="badge badge-green">LOCKED</span>';
      }

      const sigStr = item.signal_dbm !== undefined ? `${item.signal_dbm.toFixed(0)} dBm` : item.field_strength_uv !== undefined ? `${item.field_strength_uv.toFixed(0)} µV/m` : '---';

      let dataReadout = '---';
      if (item.bearing_mag !== undefined) {
        dataReadout = `Rad ${item.bearing_mag.toFixed(0)}°`;
      } else if (item.distance_nm !== undefined) {
        dataReadout = `DME ${item.distance_nm.toFixed(1)} NM`;
      } else if (item.rel_bearing !== undefined) {
        dataReadout = `Rel ${item.rel_bearing.toFixed(0)}°`;
      }

      return `
        <tr>
          <td class="font-bold text-cyan">${item.id}</td>
          <td>${item.name}</td>
          <td><span class="type-tag">${item.type}</span></td>
          <td class="font-mono text-xs">${item.freq}</td>
          <td>${statusBadge}</td>
          <td class="font-mono text-xs">${sigStr}</td>
          <td class="font-mono text-amber">${dataReadout}</td>
          <td>
            <button class="btn-xs btn-tune" data-type="${item.type}" data-id="${item.id}">TUNE</button>
          </td>
        </tr>
      `;
    }).join('');

    this.container.innerHTML = `
      <div class="receiver-matrix-panel">
        <div class="panel-section-title">
          <span>📻 IRISH FIR RADIO NAVIGATION AID RECEPTION MATRIX</span>
          <span class="text-xs text-slate-muted">${list.length} Monitored Facilities</span>
        </div>

        <div class="table-container matrix-table-container">
          <table class="arinc-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>STATION NAME</th>
                <th>FACILITY TYPE</th>
                <th>FREQUENCY</th>
                <th>STATUS</th>
                <th>SIGNAL STRENGTH</th>
                <th>OBSERVED TELEMETRY</th>
                <th>ACTION</th>
              </tr>
            </thead>
            <tbody>
              ${rowsHtml || '<tr><td colspan="8" class="text-center py-2">Scanning spectrum...</td></tr>'}
            </tbody>
          </table>
        </div>
      </div>
    `;

    // Attach tune handlers
    this.container.querySelectorAll('.btn-tune').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const target = e.currentTarget as HTMLElement;
        const id = target.getAttribute('data-id') || '';
        const type = target.getAttribute('data-type') || '';
        if (type.includes('VOR') || type.includes('ILS')) {
          api.tuneAvionics('nav1', id);
        } else if (type.includes('DME')) {
          api.tuneAvionics('dme1', id);
        } else if (type.includes('NDB')) {
          api.tuneAvionics('adf1', id);
        }
      });
    });
  }
}

