/**
 * Full Cockpit ILS Precision Approach Modal Display.
 * Provides high-fidelity EFIS Primary Flight Display (PFD) with cross-pointer flight director,
 * 3D synthetic runway perspective approach HUD, 4-light PAPI visual array,
 * Decision Height / Minimums annunciator, and real-time ARINC 429 telemetry stream.
 */

import { FullTelemetry, ILSEvaluation } from '../types';

export class FullIlsModal {
  private modalOverlay: HTMLElement | null = null;
  private pfdCanvas: HTMLCanvasElement | null = null;
  private hudCanvas: HTMLCanvasElement | null = null;
  private pfdCtx: CanvasRenderingContext2D | null = null;
  private hudCtx: CanvasRenderingContext2D | null = null;

  private isVisible: boolean = false;
  private lastAutoPromptPhase: string = '';
  private strobePhase: number = 0;

  constructor() {
    this.createModalDom();
    this.attachEvents();
  }

  private createModalDom() {
    const existing = document.getElementById('ils-fullscreen-modal');
    if (existing) existing.remove();

    const overlay = document.createElement('div');
    overlay.id = 'ils-fullscreen-modal';
    overlay.className = 'ils-modal-backdrop';
    overlay.style.display = 'none';

    overlay.innerHTML = `
      <div class="ils-modal-window">
        <!-- Modal Header -->
        <div class="ils-modal-header">
          <div class="ils-header-title">
            <span class="icon">🎯</span>
            <div>
              <div class="title-text">CAT II / III PRECISION APPROACH COCKPIT DISPLAY</div>
              <div class="sub-text" id="ils-modal-station-title">SHANNON AIRPORT (EINN) RWY 24 | ILS LOC/GP (ISW 110.95 MHz)</div>
            </div>
          </div>

          <div class="ils-header-actions">
            <div class="autoland-status-pill" id="ils-autoland-pill">CAT II DUAL ARMED</div>
            <button class="btn-close-modal" id="btn-close-ils-modal" title="Close [ESC]">✕</button>
          </div>
        </div>

        <!-- Decision Height / Minimums Alert Banner -->
        <div class="dh-alert-banner" id="dh-alert-banner" style="display: none;">
          <span class="dh-icon">⚠️</span>
          <span class="dh-text" id="dh-alert-text">DECISION HEIGHT (DH) 100 FT REACHED - MINIMUMS!</span>
        </div>

        <!-- Main Grid -->
        <div class="ils-modal-grid">
          <!-- Left: Primary Flight Display (PFD) / Flight Director -->
          <div class="ils-pfd-card">
            <div class="card-caption">
              <span>PRIMARY FLIGHT DISPLAY (PFD) & CROSS-POINTER</span>
              <span class="font-mono text-cyan" id="pfd-ra-display">RA: 2,500 FT</span>
            </div>
            <div class="canvas-wrapper">
              <canvas id="pfd-canvas" width="460" height="420"></canvas>
            </div>
          </div>

          <!-- Right: Synthetic Approach HUD & PAPI -->
          <div class="ils-hud-card">
            <div class="card-caption">
              <span>OUT-THE-WINDOW RUNWAY HUD & 4-LIGHT PAPI</span>
              <div style="display: flex; align-items: center; gap: 8px;">
                <span class="font-mono text-amber" id="papi-readout-text">PAPI: 2W 2R (ON PATH)</span>
                <button class="btn-xs btn-toggle-modal-telemetry" id="btn-toggle-modal-telem" title="Collapse digital telemetry readouts">▼ HIDE DATA</button>
              </div>
            </div>
            <div class="canvas-wrapper">
              <canvas id="hud-canvas" width="460" height="240"></canvas>
            </div>

            <!-- ARINC 429 & Telemetry Summary Box -->
            <div class="ils-telemetry-box" id="ils-modal-telem-box">
              <div class="telem-row">
                <span class="lbl">LOCALIZER:</span>
                <span class="val text-cyan" id="m-loc-dev">0.00 dots (0.0000 DDM)</span>
                <span class="lbl">ARINC 173:</span>
                <span class="val font-mono" id="m-arinc-173">03720000_16</span>
              </div>
              <div class="telem-row">
                <span class="lbl">GLIDE PATH:</span>
                <span class="val text-purple" id="m-gp-dev">0.00 dots (0.0000 DDM)</span>
                <span class="lbl">ARINC 174:</span>
                <span class="val font-mono" id="m-arinc-174">03730000_16</span>
              </div>
              <div class="telem-row">
                <span class="lbl">THRESHOLD DIST:</span>
                <span class="val text-amber" id="m-dist-thr">5.0 NM</span>
                <span class="lbl">SINK RATE:</span>
                <span class="val text-green" id="m-sink-rate">-740 FPM (NOMINAL)</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Modal Footer -->
        <div class="ils-modal-footer">
          <div class="footer-hint">
            <span>Keyboard: Press <kbd>ESC</kbd> to close | Press <kbd>I</kbd> to toggle</span>
          </div>
          <div class="approach-mode-tags">
            <span class="fma-tag">LOC TRACK</span>
            <span class="fma-tag">G/S TRACK</span>
            <span class="fma-tag">LAND 3 DUAL</span>
            <span class="fma-tag">DH 100 FT</span>
          </div>
        </div>
      </div>
    `;

    document.body.appendChild(overlay);
    this.modalOverlay = overlay;

    this.pfdCanvas = document.getElementById('pfd-canvas') as HTMLCanvasElement;
    this.hudCanvas = document.getElementById('hud-canvas') as HTMLCanvasElement;
    if (this.pfdCanvas) this.pfdCtx = this.pfdCanvas.getContext('2d');
    if (this.hudCanvas) this.hudCtx = this.hudCanvas.getContext('2d');
  }

