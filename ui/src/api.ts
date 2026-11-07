/**
 * API and real-time WebSocket client.
 */

import { SimSnapshot } from './types';

type SnapshotCallback = (snapshot: SimSnapshot) => void;

class SimApiClient {
  private ws: WebSocket | null = null;
  private listeners: SnapshotCallback[] = [];
  private reconnectTimer: any = null;
  private isConnecting: boolean = false;

  public subscribe(cb: SnapshotCallback) {
    this.listeners.push(cb);
  }

  public unsubscribe(cb: SnapshotCallback) {
    this.listeners = this.listeners.filter(l => l !== cb);
  }

  public connectWebSocket() {
    if (this.ws && (this.ws.readyState === WebSocket.OPEN || this.ws.readyState === WebSocket.CONNECTING)) {
      return;
    }

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    // If running under vite dev server at port 3000, connect to backend at 8000 if needed or through proxy
    const host = window.location.port === '3000' ? `${window.location.hostname}:8000` : window.location.host;
    const wsUrl = `${protocol}//${host}/ws/telemetry`;

    console.log(`📡 Connecting to Avionics WebSocket: ${wsUrl}`);
    try {
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        console.log('✅ WebSocket Connected to Avionics Telemetry Stream');
        if (this.reconnectTimer) {
          clearTimeout(this.reconnectTimer);
          this.reconnectTimer = null;
        }
      };

      this.ws.onmessage = (event) => {
        try {
          const snapshot: SimSnapshot = JSON.parse(event.data);
          for (const cb of this.listeners) {
            cb(snapshot);
          }
        } catch (err) {
          console.error('Failed to parse telemetry snapshot', err);
        }
      };

      this.ws.onclose = () => {
        console.warn('⚠️ WebSocket disconnected. Reconnecting in 2 seconds...');
        this.scheduleReconnect();
      };

      this.ws.onerror = (err) => {
        console.error('WebSocket error:', err);
        this.ws?.close();
      };
    } catch (e) {
      this.scheduleReconnect();
    }
  }

  private scheduleReconnect() {
    if (!this.reconnectTimer) {
      this.reconnectTimer = setTimeout(() => {
        this.reconnectTimer = null;
        this.connectWebSocket();
      }, 2000);
    }
  }

  public sendWsCommand(command: any) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(command));
    }
  }

  // REST API Methods
  public async getAirspaceGeoJson(): Promise<any> {
    const res = await fetch('/api/database/geojson');
    if (!res.ok) throw new Error('Failed to load airspace GeoJSON');
    return res.json();
  }

  public async getAirports(): Promise<any> {
    const res = await fetch('/api/database/airports');
    if (!res.ok) throw new Error('Failed to load airports');
    return res.json();
  }

  public async getScenarios(): Promise<any[]> {
    const res = await fetch('/api/scenarios');
    if (!res.ok) throw new Error('Failed to load scenarios');
    return res.json();
  }

  public async selectScenario(scenarioId: string): Promise<SimSnapshot> {
    const res = await fetch(`/api/scenarios/${scenarioId}/select`, { method: 'POST' });
    if (!res.ok) throw new Error('Failed to select scenario');
    return res.json();
  }

  public async controlSim(action: string, speed?: number, fraction?: number): Promise<SimSnapshot> {
    const res = await fetch('/api/simulation/control', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ action, speed, fraction }),
    });
    if (!res.ok) throw new Error('Sim control failed');
    return res.json();
  }

  public async tuneAvionics(receiver: string, stationId: string, obsDeg?: number): Promise<SimSnapshot> {
    const res = await fetch('/api/avionics/tune', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ receiver, station_id: stationId, obs_deg: obsDeg }),
    });
    if (!res.ok) throw new Error('Avionics tuning failed');
    return res.json();
  }

  public async manualAircraftControl(controls: any): Promise<SimSnapshot> {
    const res = await fetch('/api/aircraft/manual', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(controls),
    });
    if (!res.ok) throw new Error('Manual control failed');
    return res.json();
  }
}

export const api = new SimApiClient();

