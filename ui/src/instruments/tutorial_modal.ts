/**
 * Cockpit Instrument Educational Tutorial Modal.
 * Explains how each flight deck instrument operates according to aeronautical standards (ICAO Annex 10 & ARINC),
 * decodes each needle, flag, scale, and readout, and generates real-time plain-English interpretations
 * of what the instrument is currently telling the flight crew.
 */

import { FullTelemetry } from '../types';

export class InstrumentTutorialModal {
  private modalOverlay: HTMLElement | null = null;
  private currentTab: string = 'hsi';
  private lastTelemetry: FullTelemetry | null = null;
  private isVisible: boolean = false;

  constructor() {
    this.createDom();
    this.attachEvents();
  }

  private createDom() {
    const existing = document.getElementById('instrument-tutorial-modal');
    if (existing) existing.remove();

    const overlay = document.createElement('div');
    overlay.id = 'instrument-tutorial-modal';
    overlay.className = 'tutorial-modal-backdrop';
    overlay.style.display = 'none';

    overlay.innerHTML = `
      <div class="tutorial-modal-window">
        <!-- Header -->
        <div class="tutorial-modal-header">
          <div class="tutorial-header-title">
            <span class="icon">📖</span>
            <div>
              <div class="title-text">COCKPIT FLIGHT INSTRUMENT TUTORIAL & TELEMETRY GUIDE</div>
              <div class="sub-text">ICAO ANNEX 10 RADIO PRINCIPLES, DISPLAY ANATOMY & LIVE INTERPRETATION</div>
            </div>
          </div>
          <button class="btn-close-modal" id="btn-close-tutorial" title="Close [ESC]">✕</button>
        </div>

        <!-- Tab Bar -->
        <div class="tutorial-tab-bar">
          <button class="tut-tab-btn active" data-tab="hsi">🧭 HSI / ND</button>
          <button class="tut-tab-btn" data-tab="rmi">📻 RMI (ADF+VOR)</button>
          <button class="tut-tab-btn" data-tab="dme">📏 DME INTERROGATOR</button>
          <button class="tut-tab-btn" data-tab="ils">🎯 ILS & GLIDE PATH</button>
          <button class="tut-tab-btn" data-tab="gnss">🛰️ GNSS & RAIM</button>
          <button class="tut-tab-btn" data-tab="arinc">⚡ ARINC 429 BUS</button>
        </div>

        <!-- Content Area -->
        <div class="tutorial-modal-content" id="tutorial-content-pane">
          <!-- Dynamically populated based on active tab -->
        </div>

        <!-- Footer -->
        <div class="tutorial-modal-footer">
          <span class="text-xs text-slate-muted">Press <kbd>ESC</kbd> to exit tutorial | Switch tabs above to inspect other instruments</span>
          <button class="btn-xs btn-primary-close" id="btn-footer-close-tutorial">GOT IT / CLOSE</button>
        </div>
      </div>
    `;

    document.body.appendChild(overlay);
    this.modalOverlay = overlay;
  }

