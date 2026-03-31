/**
 * charts.js
 * Initializes Chart.js charts and Leaflet heatmap for the analytics dashboard.
 */

function initCharts(typeLabels, typeCounts, statusLabels, statusCounts, trendLabels, trendCounts, heatmapData) {
  const TYPE_COLORS = [
    '#0d6efd', '#198754', '#ffc107', '#0dcaf0', '#dc3545',
    '#fd7e14', '#6f42c1', '#20c997'
  ];
  const STATUS_COLORS = {
    SUBMITTED: '#0d6efd', ASSIGNED: '#ffc107', IN_PROGRESS: '#fd7e14',
    RESOLVED: '#198754', CLOSED: '#6c757d', ESCALATED: '#dc3545'
  };

  // ── By Type (Bar) ──────────────────────────────────────
  const typeCtx = document.getElementById('typeChart');
  if (typeCtx) {
    new Chart(typeCtx, {
      type: 'bar',
      data: {
        labels: typeLabels,
        datasets: [{
          label: 'Incidents',
          data: typeCounts,
          backgroundColor: TYPE_COLORS,
          borderRadius: 6,
        }]
      },
      options: {
        plugins: { legend: { display: false } },
        scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } }
      }
    });
  }

  // ── By Status (Doughnut) ───────────────────────────────
  const statusCtx = document.getElementById('statusChart');
  if (statusCtx) {
    new Chart(statusCtx, {
      type: 'doughnut',
      data: {
        labels: statusLabels,
        datasets: [{
          data: statusCounts,
          backgroundColor: statusLabels.map(s => STATUS_COLORS[s] || '#aaa'),
        }]
      },
      options: {
        plugins: { legend: { position: 'right' } },
        cutout: '60%'
      }
    });
  }

  // ── Trend (Line) ───────────────────────────────────────
  const trendCtx = document.getElementById('trendChart');
  if (trendCtx) {
    new Chart(trendCtx, {
      type: 'line',
      data: {
        labels: trendLabels,
        datasets: [{
          label: 'Incidents Reported',
          data: trendCounts,
          borderColor: '#0d6efd',
          backgroundColor: 'rgba(13,110,253,0.1)',
          fill: true,
          tension: 0.4,
          pointRadius: 4,
        }]
      },
      options: {
        scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } }
      }
    });
  }

  // ── Heatmap (Leaflet) ─────────────────────────────────
  const heatmapEl = document.getElementById('heatmap');
  if (heatmapEl) {
    const hmap = L.map('heatmap').setView([20.5937, 78.9629], 4);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors',
      maxZoom: 19
    }).addTo(hmap);

    // Draw circles as heatmap approximation (Leaflet.heat not bundled as CDN here)
    if (heatmapData.length > 0) {
      heatmapData.forEach(([lat, lng]) => {
        L.circleMarker([lat, lng], {
          radius: 8, color: '#dc3545', fillColor: '#dc3545',
          fillOpacity: 0.5, weight: 0
        }).addTo(hmap);
      });
    }
  }
}
