/**
 * Scenario Controller & Cockpit Flight Deck Controls.
 * Manages scenario selection, timeline scrubbing, simulation speed,
 * flight phase briefings, and manual autopilot overrides.
 *
 * Implements persistent DOM updates to prevent tearing down form inputs and dropdowns
 * on high-frequency (10 Hz) telemetry refreshes.
 */

import { ScenarioState, FullTelemetry } from '../types';
import { api } from '../api';

export class ScenarioControlView {
  private container: HTMLElement;
  private currentScenarioId: string = '';
  private isInitialized: boolean = false;
  private isUserScrubbing: boolean = false;
  private lastTelemetry: FullTelemetry | null = null;
  private lastScenario: ScenarioState | null = null;

  constructor(container: HTMLElement) {
    this.container = container;
  }

  public render(scenario: ScenarioState, telemetry: FullTelemetry) {
    this.lastScenario = scenario;
    this.lastTelemetry = telemetry;

    // If scenario changed or not initialized, build the DOM structure
    if (!this.isInitialized || this.currentScenarioId !== scenario.id) {
      this.currentScenarioId = scenario.id;
      this.buildDom(scenario, telemetry);
      this.attachEventListeners();
      this.isInitialized = true;
    }

    // Perform targeted DOM updates without destroying input focus
    this.updateDom(scenario, telemetry);
  }

