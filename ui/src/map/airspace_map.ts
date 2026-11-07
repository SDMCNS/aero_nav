/**
 * Tactical Airspace Map (Leaflet) component.
 * Displays Shannon FIR/UIR boundaries, airports, runways, ILS cones,
 * navaids with DOC range rings, and real-time aircraft trajectory.
 */

import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { FullTelemetry, ScenarioState } from '../types';
import { api } from '../api';

export class AirspaceMap {
  private map: L.Map;
  private aircraftMarker: L.Marker | null = null;
  private flightPathPolyline: L.Polyline;
  private scenarioRoutePolyline: L.Polyline;
  private firLayers: L.LayerGroup = L.layerGroup();
  private navaidLayers: L.LayerGroup = L.layerGroup();
  private airportLayers: L.LayerGroup = L.layerGroup();
  private waypointLayers: L.LayerGroup = L.layerGroup();

  private flightPathCoordinates: [number, number][] = [];
  private currentScenarioId: string = '';

  constructor(containerId: string) {
    // Center on Ireland
    this.map = L.map(containerId, {
      center: [53.15, -8.0],
      zoom: 7,
      minZoom: 5,
      maxZoom: 16,
      zoomControl: true,
    });

    // 100% Free, Reliable Base Maps (NO API Key required)
    // 1. OpenStreetMap Standard (Worldwide, zero tokens or keys)
    const osmLayer = L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      maxZoom: 19,
    });

    // 2. Esri World Dark Gray Canvas (Official free GIS base map)
    const esriDarkLayer = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}', {
      attribution: '&copy; Esri, HERE, Garmin, FAO, USGS',
      maxZoom: 16,
    });

    // 3. Esri World Imagery (Satellite)
    const esriSatLayer = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
      attribution: '&copy; Esri, Maxar, Earthstar Geographics',
      maxZoom: 18,
    });

    // Add Esri Dark by default, or fallback to OSM
    esriDarkLayer.addTo(this.map);

    // Layer control for user convenience
    const baseMaps = {
      'Tactical Dark Canvas (Free)': esriDarkLayer,
      'OpenStreetMap Standard (Free)': osmLayer,
      'Satellite Imagery (Free)': esriSatLayer,
    };

    const overlayMaps = {
      'Shannon FIR / UIR': this.firLayers,
      'Navigation Aids': this.navaidLayers,
      'Airports & Runways': this.airportLayers,
      'Irish Fixes (IE_Waypoints)': this.waypointLayers,
    };

    L.control.layers(baseMaps, overlayMaps, { position: 'topright' }).addTo(this.map);

    this.firLayers.addTo(this.map);
    this.navaidLayers.addTo(this.map);
    this.airportLayers.addTo(this.map);
    this.waypointLayers.addTo(this.map);

    // Scenario flight plan line
    this.scenarioRoutePolyline = L.polyline([], {
      color: '#38bdf8',
      weight: 3,
      dashArray: '6, 6',
      opacity: 0.8,
    }).addTo(this.map);

    // Aircraft recorded flight trail
    this.flightPathPolyline = L.polyline([], {
      color: '#facc15',
      weight: 2.5,
      opacity: 0.9,
    }).addTo(this.map);

    // Fix default marker icon issues in webpack/vite
    delete (L.Icon.Default.prototype as any)._getIconUrl;
    L.Icon.Default.mergeOptions({
      iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
      iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
      shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
    });
  }

  public async loadAirspaceData() {
    try {
      const geojson = await api.getAirspaceGeoJson();
      this.renderAirspaceFeatures(geojson);
    } catch (e) {
      console.error('Failed to load airspace features', e);
    }
  }

  private renderAirspaceFeatures(geojson: any) {
    this.firLayers.clearLayers();
    this.navaidLayers.clearLayers();
    this.airportLayers.clearLayers();

    if (!geojson || !geojson.features) return;

    for (const feature of geojson.features) {
      const p = feature.properties;

      if (p.feature_type === 'AIRSPACE_BOUNDARY') {
        const isUir = p.id === 'EISNUIR';
        const color = isUir ? '#818cf8' : '#38bdf8';
        const polygon = L.geoJSON(feature, {
          style: {
            color: color,
            weight: 2,
            opacity: 0.7,
            fillColor: color,
            fillOpacity: isUir ? 0.03 : 0.05,
            dashArray: isUir ? '4, 4' : undefined,
          },
        });
        polygon.bindTooltip(`<b>${p.id}</b><br>FL${p.min_fl} - FL${p.max_fl}`, {
          sticky: true,
          className: 'tactical-tooltip',
        });
        this.firLayers.addLayer(polygon);
      } else if (p.feature_type === 'NAVAID') {
        this.renderNavaidMarker(feature);
      } else if (p.feature_type === 'AIRPORT') {
        this.renderAirportMarker(feature);
      } else if (p.feature_type === 'WAYPOINT') {
        this.renderEnrouteWaypoint(feature);
      }
    }
  }

  private renderEnrouteWaypoint(feature: any) {
    const [lon, lat] = feature.geometry.coordinates;
    const p = feature.properties;

    const wpIcon = L.divIcon({
      className: 'enroute-wp-div-icon',
      html: `
        <div class="enroute-wp-marker">
          <svg width="12" height="12" viewBox="0 0 12 12">
            <polygon points="6,1 11,10 1,10" fill="#64748b" stroke="#94a3b8" stroke-width="1"/>
          </svg>
          <span class="enroute-wp-label">${p.name}</span>
        </div>
      `,
      iconSize: [20, 20],
      iconAnchor: [10, 10],
    });

    const marker = L.marker([lat, lon], { icon: wpIcon });
    marker.bindTooltip(`<b>${p.name}</b><br>${p.type}<br>${p.description || ''}`, {
      className: 'tactical-tooltip',
    });
    this.waypointLayers.addLayer(marker);
  }

  private renderNavaidMarker(feature: any) {
    const [lon, lat] = feature.geometry.coordinates;
    const p = feature.properties;

    // Distinct SVG icons for VOR, DME, NDB, ILS
    let iconHtml = '';
    let symbolColor = '#38bdf8';

    if (p.type.includes('DVOR') || p.type.includes('VOR')) {
      symbolColor = '#38bdf8';
      iconHtml = `
        <div class="navaid-icon vor-icon">
          <svg width="24" height="24" viewBox="0 0 24 24">
            <polygon points="12,2 21,7 21,17 12,22 3,17 3,7" fill="none" stroke="${symbolColor}" stroke-width="2"/>
            <circle cx="12" cy="12" r="3" fill="${symbolColor}"/>
          </svg>
          <span class="navaid-label">${p.id}</span>
        </div>
      `;
    } else if (p.type.includes('DME')) {
      symbolColor = '#34d399';
      iconHtml = `
        <div class="navaid-icon dme-icon">
          <svg width="22" height="22" viewBox="0 0 24 24">
            <rect x="4" y="4" width="16" height="16" fill="none" stroke="${symbolColor}" stroke-width="2"/>
            <circle cx="12" cy="12" r="2" fill="${symbolColor}"/>
          </svg>
          <span class="navaid-label">${p.id}</span>
        </div>
      `;
    } else if (p.type.includes('NDB')) {
      symbolColor = '#fb7185';
      iconHtml = `
        <div class="navaid-icon ndb-icon">
          <svg width="22" height="22" viewBox="0 0 24 24">
            <circle cx="12" cy="12" r="8" fill="none" stroke="${symbolColor}" stroke-width="2" stroke-dasharray="2, 2"/>
            <circle cx="12" cy="12" r="4" fill="${symbolColor}"/>
          </svg>
          <span class="navaid-label">${p.id}</span>
        </div>
      `;
    } else if (p.type === 'ILS_LOC') {
      symbolColor = '#a855f7';
      iconHtml = `
        <div class="navaid-icon ils-icon">
          <svg width="20" height="20" viewBox="0 0 20 20">
            <polygon points="10,1 18,18 2,18" fill="none" stroke="${symbolColor}" stroke-width="2"/>
            <line x1="10" y1="5" x2="10" y2="15" stroke="${symbolColor}" stroke-width="1.5"/>
          </svg>
          <span class="navaid-label">${p.id}</span>
        </div>
      `;
    } else {
      return; // Skip raw ILS_GP points on map to prevent clutter
    }

    const customIcon = L.divIcon({
      className: 'custom-navaid-div-icon',
      html: iconHtml,
      iconSize: [36, 36],
      iconAnchor: [18, 18],
    });

    const marker = L.marker([lat, lon], { icon: customIcon });

    // Interactive popup with Quick-Tune actions
    const popupContent = `
      <div class="tactical-popup">
        <div class="popup-title">${p.name} (${p.id})</div>
        <div class="popup-grid">
          <div><b>Type:</b> ${p.type}</div>
          <div><b>Freq:</b> ${p.frequency || 'N/A'}</div>
          <div><b>Elevation:</b> ${p.elevation_ft} ft</div>
          <div><b>DOC Range:</b> ${p.doc_range_nm} NM</div>
        </div>
        <div class="popup-actions">
          ${p.type.includes('VOR') || p.type.includes('ILS') ? `<button class="btn-tune-nav1" data-id="${p.id}">Tune NAV1</button>` : ''}
          ${p.type.includes('DME') ? `<button class="btn-tune-dme1" data-id="${p.id}">Tune DME</button>` : ''}
          ${p.type.includes('NDB') ? `<button class="btn-tune-adf1" data-id="${p.id}">Tune ADF</button>` : ''}
        </div>
      </div>
    `;

    marker.bindPopup(popupContent);
    marker.on('popupopen', () => {
      const el = marker.getPopup()?.getElement();
      if (!el) return;
      el.querySelector('.btn-tune-nav1')?.addEventListener('click', () => {
        api.tuneAvionics('nav1', p.id);
        marker.closePopup();
      });
      el.querySelector('.btn-tune-dme1')?.addEventListener('click', () => {
        api.tuneAvionics('dme1', p.id);
        marker.closePopup();
      });
      el.querySelector('.btn-tune-adf1')?.addEventListener('click', () => {
        api.tuneAvionics('adf1', p.id);
        marker.closePopup();
      });
    });

    this.navaidLayers.addLayer(marker);

    // Draw DOC range circle for major enroute facilities
    if (p.doc_range_nm && (p.type.includes('DVOR') || p.type.includes('NDB'))) {
      const radiusMeters = p.doc_range_nm * 1852.0;
      const circle = L.circle([lat, lon], {
        radius: radiusMeters,
        color: symbolColor,
        weight: 1,
        dashArray: '4, 8',
        opacity: 0.25,
        fillColor: symbolColor,
        fillOpacity: 0.01,
      });
      this.navaidLayers.addLayer(circle);
    }
  }

  private renderAirportMarker(feature: any) {
    const [lon, lat] = feature.geometry.coordinates;
    const p = feature.properties;

    // Airport ARP Marker
    const apIcon = L.divIcon({
      className: 'airport-div-icon',
      html: `
        <div class="airport-marker">
          <svg width="26" height="26" viewBox="0 0 24 24" fill="#38bdf8">
            <path d="M21 16v-2l-8-5V3.5c0-.83-.67-1.5-1.5-1.5S10 2.67 10 3.5V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5l8 2.5z"/>
          </svg>
          <span class="airport-name">${p.id}</span>
        </div>
      `,
      iconSize: [40, 40],
      iconAnchor: [20, 20],
    });

    const marker = L.marker([lat, lon], { icon: apIcon });
    marker.bindTooltip(`<b>${p.name} (${p.id})</b><br>Elevation: ${p.elevation_ft} ft<br>Mag Var: ${p.magnetic_variation}`, {
      className: 'tactical-tooltip',
    });
    this.airportLayers.addLayer(marker);

    // Draw Runways and ILS Feathers
    if (p.runways) {
      for (const rwy of p.runways) {
        if (rwy.thr_lat && rwy.thr_lon && rwy.end_lat && rwy.end_lon) {
          // Draw runway centerline
          const rwyLine = L.polyline([[rwy.thr_lat, rwy.thr_lon], [rwy.end_lat, rwy.end_lon]], {
            color: '#ffffff',
            weight: 4,
            opacity: 0.9,
          });
          this.airportLayers.addLayer(rwyLine);

          // If ILS is equipped on this runway, draw the approach feather
          if (rwy.ils_loc_id) {
            this.drawIlsFeather(
              rwy.thr_lat,
              rwy.thr_lon,
              rwy.end_lat,
              rwy.end_lon,
              rwy.magnetic_bearing_deg,
              rwy.true_bearing_deg,
              rwy.designation,
              rwy.ils_loc_id
            );
          }
        }
      }
    }
  }

  private drawIlsFeather(
    thrLat: number,
    thrLon: number,
    endLat: number,
    endLon: number,
    inboundMag: number,
    trueBearing: number,
    rwyDesig: string,
    locId: string
  ) {
    // Vector pointing from runway end through threshold outwards into the approach (100% collinear with runway)
    const dLatRwy = thrLat - endLat;
    const dLonRwy = thrLon - endLon;
    const cosThr = Math.cos(thrLat * (Math.PI / 180.0));
    const rwyLenM = Math.hypot(dLatRwy * 111139.0, dLonRwy * 111139.0 * cosThr);
    if (rwyLenM <= 0) return;

    // Extend 15 NM out into the approach along the exact runway centerline
    const lengthMeters = 15.0 * 1852.0;
    const scale = lengthMeters / rwyLenM;

    const endLatExt = thrLat + dLatRwy * scale;
    const endLonExt = thrLon + dLonRwy * scale;

    // Draw the extended runway centerline (dashed purple line)
    const centerline = L.polyline([[thrLat, thrLon], [endLatExt, endLonExt]], {
      color: '#c084fc',
      weight: 1.5,
      opacity: 0.85,
      dashArray: '6, 6',
    });
    this.airportLayers.addLayer(centerline);

    // ICAO Annex 10 Localizer Sector Fan: ±2.5° Full Scale Deflection (FSD)
    const halfAngleRad = 2.5 * (Math.PI / 180.0);
    const centerAngle = Math.atan2(dLonRwy * 111139.0 * cosThr, dLatRwy * 111139.0);

    const leftAngle = centerAngle - halfAngleRad;
    const rightAngle = centerAngle + halfAngleRad;

    const leftLat = thrLat + (lengthMeters * Math.cos(leftAngle)) / 111139.0;
    const leftLon = thrLon + (lengthMeters * Math.sin(leftAngle)) / (111139.0 * cosThr);

    const rightLat = thrLat + (lengthMeters * Math.cos(rightAngle)) / 111139.0;
    const rightLon = thrLon + (lengthMeters * Math.sin(rightAngle)) / (111139.0 * cosThr);

    const polygon = L.polygon([[thrLat, thrLon], [leftLat, leftLon], [rightLat, rightLon]], {
      color: '#c084fc',
      weight: 1,
      opacity: 0.7,
      fillColor: '#c084fc',
      fillOpacity: 0.12,
    });

    const magDisplay = inboundMag !== undefined ? `${inboundMag.toFixed(0)}°M` : '';
    const trueDisplay = trueBearing !== undefined ? ` (${trueBearing.toFixed(1)}°T)` : '';
    polygon.bindTooltip(
      `<b>ILS RWY ${rwyDesig} (${locId})</b><br>Inbound Course: ${magDisplay}${trueDisplay}<br>Localizer Coverage: ±2.5° FSD (15 NM)`,
      { className: 'tactical-tooltip' }
    );
    this.airportLayers.addLayer(polygon);
  }

  public updateTelemetry(telemetry: FullTelemetry, scenario: ScenarioState) {
    const ac = telemetry.aircraft;

    // Update scenario route polyline if changed
    if (this.currentScenarioId !== scenario.id) {
      this.currentScenarioId = scenario.id;
      this.flightPathCoordinates = [];
      this.flightPathPolyline.setLatLngs([]);

      const routePoints: [number, number][] = scenario.waypoints.map(w => [w.lat, w.lon]);
      this.scenarioRoutePolyline.setLatLngs(routePoints);

      // Render scenario waypoints
      this.waypointLayers.clearLayers();
      for (const wp of scenario.waypoints) {
        const wpIcon = L.divIcon({
          className: 'wp-div-icon',
          html: `<div class="wp-dot ${wp.is_current ? 'wp-active' : ''}"></div><span class="wp-label">${wp.name}</span>`,
          iconSize: [24, 24],
          iconAnchor: [12, 12],
        });
        const m = L.marker([wp.lat, wp.lon], { icon: wpIcon });
        m.bindTooltip(`<b>${wp.name}</b><br>Alt: ${wp.target_alt_ft} ft<br>${wp.briefing_note}`, {
          className: 'tactical-tooltip',
        });
        this.waypointLayers.addLayer(m);
      }
    }

    // Append to aircraft flight path
    this.flightPathCoordinates.push([ac.lat, ac.lon]);
    if (this.flightPathCoordinates.length > 500) {
      this.flightPathCoordinates.shift();
    }
    this.flightPathPolyline.setLatLngs(this.flightPathCoordinates);

    // Update or create Aircraft Marker
    const planeSvg = `
      <div class="aircraft-symbol-container" style="transform: rotate(${ac.true_heading_deg}deg);">
        <svg width="34" height="34" viewBox="0 0 24 24" fill="#facc15" stroke="#0f172a" stroke-width="0.8">
          <path d="M21 16v-2l-8-5V3.5c0-.83-.67-1.5-1.5-1.5S10 2.67 10 3.5V9l-8 5v2l8-2.5V19l-2 1.5V22l3.5-1 3.5 1v-1.5L13 19v-5.5l8 2.5z"/>
        </svg>
      </div>
    `;

    const planeIcon = L.divIcon({
      className: 'aircraft-div-icon',
      html: planeSvg,
      iconSize: [34, 34],
      iconAnchor: [17, 17],
    });

    if (!this.aircraftMarker) {
      this.aircraftMarker = L.marker([ac.lat, ac.lon], { icon: planeIcon, zIndexOffset: 1000 }).addTo(this.map);
    } else {
      this.aircraftMarker.setLatLng([ac.lat, ac.lon]);
      this.aircraftMarker.setIcon(planeIcon);
    }
  }

  public invalidateSize() {
    this.map.invalidateSize();
  }
}

