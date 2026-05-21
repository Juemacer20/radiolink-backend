'use strict';

const API = '';  // misma origin
let role = 'A';
let targetAzimuth = 0;
let currentHeading = 0;
let linkId = null;
let ws = null;
let profileChart = null;
const ALIGN_TOLERANCE = 5;

// ── Role selector ──────────────────────────────────────────────
function selectRole(r) {
  role = r;
  document.getElementById('btn-role-a').classList.toggle('active', r === 'A');
  document.getElementById('btn-role-b').classList.toggle('active', r === 'B');
}

// ── GPS ────────────────────────────────────────────────────────
function getGPS(tower) {
  if (!navigator.geolocation) { showToast('GPS no disponible'); return; }
  showToast('Obteniendo GPS...');
  navigator.geolocation.getCurrentPosition(
    pos => {
      document.getElementById(`lat_${tower}`).value = pos.coords.latitude.toFixed(6);
      document.getElementById(`lon_${tower}`).value = pos.coords.longitude.toFixed(6);
      showToast(`GPS Torre ${tower.toUpperCase()} capturado`);
    },
    () => showToast('No se pudo obtener el GPS')
  );
}

// ── Form submit ────────────────────────────────────────────────
document.getElementById('form-setup').addEventListener('submit', async e => {
  e.preventDefault();
  const btn = document.getElementById('btn-calcular');
  btn.disabled = true;
  btn.textContent = '⏳ Calculando...';

  const body = {
    name:     document.getElementById('link_name').value,
    tower_a:  { lat: +document.getElementById('lat_a').value, lon: +document.getElementById('lon_a').value, height_m: +document.getElementById('h_a').value },
    tower_b:  { lat: +document.getElementById('lat_b').value, lon: +document.getElementById('lon_b').value, height_m: +document.getElementById('h_b').value },
    frequency_ghz: +document.getElementById('freq').value,
    profile_points: +document.getElementById('pts').value,
  };

  try {
    const res = await fetch(`${API}/api/v1/links/analyze`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`Error ${res.status}`);
    const data = await res.json();
    showOrientation(data);
  } catch (err) {
    showToast('Error: ' + err.message);
  } finally {
    btn.disabled = false;
    btn.textContent = '📐 Calcular enlace';
  }
});

// ── Orientation view ───────────────────────────────────────────
function showOrientation(data) {
  const ori = role === 'A' ? data.tower_a_orientation : data.tower_b_orientation;
  targetAzimuth = ori.azimuth_deg;
  linkId = data.link_id;

  document.getElementById('header-name').textContent = data.name;
  document.getElementById('stat-dist').textContent   = formatDist(data.total_distance_m);
  document.getElementById('stat-az').textContent     = ori.azimuth_deg.toFixed(1) + '°';
  document.getElementById('stat-el').textContent     = (ori.elevation_angle_deg > 0 ? '+' : '') + ori.elevation_angle_deg.toFixed(2) + '°';

  const a = data.analysis;
  const fPct = a ? a.fresnel_clearance_pct : null;
  document.getElementById('stat-fresnel').textContent = fPct != null ? fPct.toFixed(0) + '%' : '—';

  showView('view-orientation');
  drawCompass();
  buildProfileChart(data.terrain_profile);
  buildAnalysisDetail(data);
  connectWS();
  startOrientation();
}

function goBack() {
  disconnectWS();
  stopOrientation();
  showView('view-setup');
}

function showView(id) {
  document.querySelectorAll('.view').forEach(v => v.classList.remove('active'));
  document.getElementById(id).classList.add('active');
  window.scrollTo(0, 0);
}

// ── Compass ────────────────────────────────────────────────────
const COMPASS_SIZE = 300;
const R = COMPASS_SIZE / 2;