  private attachEvents() {
    const btnClose = document.getElementById('btn-close-ils-modal');
    btnClose?.addEventListener('click', () => this.hide());

    const btnToggleTelem = document.getElementById('btn-toggle-modal-telem');
    const telemBox = document.getElementById('ils-modal-telem-box');
    btnToggleTelem?.addEventListener('click', () => {
      if (!telemBox) return;
      const isHidden = telemBox.style.display === 'none';
      telemBox.style.display = isHidden ? 'flex' : 'none';
      btnToggleTelem.textContent = isHidden ? '▼ HIDE DATA' : '▲ SHOW DATA';
    });

    this.modalOverlay?.addEventListener('click', (e) => {
      if (e.target === this.modalOverlay) {
        this.hide();
      }
    });

    window.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && this.isVisible) {
        this.hide();
      } else if ((e.key === 'i' || e.key === 'I') && !['INPUT', 'SELECT', 'TEXTAREA'].includes((e.target as HTMLElement)?.tagName)) {
        this.toggle();
      }
    });
  }

  public show() {
    if (!this.modalOverlay) return;
    this.modalOverlay.style.display = 'flex';
    this.isVisible = true;
  }

  public hide() {
    if (!this.modalOverlay) return;
    this.modalOverlay.style.display = 'none';
    this.isVisible = false;
  }

  public toggle() {
    if (this.isVisible) this.hide();
    else this.show();
  }

  public update(telemetry: FullTelemetry) {
    // Auto-prompt when transitioning to FINAL_APPROACH
    const phase = telemetry.aircraft.flight_phase;
    if (phase === 'FINAL_APPROACH' && this.lastAutoPromptPhase !== 'FINAL_APPROACH') {
      this.lastAutoPromptPhase = phase;
      this.showAutoPromptBanner();
    } else if (phase !== 'FINAL_APPROACH') {
      this.lastAutoPromptPhase = phase;
    }

    if (!this.isVisible) return;

    this.strobePhase = (this.strobePhase + 0.15) % (Math.PI * 2);
    this.renderPfd(telemetry);
    this.renderHud(telemetry);
    this.updateTelemetryBoxes(telemetry);
  }

  private showAutoPromptBanner() {
    // Surface an approach pill prompt if modal is not currently open
    if (this.isVisible) return;
    const promptId = 'ils-finals-prompt-toast';
    let toast = document.getElementById(promptId);
    if (!toast) {
      toast = document.createElement('div');
      toast.id = promptId;
      toast.className = 'ils-finals-toast';
      toast.innerHTML = `
        <div class="toast-body">
          <span class="icon">🎯</span>
          <div>
            <b>ESTABLISHED ON FINAL APPROACH</b>
            <div class="toast-sub">Runway 24 ILS Localizer & Glide Slope active.</div>
          </div>
          <button class="btn-xs btn-open-modal-now" id="btn-toast-open-ils">OPEN FULL ILS DISPLAY</button>
          <button class="btn-xs btn-toast-dismiss" id="btn-toast-dismiss">✕</button>
        </div>
      `;
      document.body.appendChild(toast);

      document.getElementById('btn-toast-open-ils')?.addEventListener('click', () => {
        toast?.remove();
        this.show();
      });
      document.getElementById('btn-toast-dismiss')?.addEventListener('click', () => {
        toast?.remove();
      });

      setTimeout(() => toast?.remove(), 12000);
    }
  }

  private updateTelemetryBoxes(telemetry: FullTelemetry) {
    const nav1 = telemetry.nav1;
    const ac = telemetry.aircraft;
    const ev = (nav1.mode === 'ILS' ? nav1.evaluation : null) as ILSEvaluation | null;

    const locDev = ev?.loc_deflection_dots ?? 0;
    const locDdm = ev?.loc_ddm ?? 0;
    const gpDev = ev?.gp_deflection_dots ?? 0;
    const gpDdm = ev?.gp_ddm ?? 0;
    const dist = ev?.dist_to_touchdown_nm ?? 0;

    const elLoc = document.getElementById('m-loc-dev');
    if (elLoc) elLoc.textContent = `${locDev >= 0 ? '+' : ''}${locDev.toFixed(2)} dots (${locDdm.toFixed(4)} DDM)`;

    const elGp = document.getElementById('m-gp-dev');
    if (elGp) elGp.textContent = `${gpDev >= 0 ? '+' : ''}${gpDev.toFixed(2)} dots (${gpDdm.toFixed(4)} DDM)`;

    const elDist = document.getElementById('m-dist-thr');
    if (elDist) elDist.textContent = `${dist.toFixed(2)} NM`;

    const elSink = document.getElementById('m-sink-rate');
    if (elSink) {
      const vs = ac.vertical_speed_fpm;
      elSink.textContent = `${vs.toFixed(0)} FPM (${vs <= -600 && vs >= -850 ? 'NOMINAL' : 'CHECK SINK'})`;
      elSink.className = `val ${vs < -1000 ? 'text-red' : 'text-green'}`;
    }

    // ARINC labels from telemetry bus
    const w173 = telemetry.arinc429_bus.find(w => w.label_octal === '173');
    const w174 = telemetry.arinc429_bus.find(w => w.label_octal === '174');
    const el173 = document.getElementById('m-arinc-173');
    if (el173) el173.textContent = w173 ? `0x${w173.raw_hex} (L173)` : 'NO SIGNAL';
    const el174 = document.getElementById('m-arinc-174');
    if (el174) el174.textContent = w174 ? `0x${w174.raw_hex} (L174)` : 'NO SIGNAL';

    // Station title update
    const titleEl = document.getElementById('ils-modal-station-title');
    if (titleEl) {
      if (nav1.mode === 'ILS' && nav1.station) {
        const rwy = ev?.runway_id || '24';
        const crs = ev?.runway_bearing_mag ? `${ev.runway_bearing_mag.toFixed(0)}°M` : (rwy === '06' ? '056°M' : '236°M');
        titleEl.textContent = `SHANNON AIRPORT (EINN) RWY ${rwy} | ILS LOC/GP (${nav1.station.id} ${nav1.station.frequency}) | INBOUND CRS ${crs}`;
      } else {
        titleEl.textContent = `STANDBY - NAV1 TUNED TO ${nav1.station?.id || 'VOR'} (${nav1.station?.frequency || 'STANDBY'})`;
      }
    }

    // Radio Altimeter & DH banner
    const elRa = document.getElementById('pfd-ra-display');
    const dhBanner = document.getElementById('dh-alert-banner');
    const dhText = document.getElementById('dh-alert-text');
    const rwyElev = ev?.height_above_threshold_ft !== undefined ? Math.max(0, ac.altitude_ft - ev.height_above_threshold_ft) : (ev?.runway_id === '06' ? 46.0 : 15.0);
    const raAlt = Math.max(0, ac.altitude_ft - rwyElev);

    if (elRa) {
      elRa.textContent = raAlt <= 2500 ? `RA: ${raAlt.toFixed(0)} FT` : 'BARO REF';
    }

    if (dhBanner && dhText) {
      if (raAlt <= 100 && raAlt > 10) {
        dhBanner.style.display = 'flex';
        dhBanner.className = 'dh-alert-banner';
        dhText.textContent = `DECISION HEIGHT (DH) 100 FT REACHED - RADIO ALT: ${raAlt.toFixed(0)} FT | LAND OR GO-AROUND`;
      } else if (raAlt <= 10 && ac.flight_phase === 'TOUCHDOWN') {
        const rwy = ev?.runway_id || '24';
        dhBanner.style.display = 'flex';
        dhBanner.className = 'dh-alert-banner dh-touchdown';
        dhText.textContent = `TOUCHDOWN ON RUNWAY ${rwy} | SPOILERS DEPLOYED | REVERSE THRUST`;
      } else {
        dhBanner.style.display = 'none';
      }
    }
  }

  /**
   * Renders high-fidelity Primary Flight Display (PFD).
   */
  private renderPfd(telemetry: FullTelemetry) {
    if (!this.pfdCtx || !this.pfdCanvas) return;
    const ctx = this.pfdCtx;
    const w = this.pfdCanvas.width;
    const h = this.pfdCanvas.height;

    ctx.clearRect(0, 0, w, h);

    const ac = telemetry.aircraft;
    const nav1 = telemetry.nav1;
    const ev = (nav1.mode === 'ILS' ? nav1.evaluation : null) as ILSEvaluation | null;

    const centerX = w / 2;
    const centerY = h / 2 - 10;
    const pitch = ac.pitch_deg;
    const rollRad = (ac.roll_deg * Math.PI) / 180.0;

    // 1. Attitude Indicator Horizon Sphere
    ctx.save();
    ctx.beginPath();
    ctx.rect(60, 45, w - 120, h - 90);
    ctx.clip();

    ctx.translate(centerX, centerY);
    ctx.rotate(-rollRad);

    const pitchPixelsPerDeg = 3.5;
    const pitchOffset = pitch * pitchPixelsPerDeg;

    // Sky
    ctx.fillStyle = '#0284c7'; // Sky Blue
    ctx.fillRect(-w, -h * 2 + pitchOffset, w * 2, h * 2);

    // Ground
    ctx.fillStyle = '#854d0e'; // Ground Brown
    ctx.fillRect(-w, pitchOffset, w * 2, h * 2);

    // Horizon line
    ctx.beginPath();
    ctx.moveTo(-w, pitchOffset);
    ctx.lineTo(w, pitchOffset);
    ctx.strokeStyle = '#ffffff';
    ctx.lineWidth = 2;
    ctx.stroke();

    // Pitch ladder bars
    ctx.strokeStyle = '#ffffff';
    ctx.fillStyle = '#ffffff';
    ctx.font = '10px Consolas, monospace';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.lineWidth = 1.5;

    for (let p = -20; p <= 20; p += 5) {
      if (p === 0) continue;
      const y = pitchOffset - p * pitchPixelsPerDeg;
      const barLen = Math.abs(p) % 10 === 0 ? 36 : 18;

      ctx.beginPath();
      ctx.moveTo(-barLen, y);
      ctx.lineTo(barLen, y);
      ctx.stroke();

      if (Math.abs(p) % 10 === 0) {
        ctx.fillText(Math.abs(p).toString(), -barLen - 12, y);
        ctx.fillText(Math.abs(p).toString(), barLen + 12, y);
      }
    }

    ctx.restore();

    // 2. Aircraft Symbol (Fixed Yellow Wings & Center Pip)
    ctx.strokeStyle = '#facc15';
    ctx.fillStyle = '#facc15';
    ctx.lineWidth = 3.5;

    // Center pip
    ctx.beginPath();
    ctx.arc(centerX, centerY, 3.5, 0, Math.PI * 2);
    ctx.fill();

    // Left wing
    ctx.beginPath();
    ctx.moveTo(centerX - 45, centerY);
    ctx.lineTo(centerX - 15, centerY);
    ctx.lineTo(centerX - 15, centerY + 6);
    ctx.stroke();

    // Right wing
    ctx.beginPath();
    ctx.moveTo(centerX + 15, centerY + 6);
    ctx.lineTo(centerX + 15, centerY);
    ctx.lineTo(centerX + 45, centerY);
    ctx.stroke();

    // 3. ILS Flight Director Command Crosshairs (Magenta)
    if (ev) {
      const locDots = ev.loc_deflection_dots || 0;
      const gpDots = ev.gp_deflection_dots || 0;

      // 1 dot = 18 px deflection
      const fdX = centerX + Math.max(-60, Math.min(60, locDots * 18));
      const fdY = centerY - Math.max(-60, Math.min(60, gpDots * 18));

      ctx.strokeStyle = '#d946ef'; // Magenta
      ctx.lineWidth = 2.5;

      // Vertical Localizer FD Bar
      ctx.beginPath();
      ctx.moveTo(fdX, centerY - 45);
      ctx.lineTo(fdX, centerY + 45);
      ctx.stroke();

      // Horizontal Glide Slope FD Bar
      ctx.beginPath();
      ctx.moveTo(centerX - 45, fdY);
      ctx.lineTo(centerX + 45, fdY);
      ctx.stroke();
    }

    // 4. Localizer Deviation Scale (Bottom Dots)
    const scaleY = h - 60;
    ctx.fillStyle = '#64748b';
    for (let d = -2; d <= 2; d++) {
      ctx.beginPath();
      ctx.arc(centerX + d * 25, scaleY, d === 0 ? 2 : 2.5, 0, Math.PI * 2);
      ctx.fill();
    }

    if (ev) {
      // Magenta Localizer Index Pointer
      const locDots = Math.max(-2.5, Math.min(2.5, ev.loc_deflection_dots / 2.0));
      const locPtrX = centerX + locDots * 25 * 2.0;
      ctx.fillStyle = '#d946ef';
      ctx.beginPath();
      ctx.moveTo(locPtrX, scaleY - 6);
      ctx.lineTo(locPtrX - 5, scaleY + 4);
      ctx.lineTo(locPtrX + 5, scaleY + 4);
      ctx.closePath();
      ctx.fill();
    }

    // 5. Glide Slope Deviation Scale (Right Dots)
    const scaleX = w - 75;
    ctx.fillStyle = '#64748b';
    for (let d = -2; d <= 2; d++) {
      ctx.beginPath();
      ctx.arc(scaleX, centerY + d * 25, d === 0 ? 2 : 2.5, 0, Math.PI * 2);
      ctx.fill();
    }

    if (ev) {
      // Magenta Glide Slope Diamond
      const gpDots = Math.max(-2.5, Math.min(2.5, ev.gp_deflection_dots / 2.0));
      const gpPtrY = centerY - gpDots * 25 * 2.0;

      ctx.fillStyle = '#d946ef';
      ctx.beginPath();
      ctx.moveTo(scaleX - 6, gpPtrY);
      ctx.lineTo(scaleX, gpPtrY - 5);
      ctx.lineTo(scaleX + 6, gpPtrY);
      ctx.lineTo(scaleX, gpPtrY + 5);
      ctx.closePath();
      ctx.fill();
    }

    // 6. Airspeed Tape (Left)
    ctx.fillStyle = 'rgba(15, 23, 42, 0.85)';
    ctx.fillRect(0, 45, 55, h - 90);
    ctx.strokeStyle = '#334155';
    ctx.strokeRect(0, 45, 55, h - 90);

    ctx.fillStyle = '#ffffff';
    ctx.font = 'bold 12px Consolas, monospace';
    ctx.textAlign = 'right';
    const spd = ac.groundspeed_kts;
    ctx.fillText(`${spd.toFixed(0)}`, 45, centerY);
    ctx.font = '9px Inter, sans-serif';
    ctx.fillStyle = '#94a3b8';
    ctx.fillText('KT', 45, centerY + 14);

    // 7. Altitude Tape (Right)
    ctx.fillStyle = 'rgba(15, 23, 42, 0.85)';
    ctx.fillRect(w - 60, 45, 60, h - 90);
    ctx.strokeStyle = '#334155';
    ctx.strokeRect(w - 60, 45, 60, h - 90);

    ctx.fillStyle = '#38bdf8';
    ctx.font = 'bold 12px Consolas, monospace';
    ctx.textAlign = 'left';
    ctx.fillText(`${ac.altitude_ft.toFixed(0)}`, w - 52, centerY);
    ctx.font = '9px Inter, sans-serif';
    ctx.fillStyle = '#94a3b8';
    ctx.fillText('FT', w - 52, centerY + 14);

    // 8. Flight Mode Annunciator (FMA) Header Box
    ctx.fillStyle = 'rgba(2, 6, 23, 0.95)';
    ctx.fillRect(0, 0, w, 40);
    ctx.strokeStyle = '#1e293b';
    ctx.beginPath();
    ctx.moveTo(0, 40);
    ctx.lineTo(w, 40);
    ctx.stroke();

    ctx.font = 'bold 10px Consolas, monospace';
    ctx.fillStyle = '#34d399'; // Green active
    ctx.textAlign = 'center';
    ctx.fillText('LOC', 50, 22);
    ctx.fillText('G/S', 120, 22);
    ctx.fillStyle = '#38bdf8'; // Cyan armed
    ctx.fillText('CAT 2', 200, 22);
    ctx.fillText('AP 1+2', 270, 22);
    ctx.fillText('1 FD 2', 340, 22);
    ctx.fillStyle = '#34d399';
    ctx.fillText('A/THR', 410, 22);
  }

  /**
   * Renders Out-The-Window Synthetic Runway Perspective HUD and 4-light PAPI.
   */
  private renderHud(telemetry: FullTelemetry) {
    if (!this.hudCtx || !this.hudCanvas) return;
    const ctx = this.hudCtx;
    const w = this.hudCanvas.width;
    const h = this.hudCanvas.height;

    ctx.clearRect(0, 0, w, h);

    const ac = telemetry.aircraft;
    const nav1 = telemetry.nav1;
    const ev = (nav1.mode === 'ILS' ? nav1.evaluation : null) as ILSEvaluation | null;

    // Dark Night Sky & Ground backdrop
    ctx.fillStyle = '#050811';
    ctx.fillRect(0, 0, w, h);

    // Horizon line
    const horizonY = h * 0.45;
    ctx.strokeStyle = '#0f172a';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(0, horizonY);
    ctx.lineTo(w, horizonY);
    ctx.stroke();

    // Calculate Runway Perspective geometry based on distance and altitude
    const rwyElev = ev ? (ev.runway_id === '06' ? 46.0 : (ev.runway_id === '24' ? 15.0 : 46.0)) : 15.0;
    const distNm = ev ? Math.max(0.001, ev.dist_to_touchdown_nm) : 5.0;
    const altAboveThr = Math.max(0, ac.altitude_ft - rwyElev);

    // Normalized scale factor: closer = larger
    // At 10 NM -> scale ~ 0.05; at 0.5 NM -> scale ~ 0.8
    const scale = Math.min(1.2, 1.0 / (distNm * 0.8 + 0.3));
    const locOffsetDots = ev ? ev.loc_deflection_dots : 0.0;

    const vpX = w / 2 - locOffsetDots * 15 * scale;
    const thrY = horizonY + (h - horizonY) * Math.min(0.85, 0.15 + (1.0 / (distNm + 0.5)) * 0.45);

    const rwyWidthFar = 8 * scale;
    const rwyWidthNear = 75 * scale;
    const rwyFarY = horizonY + 2;

    // Runway Asphalt Surface
    ctx.fillStyle = '#1e293b';
    ctx.beginPath();
    ctx.moveTo(vpX - rwyWidthFar, rwyFarY);
    ctx.lineTo(vpX + rwyWidthFar, rwyFarY);
    ctx.lineTo(vpX + rwyWidthNear, thrY);
    ctx.lineTo(vpX - rwyWidthNear, thrY);
    ctx.closePath();
    ctx.fill();

    // Runway Edge Lights (White)
    ctx.strokeStyle = '#f8fafc';
    ctx.lineWidth = 1.5;
    ctx.stroke();

    // Centerline Lights (Pulsing White / Red near threshold)
    ctx.strokeStyle = distNm < 0.3 ? '#ef4444' : '#fef08a';
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.moveTo(vpX, rwyFarY);
    ctx.lineTo(vpX, thrY);
    ctx.stroke();

    // Green Threshold Lights Bar
    ctx.strokeStyle = '#22c55e';
    ctx.lineWidth = 3;
    ctx.beginPath();
    ctx.moveTo(vpX - rwyWidthNear, thrY);
    ctx.lineTo(vpX + rwyWidthNear, thrY);
    ctx.stroke();

    // Approach Lighting System (ALSF-2 / Calvert) with Sequenced Flashing Rabbit
    const alsLength = (h - thrY) * 0.85;
    const numBars = 6;
    for (let i = 1; i <= numBars; i++) {
      const barY = thrY + (alsLength / numBars) * i;
      const barW = (rwyWidthNear * 0.9) * (1.0 + i * 0.15);

      // White crossbar
      ctx.strokeStyle = '#f8fafc';
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.moveTo(vpX - barW / 2, barY);
      ctx.lineTo(vpX + barW / 2, barY);
      ctx.stroke();

      // Sequenced Flashing Rabbit Strobe
      const isStrobeActive = Math.sin(this.strobePhase + i * 0.8) > 0.6;
      if (isStrobeActive) {
        ctx.fillStyle = '#ffffff';
        ctx.beginPath();
        ctx.arc(vpX, barY, 4, 0, Math.PI * 2);
        ctx.fill();
      }
    }

    // 4-Light PAPI Visual Array (Positioned beside runway Touchdown Zone, 300m past threshold)
    const papiX = vpX - rwyWidthNear - 35 * scale;
    const papiY = thrY - 10 * scale;

    // Calculate PAPI colors based on glide slope angle to the Touchdown Aiming Point (300m = 0.162 NM past threshold)
    // Nominal angle = 3.0°
    // > 3.35°: 4 White (Too High)
    // 3.15° to 3.35°: 3 White, 1 Red (Slightly High)
    // 2.85° to 3.15°: 2 White, 2 Red (ON GLIDEPATH)
    // 2.65° to 2.85°: 1 White, 3 Red (Slightly Low)
    // < 2.65°: 4 Red (Dangerously Low)
    const distPapiFt = (distNm + 0.162) * 6076.11548;
    const angleDeg = distPapiFt > 100 ? (Math.atan2(altAboveThr, distPapiFt) * 180.0) / Math.PI : 3.0;

    let lights: ('W' | 'R')[] = ['W', 'W', 'R', 'R'];
    let papiStatus = '2W 2R (ON GLIDEPATH)';

    if (distNm <= 0.05 && altAboveThr <= 5.0) {
      lights = ['R', 'R', 'R', 'R'];
      papiStatus = 'TOUCHDOWN / ROLLOUT';
    } else if (angleDeg > 3.35) {
      lights = ['W', 'W', 'W', 'W'];
      papiStatus = '4W (TOO HIGH)';
    } else if (angleDeg >= 3.15) {
      lights = ['W', 'W', 'W', 'R'];
      papiStatus = '3W 1R (SLIGHTLY HIGH)';
    } else if (angleDeg >= 2.85) {
      lights = ['W', 'W', 'R', 'R'];
      papiStatus = '2W 2R (ON GLIDEPATH)';
    } else if (angleDeg >= 2.65) {
      lights = ['W', 'R', 'R', 'R'];
      papiStatus = '1W 3R (SLIGHTLY LOW)';
    } else {
      lights = ['R', 'R', 'R', 'R'];
      papiStatus = '4R (DANGEROUSLY LOW)';
    }

    const papiLabelEl = document.getElementById('papi-readout-text');
    if (papiLabelEl) papiLabelEl.textContent = `PAPI: ${papiStatus}`;

    // Render 4 PAPI Lights Box
    ctx.fillStyle = '#0f172a';
    ctx.fillRect(papiX - 2, papiY - 6, 44, 14);
    ctx.strokeStyle = '#334155';
    ctx.strokeRect(papiX - 2, papiY - 6, 44, 14);

    lights.forEach((color, idx) => {
      const lx = papiX + idx * 10 + 4;
      ctx.beginPath();
      ctx.arc(lx, papiY, 3.5, 0, Math.PI * 2);
      ctx.fillStyle = color === 'W' ? '#ffffff' : '#ef4444';
      ctx.shadowColor = color === 'W' ? '#ffffff' : '#ef4444';
      ctx.shadowBlur = 6;
      ctx.fill();
      ctx.shadowBlur = 0; // reset
    });

    // PAPI Text label
    ctx.fillStyle = '#94a3b8';
    ctx.font = '8px Consolas, monospace';
    ctx.textAlign = 'center';
    ctx.fillText('PAPI 3.0°', papiX + 18, papiY + 16);
  }
}
