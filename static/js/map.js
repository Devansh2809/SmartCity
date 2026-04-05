/**
 * map.js
 * Shared Leaflet map utilities (marker color/icon helpers used across templates).
 * The actual map initialization lives inline in each template for flexibility.
 */

const SCMap = (function () {
  const STATUS_COLORS = {
    SUBMITTED: '#0d6efd',
    ASSIGNED: '#ffc107',
    IN_PROGRESS: '#fd7e14',
    RESOLVED: '#198754',
    CLOSED: '#6c757d',
    ESCALATED: '#dc3545',
  };

  const TYPE_EMOJI = {
    POTHOLE: '🕳️',
    GARBAGE: '🗑️',
    STREETLIGHT: '💡',
    WATER_LEAK: '💧',
    TRAFFIC: '🚦',
    MISC: '📋',
  };

  function coloredIcon(color, emoji) {
    return L.divIcon({
      className: '',
      html: `<div style="
        background:${color};
        width:32px;height:32px;
        border-radius:50% 50% 50% 0;
        transform:rotate(-45deg);
        border:2px solid white;
        box-shadow:0 2px 4px rgba(0,0,0,.3);
        display:flex;align-items:center;justify-content:center;">
        <span style="transform:rotate(45deg);font-size:14px;">${emoji}</span>
      </div>`,
      iconSize: [32, 32],
      iconAnchor: [16, 32],
      popupAnchor: [0, -34],
    });
  }

  function iconForIncident(incident) {
    const color = STATUS_COLORS[incident.status] || '#888';
    const emoji = TYPE_EMOJI[incident.incident_type] || '📍';
    return coloredIcon(color, emoji);
  }

  return { STATUS_COLORS, TYPE_EMOJI, coloredIcon, iconForIncident };
})();