  private attachEvents() {
    const btnClose = document.getElementById('btn-close-tutorial');
    const btnFooterClose = document.getElementById('btn-footer-close-tutorial');
    btnClose?.addEventListener('click', () => this.hide());
    btnFooterClose?.addEventListener('click', () => this.hide());

    this.modalOverlay?.addEventListener('click', (e) => {
      if (e.target === this.modalOverlay) this.hide();
    });

    window.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && this.isVisible) {
        this.hide();
      }
    });

    // Tab buttons
    this.modalOverlay?.querySelectorAll('.tut-tab-btn').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const tab = (e.currentTarget as HTMLElement).getAttribute('data-tab');
        if (tab) this.selectTab(tab);
      });
    });
  }

  public show(targetTab?: string) {
    if (!this.modalOverlay) return;
    if (targetTab) {
      this.currentTab = targetTab;
    }
    this.modalOverlay.style.display = 'flex';
    this.isVisible = true;
    this.renderActiveTab();
  }

  public hide() {
    if (!this.modalOverlay) return;
    this.modalOverlay.style.display = 'none';
    this.isVisible = false;
  }

  public selectTab(tabId: string) {
    this.currentTab = tabId;
    this.modalOverlay?.querySelectorAll('.tut-tab-btn').forEach(b => {
      b.classList.toggle('active', b.getAttribute('data-tab') === tabId);
    });
    this.renderActiveTab();
  }

  public updateTelemetry(telemetry: FullTelemetry) {
    this.lastTelemetry = telemetry;
    if (this.isVisible) {
      this.renderActiveTab();
    }
  }

  private renderActiveTab() {
    const pane = document.getElementById('tutorial-content-pane');
    if (!pane) return;

    switch (this.currentTab) {
      case 'hsi':
        pane.innerHTML = this.getHsiTutorialHtml();
        break;
      case 'rmi':
        pane.innerHTML = this.getRmiTutorialHtml();
        break;
      case 'dme':
        pane.innerHTML = this.getDmeTutorialHtml();
        break;
      case 'ils':
        pane.innerHTML = this.getIlsTutorialHtml();
        break;
      case 'gnss':
        pane.innerHTML = this.getGnssTutorialHtml();
        break;
      case 'arinc':
        pane.innerHTML = this.getArincTutorialHtml();
        break;
      default:
        pane.innerHTML = this.getHsiTutorialHtml();
    }
  }

  // =========================================================================
  // 1. HSI / ND TUTORIAL
  // =========================================================================
  private getHsiTutorialHtml(): string {
    const t = this.lastTelemetry;
    const ac = t?.aircraft;
    const nav1 = t?.nav1;
    const ev = nav1?.evaluation as any;
    const isIls = nav1?.mode === 'ILS';

    // Live interpretation text
    let liveReadout = 'Simulator standby. Start a flight scenario to observe live readouts.';
    if (t && ev) {
      if (isIls) {
        liveReadout = `
          <b>🎯 LIVE ILS STATUS:</b> Tuned to <b>${nav1.station?.name || 'ILS LOC'}</b> (${nav1.station?.frequency || '110.95 MHz'}).
          Inbound runway heading is <b>${(ev.runway_bearing_mag || 236).toFixed(0)}°M</b>.
          The Localizer needle is displaced by <b>${(ev.loc_deflection_dots || 0).toFixed(2)} dots</b>
          (${ev.loc_deflection_dots > 0 ? 'Right of course, steer left' : ev.loc_deflection_dots < 0 ? 'Left of course, steer right' : 'DEAD CENTER ON CENTERLINE'}).
          Glide Path deviation is <b>${(ev.gp_deflection_dots || 0).toFixed(2)} dots</b>
          (${ev.gp_deflection_dots > 0 ? 'Below glide slope, pitch up / power up' : ev.gp_deflection_dots < 0 ? 'Above glide slope, increase sink rate' : 'ON 3.0° GLIDE PATH'}).
        `;
      } else {
        liveReadout = `
          <b>🧭 LIVE VOR STATUS:</b> Tuned to <b>${nav1.station?.name || 'VOR'}</b> (${nav1.station?.frequency || '113.3 MHz'}).
          Selected OBS Course is <b>${nav1.obs_deg.toFixed(0)}°</b>.
          Current computed radial from station: <b>${ev.radial_deg.toFixed(1)}° Magnetic</b>.
          CDI Deflection: <b>${ev.cdi_deflection_dots.toFixed(2)} dots</b>
          (${Math.abs(ev.cdi_deflection_dots) < 0.2 ? 'ON SELECTED RADIAL' : ev.cdi_deflection_dots > 0 ? 'Fly right toward radial' : 'Fly left toward radial'}).
          TO/FROM Flag: <b>${ev.to_from_flag}</b> (${ev.to_from_flag === 'TO' ? 'Flying toward station' : 'Flying away from station on radial'}).
          ${ev.is_in_cone_of_confusion ? '<span class="text-red font-bold">⚠️ OVERHEAD CONE OF CONFUSION: Zenith null active, needle oscillating.</span>' : ''}
        `;
      }
    }

    const hsiDiagramSvg = `
      <div class="tut-diagram-container">
        <div class="tut-diagram-title">
          <span>📐 FIG 1: HORIZONTAL SITUATION INDICATOR (HSI / ND) ANATOMY</span>
          <span style="color:#64748b">ICAO ANNEX 10 & ARINC 407</span>
        </div>
        <svg class="tut-diagram-svg" viewBox="0 0 620 280">
          <defs>
            <linearGradient id="hsiBg" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stop-color="#0b1329" />
              <stop offset="100%" stop-color="#020617" />
            </linearGradient>
          </defs>
          <!-- Instrument Dial Face -->
          <circle cx="160" cy="140" r="115" fill="url(#hsiBg)" stroke="#334155" stroke-width="2"/>
          <circle cx="160" cy="140" r="102" fill="none" stroke="#1e293b" stroke-width="1.5" stroke-dasharray="3,3"/>

          <!-- Compass Cardinal Marks (Heading 360° at top) -->
          <text x="160" y="48" fill="#f8fafc" font-size="12" font-weight="700" font-family="monospace" text-anchor="middle">36</text>
          <text x="252" y="144" fill="#94a3b8" font-size="11" font-weight="700" font-family="monospace" text-anchor="middle">09</text>
          <text x="160" y="238" fill="#94a3b8" font-size="11" font-weight="700" font-family="monospace" text-anchor="middle">18</text>
          <text x="68" y="144" fill="#94a3b8" font-size="11" font-weight="700" font-family="monospace" text-anchor="middle">27</text>

          <!-- Top Lubber Line [1] -->
          <polygon points="160,25 153,37 167,37" fill="#f59e0b" stroke="#78350f" stroke-width="1"/>
          <line x1="160" y1="25" x2="160" y2="40" stroke="#f59e0b" stroke-width="2"/>

          <!-- Heading Bug [6] (Cyan at 040°) -->
          <path d="M 228,82 L 236,74 L 243,82 Z" fill="#38bdf8" stroke="#0284c7" stroke-width="1"/>

          <!-- Selected Course Arrow [2] (Dialed to 030°) -->
          <g transform="rotate(30, 160, 140)">
            <!-- Head -->
            <polygon points="160,42 153,62 167,62" fill="#ec4899" stroke="#9d174d" stroke-width="1"/>
            <line x1="160" y1="62" x2="160" y2="92" stroke="#ec4899" stroke-width="3"/>
            <!-- Tail -->
            <line x1="160" y1="188" x2="160" y2="238" stroke="#ec4899" stroke-width="3"/>

            <!-- 5-Dot CDI Deviation Scale [4] -->
            <circle cx="120" cy="140" r="3" fill="#64748b"/>
            <circle cx="140" cy="140" r="3" fill="#64748b"/>
            <circle cx="160" cy="140" r="2.5" fill="#334155"/>
            <circle cx="180" cy="140" r="3" fill="#64748b"/>
            <circle cx="200" cy="140" r="3" fill="#64748b"/>

            <!-- Deflected CDI Needle [3] (Displaced 1 dot to the right) -->
            <line x1="180" y1="92" x2="180" y2="188" stroke="#ec4899" stroke-width="3.5" stroke-linecap="round"/>

            <!-- TO / FROM Flag [5] (Pointing TO station) -->
            <polygon points="160,118 152,130 168,130" fill="#f8fafc"/>
          </g>

          <!-- Miniature Aircraft Symbol [7] (Center, Fixed) -->
          <circle cx="160" cy="140" r="4" fill="#f8fafc"/>
          <line x1="138" y1="140" x2="182" y2="140" stroke="#f8fafc" stroke-width="2.5" stroke-linecap="round"/>
          <line x1="160" y1="130" x2="160" y2="152" stroke="#f8fafc" stroke-width="2.5" stroke-linecap="round"/>
          <line x1="150" y1="150" x2="170" y2="150" stroke="#f8fafc" stroke-width="2" stroke-linecap="round"/>

          <!-- Callout Leader Lines & Text (Right Side) -->
          <!-- [1] Lubber Line -->
          <line x1="165" y1="28" x2="330" y2="28" stroke="#f59e0b" stroke-width="1" stroke-dasharray="2,2"/>
          <rect x="335" y="18" width="275" height="20" rx="3" fill="#1e1808" stroke="#78350f" stroke-width="1"/>
          <text x="342" y="32" fill="#fbbf24" font-size="10" font-family="monospace" font-weight="700">[1] LUBBER LINE: Current Aircraft Heading (360°M)</text>

          <!-- [2] Course Pointer -->
          <line x1="185" y1="65" x2="330" y2="60" stroke="#ec4899" stroke-width="1" stroke-dasharray="2,2"/>
          <rect x="335" y="50" width="275" height="20" rx="3" fill="#1f0917" stroke="#9d174d" stroke-width="1"/>
          <text x="342" y="64" fill="#f472b6" font-size="10" font-family="monospace" font-weight="700">[2] COURSE ARROW: Selected OBS Track (030° Inbound)</text>

          <!-- [3] CDI Needle -->
          <line x1="195" y1="110" x2="330" y2="92" stroke="#ec4899" stroke-width="1" stroke-dasharray="2,2"/>
          <rect x="335" y="82" width="275" height="20" rx="3" fill="#1f0917" stroke="#9d174d" stroke-width="1"/>
          <text x="342" y="96" fill="#f472b6" font-size="10" font-family="monospace" font-weight="700">[3] CDI BAR: Lateral Deviation (+1.0 Dot Right)</text>

          <!-- [4] 5-Dot Scale -->
          <line x1="205" y1="145" x2="330" y2="124" stroke="#94a3b8" stroke-width="1" stroke-dasharray="2,2"/>
          <rect x="335" y="114" width="275" height="20" rx="3" fill="#0f172a" stroke="#334155" stroke-width="1"/>
          <text x="342" y="128" fill="#cbd5e1" font-size="10" font-family="monospace" font-weight="700">[4] 5-DOT SCALE: 2.0°/dot (VOR) | 0.5°/dot (ILS LOC)</text>

          <!-- [5] TO/FROM Flag -->
          <line x1="172" y1="130" x2="330" y2="156" stroke="#f8fafc" stroke-width="1" stroke-dasharray="2,2"/>
          <rect x="335" y="146" width="275" height="20" rx="3" fill="#0f172a" stroke="#334155" stroke-width="1"/>
          <text x="342" y="160" fill="#f8fafc" font-size="10" font-family="monospace" font-weight="700">[5] TO / FROM ANNUNCIATOR: Triangle points TO station</text>

          <!-- [6] Heading Bug -->
          <line x1="245" y1="80" x2="330" y2="188" stroke="#38bdf8" stroke-width="1" stroke-dasharray="2,2"/>
          <rect x="335" y="178" width="275" height="20" rx="3" fill="#082f49" stroke="#0284c7" stroke-width="1"/>
          <text x="342" y="192" fill="#38bdf8" font-size="10" font-family="monospace" font-weight="700">[6] AUTOPILOT HEADING BUG: Target Command Heading</text>

          <!-- [7] Aircraft Symbol -->
          <line x1="165" y1="150" x2="330" y2="220" stroke="#f8fafc" stroke-width="1" stroke-dasharray="2,2"/>
          <rect x="335" y="210" width="275" height="20" rx="3" fill="#0f172a" stroke="#334155" stroke-width="1"/>
          <text x="342" y="224" fill="#f8fafc" font-size="10" font-family="monospace" font-weight="700">[7] AIRCRAFT SYMBOL: Fixed pictorial cockpit reference</text>
        </svg>
      </div>
    `;

    return `
      <div class="tut-section">
        <div class="tut-live-box">
          <div class="tut-live-header">📡 WHAT THIS DISPLAY IS CURRENTLY TELLING YOU:</div>
          <div class="tut-live-body">${liveReadout}</div>
        </div>

        ${hsiDiagramSvg}

        <div class="tut-grid">
          <div class="tut-col">
            <h3>1. What is an HSI / Navigation Display?</h3>
            <p>
              The <b>Horizontal Situation Indicator (HSI)</b> combines a directional gyro compass with a VHF navigation Course Deviation Indicator (CDI).
              It gives pilots a pictorial, top-down view of where the aircraft is situated relative to a selected radio course or airway.
            </p>

            <h3>2. Key Display Components</h3>
            <ul class="tut-list">
              <li><b>Rotating Compass Rose:</b> Automatically synchronized with aircraft magnetic heading (indicated under the top orange <b>Lubber Line</b>).</li>
              <li><b>Course Pointer (Arrow):</b> Shows the desired magnetic course dialed into the Omnibearing Selector (OBS).</li>
              <li><b>Course Deviation Indicator (CDI) Bar:</b> The movable center section of the course arrow. It moves laterally across 5 calibrated dots.</li>
              <li><b>5-Dot Scale Calibration:</b>
                <ul>
                  <li>In <b>VOR mode</b>: Each dot represents <b>2.0°</b> of angular error (±10° full-scale deflection).</li>
                  <li>In <b>ILS Localizer mode</b>: Each dot represents <b>0.5°</b> of angular error (±2.5° full-scale deflection, 4x more sensitive than VOR!).</li>
                </ul>
              </li>
              <li><b>TO / FROM Indicator:</b> White triangle indicating whether the dialed course will take the aircraft towards (TO) or away from (FROM) the transmitter.</li>
              <li><b>Heading Bug (Cyan notched marker):</b> Set by the autopilot or pilot to select command headings.</li>
            </ul>
          </div>

          <div class="tut-col">
            <h3>3. How VOR Phase Comparison Works (ICAO Annex 10)</h3>
            <p>
              A VHF Omnidirectional Range transmits two 30 Hz signals on the 108–118 MHz band:
            </p>
            <ol class="tut-list-num">
              <li><b>Reference Signal:</b> Omnidirectional 30 Hz FM signal emitted identically in all directions.</li>
              <li><b>Variable Signal:</b> Directional 30 Hz AM signal modulated by a rotating antenna beam (30 revolutions/sec).</li>
            </ol>
            <p>
              At Magnetic North, both signals are perfectly in phase (0°). At East (090°), the variable signal lags by 90°.
              The airborne receiver measures this exact phase difference (Δφ) to determine which <b>radial</b> the aircraft occupies.
            </p>

            <div class="formula-box">
              <div class="formula-main">Radial θ = Phase(Variable AM) − Phase(Reference FM)</div>
              <div class="formula-sub">Δφ = 0° at Magnetic North | Δφ = 90° at East (090°) | Δφ = 180° at South (180°)</div>
              <div class="formula-sub">CDI Dots = (Selected OBS − Current Radial) / 2.0° (clamped to ±5.0 dots)</div>
            </div>

            <div class="tut-tip-box">
              <b>💡 Pilot Technique:</b>
              Always "Fly to the needle". If the CDI needle is to the right of the aircraft symbol, turn right to intercept the course.
              When directly overhead the transmitter, the vertical radiation null causes the <b>Cone of Confusion</b>, where needles swing and the NAV flag momentarily drops.
            </div>
          </div>
        </div>
      </div>
    `;
  }

  // =========================================================================
  // 2. RMI TUTORIAL
  // =========================================================================
  private getRmiTutorialHtml(): string {
    const t = this.lastTelemetry;
    const ac = t?.aircraft;
    const adf = t?.adf1?.evaluation;
    const nav1 = t?.nav1?.evaluation as any;

    let liveReadout = 'Simulator standby. Start a flight scenario to observe live readouts.';
    if (t) {
      liveReadout = `
        <b>📻 LIVE RMI READOUT:</b>
        Aircraft Magnetic Heading: <b>${ac?.magnetic_heading_deg.toFixed(0)}°M</b>.
        <br>• <b>Single Needle (Yellow ADF/NDB):</b> Tuned to <b>${t.adf1.station?.name || 'Clonmel NDB'}</b> (${t.adf1.station?.frequency || '387 kHz'}).
        Relative Bearing: <b>${(adf?.relative_bearing_deg || 0).toFixed(0)}°</b> | Magnetic Bearing (QDM): <b>${(adf?.qdm_magnetic_bearing || 0).toFixed(0)}°M</b>.
        Needle points directly at station.
        <br>• <b>Double Needle (Green VOR):</b> Tuned to <b>${t.nav1.station?.name || 'Shannon DVOR'}</b> (${t.nav1.station?.frequency || '113.3 MHz'}).
        Bearing to station: <b>${(nav1?.magnetic_bearing_to_station || 0).toFixed(0)}°M</b> | Radial: <b>${(nav1?.radial_deg || 0).toFixed(0)}°</b>.
      `;
    }

    const rmiDiagramSvg = `
      <div class="tut-diagram-container">
        <div class="tut-diagram-title">
          <span>📐 FIG 2: RADIO MAGNETIC INDICATOR (RMI) DUAL-NEEDLE ANATOMY</span>
          <span style="color:#64748b">ICAO ANNEX 10 & ARINC 407 (ADF & VOR)</span>
        </div>
        <svg class="tut-diagram-svg" viewBox="0 0 620 280">
          <defs>
            <linearGradient id="rmiBg" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stop-color="#0b1329" />
              <stop offset="100%" stop-color="#020617" />
            </linearGradient>
          </defs>
          <!-- Instrument Dial Face -->
          <circle cx="160" cy="140" r="115" fill="url(#rmiBg)" stroke="#334155" stroke-width="2"/>
          <circle cx="160" cy="140" r="102" fill="none" stroke="#1e293b" stroke-width="1.5" stroke-dasharray="3,3"/>

          <!-- Compass Card Cardinal Marks (Heading 330° at Lubber line) -->
          <text x="160" y="48" fill="#f8fafc" font-size="12" font-weight="700" font-family="monospace" text-anchor="middle">33</text>
          <text x="252" y="144" fill="#94a3b8" font-size="11" font-weight="700" font-family="monospace" text-anchor="middle">06</text>
          <text x="160" y="238" fill="#94a3b8" font-size="11" font-weight="700" font-family="monospace" text-anchor="middle">15</text>
          <text x="68" y="144" fill="#94a3b8" font-size="11" font-weight="700" font-family="monospace" text-anchor="middle">24</text>

          <!-- Top Fixed Lubber Line [1] -->
          <polygon points="160,25 153,37 167,37" fill="#f59e0b" stroke="#78350f" stroke-width="1"/>
          <line x1="160" y1="25" x2="160" y2="40" stroke="#f59e0b" stroke-width="2"/>

          <!-- Single Needle [3] (Yellow ADF/NDB Arrow, pointed at 360° / 30° right of 330°) -->
          <g transform="rotate(30, 160, 140)">
            <polygon points="160,42 154,60 166,60" fill="#eab308" stroke="#854d0e" stroke-width="1"/>
            <line x1="160" y1="60" x2="160" y2="225" stroke="#eab308" stroke-width="2.5"/>
            <line x1="154" y1="225" x2="166" y2="225" stroke="#eab308" stroke-width="2"/>
          </g>

          <!-- Double Needle [4 & 5] (Green VOR Arrow, pointed at 060° / 90° right of 330°) -->
          <g transform="rotate(90, 160, 140)">
            <!-- Head: double arrowhead -->
            <polygon points="160,40 151,58 156,58 160,50 164,58 169,58" fill="#22c55e" stroke="#15803d" stroke-width="1"/>
            <!-- Twin shafts -->
            <line x1="157" y1="58" x2="157" y2="222" stroke="#22c55e" stroke-width="2"/>
            <line x1="163" y1="58" x2="163" y2="222" stroke="#22c55e" stroke-width="2"/>
            <!-- Tail: open fork [5] -->
            <line x1="151" y1="230" x2="157" y2="222" stroke="#22c55e" stroke-width="2"/>
            <line x1="169" y1="230" x2="163" y2="222" stroke="#22c55e" stroke-width="2"/>
          </g>

          <!-- Miniature Aircraft Symbol in center -->
          <circle cx="160" cy="140" r="4" fill="#f8fafc"/>
          <line x1="142" y1="140" x2="178" y2="140" stroke="#f8fafc" stroke-width="2" stroke-linecap="round"/>
          <line x1="160" y1="132" x2="160" y2="150" stroke="#f8fafc" stroke-width="2" stroke-linecap="round"/>

          <!-- Callout Leader Lines & Text (Right Side) -->
          <!-- [1] Lubber Line -->
          <line x1="165" y1="28" x2="330" y2="28" stroke="#f59e0b" stroke-width="1" stroke-dasharray="2,2"/>
          <rect x="335" y="18" width="275" height="20" rx="3" fill="#1e1808" stroke="#78350f" stroke-width="1"/>
          <text x="342" y="32" fill="#fbbf24" font-size="10" font-family="monospace" font-weight="700">[1] LUBBER LINE: Aircraft Magnetic Heading (330°M)</text>

          <!-- [2] Compass Card -->
          <line x1="250" y1="140" x2="330" y2="60" stroke="#94a3b8" stroke-width="1" stroke-dasharray="2,2"/>
          <rect x="335" y="50" width="275" height="20" rx="3" fill="#0f172a" stroke="#334155" stroke-width="1"/>
          <text x="342" y="64" fill="#cbd5e1" font-size="10" font-family="monospace" font-weight="700">[2] COMPASS CARD: Gyro-stabilized 360° rotating card</text>

          <!-- [3] Single Needle -->
          <line x1="175" y1="58" x2="330" y2="92" stroke="#eab308" stroke-width="1" stroke-dasharray="2,2"/>
          <rect x="335" y="82" width="275" height="20" rx="3" fill="#201a05" stroke="#854d0e" stroke-width="1"/>
          <text x="342" y="96" fill="#fde047" font-size="10" font-family="monospace" font-weight="700">[3] SINGLE NEEDLE (YELLOW): ADF/NDB QDM (360°M)</text>

          <!-- [4] Double Needle Tip -->
          <line x1="240" y1="140" x2="330" y2="124" stroke="#22c55e" stroke-width="1" stroke-dasharray="2,2"/>
          <rect x="335" y="114" width="275" height="20" rx="3" fill="#052010" stroke="#15803d" stroke-width="1"/>
          <text x="342" y="128" fill="#4ade80" font-size="10" font-family="monospace" font-weight="700">[4] DOUBLE NEEDLE TIP: VOR QDM (Bearing TO = 060°M)</text>

          <!-- [5] Double Needle Tail -->
          <line x1="80" y1="140" x2="330" y2="156" stroke="#22c55e" stroke-width="1" stroke-dasharray="2,2"/>
          <rect x="335" y="146" width="275" height="20" rx="3" fill="#052010" stroke="#15803d" stroke-width="1"/>
          <text x="342" y="160" fill="#4ade80" font-size="10" font-family="monospace" font-weight="700">[5] DOUBLE NEEDLE TAIL: VOR QDR (Radial FROM = 240°)</text>

          <!-- [6] Relative Bearing -->
          <line x1="170" y1="42" x2="330" y2="188" stroke="#38bdf8" stroke-width="1" stroke-dasharray="2,2"/>
          <rect x="335" y="178" width="275" height="20" rx="3" fill="#082f49" stroke="#0284c7" stroke-width="1"/>
          <text x="342" y="192" fill="#38bdf8" font-size="10" font-family="monospace" font-weight="700">[6] RELATIVE BEARING: Angular offset from aircraft nose</text>

          <!-- [7] Dual Station Intercept -->
          <line x1="160" y1="140" x2="330" y2="220" stroke="#f8fafc" stroke-width="1" stroke-dasharray="2,2"/>
          <rect x="335" y="210" width="275" height="20" rx="3" fill="#0f172a" stroke="#334155" stroke-width="1"/>
          <text x="342" y="224" fill="#f8fafc" font-size="10" font-family="monospace" font-weight="700">[7] CROSS FIX: Crossing needles provide instantaneous fix</text>
        </svg>
      </div>
    `;

    return `
      <div class="tut-section">
        <div class="tut-live-box">
          <div class="tut-live-header">📡 WHAT THIS DISPLAY IS CURRENTLY TELLING YOU:</div>
          <div class="tut-live-body">${liveReadout}</div>
        </div>

        ${rmiDiagramSvg}

        <div class="tut-grid">
          <div class="tut-col">
            <h3>1. What is an RMI (Radio Magnetic Indicator)?</h3>
            <p>
              The <b>Radio Magnetic Indicator (RMI)</b> is a navigational instrument that overlays two independent radio direction pointers
              directly onto a motorized 360° compass card that rotates with aircraft heading.
            </p>

            <h3>2. Understanding the Dual Needles</h3>
            <ul class="tut-list">
              <li><b>Pointer 1 (Single Yellow Arrow):</b> Driven by the <b>Automatic Direction Finder (ADF)</b> tuned to Non-Directional Beacons (NDB).
                The needle tip <i>always points directly to the ground radio station</i>.
              </li>
              <li><b>Pointer 2 (Double Green Arrow):</b> Driven by the <b>VOR Receiver</b>.
                The arrow tip indicates the magnetic bearing <i>to</i> the VOR, while the tail indicates the radial the aircraft is currently on (QDR).
              </li>
              <li><b>Rotating Compass Card:</b> Driven by the aircraft flux gate gyro, meaning needle indications automatically read out in true magnetic bearings with no mental arithmetic!
              </li>
            </ul>
          </div>

          <div class="tut-col">
            <h3>3. Mathematical Relationships (QDM vs QDR)</h3>
            <p>
              The RMI solves the fundamental navigation equations automatically:
            </p>
            <div class="formula-box">
              <div class="formula-main">QDM (Magnetic Inbound Bearing) = Aircraft Heading + Relative Bearing (RB)</div>
              <div class="formula-sub">QDR (Magnetic Outbound Radial) = (QDM ± 180°) mod 360°</div>
              <div class="formula-sub">Relative Bearing (RB) = (QDM − Aircraft Heading + 360°) mod 360°</div>
            </div>

            <h3>4. ADF Loop Antenna Groundwave Physics</h3>
            <p>
              NDBs broadcast LF/MF signals (190–1750 kHz) that travel as groundwaves hugging Earth curvature.
              The airborne receiver uses a crossed ferrite loop antenna to find the signal null combined with a vertical sense antenna to resolve 180° ambiguity, creating a cardioid directional reception pattern.
            </p>

            <div class="tut-tip-box">
              <b>💡 Pilot Technique:</b>
              To fly direct to an NDB, simply turn the aircraft until the single needle points straight up to the lubber line (0° Relative Bearing).
              Cross-fixing: When two needles cross at 90°, you have a precise positive fix!
            </div>
          </div>
        </div>
      </div>
    `;
  }

  // =========================================================================
  // 3. DME TUTORIAL
  // =========================================================================
  private getDmeTutorialHtml(): string {
    const t = this.lastTelemetry;
    const dme = t?.dme1?.evaluation;

    let liveReadout = 'Simulator standby. Start a flight scenario to observe live readouts.';
    if (t && dme) {
      liveReadout = `
        <b>📏 LIVE DME READOUT:</b> Tuned to <b>${t.dme1.station?.name || 'Shannon DME'}</b> (CH ${dme.channel} / ${dme.reply_freq_mhz.toFixed(1)} MHz).
        <br>• <b>Slant Range:</b> <span class="text-cyan font-bold">${dme.slant_range_nm.toFixed(2)} NM</span>
        (Ground Distance: ${dme.ground_dist_nm.toFixed(2)} NM | Altitude Diff: ${dme.altitude_diff_ft.toFixed(0)} ft).
        <br>• <b>Groundspeed Readout:</b> <b>${dme.groundspeed_readout_kts.toFixed(0)} KT</b> | <b>Time to Station:</b> <b>${dme.time_to_station_min.toFixed(1)} MIN</b>.
        <br>• <b>Receiver Status:</b> <span class="badge ${dme.lock_status === 'LOCKED' ? 'badge-green' : 'badge-amber'}">${dme.lock_status}</span>
        (${dme.is_in_los ? 'Within Radio Horizon' : 'Beyond Radio Line-of-Sight'}).
      `;
    }

    const dmeDiagramSvg = `
      <div class="tut-diagram-container">
        <div class="tut-diagram-title">
          <span>📐 FIG 3: DISTANCE MEASURING EQUIPMENT (DME) SLANT-RANGE & TIMING</span>
          <span style="color:#64748b">ICAO ANNEX 10 & ARINC 709 (UHF SECONDARY RADAR)</span>
        </div>
        <svg class="tut-diagram-svg" viewBox="0 0 620 280">
          <defs>
            <linearGradient id="dmeBezel" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stop-color="#1e293b" />
              <stop offset="100%" stop-color="#020617" />
            </linearGradient>
          </defs>

          <!-- Terrain / Ground Baseline -->
          <line x1="40" y1="210" x2="340" y2="210" stroke="#334155" stroke-width="2"/>
          <line x1="40" y1="210" x2="40" y2="215" stroke="#334155" stroke-width="1"/>
          <line x1="340" y1="210" x2="340" y2="215" stroke="#334155" stroke-width="1"/>

          <!-- Ground Station Beacon [2] -->
          <polygon points="60,210 52,175 68,175" fill="#38bdf8" stroke="#0284c7" stroke-width="1"/>
          <rect x="56" y="165" width="8" height="10" fill="#38bdf8"/>
          <circle cx="60" cy="160" r="4" fill="#eab308"/>
          <text x="60" y="228" fill="#38bdf8" font-size="10" font-family="monospace" font-weight="700" text-anchor="middle">VOR/DME STATION</text>
          <text x="60" y="240" fill="#64748b" font-size="9" font-family="monospace" text-anchor="middle">50.0 µs Reply Delay</text>

          <!-- Aircraft Symbol [1] -->
          <g transform="translate(290, 60)">
            <ellipse cx="0" cy="0" rx="14" ry="4" fill="#f8fafc"/>
            <polygon points="-4,-12 0,0 -4,12" fill="#f8fafc"/>
            <rect x="8" y="-6" width="3" height="12" fill="#f8fafc"/>
            <text x="0" y="-12" fill="#f8fafc" font-size="10" font-family="monospace" font-weight="700" text-anchor="middle">AIRCRAFT (FL350)</text>
          </g>

          <!-- Triangle Legs: Altitude Difference Δh [5] -->
          <line x1="290" y1="65" x2="290" y2="210" stroke="#ef4444" stroke-width="2" stroke-dasharray="4,3"/>
          <text x="296" y="145" fill="#f87171" font-size="10" font-family="monospace" font-weight="700">Δh (Alt Diff)</text>

          <!-- Triangle Legs: Ground Distance D_ground [4] -->
          <line x1="60" y1="210" x2="290" y2="210" stroke="#22c55e" stroke-width="2.5"/>
          <text x="175" y="202" fill="#4ade80" font-size="10" font-family="monospace" font-weight="700" text-anchor="middle">D_ground (Horizontal)</text>

          <!-- Hypotenuse: Slant Range R_slant [3] -->
          <line x1="60" y1="160" x2="290" y2="65" stroke="#38bdf8" stroke-width="2.5"/>
          <text x="165" y="100" fill="#38bdf8" font-size="11" font-family="monospace" font-weight="700" transform="rotate(-23, 165, 100)" text-anchor="middle">R_slant (Hypotenuse)</text>

          <!-- Interrogation & Reply Pulses -->
          <text x="145" y="118" fill="#eab308" font-size="8" font-family="monospace" transform="rotate(-23, 145, 118)">>>> 12 µs Pulse Pairs >>></text>
          <text x="180" y="128" fill="#22c55e" font-size="8" font-family="monospace" transform="rotate(-23, 180, 128)"><<< 36 µs Reply Pulse <<<</text>

          <!-- Callout Leader Lines & Text (Right Side) -->
          <!-- [1] Interrogator -->
          <line x1="305" y1="60" x2="350" y2="28" stroke="#f8fafc" stroke-width="1" stroke-dasharray="2,2"/>
          <rect x="355" y="18" width="255" height="20" rx="3" fill="#0f172a" stroke="#334155" stroke-width="1"/>
          <text x="362" y="32" fill="#f8fafc" font-size="10" font-family="monospace" font-weight="700">[1] AIRBORNE INTERROGATOR: Transmits pulse pairs</text>

          <!-- [2] Transponder -->
          <line x1="60" y1="160" x2="350" y2="60" stroke="#38bdf8" stroke-width="1" stroke-dasharray="2,2"/>
          <rect x="355" y="50" width="255" height="20" rx="3" fill="#082f49" stroke="#0284c7" stroke-width="1"/>
          <text x="362" y="64" fill="#38bdf8" font-size="10" font-family="monospace" font-weight="700">[2] GROUND TRANSPONDER: 50.0 µs fixed delay</text>

          <!-- [3] Slant Range -->
          <line x1="190" y1="92" x2="350" y2="92" stroke="#38bdf8" stroke-width="1" stroke-dasharray="2,2"/>
          <rect x="355" y="82" width="255" height="20" rx="3" fill="#082f49" stroke="#0284c7" stroke-width="1"/>
          <text x="362" y="96" fill="#38bdf8" font-size="10" font-family="monospace" font-weight="700">[3] SLANT RANGE: Direct hypotenuse time-of-flight</text>

          <!-- [4] Ground Distance -->
          <line x1="210" y1="210" x2="350" y2="124" stroke="#22c55e" stroke-width="1" stroke-dasharray="2,2"/>
          <rect x="355" y="114" width="255" height="20" rx="3" fill="#052010" stroke="#15803d" stroke-width="1"/>
          <text x="362" y="128" fill="#4ade80" font-size="10" font-family="monospace" font-weight="700">[4] GROUND DISTANCE: True surface horizontal track</text>

          <!-- [5] Altitude Separation -->
          <line x1="290" y1="135" x2="350" y2="156" stroke="#ef4444" stroke-width="1" stroke-dasharray="2,2"/>
          <rect x="355" y="146" width="255" height="20" rx="3" fill="#200508" stroke="#991b1b" stroke-width="1"/>
          <text x="362" y="160" fill="#f87171" font-size="10" font-family="monospace" font-weight="700">[5] ALTITUDE ILLUSION: Reads 6.09 NM at zenith FL370</text>

          <!-- [6] Cockpit Readout Display Bezel -->
          <rect x="355" y="178" width="255" height="52" rx="4" fill="url(#dmeBezel)" stroke="#38bdf8" stroke-width="1.5"/>
          <text x="365" y="196" fill="#64748b" font-size="9" font-family="monospace">DME-1 DIGITAL INDICATOR</text>
          <text x="365" y="218" fill="#38bdf8" font-size="16" font-family="monospace" font-weight="700">14.2<tspan font-size="10" fill="#94a3b8">NM</tspan></text>
          <text x="445" y="218" fill="#f8fafc" font-size="16" font-family="monospace" font-weight="700">280<tspan font-size="10" fill="#94a3b8">KT</tspan></text>
          <text x="525" y="218" fill="#f59e0b" font-size="16" font-family="monospace" font-weight="700">03<tspan font-size="10" fill="#94a3b8">MIN</tspan></text>
          <text x="365" y="244" fill="#94a3b8" font-size="9" font-family="monospace">[6] COCKPIT READOUT: Distance (NM), Speed (KT), Time (MIN)</text>
        </svg>
      </div>
    `;

    return `
      <div class="tut-section">
        <div class="tut-live-box">
          <div class="tut-live-header">📡 WHAT THIS DISPLAY IS CURRENTLY TELLING YOU:</div>
          <div class="tut-live-body">${liveReadout}</div>
        </div>

        ${dmeDiagramSvg}

        <div class="tut-grid">
          <div class="tut-col">
            <h3>1. What is Distance Measuring Equipment (DME)?</h3>
            <p>
              DME is an active UHF secondary radar system operating in the 960–1215 MHz frequency band.
              Unlike passive VOR reception, the airborne aircraft actively <b>interrogates</b> the ground transponder with pulse pairs and listens for the reply.
            </p>

            <h3>2. The Slant-Range Altitude Error</h3>
            <p>
              DME measures the direct hypotenuse distance between the aircraft antenna and the ground antenna.
              This direct distance is called <b>Slant Range (R_slant)</b>:
            </p>
            <div class="formula-box">
              <div class="formula-main">R_slant = √[ D_ground² + (Δh_ft / 6076.115)² ]</div>
              <div class="formula-sub">D_ground = √[ R_slant² − (Δh_ft / 6076.115)² ] (Clamped to 0 when overhead)</div>
            </div>
            <p>
              <b>The Altitude Illusion:</b> If an aircraft is directly overhead a DVOR/DME at FL370 (37,000 ft),
              the ground distance is 0.0 NM, but the DME interrogator reads <b>6.09 NM</b>!
            </p>
          </div>

          <div class="tut-col">
            <h3>3. Pulse-Pair Timing Mechanics (ARINC 709)</h3>
            <ol class="tut-list-num">
              <li><b>Interrogation:</b> Aircraft interrogator transmits Gaussian pulse pairs spaced by 12 µs (X-channel) or 36 µs (Y-channel).</li>
              <li><b>Ground Delay:</b> The ground transponder receives the pulse, delays it by an exact calibrated constant of <b>50.0 µs</b>, and transmits a reply on a frequency paired ±63 MHz apart.</li>
              <li><b>Time of Flight:</b> Total elapsed time Δt minus 50 µs divided by twice the speed of light (c) yields distance (12.36 µs round-trip per nautical mile).</li>
            </ol>

            <div class="formula-box">
              <div class="formula-main">Elapsed Time Δt = 50.0 µs + (12.359 µs/NM × R_slant)</div>
              <div class="formula-sub">Round-trip radar constant: 1 NM = 6076.115 ft = 1852 m → 2 × 1852 / (2.9979 × 10⁸ m/s) = 12.359 µs</div>
            </div>

            <div class="tut-tip-box">
              <b>💡 Velocity & TTS Calculation:</b>
              The airborne processor differentiates distance over time to compute groundspeed (KT) and Time-To-Station (TTS).
              Note that groundspeed is only accurate when flying directly toward or away from the beacon!
            </div>
          </div>
        </div>
      </div>
    `;
  }

  // =========================================================================
  // 4. ILS TUTORIAL
  // =========================================================================
  private getIlsTutorialHtml(): string {
    const t = this.lastTelemetry;
    const ac = t?.aircraft;
    const ev = (t?.nav1?.mode === 'ILS' ? t?.nav1?.evaluation : null) as any;

    let liveReadout = 'Simulator standby. Select Scenario 2 (A320 Shannon Arrival) or tune ISW (110.95 MHz) to observe live precision guidance.';
    if (t && ev) {
      liveReadout = `
        <b>🎯 LIVE PRECISION APPROACH STATUS (RWY ${ev.runway_id}):</b>
        <br>• <b>Localizer Deviation:</b> <b>${(ev.loc_deflection_dots || 0).toFixed(2)} dots</b> (${(ev.loc_ddm || 0).toFixed(4)} DDM).
        ${Math.abs(ev.loc_deflection_dots || 0) < 0.2 ? '<span class="text-green font-bold">LOCKED ON CENTERLINE</span>' : ev.loc_deflection_dots > 0 ? 'Aircraft is RIGHT of centerline (Turn Left)' : 'Aircraft is LEFT of centerline (Turn Right)'}.
        <br>• <b>Glide Path Deviation:</b> <b>${(ev.gp_deflection_dots || 0).toFixed(2)} dots</b> (${(ev.gp_ddm || 0).toFixed(4)} DDM).
        ${Math.abs(ev.gp_deflection_dots || 0) < 0.2 ? '<span class="text-green font-bold">ON 3.0° GLIDE PATH</span>' : ev.gp_deflection_dots > 0 ? 'Aircraft is BELOW path (Fly Up / Pitch Up)' : 'Aircraft is ABOVE path (Fly Down / Reduce Power)'}.
        <br>• <b>Distance to Touchdown:</b> <b>${(ev.dist_to_touchdown_nm || 0).toFixed(2)} NM</b> | Height above threshold: <b>${(ev.height_above_threshold_ft || 0).toFixed(0)} FT</b>.
        <br>• <b>Autoland Guidance:</b> <span class="badge ${ev.autoland_guidance_valid ? 'badge-green' : 'badge-amber'}">${ev.autoland_guidance_valid ? 'CAT II DUAL VALID' : 'APPROACH ARMED'}</span>.
      `;
    }

    const ilsDiagramSvg = `
      <div class="tut-diagram-container">
        <div class="tut-diagram-title">
          <span>📐 FIG 4: INSTRUMENT LANDING SYSTEM (ILS) BEAMS & APPROACH GEOMETRY</span>
          <span style="color:#64748b">ICAO ANNEX 10 (CAT I/II/III LOCALIZER, GLIDE PATH & PAPI)</span>
        </div>
        <svg class="tut-diagram-svg" viewBox="0 0 620 280">
          <defs>
            <linearGradient id="gpBeam" x1="0%" y1="100%" x2="100%" y2="0%">
              <stop offset="0%" stop-color="rgba(56, 189, 248, 0.4)" />
              <stop offset="100%" stop-color="rgba(56, 189, 248, 0.05)" />
            </linearGradient>
            <linearGradient id="pfdBezel" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stop-color="#1e293b" />
              <stop offset="100%" stop-color="#020617" />
            </linearGradient>
          </defs>

          <!-- Ground Baseline -->
          <line x1="30" y1="210" x2="330" y2="210" stroke="#334155" stroke-width="2"/>

          <!-- Runway Asphalt & Markings -->
          <polygon points="50,210 50,216 200,216 200,210" fill="#1e293b" stroke="#475569" stroke-width="1"/>
          <!-- Threshold [6] -->
          <line x1="190" y1="210" x2="190" y2="216" stroke="#f8fafc" stroke-width="2"/>
          <text x="190" y="228" fill="#f8fafc" font-size="9" font-family="monospace" text-anchor="middle">THRESHOLD</text>
          <!-- Touchdown Zone (TDZ) -->
          <rect x="150" y="210" width="16" height="5" fill="#f8fafc"/>
          <text x="150" y="240" fill="#4ade80" font-size="9" font-family="monospace" text-anchor="middle">TDZ (1,200ft)</text>

          <!-- Localizer Antenna [1] at stop end -->
          <polygon points="45,210 40,195 50,195" fill="#f59e0b" stroke="#78350f" stroke-width="1"/>
          <rect x="36" y="190" width="18" height="5" fill="#f59e0b"/>
          <text x="45" y="184" fill="#f59e0b" font-size="8" font-family="monospace" text-anchor="middle">LOC</text>

          <!-- Glide Slope Mast [2] at TDZ -->
          <line x1="150" y1="210" x2="150" y2="185" stroke="#38bdf8" stroke-width="2"/>
          <circle cx="150" cy="185" r="3" fill="#38bdf8"/>
          <text x="150" y="178" fill="#38bdf8" font-size="8" font-family="monospace" text-anchor="middle">GS</text>

          <!-- 3.0° Glide Path Beam [2] -->
          <polygon points="150,210 320,60 320,80" fill="url(#gpBeam)"/>
          <line x1="150" y1="210" x2="320" y2="70" stroke="#38bdf8" stroke-width="2.5" stroke-dasharray="6,3"/>
          <text x="240" y="125" fill="#38bdf8" font-size="10" font-family="monospace" font-weight="700" transform="rotate(-38, 240, 125)">3.0° GLIDE PATH</text>

          <!-- 3,000 ft Intermediate Platform [3] -->
          <line x1="280" y1="70" x2="330" y2="70" stroke="#a855f7" stroke-width="2"/>
          <text x="305" y="62" fill="#c084fc" font-size="9" font-family="monospace" font-weight="700" text-anchor="middle">3,000 ft PLATFORM</text>
          <!-- GS Intercept from Below Arrow -->
          <path d="M 300,75 L 290,75 L 265,95" fill="none" stroke="#22c55e" stroke-width="2" marker-end="url(#arrow)"/>
          <text x="285" y="92" fill="#4ade80" font-size="8" font-family="monospace">Intercept from Below</text>

          <!-- Approaching Aircraft Symbol -->
          <g transform="translate(240, 135) rotate(-10)">
            <ellipse cx="0" cy="0" rx="12" ry="3.5" fill="#f8fafc"/>
            <polygon points="-3,-10 0,0 -3,10" fill="#f8fafc"/>
          </g>

          <!-- Decision Height Gate [5] -->
          <line x1="178" y1="188" x2="178" y2="210" stroke="#ef4444" stroke-width="1.5" stroke-dasharray="2,2"/>
          <text x="178" y="180" fill="#f87171" font-size="8" font-family="monospace" font-weight="700" text-anchor="middle">DH 100ft</text>

          <!-- 4-Box PAPI Array [4] -->
          <g transform="translate(130, 218)">
            <rect x="0" y="0" width="6" height="5" fill="#ffffff" stroke="#334155"/>
            <rect x="8" y="0" width="6" height="5" fill="#ffffff" stroke="#334155"/>
            <rect x="16" y="0" width="6" height="5" fill="#ef4444" stroke="#334155"/>
            <rect x="24" y="0" width="6" height="5" fill="#ef4444" stroke="#334155"/>
            <text x="15" y="14" fill="#cbd5e1" font-size="7" font-family="monospace" text-anchor="middle">PAPI: 2W / 2R</text>
          </g>

          <!-- Callout Leader Lines & Text (Right Side) -->
          <!-- [1] Localizer Array -->
          <line x1="50" y1="190" x2="350" y2="28" stroke="#f59e0b" stroke-width="1" stroke-dasharray="2,2"/>
          <rect x="355" y="18" width="255" height="20" rx="3" fill="#1e1808" stroke="#78350f" stroke-width="1"/>
          <text x="362" y="32" fill="#fbbf24" font-size="10" font-family="monospace" font-weight="700">[1] LOCALIZER ARRAY: VHF 108.1-111.95MHz (±2.5°)</text>

          <!-- [2] Glide Slope Mast -->
          <line x1="155" y1="185" x2="350" y2="60" stroke="#38bdf8" stroke-width="1" stroke-dasharray="2,2"/>
          <rect x="355" y="50" width="255" height="20" rx="3" fill="#082f49" stroke="#0284c7" stroke-width="1"/>
          <text x="362" y="64" fill="#38bdf8" font-size="10" font-family="monospace" font-weight="700">[2] GLIDE SLOPE MAST: UHF 329-335MHz (3.0° Beam)</text>

          <!-- [3] Intermediate Platform -->
          <line x1="310" y1="70" x2="350" y2="92" stroke="#a855f7" stroke-width="1" stroke-dasharray="2,2"/>
          <rect x="355" y="82" width="255" height="20" rx="3" fill="#2e1065" stroke="#7e22ce" stroke-width="1"/>
          <text x="362" y="96" fill="#c084fc" font-size="10" font-family="monospace" font-weight="700">[3] 3,000 FT PLATFORM: Intercept GS from below</text>

          <!-- [4] 4-Unit PAPI -->
          <line x1="165" y1="222" x2="350" y2="124" stroke="#cbd5e1" stroke-width="1" stroke-dasharray="2,2"/>
          <rect x="355" y="114" width="255" height="20" rx="3" fill="#0f172a" stroke="#334155" stroke-width="1"/>
          <text x="362" y="128" fill="#e2e8f0" font-size="10" font-family="monospace" font-weight="700">[4] 4-UNIT PAPI: 2 White / 2 Red on 3.0° slope</text>

          <!-- [5] Decision Height -->
          <line x1="178" y1="195" x2="350" y2="156" stroke="#ef4444" stroke-width="1" stroke-dasharray="2,2"/>
          <rect x="355" y="146" width="255" height="20" rx="3" fill="#200508" stroke="#991b1b" stroke-width="1"/>
          <text x="362" y="160" fill="#f87171" font-size="10" font-family="monospace" font-weight="700">[5] DECISION HEIGHT: 100 ft DH CAT II Go-Around Gate</text>

          <!-- [6] Cockpit PFD Cross-Pointer Bezel -->
          <rect x="355" y="178" width="255" height="56" rx="4" fill="url(#pfdBezel)" stroke="#38bdf8" stroke-width="1.5"/>
          <circle cx="390" cy="206" r="22" fill="#020617" stroke="#334155"/>
          <circle cx="390" cy="206" r="1.5" fill="#f8fafc"/>
          <!-- LOC Needle (Vertical, centered) -->
          <line x1="390" y1="188" x2="390" y2="224" stroke="#ec4899" stroke-width="2"/>
          <!-- GS Needle (Horizontal, centered) -->
          <line x1="372" y1="206" x2="408" y2="206" stroke="#ec4899" stroke-width="2"/>
          <!-- Scale dots -->
          <circle cx="378" cy="206" r="1.5" fill="#64748b"/>
          <circle cx="402" cy="206" r="1.5" fill="#64748b"/>
          <circle cx="390" cy="194" r="1.5" fill="#64748b"/>
          <circle cx="390" cy="218" r="1.5" fill="#64748b"/>
          <text x="425" y="198" fill="#38bdf8" font-size="10" font-family="monospace" font-weight="700">PFD CROSS-POINTER</text>
          <text x="425" y="212" fill="#4ade80" font-size="9" font-family="monospace">LOC: 0.00 | GS: 0.00 DDM</text>
          <text x="425" y="226" fill="#f8fafc" font-size="9" font-family="monospace">CAT II AUTOLAND DUAL</text>
          <text x="365" y="248" fill="#94a3b8" font-size="9" font-family="monospace">[6] PFD CROSS-POINTER: Centered needles confirm touchdown alignment</text>
        </svg>
      </div>
    `;

    return `
      <div class="tut-section">
        <div class="tut-live-box">
          <div class="tut-live-header">📡 WHAT THIS DISPLAY IS CURRENTLY TELLING YOU:</div>
          <div class="tut-live-body">${liveReadout}</div>
        </div>

        ${ilsDiagramSvg}

        <div class="tut-grid">
          <div class="tut-col">
            <h3>1. What is an Instrument Landing System (ILS)?</h3>
            <p>
              An ILS provides highly accurate lateral and vertical guidance to an aircraft approaching a runway,
              permitting safe landings under low-visibility instrument meteorological conditions (CAT I, II, and III).
            </p>

            <h3>2. Localizer (LOC) Modulation Physics (90 Hz vs 150 Hz)</h3>
            <p>
              The Localizer antenna array at the far end of the runway transmits a VHF carrier (108.10–111.95 MHz) with two overlapping antenna radiation patterns:
            </p>
            <ul class="tut-list">
              <li><b>90 Hz Tone:</b> Modulated predominantly on the <b>Left</b> side of the extended runway centerline.</li>
              <li><b>150 Hz Tone:</b> Modulated predominantly on the <b>Right</b> side of the extended runway centerline.</li>
              <li><b>Centerline:</b> The Difference in Depth of Modulation (DDM = |M_90 − M_150|) is exactly zero (0.0000 DDM).</li>
              <li><b>Sensitivity:</b> Full scale (5 dots) is reached at only ±2.5° (0.5°/dot, 4x sharper than VOR).</li>
            </ul>

            <div class="formula-box">
              <div class="formula-main">DDM = |Depth_Mod(90 Hz) − Depth_Mod(150 Hz)|</div>
              <div class="formula-sub">LOC: Centerline = 0.0000 DDM | Full-Scale (5 dots) = ±0.1550 DDM (±2.5°, 0.5°/dot)</div>
              <div class="formula-sub">GS: 3.0° Slope = 0.0000 DDM | Full-Scale (5 dots) = ±0.1750 DDM (±0.7°, 0.14°/dot)</div>
            </div>

            <h3>3. Glide Path (GP) 3.0° Beam Physics</h3>
            <p>
              The Glide Slope mast sits beside the runway Touchdown Zone (~300m past threshold).
              It broadcasts a UHF signal (329–335 MHz) with 90 Hz modulated on top and 150 Hz modulated below.
              The nominal null plane forms a standard <b>3.0° descent slope</b> (0.14°/dot on 5 dots).
            </p>
          </div>

          <div class="tut-col">
            <h3>4. Intercepting from Below & Flying the Path</h3>
            <p>
              In airline operations, aircraft fly level at the intermediate platform altitude (3,000 ft) on the Localizer to <b>intercept the glide slope from BELOW</b>.
              Never descend into a glide slope from above, as this risks false lobes (6° and 9°) and dangerous high sink rates!
            </p>

            <h3>5. 4-Light PAPI Visual Array Guide</h3>
            <ul class="tut-list">
              <li><code>⚪⚪⚪⚪</code> <b>4 White:</b> Too high (&gt; 3.5°).</li>
              <li><code>⚪⚪⚪🔴</code> <b>3 White, 1 Red:</b> Slightly high (3.2° − 3.5°).</li>
              <li><code>⚪⚪🔴🔴</code> <b>2 White, 2 Red:</b> <span class="text-green font-bold">ON GLIDE PATH (2.8° − 3.2°)</span>.</li>
              <li><code>⚪🔴🔴🔴</code> <b>1 White, 3 Red:</b> Slightly low (2.5° − 2.8°).</li>
              <li><code>🔴🔴🔴🔴</code> <b>4 Red:</b> Dangerously low (&lt; 2.5°). Terrain warning!</li>
            </ul>

            <div class="tut-tip-box">
              <b>💡 Decision Height (DH):</b>
              CAT II ILS has a Decision Height of 100 ft Radio Altitude.
              If the runway visual cues are not in sight at 100 ft, the pilot MUST immediately execute a Missed Approach (TO/GA go-around).
            </div>
          </div>
        </div>
      </div>
    `;
  }

  // =========================================================================
  // 5. GNSS TUTORIAL
  // =========================================================================
  private getGnssTutorialHtml(): string {
    const t = this.lastTelemetry;
    const gnss = t?.gnss;

    let liveReadout = 'Simulator standby. Start flight to stream satellite telemetry.';
    if (t && gnss) {
      liveReadout = `
        <b>🛰️ LIVE GNSS CONSTELLATION STATUS:</b>
        <br>• <b>Satellites Tracked:</b> <b>${gnss.satellites_tracked} / ${gnss.satellites_total}</b> (GPS + Galileo multi-constellation).
        <br>• <b>Geometry Dilution of Precision:</b> <b>HDOP: ${gnss.hdop.toFixed(2)}</b> (Horizontal) | <b>VDOP: ${gnss.vdop.toFixed(2)}</b> (Vertical) | <b>PDOP: ${gnss.pdop.toFixed(2)}</b> (3D Position).
        <br>• <b>RAIM Integrity Monitor:</b> <span class="badge ${gnss.raim_status === 'NORMAL' || gnss.raim_status === 'ACTIVE' || gnss.raim_status === 'SBAS_AUGMENTED' ? 'badge-green' : 'badge-amber'}">${gnss.raim_status}</span>
        (HPL: <b>${gnss.hpl_meters.toFixed(1)}m</b> | VPL: <b>${gnss.vpl_meters.toFixed(1)}m</b> vs Alert Limit: <b>${gnss.hpl_meters < 40 ? '25m (LPV)' : '556m (RNP 0.3)'}</b>).
      `;
    }

    const gnssDiagramSvg = `
      <div class="tut-diagram-container">
        <div class="tut-diagram-title">
          <span>📐 FIG 5: GNSS SATELLITE POLAR SKYPLOT & DILUTION OF PRECISION (DOP)</span>
          <span style="color:#64748b">DO-229 / ICAO ANNEX 10 (GPS + GALILEO & RAIM INTEGRITY)</span>
        </div>
        <svg class="tut-diagram-svg" viewBox="0 0 620 280">
          <defs>
            <linearGradient id="skyplotBg" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stop-color="#0b1329" />
              <stop offset="100%" stop-color="#020617" />
            </linearGradient>
          </defs>

          <!-- Polar Skyplot Face -->
          <circle cx="160" cy="140" r="115" fill="url(#skyplotBg)" stroke="#334155" stroke-width="2"/>
          <!-- 30° Elevation Ring (r = 76) [2] -->
          <circle cx="160" cy="140" r="76" fill="none" stroke="#1e293b" stroke-width="1.5" stroke-dasharray="3,3"/>
          <!-- 60° Elevation Ring (r = 38) [2] -->
          <circle cx="160" cy="140" r="38" fill="none" stroke="#1e293b" stroke-width="1.5" stroke-dasharray="3,3"/>
          <!-- Center Zenith Crosshair [3] -->
          <line x1="160" y1="25" x2="160" y2="255" stroke="#1e293b" stroke-width="1"/>
          <line x1="45" y1="140" x2="275" y2="140" stroke="#1e293b" stroke-width="1"/>
          <circle cx="160" cy="140" r="3" fill="#f8fafc"/>

          <!-- Skyplot Cardinal Labels [1] -->
          <text x="160" y="40" fill="#f8fafc" font-size="11" font-weight="700" font-family="monospace" text-anchor="middle">N (0°)</text>
          <text x="262" y="144" fill="#94a3b8" font-size="10" font-weight="700" font-family="monospace" text-anchor="middle">E</text>
          <text x="160" y="250" fill="#94a3b8" font-size="10" font-weight="700" font-family="monospace" text-anchor="middle">S</text>
          <text x="58" y="144" fill="#94a3b8" font-size="10" font-weight="700" font-family="monospace" text-anchor="middle">W</text>
          <text x="160" y="152" fill="#64748b" font-size="8" font-family="monospace" text-anchor="middle">Zenith 90°</text>

          <!-- Satellites Tracked [4] (GPS: Cyan, Galileo: Green, SBAS: Amber) -->
          <!-- GPS G12 -->
          <circle cx="190" cy="85" r="9" fill="#082f49" stroke="#38bdf8" stroke-width="1.5"/>
          <text x="190" y="89" fill="#38bdf8" font-size="8" font-family="monospace" font-weight="700" text-anchor="middle">G12</text>
          <!-- GPS G25 -->
          <circle cx="120" cy="100" r="9" fill="#082f49" stroke="#38bdf8" stroke-width="1.5"/>
          <text x="120" y="104" fill="#38bdf8" font-size="8" font-family="monospace" font-weight="700" text-anchor="middle">G25</text>
          <!-- GPS G07 -->
          <circle cx="150" cy="175" r="9" fill="#082f49" stroke="#38bdf8" stroke-width="1.5"/>
          <text x="150" y="179" fill="#38bdf8" font-size="8" font-family="monospace" font-weight="700" text-anchor="middle">G07</text>
          <!-- Galileo E08 -->
          <circle cx="215" cy="155" r="9" fill="#052010" stroke="#22c55e" stroke-width="1.5"/>
          <text x="215" y="159" fill="#4ade80" font-size="8" font-family="monospace" font-weight="700" text-anchor="middle">E08</text>
          <!-- Galileo E19 -->
          <circle cx="105" cy="165" r="9" fill="#052010" stroke="#22c55e" stroke-width="1.5"/>
          <text x="105" y="169" fill="#4ade80" font-size="8" font-family="monospace" font-weight="700" text-anchor="middle">E19</text>
          <!-- SBAS EGNOS S120 -->
          <circle cx="160" cy="205" r="9" fill="#201a05" stroke="#f59e0b" stroke-width="1.5"/>
          <text x="160" y="209" fill="#fbbf24" font-size="7" font-family="monospace" font-weight="700" text-anchor="middle">S120</text>

          <!-- Callout Leader Lines & Text (Right Side) -->
          <!-- [1] Horizon Ring -->
          <line x1="270" y1="120" x2="350" y2="28" stroke="#94a3b8" stroke-width="1" stroke-dasharray="2,2"/>
          <rect x="355" y="18" width="255" height="20" rx="3" fill="#0f172a" stroke="#334155" stroke-width="1"/>
          <text x="362" y="32" fill="#cbd5e1" font-size="10" font-family="monospace" font-weight="700">[1] OUTER HORIZON CIRCLE: 0° Elevation (5° Mask)</text>

          <!-- [2] Elevation Rings -->
          <line x1="235" y1="140" x2="350" y2="60" stroke="#94a3b8" stroke-width="1" stroke-dasharray="2,2"/>
          <rect x="355" y="50" width="255" height="20" rx="3" fill="#0f172a" stroke="#334155" stroke-width="1"/>
          <text x="362" y="64" fill="#cbd5e1" font-size="10" font-family="monospace" font-weight="700">[2] CONCENTRIC RINGS: 30° and 60° Elevation</text>

          <!-- [3] Zenith -->
          <line x1="165" y1="140" x2="350" y2="92" stroke="#f8fafc" stroke-width="1" stroke-dasharray="2,2"/>
          <rect x="355" y="82" width="255" height="20" rx="3" fill="#0f172a" stroke="#334155" stroke-width="1"/>
          <text x="362" y="96" fill="#f8fafc" font-size="10" font-family="monospace" font-weight="700">[3] CENTER ZENITH: 90° directly overhead aircraft</text>

          <!-- [4] Constellation PRNs -->
          <line x1="200" y1="85" x2="350" y2="124" stroke="#38bdf8" stroke-width="1" stroke-dasharray="2,2"/>
          <rect x="355" y="114" width="255" height="20" rx="3" fill="#082f49" stroke="#0284c7" stroke-width="1"/>
          <text x="362" y="128" fill="#38bdf8" font-size="10" font-family="monospace" font-weight="700">[4] MULTI-CONSTELLATION: GPS (Cyan), Galileo (Green)</text>

          <!-- [5] Dilution of Precision -->
          <line x1="225" y1="160" x2="350" y2="156" stroke="#22c55e" stroke-width="1" stroke-dasharray="2,2"/>
          <rect x="355" y="146" width="255" height="20" rx="3" fill="#052010" stroke="#15803d" stroke-width="1"/>
          <text x="362" y="160" fill="#4ade80" font-size="10" font-family="monospace" font-weight="700">[5] DOP GEOMETRY: HDOP &lt; 1.5, VDOP &lt; 2.0 (Solid)</text>

          <!-- [6] RAIM Integrity Status -->
          <line x1="160" y1="215" x2="350" y2="188" stroke="#f59e0b" stroke-width="1" stroke-dasharray="2,2"/>
          <rect x="355" y="178" width="255" height="52" rx="4" fill="#1e1808" stroke="#f59e0b" stroke-width="1.5"/>
          <text x="365" y="196" fill="#fbbf24" font-size="10" font-family="monospace" font-weight="700">RAIM INTEGRITY MONITOR: ACTIVE</text>
          <text x="365" y="210" fill="#4ade80" font-size="9" font-family="monospace">HPL: 14.2m ≤ HAL: 25.0m (LPV SAFE)</text>
          <text x="365" y="224" fill="#94a3b8" font-size="9" font-family="monospace">Fault Detection &amp; Exclusion: 8 Satellites</text>
          <text x="365" y="244" fill="#94a3b8" font-size="9" font-family="monospace">[6] RAIM INTEGRITY: Continuous autonomous fault exclusion</text>
        </svg>
      </div>
    `;

    return `
      <div class="tut-section">
        <div class="tut-live-box">
          <div class="tut-live-header">📡 WHAT THIS DISPLAY IS CURRENTLY TELLING YOU:</div>
          <div class="tut-live-body">${liveReadout}</div>
        </div>

        ${gnssDiagramSvg}

        <div class="tut-grid">
          <div class="tut-col">
            <h3>1. What is the GNSS Polar Skyplot?</h3>
            <p>
              The Polar Skyplot displays all orbiting navigation satellites (GPS NAVSTAR and European Galileo) in view above the local horizon.
              Azimuth is shown around the perimeter (0° North to 360°), and elevation is plotted radially from the horizon (0°) to zenith (90° directly overhead).
            </p>

            <h3>2. Geometric Dilution of Precision (DOP)</h3>
            <p>
              Positioning accuracy depends on satellite geometry across the sky.
              If all satellites are bunched together, small timing errors cause huge position uncertainty.
              DOP is derived from the covariance matrix Q = (Gᵀ · G)⁻¹:
            </p>
            <div class="formula-box">
              <div class="formula-main">DOP Covariance Matrix: Q = (Gᵀ · G)⁻¹</div>
              <div class="formula-sub">PDOP = √(σ_x² + σ_y² + σ_z²) | HDOP = √(σ_x² + σ_y²) | VDOP = σ_z</div>
              <div class="formula-sub">Integrity Gate: Horizontal Protection Level (HPL) ≤ Horizontal Alert Limit (HAL)</div>
            </div>
            <ul class="tut-list">
              <li><b>HDOP &lt; 1.5:</b> Excellent horizontal geometry.</li>
              <li><b>VDOP &lt; 2.0:</b> Solid vertical triangulation.</li>
              <li><b>PDOP &lt; 3.0:</b> High 3D positioning integrity.</li>
            </ul>
          </div>

          <div class="tut-col">
            <h3>3. Receiver Autonomous Integrity Monitoring (RAIM)</h3>
            <p>
              Civil aviation cannot rely on unmonitored GPS signals because a clock drift in a single satellite could silently introduce a lethal 1-mile position error.
            </p>
            <ul class="tut-list">
              <li><b>Fault Detection (5 satellites):</b> Cross-checks pseudoranges from 5 satellites to detect if any single satellite is malfunctioning.</li>
              <li><b>Fault Exclusion (6 satellites):</b> Isolates and removes the corrupt satellite from the navigation solution.</li>
              <li><b>Protection Levels (HPL vs HAL):</b> The <b>Horizontal Protection Level (HPL)</b> is the statistical bound containing the aircraft.
                If HPL exceeds the published <b>Horizontal Alert Limit (HAL)</b>, RAIM issues an integrity warning and the approach must be aborted!
              </li>
            </ul>
          </div>
        </div>
      </div>
    `;
  }

  // =========================================================================
  // 6. ARINC 429 TUTORIAL
  // =========================================================================
  private getArincTutorialHtml(): string {
    const t = this.lastTelemetry;
    const words = t?.arinc429_bus || [];

    let liveReadout = 'Simulator standby. Start flight to view live ARINC 429 bus words.';
    if (words.length > 0) {
      liveReadout = `
        <b>⚡ LIVE ARINC 429 DIGITAL BUS ACTIVITY:</b> Streaming <b>${words.length} active words</b> across low/high-speed bipolar channels.
        <br>• <b>Label 212 (VOR Bearing):</b> 0x${words.find(w => w.label_octal === '212')?.raw_hex || 'N/A'} -> ${words.find(w => w.label_octal === '212')?.decoded_value || '0'}°
        <br>• <b>Label 037 (DME Distance):</b> 0x${words.find(w => w.label_octal === '037')?.raw_hex || 'N/A'} -> ${words.find(w => w.label_octal === '037')?.decoded_value || '0'} NM
        <br>• <b>Label 173 (LOC Deviation):</b> 0x${words.find(w => w.label_octal === '173')?.raw_hex || 'N/A'} -> ${words.find(w => w.label_octal === '173')?.decoded_value || '0'} DDM
        <br>• <b>Label 174 (GS Deviation):</b> 0x${words.find(w => w.label_octal === '174')?.raw_hex || 'N/A'} -> ${words.find(w => w.label_octal === '174')?.decoded_value || '0'} DDM
      `;
    }

    const arincDiagramSvg = `
      <div class="tut-diagram-container">
        <div class="tut-diagram-title">
          <span>📐 FIG 6: ARINC 429 32-BIT WORD ARCHITECTURE & BIPOLAR RZ SIGNAL</span>
          <span style="color:#64748b">ARINC 429 SPECIFICATION (AIRBUS A320 & BOEING 737 DIGITAL AVIONICS)</span>
        </div>
        <svg class="tut-diagram-svg" viewBox="0 0 620 280">
          <!-- 32-Bit Word Box Strip -->
          <g transform="translate(10, 20)">
            <!-- Header Label -->
            <text x="0" y="-6" fill="#94a3b8" font-size="9" font-family="monospace">ARINC 429 32-BIT SERIAL FRAME (TRANSMITTED LSB TO MSB):</text>

            <!-- Bits 1-8: Label [1] -->
            <rect x="0" y="0" width="140" height="38" fill="#082f49" stroke="#38bdf8" stroke-width="1.5" rx="3"/>
            <text x="70" y="16" fill="#38bdf8" font-size="10" font-family="monospace" font-weight="700" text-anchor="middle">BITS 1–8: LABEL</text>
            <text x="70" y="30" fill="#94a3b8" font-size="9" font-family="monospace" text-anchor="middle">Octal (e.g. 212 VOR)</text>

            <!-- Bits 9-10: SDI [2] -->
            <rect x="145" y="0" width="60" height="38" fill="#1e1808" stroke="#f59e0b" stroke-width="1.5" rx="3"/>
            <text x="175" y="16" fill="#fbbf24" font-size="10" font-family="monospace" font-weight="700" text-anchor="middle">9–10: SDI</text>
            <text x="175" y="30" fill="#94a3b8" font-size="9" font-family="monospace" text-anchor="middle">Source/Dest</text>

            <!-- Bits 11-29: Data Payload [3] -->
            <rect x="210" y="0" width="240" height="38" fill="#052010" stroke="#22c55e" stroke-width="1.5" rx="3"/>
            <text x="330" y="16" fill="#4ade80" font-size="10" font-family="monospace" font-weight="700" text-anchor="middle">BITS 11–29: DATA PAYLOAD</text>
            <text x="330" y="30" fill="#94a3b8" font-size="9" font-family="monospace" text-anchor="middle">19-Bit BNR (Binary) / BCD Payload</text>

            <!-- Bits 30-31: SSM [4] -->
            <rect x="455" y="0" width="85" height="38" fill="#2e1065" stroke="#a855f7" stroke-width="1.5" rx="3"/>
            <text x="497" y="16" fill="#c084fc" font-size="10" font-family="monospace" font-weight="700" text-anchor="middle">30–31: SSM</text>
            <text x="497" y="30" fill="#94a3b8" font-size="9" font-family="monospace" text-anchor="middle">Status Matrix</text>

            <!-- Bit 32: Parity [5] -->
            <rect x="545" y="0" width="55" height="38" fill="#200508" stroke="#ef4444" stroke-width="1.5" rx="3"/>
            <text x="572" y="16" fill="#f87171" font-size="10" font-family="monospace" font-weight="700" text-anchor="middle">32: P</text>
            <text x="572" y="30" fill="#94a3b8" font-size="9" font-family="monospace" text-anchor="middle">Odd Parity</text>
          </g>

          <!-- Waveform Section [6]: Bipolar Return-to-Zero (RZ) -->
          <g transform="translate(10, 95)">
            <text x="0" y="-8" fill="#94a3b8" font-size="9" font-family="monospace">BIPOLAR RETURN-TO-ZERO (RZ) ELECTRICAL WAVEFORM (+10V / 0V / −10V):</text>

            <!-- Voltage Reference Rails -->
            <line x1="0" y1="10" x2="600" y2="10" stroke="#334155" stroke-width="1" stroke-dasharray="2,3"/>
            <text x="605" y="13" fill="#64748b" font-size="8" font-family="monospace">+10V (HI)</text>

            <line x1="0" y1="35" x2="600" y2="35" stroke="#475569" stroke-width="1.5"/>
            <text x="605" y="38" fill="#94a3b8" font-size="8" font-family="monospace">0V (NULL)</text>

            <line x1="0" y1="60" x2="600" y2="60" stroke="#334155" stroke-width="1" stroke-dasharray="2,3"/>
            <text x="605" y="63" fill="#64748b" font-size="8" font-family="monospace">-10V (LO)</text>

            <!-- Bipolar RZ Pulse Train: Logic '1', Logic '0', Logic '1', NULL -->
            <!-- Bit 1 = '1': Pulse to +10V then return to 0V -->
            <path d="M 0,35 L 20,35 L 20,10 L 50,10 L 50,35 L 80,35" fill="none" stroke="#38bdf8" stroke-width="2.5"/>
            <text x="50" y="28" fill="#38bdf8" font-size="9" font-family="monospace" font-weight="700" text-anchor="middle">Bit='1'</text>

            <!-- Bit 2 = '0': Pulse to -10V then return to 0V -->
            <path d="M 80,35 L 100,35 L 100,60 L 130,60 L 130,35 L 160,35" fill="none" stroke="#f59e0b" stroke-width="2.5"/>
            <text x="130" y="52" fill="#fbbf24" font-size="9" font-family="monospace" font-weight="700" text-anchor="middle">Bit='0'</text>

            <!-- Bit 3 = '1': Pulse to +10V then return to 0V -->
            <path d="M 160,35 L 180,35 L 180,10 L 210,10 L 210,35 L 240,35" fill="none" stroke="#38bdf8" stroke-width="2.5"/>
            <text x="210" y="28" fill="#38bdf8" font-size="9" font-family="monospace" font-weight="700" text-anchor="middle">Bit='1'</text>

            <!-- Bit 4 = '0': Pulse to -10V then return to 0V -->
            <path d="M 240,35 L 260,35 L 260,60 L 290,60 L 290,35 L 320,35" fill="none" stroke="#f59e0b" stroke-width="2.5"/>
            <text x="290" y="52" fill="#fbbf24" font-size="9" font-family="monospace" font-weight="700" text-anchor="middle">Bit='0'</text>

            <!-- Word Gap / Null -->
            <line x1="320" y1="35" x2="400" y2="35" stroke="#22c55e" stroke-width="2.5"/>
            <text x="360" y="30" fill="#4ade80" font-size="8" font-family="monospace" text-anchor="middle">&gt;= 4-Bit Inter-Word Gap</text>
          </g>

          <!-- Callout Grid & Summary (Bottom) -->
          <g transform="translate(10, 185)">
            <rect x="0" y="0" width="195" height="42" rx="3" fill="#082f49" stroke="#0284c7" stroke-width="1"/>
            <text x="8" y="16" fill="#38bdf8" font-size="9" font-family="monospace" font-weight="700">[1-2] BITS 1-10: IDENT &amp; ROUTE</text>
            <text x="8" y="30" fill="#cbd5e1" font-size="8" font-family="monospace">Octal Label + Source/Dest SDI</text>

            <rect x="202" y="0" width="195" height="42" rx="3" fill="#052010" stroke="#15803d" stroke-width="1"/>
            <text x="210" y="16" fill="#4ade80" font-size="9" font-family="monospace" font-weight="700">[3] BITS 11-29: DATA PAYLOAD</text>
            <text x="210" y="30" fill="#cbd5e1" font-size="8" font-family="monospace">19-bit Two's Complement BNR/BCD</text>

            <rect x="405" y="0" width="195" height="42" rx="3" fill="#200508" stroke="#991b1b" stroke-width="1"/>
            <text x="413" y="16" fill="#f87171" font-size="9" font-family="monospace" font-weight="700">[4-5] BITS 30-32: STATUS &amp; PARITY</text>
            <text x="413" y="30" fill="#cbd5e1" font-size="8" font-family="monospace">SSM Matrix + Odd Parity Bit</text>

            <text x="0" y="58" fill="#94a3b8" font-size="9" font-family="monospace">[6] BIPOLAR RZ SIGNAL: High Speed = 100 kbps (10 µs/bit) | Low Speed = 12.5 kbps (80 µs/bit)</text>
          </g>
        </svg>
      </div>
    `;

    return `
      <div class="tut-section">
        <div class="tut-live-box">
          <div class="tut-live-header">📡 WHAT THIS DISPLAY IS CURRENTLY TELLING YOU:</div>
          <div class="tut-live-body">${liveReadout}</div>
        </div>

        ${arincDiagramSvg}

        <div class="tut-grid">
          <div class="tut-col">
            <h3>1. What is the ARINC 429 Digital Avionics Bus?</h3>
            <p>
              <b>ARINC Specification 429</b> is the dominant commercial avionics data bus standard (Boeing 737/777, Airbus A320/A330).
              It transmits 32-bit digital words over shielded twisted-pair cables using bipolar Return-to-Zero (RZ) modulation at 100 kbps (high-speed) or 12.5 kbps (low-speed).
            </p>

            <div class="formula-box">
              <div class="formula-main">Bus Speed: High = 100 kbps (10 µs/bit) | Low = 12.5 kbps (80 µs/bit)</div>
              <div class="formula-sub">Odd Parity Check: [ ∑(Bit 1 .. Bit 32) ] mod 2 ≡ 1 (Odd, noise rejection)</div>
            </div>

            <h3>2. 32-Bit Word Architecture</h3>
            <table class="tut-table">
              <thead>
                <tr><th>Bits</th><th>Name</th><th>Function</th></tr>
              </thead>
              <tbody>
                <tr><td>1–8</td><td><b>Label (Octal)</b></td><td>Identifies data parameter (e.g. 212 = VOR, 037 = DME). Transmitted bit-reversed (MSB first).</td></tr>
                <tr><td>9–10</td><td><b>SDI</b></td><td>Source/Destination Identifier (00 = All, 01 = Radio 1, 10 = Radio 2).</td></tr>
                <tr><td>11–29</td><td><b>Data Field</b></td><td>19 bits of parameter payload in two's complement BNR (binary) or BCD (decimal).</td></tr>
                <tr><td>30–31</td><td><b>SSM</b></td><td>Sign/Status Matrix (00 = Failure Warning, 01 = No Computed Data, 11 = Normal Operation).</td></tr>
                <tr><td>32</td><td><b>Parity (P)</b></td><td>Odd parity bit ensures total number of '1' bits in word is always odd.</td></tr>
              </tbody>
            </table>
          </div>

          <div class="tut-col">
            <h3>3. Standard Aeronautical Labels in IFR Airspace</h3>
            <ul class="tut-list">
              <li><b>Label 212 (Octal):</b> VOR Omnibearing course angle (0.0° to 359.9°).</li>
              <li><b>Label 037 (Octal):</b> DME slant range distance (0.00 to 256.0 NM).</li>
              <li><b>Label 173 (Octal):</b> ILS Localizer angular deviation (microamperes / DDM).</li>
              <li><b>Label 174 (Octal):</b> ILS Glide Slope angular deviation (microamperes / DDM).</li>
              <li><b>Label 162 (Octal):</b> ADF Relative bearing from aircraft heading.</li>
              <li><b>Label 310 / 311:</b> GNSS Latitude and Longitude coordinates.</li>
            </ul>

            <div class="tut-tip-box">
              <b>💡 Parity Verification:</b>
              Every receiver counts the number of 1s in the received 32 bits. If the sum is even, the word is immediately rejected as noise or bus corrupt!
            </div>
          </div>
        </div>
      </div>
    `;
  }
}
