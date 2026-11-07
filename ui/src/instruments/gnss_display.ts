/**
 * GNSS Multi-Constellation Satellite Skyplot & Integrity Matrix.
 * Displays polar azimuth/elevation plot, active space vehicles, SNR bars,
 * and RAIM horizontal/vertical protection levels.
 */

import { FullTelemetry } from '../types';

export class GnssDisplay {
  private canvas: HTMLCanvasElement;
  private ctx: CanvasRenderingContext2D;

  constructor(canvas: HTMLCanvasElement) {
    this.canvas = canvas;
    const context = canvas.getContext('2d');
    if (!context) throw new Error('Could not get 2D context for GNSS');
    this.ctx = context;
  }

  public render(telemetry: FullTelemetry) {
    const ctx = this.ctx;
    const width = this.canvas.width;
    const height = this.canvas.height;
    const cx = width / 2;
    const cy = height * 0.44;
    const radius = Math.min(width, height) * 0.36;

    ctx.clearRect(0, 0, width, height);

    const gnss = telemetry.gnss;

    // Bezel & Polar Rings
    ctx.save();
    ctx.fillStyle = '#080d1a';
    ctx.fillRect(0, 0, width, height);

    // Elevation rings: 0° (horizon, outer), 30°, 60°
    const rings = [
      { r: radius, label: '0°' },
      { r: radius * (60 / 90), label: '30°' },
      { r: radius * (30 / 90), label: '60°' },
    ];

    for (const ring of rings) {
      ctx.beginPath();
      ctx.arc(cx, cy, ring.r, 0, Math.PI * 2);
      ctx.strokeStyle = '#1e293b';
      ctx.lineWidth = 1;
      ctx.stroke();

      ctx.fillStyle = '#475569';
      ctx.font = '8px Consolas, monospace';
      ctx.fillText(ring.label, cx + ring.r - 14, cy - 2);
    }

    // Crosshairs
    ctx.beginPath();
    ctx.moveTo(cx - radius, cy);
    ctx.lineTo(cx + radius, cy);
    ctx.moveTo(cx, cy - radius);
    ctx.lineTo(cx, cy + radius);
    ctx.strokeStyle = '#1e293b';
    ctx.setLineDash([2, 4]);
    ctx.stroke();
    ctx.setLineDash([]);

    // Cardinal directions
    ctx.fillStyle = '#94a3b8';
    ctx.font = 'bold 9px Inter, sans-serif';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText('N', cx, cy - radius - 8);
    ctx.fillText('S', cx, cy + radius + 8);
    ctx.fillText('E', cx + radius + 8, cy);
    ctx.fillText('W', cx - radius - 8, cy);

    // Plot Satellites
    if (gnss && gnss.satellites) {
      for (const sat of gnss.satellites) {
        // Polar to Cartesian
        // Zenith (90 deg) is center, 0 deg elevation is outer rim
        const rSat = radius * ((90.0 - sat.elevation) / 90.0);
        const azRad = (sat.azimuth * Math.PI) / 180.0;
        const sx = cx + rSat * Math.sin(azRad);
        const sy = cy - rSat * Math.cos(azRad);

        const isGps = sat.constellation === 'GPS';
        const color = isGps ? '#34d399' : '#38bdf8'; // Green for GPS, Cyan for Galileo

        ctx.beginPath();
        ctx.arc(sx, sy, 7, 0, Math.PI * 2);
        ctx.fillStyle = color;
        ctx.fill();
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 1;
        ctx.stroke();

        ctx.fillStyle = '#0f172a';
        ctx.font = 'bold 8px Consolas, monospace';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(sat.prn, sx, sy);
      }
    }

    // Telemetry & Metrics Box at Bottom
    const boxY = height - 58;
    ctx.fillStyle = '#0b1120';
    ctx.strokeStyle = '#1e293b';
    ctx.lineWidth = 1;
    ctx.fillRect(8, boxY, width - 16, 50);
    ctx.strokeRect(8, boxY, width - 16, 50);

    ctx.fillStyle = '#f8fafc';
    ctx.font = 'bold 10px Consolas, monospace';
    ctx.textAlign = 'left';
    ctx.fillText(`FIX: 3D SBAS (${gnss.satellites_tracked}/${gnss.satellites_total} SVs)`, 16, boxY + 16);

    ctx.fillStyle = '#38bdf8';
    ctx.fillText(`HDOP: ${gnss.hdop.toFixed(1)} | VDOP: ${gnss.vdop.toFixed(1)} | PDOP: ${gnss.pdop.toFixed(1)}`, 16, boxY + 32);

    ctx.textAlign = 'right';
    const isOk = gnss.raim_status === 'INTEGRITY_OK';
    ctx.fillStyle = isOk ? '#34d399' : '#f59e0b';
    ctx.fillText(`RAIM: ${gnss.raim_status}`, width - 16, boxY + 16);

    ctx.fillStyle = '#94a3b8';
    ctx.fillText(`HPL: ${gnss.hpl_meters}m | VPL: ${gnss.vpl_meters}m`, width - 16, boxY + 32);

    ctx.restore();
  }
}

