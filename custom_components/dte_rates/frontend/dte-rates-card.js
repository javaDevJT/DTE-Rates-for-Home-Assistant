class DteRatesCard extends HTMLElement {
  static getConfigElement() {
    return document.createElement('hui-entity-card-editor');
  }

  static getStubConfig() {
    return {
      title: 'DTE Rates',
      import_entity: 'sensor.dte_import_rate',
      export_entity: 'sensor.dte_export_rate',
      name_entity: 'sensor.dte_current_rate_name',
      schedule_entity: 'sensor.dte_rate_schedule',
    };
  }

  setConfig(config) {
    if (!config.import_entity || !config.export_entity || !config.name_entity || !config.schedule_entity) {
      throw new Error('dte-rates-card requires import_entity, export_entity, name_entity, schedule_entity');
    }
    this._config = config;
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._content) {
      this._root = this.attachShadow({ mode: 'open' });
      this._root.innerHTML = `
        <style>
          :host { display:block; }
          ha-card {
            border-radius: 20px;
            overflow: hidden;
            background: linear-gradient(140deg, #0f4d7a 0%, #147ca5 45%, #7fd4d9 100%);
            color: #f8fcff;
          }
          .wrap { padding: 18px; }
          .title { font-size: 1.2rem; font-weight: 700; letter-spacing: 0.2px; }
          .subtitle { margin-top: 6px; opacity: 0.92; font-size: 0.95rem; }
          .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-top: 14px; }
          .tile {
            background: rgba(255,255,255,0.14);
            border: 1px solid rgba(255,255,255,0.28);
            border-radius: 14px;
            padding: 12px;
            backdrop-filter: blur(3px);
          }
          .label { font-size: 0.82rem; text-transform: uppercase; letter-spacing: 0.08em; opacity: 0.88; }
          .value { margin-top: 6px; font-size: 1.2rem; font-weight: 700; }
          .next { margin-top: 14px; font-size: 0.95rem; }
          .schedule {
            margin-top: 14px;
            background: rgba(6, 34, 54, 0.42);
            border: 1px solid rgba(255,255,255,0.2);
            border-radius: 12px;
            padding: 10px;
            max-height: 210px;
            overflow: auto;
            font-size: 0.80rem;
            line-height: 1.35;
          }
          .season-title {
            margin-top: 8px;
            margin-bottom: 6px;
            font-weight: 700;
            font-size: 0.85rem;
            letter-spacing: 0.03em;
            text-transform: uppercase;
            opacity: 0.92;
          }
          table { width: 100%; border-collapse: collapse; margin-bottom: 6px; }
          th, td { text-align: left; padding: 4px 6px; border-bottom: 1px solid rgba(255,255,255,0.14); }
          th { font-size: 0.72rem; opacity: 0.85; text-transform: uppercase; letter-spacing: 0.06em; }
          td { font-size: 0.80rem; }
          @media (max-width: 620px) {
            .grid { grid-template-columns: 1fr; }
          }
        </style>
        <ha-card>
          <div class="wrap">
            <div class="title"></div>
            <div class="subtitle"></div>
            <div class="grid">
              <div class="tile"><div class="label">Import</div><div class="value import-value">-</div></div>
              <div class="tile"><div class="label">Export</div><div class="value export-value">-</div></div>
            </div>
            <div class="next"></div>
            <div class="schedule"></div>
          </div>
        </ha-card>
      `;
      this._content = true;
    }

    const title = this._config.title || 'DTE Rates';
    const importState = hass.states[this._config.import_entity];
    const exportState = hass.states[this._config.export_entity];
    const nameState = hass.states[this._config.name_entity];
    const scheduleState = hass.states[this._config.schedule_entity];

    const importRate = importState?.state;
    const exportRate = exportState?.state;

    const currentRateName = nameState?.state || scheduleState?.attributes?.current_rate_name || 'Unknown';
    const nextAt = scheduleState?.attributes?.next_rate_change || importState?.attributes?.next_rate_change;
    const nextName = scheduleState?.attributes?.next_rate_name || importState?.attributes?.next_rate_name;
    const nextValue = scheduleState?.attributes?.next_rate_value || importState?.attributes?.next_rate_value;
    const scheduleRows = scheduleState?.attributes?.schedule_by_season || [];

    this._root.querySelector('.title').textContent = title;
    this._root.querySelector('.subtitle').textContent = `Current: ${currentRateName}`;
    this._root.querySelector('.import-value').textContent = importRate ? `$${Number(importRate).toFixed(5)}/kWh` : 'Unavailable';
    this._root.querySelector('.export-value').textContent = exportRate ? `$${Number(exportRate).toFixed(5)}/kWh` : 'Unavailable';
    this._root.querySelector('.next').textContent = nextAt
      ? `Next: ${nextName || 'Rate change'} at ${nextAt}${nextValue != null ? ` ($${Number(nextValue).toFixed(5)}/kWh)` : ''}`
      : 'No upcoming rate change found';
    const scheduleRoot = this._root.querySelector('.schedule');
    if (!Array.isArray(scheduleRows) || scheduleRows.length === 0) {
      scheduleRoot.textContent = 'Schedule unavailable';
      return;
    }

    const bySeason = scheduleRows.reduce((acc, row) => {
      const key = row.season || 'year_round';
      if (!acc[key]) acc[key] = [];
      acc[key].push(row);
      return acc;
    }, {});

    const blocks = Object.keys(bySeason).sort().map((season) => {
      const rows = bySeason[season].map((row) => `
        <tr>
          <td>${row.name || row.period || ''}</td>
          <td>${row.time_window || '-'}</td>
          <td>$${Number(row.import_usd_per_kwh ?? 0).toFixed(5)}</td>
          <td>$${Number(row.export_usd_per_kwh ?? 0).toFixed(5)}</td>
        </tr>
      `).join('');
      return `
        <div class="season-title">${season.replaceAll('_', ' ')}</div>
        <table>
          <thead>
            <tr><th>Rate</th><th>Window</th><th>Import</th><th>Export</th></tr>
          </thead>
          <tbody>${rows}</tbody>
        </table>
      `;
    }).join('');

    scheduleRoot.innerHTML = blocks;
  }

  getCardSize() {
    return 6;
  }
}

customElements.define('dte-rates-card', DteRatesCard);
window.customCards = window.customCards || [];
window.customCards.push({
  type: 'dte-rates-card',
  name: 'DTE Rates Card',
  description: 'Stylized DTE rate card showing current/next pricing and full schedule.',
  preview: true,
});
