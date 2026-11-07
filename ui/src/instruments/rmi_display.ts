/**
 * Dual-Needle Radio Magnetic Indicator (RMI).
 * Slaved heading card with Pointer 1 (single green arrow, ADF/NDB)
 * and Pointer 2 (double yellow arrow, VOR).
 */

import { FullTelemetry } from '../types';

export class RmiDisplay {
  private canvas: HTMLCanvasElement;
  private ctx: CanvasRenderingContext2D;

  constructor(canvas: HTMLCanvasElement) {
    this.canvas = canvas;
    const context = canvas.getContext('2d');
    if (!context) throw new Error('Could not get 2D context for RMI');
    this.ctx = context;
  }

  public render(telemetry: FullTelemetry) {
    const ctx = this.ctx;
    const width = this.canvas.width;
    const height = this.canvas.height;
    const cx = width / 2;
    const cy = height / 2;
    const radius = Math.min(width, height) * 0.42;

    ctx.clearRect(0, 0, width, height);

    const ac = telemetry.aircraft;
    const adf = telemetry.adf1;
    const nav1 = telemetry.nav1;
    const hdg = ac.magnetic_heading_deg;

    // Bezel
    ctx.save();
    ctx.beginPath();
    ctx.arc(cx, cy, radius + 12, 0, Math.PI * 2);
    ctx.fillStyle = '#080d1a';
    ctx.fill();
    ctx.lineWidth = 3.5;
    ctx.strokeStyle = '#1e293b';
    ctx.stroke();

    // Rotating Compass Card
    ctx.save();
    ctx.translate(cx, cy);
    ctx.rotate((-hdg * Math.PI) / 180.0);

    ctx.beginPath();
    ctx.arc(0, 0, radius, 0, Math.PI * 2);
    ctx.strokeStyle = '#334155';
    ctx.lineWidth = 1.5;
    ctx.stroke();

    for (let deg = 0; deg < 360; deg += 5) {
      const rad = (deg * Math.PI) / 180.0;
      const is30 = deg % 30 === 0;
      const is10 = deg % 10 === 0;
      const len = is30 ? 12 : is10 ? 8 : 4;

      const x1 = (radius - len) * Math.sin(rad);
      const y1 = -(radius - len) * Math.cos(rad);
      const x2 = radius * Math.sin(rad);
      const y2 = -radius * Math.cos(rad);

      ctx.beginPath();
      ctx.moveTo(x1, y1);
      ctx.lineTo(x2, y2);
      ctx.strokeStyle = is30 ? '#f8fafc' : '#64748b';
      ctx.lineWidth = is30 ? 2 : 1;
      ctx.stroke();

      if (is30) {
        ctx.save();
        const dist = radius - 20;
        ctx.translate(dist * Math.sin(rad), -dist * Math.cos(rad));
        ctx.rotate(rad);
        ctx.fillStyle = '#f8fafc';
        ctx.font = 'bold 10px Inter, sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        let label = (deg / 10).toString();
        if (deg === 0) label = 'N';
        else if (deg === 90) label = 'E';
        else if (deg === 180) label = 'S';
        else if (deg === 270) label = 'W';
        ctx.fillText(label, 0, 0);
        ctx.restore();
      }
    }

    // Pointer 1: ADF / NDB Needle (Single Green Arrow)
    // Points toward station magnetic bearing (QDM)
    if (adf?.evaluation && adf.evaluation.is_received) {
      const qdm = adf.evaluation.qdm_magnetic_bearing;
      ctx.save();
      ctx.rotate((qdm * Math.PI) / 180.0);

      const arrowLen = radius - 10;
      ctx.beginPath();
      ctx.moveTo(0, -arrowLen);
      ctx.lineTo(-6, -arrowLen + 16);
      ctx.lineTo(6, -arrowLen + 16);
      ctx.closePath();
      ctx.fillStyle = '#34d399'; // Bright green
      ctx.fill();

      // Shaft and tail
      ctx.beginPath();
      ctx.moveTo(0, -arrowLen + 16);
      ctx.lineTo(0, arrowLen);
      ctx.strokeStyle = '#34d399';
      ctx.lineWidth = 2.5;
      ctx.stroke();

      // Tail crossbar
      ctx.beginPath();
      ctx.moveTo(-8, arrowLen - 12);
      ctx.lineTo(8, arrowLen - 12);
      ctx.stroke();

      ctx.restore();
    }

    // Pointer 2: VOR Needle (Double Yellow Arrow)
    if (nav1.mode === 'VOR' && nav1.evaluation && !(nav1.evaluation as any).failure_flag) {
      const vorBrg = (nav1.evaluation as any).magnetic_bearing_to_station;
      ctx.save();
      ctx.rotate((vorBrg * Math.PI) / 180.0);

      const arrowLen = radius - 12;
      // Double arrowhead
      ctx.beginPath();
      ctx.moveTo(-4, -arrowLen + 16);
      ctx.lineTo(-4, -arrowLen);
      ctx.lineTo(0, -arrowLen - 5);
      ctx.lineTo(4, -arrowLen);
      ctx.lineTo(4, -arrowLen + 16);
      ctx.strokeStyle = '#facc15';
      ctx.lineWidth = 2;
      ctx.stroke();

      ctx.beginPath();
      ctx.moveTo(-3, -arrowLen + 16);
      ctx.lineTo(-3, arrowLen);
      ctx.moveTo(3, -arrowLen + 16);
      ctx.lineTo(3, arrowLen);
      ctx.stroke();

      ctx.restore();
    }

    ctx.restore(); // restore Compass translation

    // Fixed Top Reference Index (Lubber Line)
    ctx.beginPath();
    ctx.moveTo(cx, cy - radius - 8);
    ctx.lineTo(cx - 6, cy - radius);
    ctx.lineTo(cx + 6, cy - radius);
    ctx.closePath();
    ctx.fillStyle = '#f8fafc';
    ctx.fill();

    // Center pivot
    ctx.beginPath();
    ctx.arc(cx, cy, 5, 0, Math.PI * 2);
    ctx.fillStyle = '#38bdf8';
    ctx.fill();

    // Labels & Telemetry Readouts
    ctx.font = 'bold 10px Consolas, monospace';
    ctx.fillStyle = '#34d399';
    ctx.textAlign = 'left';
    const adfId = adf.station?.id || '---';
    const adfQdm = adf.evaluation?.qdm_magnetic_bearing ?? 0;
    const adfFreq = adf.station?.frequency ? ` ${adf.station.frequency}` : '';
    ctx.fillText(`ADF [${adfId}${adfFreq}]: QDM ${adfQdm.toFixed(0)}°`, 10, 18);

    ctx.fillStyle = '#facc15';
    ctx.textAlign = 'right';
    const vorId = nav1.mode === 'VOR'
      ? `${nav1.station?.id || '---'} ${nav1.station?.frequency || ''}`
      : (nav1.mode === 'ILS' ? `ILS:${nav1.station?.id || 'LOC'} ${nav1.station?.frequency || ''}` : '---');
    ctx.fillText(`${nav1.mode === 'ILS' ? '' : 'VOR '}[${vorId.trim()}]`, width - 10, 18);

    ctx.restore();
  }
}

