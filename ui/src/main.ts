/**
 * Main application entrypoint.
 * Coordinates real-time avionics telemetry stream, instruments, map, and scenario controller.
 */

import './style.css';
import { api } from './api';
import { SimSnapshot } from './types';
import { AirspaceMap } from './map/airspace_map';
import { HsiDisplay } from './instruments/hsi_display';
import { RmiDisplay } from './instruments/rmi_display';
import { DmeDisplay } from './instruments/dme_display';
import { GnssDisplay } from './instruments/gnss_display';
import { IlsProfileDisplay } from './instruments/ils_profile';
import { FullIlsModal } from './instruments/ils_modal';
import { InstrumentTutorialModal } from './instruments/tutorial_modal';
import { AvionicsBusView } from './views/avionics_bus';
import { ReceiverMatrixView } from './views/receiver_matrix';
import { ScenarioControlView } from './views/scenario_ctrl';

class AvionicsApp {
  private map!: AirspaceMap;
  private hsiDisplay!: HsiDisplay;
  private rmiDisplay!: RmiDisplay;
  private dmeDisplay!: DmeDisplay;
  private gnssDisplay!: GnssDisplay;
  private ilsProfileDisplay!: IlsProfileDisplay;
  private ilsModal!: FullIlsModal;
  private tutorialModal!: InstrumentTutorialModal;
  private busView!: AvionicsBusView;
  private matrixView!: ReceiverMatrixView;
  private scenarioControlView!: ScenarioControlView;

  private lastSnapshot: SimSnapshot | null = null;

  public async init() {
    console.log('🚀 Initializing Aviation Navaid & Cockpit Avionics Simulator...');

    // 1. Initialize Map
    this.map = new AirspaceMap('airspace-map');
    await this.map.loadAirspaceData();

    // 2. Initialize Instruments
    const hsiCanvas = document.getElementById('hsi-canvas') as HTMLCanvasElement;
    this.hsiDisplay = new HsiDisplay(hsiCanvas);

    const rmiCanvas = document.getElementById('rmi-canvas') as HTMLCanvasElement;
    this.rmiDisplay = new RmiDisplay(rmiCanvas);

    const dmeContainer = document.getElementById('dme-container') as HTMLElement;
    this.dmeDisplay = new DmeDisplay(dmeContainer);

    const gnssCanvas = document.getElementById('gnss-canvas') as HTMLCanvasElement;
    this.gnssDisplay = new GnssDisplay(gnssCanvas);

    const ilsCanvas = document.getElementById('ils-canvas') as HTMLCanvasElement;
    this.ilsProfileDisplay = new IlsProfileDisplay(ilsCanvas);

    // Full Precision Approach Modal
    this.ilsModal = new FullIlsModal();
    const btnOpenIls = document.getElementById('btn-open-ils-modal');
    btnOpenIls?.addEventListener('click', () => {
      this.ilsModal.show();
    });

    // Instrument Educational Tutorial Modal
    this.tutorialModal = new InstrumentTutorialModal();
    document.getElementById('btn-tut-hsi')?.addEventListener('click', () => this.tutorialModal.show('hsi'));
    document.getElementById('btn-tut-rmi')?.addEventListener('click', () => this.tutorialModal.show('rmi'));
    document.getElementById('btn-tut-dme')?.addEventListener('click', () => this.tutorialModal.show('dme'));
    document.getElementById('btn-tut-ils')?.addEventListener('click', () => this.tutorialModal.show('ils'));
    document.getElementById('btn-open-tutorials')?.addEventListener('click', () => this.tutorialModal.show());

    // 3. Initialize Views
    const busContainer = document.getElementById('bus-view-container') as HTMLElement;
    this.busView = new AvionicsBusView(busContainer);

    const matrixContainer = document.getElementById('matrix-view-container') as HTMLElement;
    this.matrixView = new ReceiverMatrixView(matrixContainer);

    const scenarioContainer = document.getElementById('scenario-control-container') as HTMLElement;
    this.scenarioControlView = new ScenarioControlView(scenarioContainer);

    // 4. Setup Tabs
    this.setupTabs();

    // 5. Connect WebSocket
    api.subscribe((snapshot: SimSnapshot) => {
      this.handleSnapshot(snapshot);
    });
    api.connectWebSocket();

    // Fallback initial poll
    try {
      const res = await fetch('/api/simulation/state');
      if (res.ok) {
        const initialSnap = await res.json();
        this.handleSnapshot(initialSnap);
      }
    } catch (e) {
      // Backend may still be starting
    }
  }

