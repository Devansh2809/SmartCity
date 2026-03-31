/**
 * websocket.js
 * Manages the WebSocket connection to /ws/incidents/ and dispatches updates.
 */
(function () {
  const protocol = window.location.protocol === 'https:' ? 'wss' : 'ws';
  const url = `${protocol}://${window.location.host}/ws/incidents/`;
  let socket;
  let reconnectDelay = 3000;

  const statusEl = document.getElementById('ws-status');

  function setStatus(text, color) {
    if (statusEl) {
      statusEl.innerHTML = `<i class="bi bi-circle-fill me-1" style="font-size:.5rem;color:${color}"></i>${text}`;
    }
  }

  function connect() {
    socket = new WebSocket(url);

    socket.onopen = function () {
      setStatus('Live', '#2ecc71');
      reconnectDelay = 3000;
    };

    socket.onmessage = function (e) {
      try {
        const data = JSON.parse(e.data);
        showToast(`Incident ${data.tracking_id} → ${data.status_display}`);
        if (typeof window.onIncidentUpdate === 'function') {
          window.onIncidentUpdate(data);
        }
      } catch (_) {}
    };

    socket.onclose = function () {
      setStatus('Reconnecting...', '#e67e22');
      setTimeout(connect, reconnectDelay);
      reconnectDelay = Math.min(reconnectDelay * 1.5, 30000);
    };

    socket.onerror = function () {
      setStatus('Offline', '#e74c3c');
    };
  }

  function showToast(message) {
    const toastEl = document.getElementById('liveToast');
    const toastBody = document.getElementById('toastBody');
    if (!toastEl || !toastBody) return;
    toastBody.textContent = message;
    const toast = bootstrap.Toast.getOrCreateInstance(toastEl, { delay: 4000 });
    toast.show();
  }

  document.addEventListener('DOMContentLoaded', connect);
})();