  private buildDom(scenario: ScenarioState, telemetry: FullTelemetry) {
    const ac = telemetry.aircraft;
    const progressFrac = scenario.total_waypoints > 1
      ? scenario.current_waypoint_index / (scenario.total_waypoints - 1)
      : 0;

    this.container.innerHTML = `
      <div class="control-deck-container">
        <!-- 1. Scenario Selector Tabs -->
        <div class="scenario-selector-cards">
          <div class="scenario-card ${scenario.id === 'long_haul_overflight' ? 'active-card' : ''}" data-id="long_haul_overflight">
            <div class="sc-badge">FL370 CRUISE</div>
            <div class="sc-title">1. Transatlantic Overflight</div>
            <div class="sc-route">GISTI &rarr; SHA &rarr; DUB &rarr; LIPGO</div>
            <div class="sc-desc">Heavy B77W overflying Shannon UIR. High-altitude VOR/DME geometry & oceanic transition.</div>
          </div>

          <div class="scenario-card ${scenario.id === 'a320_shannon_arrival' ? 'active-card' : ''}" data-id="a320_shannon_arrival">
            <div class="sc-badge badge-purple">CAT II ILS RWY 24</div>
            <div class="sc-title">2. A320 Shannon Arrival</div>
            <div class="sc-route">SLANY &rarr; TIPUR &rarr; Shannon ILS 24</div>
            <div class="sc-desc">Airbus arrival from UK. Enroute VOR/NDB to terminal localizer and 3.0° glideslope capture.</div>
          </div>

          <div class="scenario-card ${scenario.id === 'city_hopper_dub_snn' ? 'active-card' : ''}" data-id="city_hopper_dub_snn">
            <div class="sc-badge badge-green">FL160 REGIONAL</div>
            <div class="sc-title">3. Dublin to Shannon Hopper</div>
            <div class="sc-route">EIDW (28L) &rarr; WTP &rarr; EINN (06)</div>
            <div class="sc-desc">Midlands domestic flight. Slant range errors, Wolftrap DME, and CAT I ILS RWY 06 approach.</div>
          </div>
        </div>

        <!-- 2. Simulation Playback Controls -->
        <div class="playback-controls-bar">
          <div class="playback-btn-group">
            <button class="btn-ctrl btn-play" id="btn-toggle-play">
              ${scenario.is_running ? '⏸ PAUSE' : '▶ PLAY'}
            </button>
            <button class="btn-ctrl" id="btn-step">⏯ STEP</button>
            <button class="btn-ctrl" id="btn-reset">↺ RESET</button>
          </div>

          <!-- Speed Multipliers -->
          <div class="speed-btn-group">
            <span class="speed-label">SPEED:</span>
            ${[1, 2, 5, 10, 25, 50].map(s => `
              <button class="btn-speed ${scenario.speed_multiplier === s ? 'active-speed' : ''}" data-speed="${s}">${s}x</button>
            `).join('')}
          </div>

          <!-- Timeline Scrubber -->
          <div class="timeline-scrubber-box">
            <span class="timeline-time" id="ctrl-elapsed-time">${(scenario.elapsed_time_sec / 60).toFixed(1)}m elapsed</span>
            <input type="range" min="0" max="1" step="0.005" value="${progressFrac}" class="timeline-slider" id="scenario-timeline-slider" />
            <span class="timeline-wp" id="ctrl-target-wp">WP: <b>${scenario.target_waypoint_name}</b> (${scenario.current_waypoint_index + 1}/${scenario.total_waypoints})</span>
          </div>
        </div>

        <!-- 3. Active Flight Briefing & Waypoint Note -->
        <div class="briefing-banner" id="briefing-banner">
          <div class="briefing-phase-tag" id="ctrl-phase-tag">${ac.flight_phase}</div>
          <div class="briefing-text" id="ctrl-briefing-text">
            <b>Target: ${scenario.target_waypoint_name}:</b> ${scenario.target_waypoint_note}
          </div>
        </div>

        <!-- 4. Autopilot & Radio Tuning Override Deck -->
        <div class="cockpit-overrides-bar">
          <div class="override-cell">
            <label>VOR1 OBS (°)</label>
            <div class="input-with-btns">
              <button class="btn-dial" id="obs-minus-10">-10</button>
              <button class="btn-dial" id="obs-minus-1">-1</button>
              <input type="number" id="obs-input" min="0" max="359" value="${telemetry.nav1.obs_deg.toFixed(0)}" />
              <button class="btn-dial" id="obs-plus-1">+1</button>
              <button class="btn-dial" id="obs-plus-10">+10</button>
            </div>
          </div>

          <div class="override-cell">
            <label>HDG BUG (°)</label>
            <div class="input-with-btns">
              <button class="btn-dial" id="hdg-minus-10">-10</button>
              <input type="number" id="hdg-input" min="0" max="359" value="${ac.magnetic_heading_deg.toFixed(0)}" />
              <button class="btn-dial" id="hdg-plus-10">+10</button>
            </div>
          </div>

          <div class="override-cell">
            <label>TARGET ALT (FT)</label>
            <input type="number" id="alt-input" step="500" value="${ac.altitude_ft.toFixed(0)}" />
          </div>

          <div class="override-cell">
            <label>SPEED (KTS)</label>
            <input type="number" id="spd-input" step="10" value="${ac.groundspeed_kts.toFixed(0)}" />
          </div>

          <div class="override-cell" style="min-width: 240px;">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 2px;">
              <label>MANUAL TUNE NAV1</label>
              <span id="tune-status-badge" class="badge ${scenario.manual_tune_overridden ? 'badge-amber' : 'badge-green'}">
                ${scenario.manual_tune_overridden ? 'MANUAL' : 'AUTO (FPL)'}
              </span>
            </div>
            <div style="display: flex; gap: 4px;">
              <select id="quick-tune-select" style="flex: 1;">
                <option value="">-- Tune Radio Station --</option>
                <option value="SHA">SHA DVOR/DME (113.3 MHz)</option>
                <option value="ISW">EINN ILS 24 LOC (110.95 MHz)</option>
                <option value="ISE">EINN ILS 06 LOC (109.5 MHz)</option>
                <option value="DUB">DUB DVOR/DME (114.9 MHz)</option>
                <option value="DAP">DAP DVOR/DME (111.2 MHz)</option>
                <option value="BAL">BAL DVOR/DME (115.8 MHz)</option>
                <option value="WTP">WTP DME (116.3 MHz)</option>
                <option value="CRK">CRK DVOR/DME (114.6 MHz)</option>
              </select>
              <button class="btn-xs" id="btn-re-autotune" title="Restore Flight Plan Auto-Tuning" style="${scenario.manual_tune_overridden ? '' : 'display:none;'}">↺ AUTO</button>
            </div>
          </div>
        </div>
      </div>
    `;
  }