function drawCompass() {
  const canvas = document.getElementById('compass');
  const ctx = canvas.getContext('2d');
  ctx.clearRect(0, 0, COMPASS_SIZE, COMPASS_SIZE);

  // Background circle
  ctx.beginPath(); ctx.arc(R, R, R - 4, 0, 2 * Math.PI);
  ctx.fillStyle = '#161B22'; ctx.fill();
  ctx.strokeStyle = '#30363D'; ctx.lineWidth = 2; ctx.stroke();

  // Tick marks + cardinal labels
  const cardinals = ['N', 'E', 'S', 'O'];
  for (let i = 0; i < 360; i += 10) {
    const angle = (i - currentHeading) * Math.PI / 180;
    const isCard = i % 90 === 0;
    const isMajor = i % 45 === 0;
    const r1 = isCard ? R - 26 : isMajor ? R - 20 : R - 14;
    const r2 = R - 8;
    ctx.beginPath();
    ctx.moveTo(R + r1 * Math.sin(angle), R - r1 * Math.cos(angle));
    ctx.lineTo(R + r2 * Math.sin(angle), R - r2 * Math.cos(angle));
    ctx.strokeStyle = isCard ? '#E6EDF3' : '#8B949E';
    ctx.lineWidth = isCard ? 2 : 1;
    ctx.stroke();
    if (isCard) {
      const tr = R - 40;
      ctx.fillStyle = i === 0 ? '#F85149' : '#E6EDF3';
      ctx.font = `bold 14px -apple-system, sans-serif`;
      ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
      ctx.fillText(cardinals[i / 90], R + tr * Math.sin(angle), R - tr * Math.cos(angle));
    }
  }

  // Target azimuth line (blue or green)
  const diffRaw = ((targetAzimuth - currentHeading) % 360 + 360) % 360;
  const diff = diffRaw > 180 ? diffRaw - 360 : diffRaw;
  const aligned = Math.abs(diff) <= ALIGN_TOLERANCE;
  const targetAngle = (targetAzimuth - currentHeading) * Math.PI / 180;

  ctx.beginPath();
  ctx.moveTo(R, R);
  ctx.lineTo(R + (R - 30) * Math.sin(targetAngle), R - (R - 30) * Math.cos(targetAngle));
  ctx.strokeStyle = aligned ? '#3FB950' : '#44AAFF';
  ctx.lineWidth = 3;
  ctx.setLineDash([8, 4]);
  ctx.stroke();
  ctx.setLineDash([]);

  // Azimuth label at tip
  const lx = R + (R - 16) * Math.sin(targetAngle);
  const ly = R - (R - 16) * Math.cos(targetAngle);
  ctx.beginPath(); ctx.arc(lx, ly, 10, 0, 2 * Math.PI);
  ctx.fillStyle = aligned ? '#3FB950' : '#44AAFF'; ctx.fill();
  ctx.fillStyle = '#000'; ctx.font = 'bold 8px sans-serif';
  ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
  ctx.fillText('AZ', lx, ly);

  // Current heading needle (red)
  ctx.beginPath();
  ctx.moveTo(R, R + 15);
  ctx.lineTo(R - 8, R + 8);
  ctx.lineTo(R, R - (R - 30));
  ctx.lineTo(R + 8, R + 8);
  ctx.closePath();
  ctx.fillStyle = '#F85149'; ctx.fill();

  // Center dot
  ctx.beginPath(); ctx.arc(R, R, 6, 0, 2 * Math.PI);
  ctx.fillStyle = '#E6EDF3'; ctx.fill();

  // Alignment banner update
  updateAlignmentBanner(diff, aligned);

  // Send WS update
  if (ws && ws.readyState === WebSocket.OPEN) {
    ws.send(JSON.stringify({ role, aligned, heading: currentHeading, azimuth: targetAzimuth }));
  }
}

function updateAlignmentBanner(diff, aligned) {
  const banner = document.getElementById('alignment-banner');
  const txt = document.getElementById('alignment-text');
  if (aligned) {
    banner.className = 'alignment-banner aligned';
    txt.textContent = `✓ ALINEADO — Azimut ${targetAzimuth.toFixed(1)}°`;
  } else if (Math.abs(diff) <= 20) {
    banner.className = 'alignment-banner warning';
    const dir = diff > 0 ? 'derecha' : 'izquierda';
    txt.textContent = `Girá ${Math.abs(diff).toFixed(0)}° hacia la ${dir}`;
  } else {
    banner.className = 'alignment-banner';
    const dir = diff > 0 ? 'derecha →' : '← izquierda';
    txt.textContent = `Girá hacia ${dir} (${Math.abs(diff).toFixed(0)}° restantes)`;
  }
}

// ── Device Orientation ─────────────────────────────────────────
let orientationHandler = null;

function startOrientation() {
  if (typeof DeviceOrientationEvent === 'undefined') {
    document.getElementById('compass-hint').textContent = 'Brújula no disponible en este dispositivo';
    return;
  }
  if (typeof DeviceOrientationEvent.requestPermission === 'function') {
    DeviceOrientationEvent.requestPermission()
      .then(state => { if (state === 'granted') listenOrientation(); })
      .catch(() => {});
  } else {
    listenOrientation();
  }
}

function listenOrientation() {
  document.getElementById('compass-hint').textContent = 'Brújula activa — apuntá hacia la antena';
  orientationHandler = e => {
    if (e.webkitCompassHeading != null) {
      currentHeading = e.webkitCompassHeading;
    } else if (e.alpha != null) {
      currentHeading = (360 - e.alpha) % 360;
    }
    drawCompass();
  };
  window.addEventListener('deviceorientation', orientationHandler, true);
}

function stopOrientation() {
  if (orientationHandler) {
    window.removeEventListener('deviceorientation', orientationHandler, true);
    orientationHandler = null;
  }
}