  private setupTabs() {
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabPanes = document.querySelectorAll('.tab-pane');
    const bottomDeck = document.getElementById('bottom-deck');
    const btnToggleDeck = document.getElementById('btn-toggle-bottom-deck');
    const collapseIcon = document.getElementById('collapse-icon');
    const collapseText = document.getElementById('collapse-text');

    const toggleCollapse = (forceExpand: boolean = false) => {
      if (!bottomDeck) return;
      const isCurrentlyCollapsed = bottomDeck.classList.contains('collapsed');
      const shouldCollapse = forceExpand ? false : !isCurrentlyCollapsed;

      if (shouldCollapse) {
        bottomDeck.classList.add('collapsed');
        if (collapseIcon) collapseIcon.textContent = '▲';
        if (collapseText) collapseText.textContent = 'EXPAND READOUTS';
        btnToggleDeck?.classList.add('is-collapsed');
      } else {
        bottomDeck.classList.remove('collapsed');
        if (collapseIcon) collapseIcon.textContent = '▼';
        if (collapseText) collapseText.textContent = 'COLLAPSE READOUTS';
        btnToggleDeck?.classList.remove('is-collapsed');
      }

      // Invalidate map size so Leaflet takes full expanded viewport
      setTimeout(() => {
        this.map.invalidateSize();
      }, 260);
    };

    btnToggleDeck?.addEventListener('click', () => toggleCollapse());

    // Keyboard shortcut: Press 'C' to toggle collapsing digital readouts
    window.addEventListener('keydown', (e) => {
      if ((e.key === 'c' || e.key === 'C') && !['INPUT', 'SELECT', 'TEXTAREA'].includes((e.target as HTMLElement)?.tagName)) {
        toggleCollapse();
      }
    });

    tabBtns.forEach(btn => {
      btn.addEventListener('click', (e) => {
        // If collapsed, auto-expand upon clicking a tab
        if (bottomDeck?.classList.contains('collapsed')) {
          toggleCollapse(true);
        }

        const targetTab = (e.currentTarget as HTMLElement).getAttribute('data-tab');

        tabBtns.forEach(b => b.classList.remove('active-tab'));
        btn.classList.add('active-tab');

        tabPanes.forEach(p => {
          (p as HTMLElement).style.display = p.id === targetTab ? 'block' : 'none';
        });

        // Trigger redraw if canvas tab becomes visible
        if (targetTab === 'tab-gnss' && this.lastSnapshot) {
          this.gnssDisplay.render(this.lastSnapshot.telemetry);
        }
      });
    });
  }

  private handleSnapshot(snapshot: SimSnapshot) {
    this.lastSnapshot = snapshot;
    const { scenario, telemetry } = snapshot;
    const ac = telemetry.aircraft;

    // 1. Update Header Telemetry Strip
    const elCallsign = document.getElementById('hdr-callsign');
    const elType = document.getElementById('hdr-type');
    const elAlt = document.getElementById('hdr-alt');
    const elHdg = document.getElementById('hdr-hdg');
    const elGs = document.getElementById('hdr-gs');
    const elPhase = document.getElementById('hdr-phase');

    if (elCallsign) elCallsign.textContent = ac.callsign;
    if (elType) elType.textContent = ac.type;
    if (elAlt) elAlt.textContent = `${ac.altitude_ft.toLocaleString(undefined, { maximumFractionDigits: 0 })} FT`;
    if (elHdg) elHdg.textContent = `${ac.magnetic_heading_deg.toFixed(0)}°`;
    if (elGs) elGs.textContent = `${ac.groundspeed_kts.toFixed(0)} KT`;
    if (elPhase) elPhase.textContent = ac.flight_phase;

    // 2. Update Map
    this.map.updateTelemetry(telemetry, scenario);

    // 3. Update Cockpit Instruments
    this.hsiDisplay.render(telemetry);
    this.rmiDisplay.render(telemetry);
    this.dmeDisplay.render(telemetry);
    this.ilsProfileDisplay.render(telemetry);
    this.gnssDisplay.render(telemetry);
    this.ilsModal.update(telemetry);
    this.tutorialModal.updateTelemetry(telemetry);

    // 4. Update Views
    this.scenarioControlView.render(scenario, telemetry);
    this.busView.render(telemetry);
    this.matrixView.render(telemetry);

    // 5. Update Cockpit Instrument Card Headers dynamically on station switch
    const hsiTag = document.getElementById('hsi-mode-tag');
    if (hsiTag) {
      if (telemetry.nav1.mode === 'ILS') {
        const rwy = (telemetry.nav1.evaluation as any)?.runway_id || '';
        hsiTag.textContent = `ILS ${rwy}: ${telemetry.nav1.station?.id || 'LOC'} (${telemetry.nav1.station?.frequency || ''})`;
      } else {
        hsiTag.textContent = `VOR: ${telemetry.nav1.station?.id || '---'} (${telemetry.nav1.station?.frequency || ''})`;
      }
    }

    const rmiTag = document.getElementById('rmi-header-tag');
    if (rmiTag) {
      const adfStr = telemetry.adf1.station ? `${telemetry.adf1.station.id} (${telemetry.adf1.station.frequency})` : '---';
      const vorStr = telemetry.nav1.mode === 'VOR' && telemetry.nav1.station
        ? `${telemetry.nav1.station.id} (${telemetry.nav1.station.frequency})`
        : (telemetry.nav1.mode === 'ILS' ? `ILS [${telemetry.nav1.station?.id || 'LOC'}]` : '---');
      rmiTag.textContent = `ADF: ${adfStr} | VOR: ${vorStr}`;
    }

    const dmeTag = document.getElementById('dme-header-tag');
    if (dmeTag) {
      const st = telemetry.dme1.station;
      const ch = (telemetry.dme1.evaluation as any)?.channel || st?.channel || '';
      dmeTag.textContent = st ? `${st.id} (${ch ? 'CH ' + ch : st.frequency})` : 'UHF 1030 MHz';
    }

    const ilsTitle = document.getElementById('ils-header-title');
    const ilsTag = document.getElementById('ils-header-tag');
    if (ilsTitle) {
      if (telemetry.nav1.mode === 'ILS') {
        const ev = telemetry.nav1.evaluation as any;
        ilsTitle.textContent = `ILS RWY ${ev?.runway_id || '24'} DESCENT PROFILE`;
      } else {
        ilsTitle.textContent = 'ILS DESCENT PROFILE (STANDBY)';
      }
    }
    if (ilsTag) {
      if (telemetry.nav1.mode === 'ILS') {
        ilsTag.textContent = `${telemetry.nav1.station?.id || 'LOC'} ${telemetry.nav1.station?.frequency || ''}`;
      } else {
        ilsTag.textContent = 'STANDBY';
      }
    }
  }
}

// Start application
window.addEventListener('DOMContentLoaded', () => {
  const app = new AvionicsApp();
  app.init();
});