  private updateDom(scenario: ScenarioState, telemetry: FullTelemetry) {
    const ac = telemetry.aircraft;

    // 1. Play / Pause Button Text
    const btnPlay = this.container.querySelector('#btn-toggle-play');
    if (btnPlay) {
      btnPlay.textContent = scenario.is_running ? '⏸ PAUSE' : '▶ PLAY';
    }

    // 2. Active Scenario Card highlight
    this.container.querySelectorAll('.scenario-card').forEach(card => {
      const cardId = card.getAttribute('data-id');
      card.classList.toggle('active-card', cardId === scenario.id);
    });

    // 3. Speed button highlight
    this.container.querySelectorAll('.btn-speed').forEach(btn => {
      const spd = parseFloat(btn.getAttribute('data-speed') || '1');
      btn.classList.toggle('active-speed', spd === scenario.speed_multiplier);
    });

    // 4. Timeline
    const timeEl = this.container.querySelector('#ctrl-elapsed-time');
    if (timeEl) {
      timeEl.textContent = `${(scenario.elapsed_time_sec / 60).toFixed(1)}m elapsed`;
    }

    const slider = this.container.querySelector('#scenario-timeline-slider') as HTMLInputElement;
    if (slider && !this.isUserScrubbing) {
      const progressFrac = scenario.total_waypoints > 1
        ? scenario.current_waypoint_index / (scenario.total_waypoints - 1)
        : 0;
      slider.value = progressFrac.toString();
    }

    const wpEl = this.container.querySelector('#ctrl-target-wp');
    if (wpEl) {
      wpEl.innerHTML = `WP: <b>${scenario.target_waypoint_name}</b> (${scenario.current_waypoint_index + 1}/${scenario.total_waypoints})`;
    }

    // 5. Briefing Banner
    const phaseEl = this.container.querySelector('#ctrl-phase-tag');
    if (phaseEl) {
      phaseEl.textContent = ac.flight_phase;
    }

    const briefingEl = this.container.querySelector('#ctrl-briefing-text');
    if (briefingEl) {
      briefingEl.innerHTML = `<b>Target: ${scenario.target_waypoint_name}:</b> ${scenario.target_waypoint_note}`;
    }

    // 6. Non-focused form fields
    const obsInput = this.container.querySelector('#obs-input') as HTMLInputElement;
    if (obsInput && document.activeElement !== obsInput) {
      obsInput.value = telemetry.nav1.obs_deg.toFixed(0);
    }

    const hdgInput = this.container.querySelector('#hdg-input') as HTMLInputElement;
    if (hdgInput && document.activeElement !== hdgInput) {
      hdgInput.value = ac.magnetic_heading_deg.toFixed(0);
    }

    const altInput = this.container.querySelector('#alt-input') as HTMLInputElement;
    if (altInput && document.activeElement !== altInput) {
      altInput.value = ac.altitude_ft.toFixed(0);
    }

    const spdInput = this.container.querySelector('#spd-input') as HTMLInputElement;
    if (spdInput && document.activeElement !== spdInput) {
      spdInput.value = ac.groundspeed_kts.toFixed(0);
    }

    // 7. Tune Status & Auto-Tune button
    const tuneBadge = this.container.querySelector('#tune-status-badge');
    const btnAuto = this.container.querySelector('#btn-re-autotune') as HTMLElement;
    const quickSelect = this.container.querySelector('#quick-tune-select') as HTMLSelectElement;
    if (tuneBadge) {
      tuneBadge.className = `badge ${scenario.manual_tune_overridden ? 'badge-amber' : 'badge-green'}`;
      tuneBadge.textContent = scenario.manual_tune_overridden ? 'MANUAL' : 'AUTO (FPL)';
    }
    if (btnAuto) {
      btnAuto.style.display = scenario.manual_tune_overridden ? 'inline-block' : 'none';
    }
    if (quickSelect && document.activeElement !== quickSelect) {
      const currentStationId = telemetry.nav1.station?.id || '';
      if (quickSelect.value !== currentStationId) {
        quickSelect.value = currentStationId;
      }
    }
  }