// ── WebSocket ──────────────────────────────────────────────────
function connectWS() {
  if (!linkId) return;
  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  const url = `${proto}://${location.host}/ws/link/${linkId}`;
  ws = new WebSocket(url);

  ws.onopen = () => {
    document.getElementById('partner-dot').classList.add('online');
  };
  ws.onmessage = e => {
    try {
      const msg = JSON.parse(e.data);
      const partnerRole = msg.role === 'A' ? 'B' : 'A';
      const icon = msg.aligned ? '✅' : '⏳';
      document.getElementById('partner-text').textContent =
        `Torre ${msg.role} ${icon} — Rumbo actual: ${msg.heading != null ? msg.heading.toFixed(0) + '°' : '—'}`;
      document.getElementById('partner-dot').classList.add('online');
    } catch {}
  };
  ws.onclose = () => {
    document.getElementById('partner-dot').classList.remove('online');
    document.getElementById('partner-text').textContent = 'Técnico en la otra torre: desconectado';
  };
}

function disconnectWS() {
  if (ws) { ws.close(); ws = null; }
}

// ── Terrain Profile Chart ──────────────────────────────────────
function buildProfileChart(profile) {
  if (profileChart) { profileChart.destroy(); profileChart = null; }

  const labels   = profile.map(p => (p.distance_m / 1000).toFixed(2));
  const terrain  = profile.map(p => p.elevation_m);
  const los      = profile.map(p => p.los_height_m);
  const obsX     = profile.filter(p => p.is_obstructed).map(p => (p.distance_m / 1000).toFixed(2));
  const obsY     = profile.filter(p => p.is_obstructed).map(p => p.elevation_m);

  const ctx = document.getElementById('profile-chart').getContext('2d');
  profileChart = new Chart(ctx, {
    type: 'line',
    data: {
      labels,
      datasets: [
        {
          label: 'Terreno', data: terrain,
          borderColor: '#8B6914', backgroundColor: 'rgba(139,105,20,0.3)',
          fill: true, tension: 0.3, pointRadius: 0, borderWidth: 2,
        },
        {
          label: 'LOS', data: los,
          borderColor: '#44AAFF', borderDash: [8, 4],
          fill: false, tension: 0, pointRadius: 0, borderWidth: 2,
        },
        {
          label: 'Obstrucciones',
          data: labels.map((l, i) => obsX.includes(l) ? obsY[obsX.indexOf(l)] : null),
          borderColor: 'transparent',
          backgroundColor: '#F85149',
          pointRadius: 5, pointStyle: 'circle', showLine: false,
        },
      ],
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      animation: false,
      plugins: { legend: { display: false } },
      scales: {
        x: {
          ticks: { color: '#8B949E', maxTicksLimit: 6,
            callback: (v, i) => labels[i] + ' km' },
          grid: { color: '#21262D' },
        },
        y: {
          ticks: { color: '#8B949E', callback: v => v + 'm' },
          grid: { color: '#21262D' },
        },
      },
    },
  });
}

// ── Analysis detail ────────────────────────────────────────────
function buildAnalysisDetail(data) {
  const a = data.analysis || {};
  const ori = role === 'A' ? data.tower_a_orientation : data.tower_b_orientation;
  const otherOri = role === 'A' ? data.tower_b_orientation : data.tower_a_orientation;
  const fPct = a.fresnel_clearance_pct;
  const fClass = fPct == null ? '' : fPct >= 60 ? 'ok' : fPct >= 40 ? 'warn' : 'bad';

  const rows = [
    { label: `Azimut Torre ${role}`, val: ori.azimuth_deg.toFixed(2) + '°', cls: '' },
    { label: `Azimut Torre ${role === 'A' ? 'B' : 'A'}`, val: otherOri.azimuth_deg.toFixed(2) + '°', cls: '' },
    { label: 'Elevación', val: (ori.elevation_angle_deg > 0 ? '+' : '') + ori.elevation_angle_deg.toFixed(3) + '°', cls: '' },
    { label: 'Distancia', val: formatDist(data.total_distance_m), cls: '' },
    { label: 'Fresnel libre', val: fPct != null ? fPct.toFixed(1) + '%' : '—', cls: fClass },
    { label: 'Obstrucciones', val: a.obstruction_count != null ? a.obstruction_count : '—',
      cls: a.obstruction_count > 0 ? 'bad' : 'ok' },
    { label: 'Elevación base A', val: data.tower_a_orientation.ground_elevation_m + ' m', cls: '' },
    { label: 'Elevación base B', val: data.tower_b_orientation.ground_elevation_m + ' m', cls: '' },
  ];

  document.getElementById('analysis-detail').innerHTML = rows.map(r =>
    `<div class="analysis-row"><div class="a-label">${r.label}</div><div class="a-val ${r.cls}">${r.val}</div></div>`
  ).join('');
}

// ── Helpers ────────────────────────────────────────────────────
function formatDist(m) {
  return m >= 1000 ? (m / 1000).toFixed(2) + ' km' : m.toFixed(0) + ' m';
}

function showToast(msg, ms = 2500) {
  const t = document.getElementById('toast');
  t.textContent = msg; t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), ms);
}

// Draw initial compass on page load (no heading yet)
window.addEventListener('load', () => drawCompass());
