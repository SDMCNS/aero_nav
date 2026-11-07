/**
 * ILS Vertical Approach Descent Profile & Cross-Pointer Display.
 * Renders the vertical glide path descent (3.0° slope) relative to the runway threshold,
 * plus the dual-axis ILS Flight Director crosshairs.
 */

import { FullTelemetry } from '../types';

export class IlsProfileDisplay {
  private canvas: HTMLCanvasElement;
  private ctx: CanvasRenderingContext2D;

  constructor(canvas: HTMLCanvasElement) {
    this.canvas = canvas;
    const context = canvas.getContext('2d');
    if (!context) throw new Error('Could not get 2D context for ILS Profile');
    this.ctx = context;
  }

  public render(telemetry: FullTelemetry) {
    const ctx = this.ctx;
    const width = this.canvas.width;
    const height = this.canvas.height;

    ctx.clearRect(0, 0, width, height);

    const nav1 = telemetry.nav1;
    const ac = telemetry.aircraft;
    const isIls = nav1.mode === 'ILS';

    ctx.save();
    ctx.fillStyle = '#080d1a';
    ctx.fillRect(0, 0, width, height);

    if (!isIls || !nav1.evaluation) {
      // Standby / Non-ILS banner
      ctx.fillStyle = '#64748b';
      ctx.font = '12px Inter, sans-serif';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText('ILS INACTIVE - TUNE ILS LOC/GP (e.g. ISW 110.95 or ISE 109.5)', width / 2, height / 2);
      ctx.restore();
      return;
    }

    const ev = nav1.evaluation as any;
    const distTouchdown = ev.dist_to_touchdown_nm || 0.0;
    const altFt = ac.altitude_ft;

    // Graph bounds:
    // X-axis: 0 to 12 NM (Threshold at left: x=60px, 12 NM at right: x=width-20px)
    // Y-axis: 0 to 4000 ft (Threshold elevation at bottom: y=height-30px, 4000ft at top: y=30px)
    const marginL = 50;
    const marginR = 20;
    const marginT = 25;
    const marginB = 30;
    const plotW = width - marginL - marginR;
    const plotH = height - marginT - marginB;

    const maxDist = 12.0; // NM
    const maxAlt = 4000.0; // ft

    const xFromDist = (d: number) => marginL + (Math.min(maxDist, Math.max(0, d)) / maxDist) * plotW;
    const yFromAlt = (a: number) => marginT + plotH - (Math.min(maxAlt, Math.max(0, a)) / maxAlt) * plotH;

    // Grid lines
    ctx.strokeStyle = '#1e293b';
    ctx.lineWidth = 1;

    for (let d = 2; d <= 12; d += 2) {
      const gx = xFromDist(d);
      ctx.beginPath();
      ctx.moveTo(gx, marginT);
      ctx.lineTo(gx, marginT + plotH);
      ctx.stroke();

      ctx.fillStyle = '#64748b';
      ctx.font = '9px Consolas, monospace';
      ctx.textAlign = 'center';
      ctx.fillText(`${d}NM`, gx, height - 12);
    }

    for (let a = 1000; a <= 4000; a += 1000) {
      const gy = yFromAlt(a);
      ctx.beginPath();
      ctx.moveTo(marginL, gy);
      ctx.lineTo(marginL + plotW, gy);
      ctx.stroke();

      ctx.fillStyle = '#64748b';
      ctx.font = '9px Consolas, monospace';
      ctx.textAlign = 'right';
      ctx.fillText(`${a}ft`, marginL - 6, gy + 3);
    }

    // Runway Threshold at X=0
    const rwyElev = ev.runway_id === '06' ? 46.0 : (ev.runway_id === '24' ? 15.0 : 46.0);
    const thrX = xFromDist(0);
    const thrY = yFromAlt(rwyElev);
    ctx.fillStyle = '#ffffff';
    ctx.fillRect(thrX - 4, thrY - 4, 16, 6);
    ctx.fillStyle = '#38bdf8';
    ctx.font = 'bold 9px Inter, sans-serif';
    ctx.textAlign = 'left';
    ctx.fillText(`RWY ${ev.runway_id} (${rwyElev.toFixed(0)}ft)`, thrX + 16, thrY);

    // 3.0° Nominal Glide Path Beam (Aiming at TDZ with 50 ft Threshold Crossing Height)
    // Height at d NM from threshold = d * 6076.115 * tan(3 deg) + rwyElev + 50 ft
    const gp0Alt = rwyElev + 50.0;
    const gp10Alt = 10.0 * 6076.115 * Math.tan((3.0 * Math.PI) / 180.0) + gp0Alt;
    const gpX0 = thrX;
    const gpY0 = yFromAlt(gp0Alt);
    const gpX10 = xFromDist(10.0);
    const gpY10 = yFromAlt(gp10Alt);

    ctx.beginPath();
    ctx.moveTo(gpX0, gpY0);
    ctx.lineTo(gpX10, gpY10);
    ctx.strokeStyle = '#c084fc'; // Purple glide path
    ctx.lineWidth = 2;
    ctx.stroke();

    // Beam corridor (+/- 0.7 deg)
    const upperAlt = 10.0 * 6076.115 * Math.tan((3.7 * Math.PI) / 180.0) + gp0Alt;
    const lowerAlt = 10.0 * 6076.115 * Math.tan((2.3 * Math.PI) / 180.0) + gp0Alt;
    ctx.beginPath();
    ctx.moveTo(gpX0, gpY0);
    ctx.lineTo(gpX10, yFromAlt(upperAlt));
    ctx.lineTo(gpX10, yFromAlt(lowerAlt));
    ctx.closePath();
    ctx.fillStyle = 'rgba(192, 132, 252, 0.12)';
    ctx.fill();

    // Plot Aircraft Current Position on Profile
    if (distTouchdown <= maxDist) {
      const acX = xFromDist(distTouchdown);
      const acY = yFromAlt(altFt);

      ctx.beginPath();
      ctx.arc(acX, acY, 5, 0, Math.PI * 2);
      ctx.fillStyle = '#facc15'; // Amber yellow
      ctx.fill();
      ctx.strokeStyle = '#0f172a';
      ctx.lineWidth = 1.5;
      ctx.stroke();

      // Aircraft readout
      ctx.fillStyle = '#facc15';
      ctx.font = 'bold 9px Consolas, monospace';
      ctx.textAlign = 'left';
      ctx.fillText(`${altFt.toFixed(0)}ft`, acX + 8, acY - 4);
    }

    // Top Header info
    ctx.fillStyle = '#f8fafc';
    ctx.font = 'bold 10px Consolas, monospace';
    ctx.textAlign = 'left';
    ctx.fillText(`ILS RWY ${ev.runway_id} (${ev.morse_code || 'ISW'}) | GP 3.0°`, marginL, 16);

    ctx.textAlign = 'right';
    const autoland = ev.autoland_guidance_valid;
    ctx.fillStyle = autoland ? '#34d399' : '#f59e0b';
    ctx.fillText(autoland ? 'AUTOLAND CAT II / III ARMED' : 'ILS FLIGHT GUIDANCE ACTIVE', width - marginR, 16);

    ctx.restore();
  }
}