  private attachEventListeners() {
    // Scenario cards click
    this.container.querySelectorAll('.scenario-card').forEach(card => {
      card.addEventListener('click', (e) => {
        const id = (e.currentTarget as HTMLElement).getAttribute('data-id');
        if (id && id !== this.currentScenarioId) {
          api.selectScenario(id);
        }
      });
    });

    // Play / Pause
    this.container.querySelector('#btn-toggle-play')?.addEventListener('click', () => {
      const isRunning = this.lastScenario?.is_running || false;
      api.controlSim(isRunning ? 'pause' : 'play');
    });

    // Step
    this.container.querySelector('#btn-step')?.addEventListener('click', () => {
      api.controlSim('step');
    });

    // Reset
    this.container.querySelector('#btn-reset')?.addEventListener('click', () => {
      api.controlSim('reset');
    });

    // Speed multiplier buttons
    this.container.querySelectorAll('.btn-speed').forEach(btn => {
      btn.addEventListener('click', (e) => {
        const speed = parseFloat((e.currentTarget as HTMLElement).getAttribute('data-speed') || '1');
        api.controlSim('set_speed', speed);
      });
    });

    // Scrubber
    const slider = this.container.querySelector('#scenario-timeline-slider') as HTMLInputElement;
    if (slider) {
      slider.addEventListener('mousedown', () => { this.isUserScrubbing = true; });
      slider.addEventListener('touchstart', () => { this.isUserScrubbing = true; });
      slider.addEventListener('change', () => {
        this.isUserScrubbing = false;
        const frac = parseFloat(slider.value);
        api.controlSim('seek', undefined, frac);
      });
      slider.addEventListener('mouseup', () => { this.isUserScrubbing = false; });
      slider.addEventListener('touchend', () => { this.isUserScrubbing = false; });
    }

    // OBS adjustments
    const obsInput = this.container.querySelector('#obs-input') as HTMLInputElement;
    const updateObs = (delta: number) => {
      let cur = parseFloat(obsInput?.value || '0');
      cur = (cur + delta + 360) % 360;
      if (obsInput) obsInput.value = cur.toFixed(0);
      const stationId = this.lastTelemetry?.nav1.station?.id || 'SHA';
      api.tuneAvionics('nav1', stationId, cur);
    };

    this.container.querySelector('#obs-minus-10')?.addEventListener('click', () => updateObs(-10));
    this.container.querySelector('#obs-minus-1')?.addEventListener('click', () => updateObs(-1));
    this.container.querySelector('#obs-plus-1')?.addEventListener('click', () => updateObs(1));
    this.container.querySelector('#obs-plus-10')?.addEventListener('click', () => updateObs(10));
    obsInput?.addEventListener('change', () => updateObs(0));

    // Heading adjustments
    const hdgInput = this.container.querySelector('#hdg-input') as HTMLInputElement;
    this.container.querySelector('#hdg-minus-10')?.addEventListener('click', () => {
      let cur = (parseFloat(hdgInput?.value || '0') - 10 + 360) % 360;
      if (hdgInput) hdgInput.value = cur.toFixed(0);
      api.manualAircraftControl({ heading_deg: cur });
    });
    this.container.querySelector('#hdg-plus-10')?.addEventListener('click', () => {
      let cur = (parseFloat(hdgInput?.value || '0') + 10 + 360) % 360;
      if (hdgInput) hdgInput.value = cur.toFixed(0);
      api.manualAircraftControl({ heading_deg: cur });
    });
    hdgInput?.addEventListener('change', () => {
      api.manualAircraftControl({ heading_deg: parseFloat(hdgInput.value) });
    });

    // Alt & Speed overrides
    this.container.querySelector('#alt-input')?.addEventListener('change', (e) => {
      const alt = parseFloat((e.target as HTMLInputElement).value);
      api.manualAircraftControl({ altitude_ft: alt });
    });
    this.container.querySelector('#spd-input')?.addEventListener('change', (e) => {
      const spd = parseFloat((e.target as HTMLInputElement).value);
      api.manualAircraftControl({ groundspeed_kts: spd });
    });

    // Quick tune
    const quickTuneSelect = this.container.querySelector('#quick-tune-select') as HTMLSelectElement;
    quickTuneSelect?.addEventListener('change', (e) => {
      const val = (e.target as HTMLSelectElement).value;
      if (val) {
        api.tuneAvionics('nav1', val);
      }
    });

    // Re-arm auto-tune
    this.container.querySelector('#btn-re-autotune')?.addEventListener('click', () => {
      api.tuneAvionics('auto', '');
    });
  }
}
