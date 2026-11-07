/**
 * Electronic Horizontal Situation Indicator (HSI) / Navigation Display.
 * Renders high-fidelity compass card, VOR OBS course needle, Course Deviation Indicator (CDI),
 * TO/FROM flag, ILS Localizer needle, and Glide Slope diamond scale.
 */

import { FullTelemetry } from '../types';

export class HsiDisplay {
  private canvas: HTMLCanvasElement;
  private ctx: CanvasRenderingContext2D;

  constructor(canvas: HTMLCanvasElement) {
    this.canvas = canvas;
    const context = canvas.getContext('2d');
    if (!context) throw new Error('Could not get 2D context for HSI canvas');
    this.ctx = context;
  }

  public render(telemetry: FullTelemetry) {
    const ctx = this.ctx;
    const width = this.canvas.width;
    const height = this.canvas.height;
    const cx = width / 2;
    const cy = height / 2;
    const radius = Math.min(width, height) * 0.44;

    ctx.clearRect(0, 0, width, height);

    const ac = telemetry.aircraft;
    const nav1 = telemetry.nav1;
    const dme1 = telemetry.dme1;
    const isIls = nav1.mode === 'ILS';
    const hdg = ac.magnetic_heading_deg;
    const obs = nav1.obs_deg;

    // 1. Dark instrument bezel & background
    ctx.save();
    ctx.beginPath();
    ctx.arc(cx, cy, radius + 14, 0, Math.PI * 2);
    ctx.fillStyle = '#080d1a';
    ctx.fill();
    ctx.lineWidth = 4;
    ctx.strokeStyle = '#1e293b';
    ctx.stroke();

    // 2. Rotating Compass Rose
    // The compass card rotates counter to heading so aircraft heading is always at top (12 o'clock)
    ctx.save();
    ctx.translate(cx, cy);
    ctx.rotate((-hdg * Math.PI) / 180.0);

    // Compass ring circle
    ctx.beginPath();
    ctx.arc(0, 0, radius, 0, Math.PI * 2);
    ctx.strokeStyle = '#334155';
    ctx.lineWidth = 1.5;
    ctx.stroke();

    // Compass tick marks every 5 and 10 degrees, numbers every 30 degrees
    for (let deg = 0; deg < 360; deg += 5) {
      const rad = (deg * Math.PI) / 180.0;
      const is30 = deg % 30 === 0;
      const is10 = deg % 10 === 0;
      const tickLen = is30 ? 14 : is10 ? 9 : 5;

      const x1 = (radius - tickLen) * Math.sin(rad);
      const y1 = -(radius - tickLen) * Math.cos(rad);
      const x2 = radius * Math.sin(rad);
      const y2 = -radius * Math.cos(rad);

      ctx.beginPath();
      ctx.moveTo(x1, y1);
      ctx.lineTo(x2, y2);
      ctx.strokeStyle = is30 ? '#f8fafc' : is10 ? '#94a3b8' : '#475569';
      ctx.lineWidth = is30 ? 2 : 1;
      ctx.stroke();

      if (is30) {
        ctx.save();
        const textDist = radius - 24;
        const tx = textDist * Math.sin(rad);
        const ty = -textDist * Math.cos(rad);
        ctx.translate(tx, ty);
        ctx.rotate(rad); // Align text radially or upright
        ctx.fillStyle = '#f8fafc';
        ctx.font = 'bold 11px Inter, sans-serif';
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

    // 3. Dialed Course Pointer (OBS Course Arrow)
    // Rotates with the compass card and points to selected OBS course
    ctx.save();
    ctx.rotate((obs * Math.PI) / 180.0);

    const pointerLen = radius - 8;
    const arrowColor = isIls ? '#c084fc' : '#38bdf8'; // Purple for ILS, Cyan for VOR

    // Course Head Arrow
    ctx.beginPath();
    ctx.moveTo(0, -pointerLen);
    ctx.lineTo(-8, -pointerLen + 18);
    ctx.lineTo(8, -pointerLen + 18);
    ctx.closePath();
    ctx.fillStyle = arrowColor;
    ctx.fill();

    // Reciprocal tail
    ctx.beginPath();
    ctx.moveTo(0, pointerLen);
    ctx.lineTo(0, pointerLen - 16);
    ctx.strokeStyle = arrowColor;
    ctx.lineWidth = 3;
    ctx.stroke();

    // CDI Scale Dots (5 dots on each side)
    const dotSpacing = 16;
    for (let dot = -2; dot <= 2; dot++) {
      if (dot === 0) continue;
      ctx.beginPath();
      ctx.arc(dot * dotSpacing, 0, 2.5, 0, Math.PI * 2);
      ctx.fillStyle = '#64748b';
      ctx.fill();
    }

    // CDI Needle Deflection
    let cdiDots = 0.0;
    let navFlag = true;
    let toFrom: string = 'OFF';

    if (nav1.evaluation) {
      if (isIls) {
        const ev = nav1.evaluation as any;
        cdiDots = ev.loc_deflection_dots || 0.0;
        navFlag = !ev.loc_received;
        toFrom = 'ILS';
      } else {
        const ev = nav1.evaluation as any;
        cdiDots = ev.cdi_deflection_dots || 0.0;
        navFlag = ev.failure_flag;
        toFrom = ev.to_from_flag;
      }
    }

    if (!navFlag) {
      // CDI Needle
      const needleX = cdiDots * (dotSpacing / 1.0); // 1 dot = dotSpacing px
      ctx.beginPath();
      ctx.moveTo(needleX, -pointerLen + 24);
      ctx.lineTo(needleX, pointerLen - 24);
      ctx.strokeStyle = '#facc15'; // Amber yellow CDI needle
      ctx.lineWidth = 3.5;
      ctx.stroke();

      // TO / FROM Arrow
      if (toFrom === 'TO') {
        ctx.beginPath();
        ctx.moveTo(22, 0);
        ctx.lineTo(34, -10);
        ctx.lineTo(34, 10);
        ctx.closePath();
        ctx.fillStyle = '#38bdf8';
        ctx.fill();
      } else if (toFrom === 'FROM') {
        ctx.beginPath();
        ctx.moveTo(34, 0);
        ctx.lineTo(22, -10);
        ctx.lineTo(22, 10);
        ctx.closePath();
        ctx.fillStyle = '#38bdf8';
        ctx.fill();
      }
    } else {
      // NAV Warning Flag
      ctx.save();
      ctx.fillStyle = '#dc2626'; // Red warning flag
      ctx.fillRect(-28, -12, 56, 24);
      ctx.fillStyle = '#ffffff';
      ctx.font = 'bold 10px Consolas, monospace';
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      ctx.fillText('NAV FLAG', 0, 0);
      ctx.restore();
    }

    ctx.restore(); // restore OBS rotation
    ctx.restore(); // restore Compass rotation

    // 4. Fixed Aircraft Reference Symbol (Lubber Line at Top Center)
    ctx.beginPath();
    ctx.moveTo(cx, cy - radius - 10);
    ctx.lineTo(cx - 7, cy - radius);
    ctx.lineTo(cx + 7, cy - radius);
    ctx.closePath();
    ctx.fillStyle = '#f8fafc';
    ctx.fill();

    // Center aircraft crosshair symbol
    ctx.beginPath();
    ctx.moveTo(cx - 14, cy);
    ctx.lineTo(cx + 14, cy);
    ctx.moveTo(cx, cy - 14);
    ctx.lineTo(cx, cy + 14);
    ctx.strokeStyle = '#facc15';
    ctx.lineWidth = 2;
    ctx.stroke();

    // 5. Glide Slope Deviation Scale (if ILS is tuned)
    if (isIls) {
      const gsX = cx + radius + 6;
      ctx.save();
      // Draw 5 dots vertically
      for (let dot = -2; dot <= 2; dot++) {
        const dotY = cy + dot * 18;
        ctx.beginPath();
        ctx.arc(gsX, dotY, 2.5, 0, Math.PI * 2);
        ctx.fillStyle = '#94a3b8';
        ctx.fill();
      }
      ctx.beginPath();
      ctx.moveTo(gsX - 6, cy);
      ctx.lineTo(gsX + 6, cy);
      ctx.strokeStyle = '#ffffff';
      ctx.lineWidth = 1.5;
      ctx.stroke();

      const ev = nav1.evaluation as any;
      if (ev && ev.gp_received) {
        // Glide slope diamond
        const gsDots = ev.gp_deflection_dots || 0.0;
        const diamondY = cy + gsDots * 18;
        ctx.beginPath();
        ctx.moveTo(gsX, diamondY - 7);
        ctx.lineTo(gsX + 7, diamondY);
        ctx.lineTo(gsX, diamondY + 7);
        ctx.lineTo(gsX - 7, diamondY);
        ctx.closePath();
        ctx.fillStyle = '#c084fc'; // Purple diamond
        ctx.fill();
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 1.5;
        ctx.stroke();
      } else {
        // GS Flag
        ctx.fillStyle = '#dc2626';
        ctx.fillRect(gsX - 18, cy - 8, 36, 16);
        ctx.fillStyle = '#ffffff';
        ctx.font = 'bold 8px Consolas, monospace';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText('GS', gsX, cy);
      }
      ctx.restore();
    }

    // 6. Corner Annunciators & Readouts
    ctx.fillStyle = '#38bdf8';
    ctx.font = 'bold 11px Consolas, monospace';
    ctx.textAlign = 'left';
    const stationId = nav1.station?.id || '---';
    const freqStr = nav1.station?.frequency || '---';
    ctx.fillText(`NAV1: ${stationId} (${freqStr})`, 12, 22);

    ctx.fillStyle = '#94a3b8';
    ctx.font = '10px Inter, sans-serif';
    ctx.fillText(`MODE: ${nav1.mode} | CRS: ${obs.toFixed(0)}°`, 12, 36);

    // DME in upper right corner
    ctx.textAlign = 'right';
    ctx.fillStyle = '#34d399';
    ctx.font = 'bold 12px Consolas, monospace';
    const dmeDist = dme1?.evaluation?.slant_range_nm;
    const dmeStr = dmeDist !== undefined && dmeDist > 0 ? `${dmeDist.toFixed(1)} NM` : 'DME: ---';
    ctx.fillText(dmeStr, width - 12, 22);

    ctx.fillStyle = '#94a3b8';
    ctx.font = '10px Inter, sans-serif';
    const gsKts = dme1?.evaluation?.groundspeed_readout_kts || ac.groundspeed_kts;
    ctx.fillText(`GS: ${gsKts.toFixed(0)} KT`, width - 12, 36);

    ctx.restore();
  }
}

