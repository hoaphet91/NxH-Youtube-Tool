// ============================================================
// TIỆN ÍCH CHUNG
// ============================================================
function $(sel) { return document.querySelector(sel); }
function $all(sel) { return Array.from(document.querySelectorAll(sel)); }

function toast(msg, isError) {
  const root = $('#toastRoot');
  const el = document.createElement('div');
  el.className = 'toast' + (isError ? ' error' : '');
  el.textContent = msg;
  root.appendChild(el);
  setTimeout(() => el.remove(), 3600);
}

async function api(path, opts = {}) {
  const res = await fetch(path, opts);
  if (res.status === 401) {
    window.location.href = '/login';
    throw new Error('unauthorized');
  }
  if (!res.ok) {
    let detail = res.statusText;
    try { const j = await res.json(); detail = j.detail || j.error || detail; } catch (e) {}
    throw new Error(detail);
  }
  const ct = res.headers.get('content-type') || '';
  return ct.includes('application/json') ? res.json() : res.text();
}

async function apiJSON(path, method, body) {
  return api(path, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: body !== undefined ? JSON.stringify(body) : undefined,
  });
}

// ============================================================
// TAB SWITCHING
// ============================================================
$all('#tabNav button').forEach((btn) => {
  btn.addEventListener('click', () => {
    $all('#tabNav button').forEach((b) => b.classList.remove('active'));
    btn.classList.add('active');
    $all('.tab-panel').forEach((p) => p.classList.remove('active'));
    $('#tab-' + btn.dataset.tab).classList.add('active');
  });
});

$('#btnLogout').addEventListener('click', async () => {
  await apiJSON('/api/logout', 'POST');
  window.location.href = '/login';
});

// ============================================================
// TAB: KỊCH BẢN
// ============================================================
function estimateScriptStats(text) {
  const chars = text.length;
  let scenes;
  if (text.includes('[SCENE]')) {
    scenes = (text.match(/\[SCENE\]/g) || []).length;
  } else {
    scenes = text.split(/\n\s*\n/).map((p) => p.trim()).filter(Boolean).length;
  }
  return `${chars} ký tự · ~${scenes} cảnh ước tính`;
}

function refreshScriptStats() {
  $('#scriptStats').textContent = estimateScriptStats($('#scriptText').value);
}

$('#scriptText').addEventListener('input', refreshScriptStats);

$('#scriptDrop').addEventListener('click', () => $('#scriptFileInput').click());
setupDropZone($('#scriptDrop'), async (files) => {
  if (!files.length) return;
  await uploadScriptFile(files[0]);
});
$('#scriptFileInput').addEventListener('change', async (e) => {
  if (e.target.files.length) await uploadScriptFile(e.target.files[0]);
  e.target.value = '';
});

async function uploadScriptFile(file) {
  const fd = new FormData();
  fd.append('file', file);
  try {
    const data = await api('/api/script/upload', { method: 'POST', body: fd });
    $('#scriptText').value = data.content;
    refreshScriptStats();
    toast('Đã tải kịch bản: ' + file.name);
  } catch (e) {
    toast('Lỗi tải kịch bản: ' + e.message, true);
  }
}

$('#btnSaveScript').addEventListener('click', async () => {
  try {
    await apiJSON('/api/script', 'POST', { content: $('#scriptText').value });
    toast('Đã lưu kịch bản.');
  } catch (e) {
    toast('Lỗi lưu kịch bản: ' + e.message, true);
  }
});

async function loadScript() {
  try {
    const data = await api('/api/script');
    $('#scriptText').value = data.content || '';
    refreshScriptStats();
  } catch (e) { /* im lặng, có thể chưa đăng nhập */ }
}

// ============================================================
// DROP ZONE TIỆN ÍCH DÙNG CHUNG
// ============================================================
function setupDropZone(el, onFiles) {
  ['dragover', 'dragenter'].forEach((ev) => el.addEventListener(ev, (e) => {
    e.preventDefault(); el.classList.add('dragover');
  }));
  ['dragleave', 'drop'].forEach((ev) => el.addEventListener(ev, (e) => {
    e.preventDefault(); el.classList.remove('dragover');
  }));
  el.addEventListener('drop', (e) => {
    const files = Array.from(e.dataTransfer.files || []);
    onFiles(files);
  });
}

// ============================================================
// TAB: ẢNH & VIDEO
// ============================================================
let imageQueue = []; // File[] theo đúng thứ tự sẽ upload
let videoQueue = [];

function renderImageQueue() {
  const grid = $('#imagePreviewGrid');
  grid.innerHTML = '';
  imageQueue.forEach((file, idx) => {
    const item = document.createElement('div');
    item.className = 'thumb-item';
    const img = document.createElement('img');
    img.src = URL.createObjectURL(file);
    const num = document.createElement('div');
    num.className = 'thumb-num';
    num.textContent = idx + 1;
    const rm = document.createElement('button');
    rm.className = 'thumb-remove';
    rm.textContent = '✕';
    rm.title = 'Bỏ ảnh này';
    rm.addEventListener('click', () => { imageQueue.splice(idx, 1); renderImageQueue(); });
    item.appendChild(img);
    item.appendChild(num);
    item.appendChild(rm);
    item.title = 'Bấm giữ để kéo sắp xếp lại (máy tính) — hoặc dùng nút ✕ rồi chọn lại theo thứ tự mong muốn (điện thoại)';
    item.draggable = true;
    item.addEventListener('dragstart', (e) => e.dataTransfer.setData('text/plain', String(idx)));
    item.addEventListener('dragover', (e) => e.preventDefault());
    item.addEventListener('drop', (e) => {
      e.preventDefault();
      const from = parseInt(e.dataTransfer.getData('text/plain'), 10);
      const [moved] = imageQueue.splice(from, 1);
      imageQueue.splice(idx, 0, moved);
      renderImageQueue();
    });
    grid.appendChild(item);
  });
}

$('#imageDrop').addEventListener('click', () => $('#imageFileInput').click());
setupDropZone($('#imageDrop'), (files) => {
  imageQueue = imageQueue.concat(files.filter((f) => /\.(png|jpe?g)$/i.test(f.name)));
  renderImageQueue();
});
$('#imageFileInput').addEventListener('change', (e) => {
  imageQueue = imageQueue.concat(Array.from(e.target.files));
  renderImageQueue();
  e.target.value = '';
});
$('#btnClearImageQueue').addEventListener('click', () => { imageQueue = []; renderImageQueue(); });

$('#btnUploadImages').addEventListener('click', async () => {
  if (!imageQueue.length) { toast('Chưa chọn ảnh nào.', true); return; }
  const fd = new FormData();
  imageQueue.forEach((f) => fd.append('files', f));
  fd.append('clear_existing', $('#imageClearExisting').checked ? 'true' : 'false');
  try {
    const data = await api('/api/images', { method: 'POST', body: fd });
    toast(`Đã tải lên ${data.count} ảnh theo đúng thứ tự.`);
    imageQueue = [];
    renderImageQueue();
    await refreshServerImages();
  } catch (e) {
    toast('Lỗi tải ảnh: ' + e.message, true);
  }
});

async function refreshServerImages() {
  try {
    const data = await api('/api/images');
    const list = $('#serverImageList');
    list.innerHTML = '';
    data.files.forEach((name, idx) => {
      const chip = document.createElement('div');
      chip.className = 'file-chip';
      chip.innerHTML = `<span class="idx">${idx + 1}</span><span>${name}</span>`;
      list.appendChild(chip);
    });
    if (!data.files.length) list.innerHTML = '<span class="hint">Chưa có ảnh nào trên máy chủ.</span>';
  } catch (e) {}
}

$('#btnRefreshImages').addEventListener('click', refreshServerImages);
$('#btnDeleteAllImages').addEventListener('click', async () => {
  if (!confirm('Xoá toàn bộ ảnh trên máy chủ?')) return;
  await api('/api/images', { method: 'DELETE' });
  toast('Đã xoá toàn bộ ảnh.');
  refreshServerImages();
});

// --- Video dựng sẵn ---
function renderVideoQueue() {
  const list = $('#videoQueueList');
  list.innerHTML = '';
  videoQueue.forEach((file, idx) => {
    const chip = document.createElement('div');
    chip.className = 'file-chip';
    chip.innerHTML = `<span>${file.name}</span><button data-idx="${idx}">✕</button>`;
    chip.querySelector('button').addEventListener('click', () => { videoQueue.splice(idx, 1); renderVideoQueue(); });
    list.appendChild(chip);
  });
}
$('#videoDrop').addEventListener('click', () => $('#videoFileInput').click());
setupDropZone($('#videoDrop'), (files) => { videoQueue = videoQueue.concat(files); renderVideoQueue(); });
$('#videoFileInput').addEventListener('change', (e) => {
  videoQueue = videoQueue.concat(Array.from(e.target.files));
  renderVideoQueue();
  e.target.value = '';
});

$('#btnUploadVideos').addEventListener('click', async () => {
  if (!videoQueue.length) { toast('Chưa chọn video nào.', true); return; }
  const fd = new FormData();
  videoQueue.forEach((f) => fd.append('files', f));
  try {
    const data = await api('/api/videos', { method: 'POST', body: fd });
    toast(`Đã tải lên ${data.saved.length} video.`);
    videoQueue = [];
    renderVideoQueue();
    await refreshServerVideos();
  } catch (e) {
    toast('Lỗi tải video: ' + e.message, true);
  }
});

async function refreshServerVideos() {
  try {
    const data = await api('/api/videos');
    const list = $('#serverVideoList');
    list.innerHTML = '';
    data.files.forEach((name) => {
      const chip = document.createElement('div');
      chip.className = 'file-chip';
      chip.innerHTML = `<span>${name}</span><button>✕</button>`;
      chip.querySelector('button').addEventListener('click', async () => {
        await api('/api/videos/' + encodeURIComponent(name), { method: 'DELETE' });
        refreshServerVideos();
      });
      list.appendChild(chip);
    });
    if (!data.files.length) list.innerHTML = '<span class="hint">Chưa có video nào trên máy chủ.</span>';
  } catch (e) {}
}

// ============================================================
// TAB: AUDIO TEST
// ============================================================
let audioQueue = [];
function renderAudioQueue() {
  const list = $('#audioQueueList');
  list.innerHTML = '';
  audioQueue.forEach((file, idx) => {
    const chip = document.createElement('div');
    chip.className = 'file-chip';
    chip.innerHTML = `<span class="idx">${idx + 1}</span><span>${file.name}</span><button>✕</button>`;
    chip.querySelector('button').addEventListener('click', () => { audioQueue.splice(idx, 1); renderAudioQueue(); });
    list.appendChild(chip);
  });
}
$('#audioDrop').addEventListener('click', () => $('#audioFileInput').click());
setupDropZone($('#audioDrop'), (files) => { audioQueue = audioQueue.concat(files); renderAudioQueue(); });
$('#audioFileInput').addEventListener('change', (e) => {
  audioQueue = audioQueue.concat(Array.from(e.target.files));
  renderAudioQueue();
  e.target.value = '';
});

$('#btnUploadAudio').addEventListener('click', async () => {
  if (!audioQueue.length) { toast('Chưa chọn audio nào.', true); return; }
  const fd = new FormData();
  audioQueue.forEach((f) => fd.append('files', f));
  fd.append('clear_existing', $('#audioClearExisting').checked ? 'true' : 'false');
  try {
    const data = await api('/api/audio', { method: 'POST', body: fd });
    toast(`Đã tải lên ${data.count} audio theo đúng thứ tự.`);
    audioQueue = [];
    renderAudioQueue();
    await refreshServerAudio();
  } catch (e) {
    toast('Lỗi tải audio: ' + e.message, true);
  }
});

async function refreshServerAudio() {
  try {
    const data = await api('/api/audio');
    const list = $('#serverAudioList');
    list.innerHTML = '';
    data.files.forEach((name, idx) => {
      const chip = document.createElement('div');
      chip.className = 'file-chip';
      chip.innerHTML = `<span class="idx">${idx + 1}</span><span>${name}</span>`;
      list.appendChild(chip);
    });
    if (!data.files.length) list.innerHTML = '<span class="hint">Chưa có audio nào trên máy chủ.</span>';
  } catch (e) {}
}
$('#btnRefreshAudio').addEventListener('click', refreshServerAudio);
$('#btnDeleteAllAudio').addEventListener('click', async () => {
  if (!confirm('Xoá toàn bộ audio trên máy chủ?')) return;
  await api('/api/audio', { method: 'DELETE' });
  toast('Đã xoá toàn bộ audio.');
  refreshServerAudio();
});

// ============================================================
// TAB: CẤU HÌNH
// ============================================================
const CONFIG_GROUPS = [
  { title: 'TTS — Giọng đọc', fields: [
    { key: 'TTS_ENABLED', label: 'Bật gọi API TTS thật (tắt = dùng audio test)', type: 'bool', def: 'true' },
    { key: 'TTS_PROVIDER', label: 'Nhà cung cấp TTS', type: 'select', opts: ['edge', 'elevenlabs', 'openai'], def: 'edge' },
    { key: 'ELEVENLABS_API_KEY', label: 'ElevenLabs API Key', type: 'password' },
    { key: 'ELEVENLABS_VOICE_ID', label: 'ElevenLabs Voice ID', type: 'text' },
    { key: 'OPENAI_API_KEY', label: 'OpenAI API Key', type: 'password' },
    { key: 'EDGE_TTS_VOICE', label: 'Giọng Edge-TTS', type: 'text', def: 'en-US-AndrewNeural' },
    { key: 'EDGE_TTS_RATE', label: 'Tốc độ đọc (VD -15%)', type: 'text', def: '-15%' },
    { key: 'EDGE_TTS_PITCH', label: 'Cao độ giọng (VD -10Hz)', type: 'text', def: '-10Hz' },
  ]},
  { title: 'Nhạc nền (Freesound)', fields: [
    { key: 'MUSIC_ENABLED', label: 'Bật nhạc nền', type: 'bool', def: 'true' },
    { key: 'FREESOUND_API_KEY', label: 'Freesound API Key', type: 'password' },
    { key: 'MUSIC_VOLUME', label: 'Âm lượng nhạc nền (0-1)', type: 'number', step: '0.01', def: '0.12' },
  ]},
  { title: 'Hiệu ứng Ken Burns', fields: [
    { key: 'EFFECT_SELECTION_MODE', label: 'Chế độ chọn hiệu ứng', type: 'select', opts: ['heuristic', 'ai'], def: 'heuristic' },
    { key: 'KEN_BURNS_ZOOM_RATIO', label: 'Tỉ lệ phóng to dự phòng', type: 'number', step: '0.01', def: '1.15' },
  ]},
  { title: 'Chuyển cảnh & Timing', fields: [
    { key: 'TRANSITION_STYLE', label: 'Kiểu chuyển cảnh', type: 'select', opts: ['crossfade', 'fade_black'], def: 'crossfade' },
    { key: 'SCENE_AUDIO_GAP', label: 'Khoảng lặng giữa 2 cảnh (giây)', type: 'number', step: '0.01', def: '0.95' },
    { key: 'VIDEO_ORIGINAL_AUDIO_VOLUME', label: 'Âm lượng gốc của video dựng sẵn (0-1)', type: 'number', step: '0.01', def: '0.3' },
  ]},
  { title: 'Phụ đề (Whisper)', fields: [
    { key: 'WHISPER_MODEL_SIZE', label: 'Model Whisper', type: 'select', opts: ['tiny', 'base', 'small', 'medium', 'large-v3'], def: 'small' },
    { key: 'WHISPER_DEVICE', label: 'Thiết bị chạy Whisper', type: 'select', opts: ['cpu', 'cuda'], def: 'cpu' },
    { key: 'WHISPER_COMPUTE_TYPE', label: 'Compute type', type: 'select', opts: ['int8', 'float16'], def: 'int8' },
  ]},
  { title: 'Encoder video', fields: [
    { key: 'VIDEO_ENCODER', label: 'Encoder', type: 'select', opts: ['h264_nvenc', 'libx264'], def: 'h264_nvenc' },
    { key: 'VIDEO_NVENC_PRESET', label: 'NVENC Preset (p1 nhanh — p7 nén tốt)', type: 'text', def: 'p5' },
    { key: 'VIDEO_CQ', label: 'NVENC CQ (thấp = nét hơn)', type: 'number', def: '18' },
    { key: 'VIDEO_PRESET', label: 'libx264 preset', type: 'text', def: 'medium' },
    { key: 'VIDEO_CRF', label: 'libx264 CRF', type: 'number', def: '18' },
  ]},
  { title: 'Khác', fields: [
    { key: 'IMAGES_ARE_AI_GENERATED', label: 'Ảnh gốc do AI tạo? (bật "Altered content" khi đăng)', type: 'bool', def: 'false' },
  ]},
];

function renderConfigForm() {
  const container = $('#configFormContainer');
  container.innerHTML = '';
  CONFIG_GROUPS.forEach((group) => {
    const h3 = document.createElement('h3');
    h3.textContent = group.title;
    container.appendChild(h3);
    const grid = document.createElement('div');
    grid.className = 'grid-2';
    group.fields.forEach((f) => {
      const wrap = document.createElement('div');
      const label = document.createElement('label');
      label.textContent = f.label;
      wrap.appendChild(label);
      let input;
      if (f.type === 'select') {
        input = document.createElement('select');
        f.opts.forEach((o) => {
          const opt = document.createElement('option');
          opt.value = o; opt.textContent = o;
          input.appendChild(opt);
        });
      } else if (f.type === 'bool') {
        const row = document.createElement('div');
        row.className = 'checkbox-row';
        input = document.createElement('input');
        input.type = 'checkbox';
        input.id = 'cfg_' + f.key;
        const lbl2 = document.createElement('label');
        lbl2.setAttribute('for', input.id);
        lbl2.textContent = 'Bật';
        row.appendChild(input);
        row.appendChild(lbl2);
        wrap.appendChild(row);
        grid.appendChild(wrap);
        input.dataset.key = f.key;
        input.dataset.type = 'bool';
        return;
      } else {
        input = document.createElement('input');
        input.type = f.type === 'password' ? 'password' : (f.type === 'number' ? 'number' : 'text');
        if (f.step) input.step = f.step;
      }
      input.id = 'cfg_' + f.key;
      input.dataset.key = f.key;
      input.dataset.type = f.type;
      wrap.appendChild(input);
      grid.appendChild(wrap);
    });
    container.appendChild(grid);
  });
}

async function loadConfig() {
  renderConfigForm();
  try {
    const env = await api('/api/config');
    $('#cfg_WEBUI_PASSWORD').value = env['WEBUI_PASSWORD'] || '';
    CONFIG_GROUPS.forEach((group) => group.fields.forEach((f) => {
      const el = document.getElementById('cfg_' + f.key);
      if (!el) return;
      const val = env[f.key] !== undefined ? env[f.key] : (f.def || '');
      if (f.type === 'bool') {
        el.checked = String(val).toLowerCase() === 'true';
      } else {
        el.value = val;
      }
    }));
  } catch (e) {}
}

$('#btnSaveConfig').addEventListener('click', async () => {
  const payload = { WEBUI_PASSWORD: $('#cfg_WEBUI_PASSWORD').value };
  $all('[data-key]').forEach((el) => {
    if (el.dataset.type === 'bool') {
      payload[el.dataset.key] = el.checked ? 'true' : 'false';
    } else {
      payload[el.dataset.key] = el.value;
    }
  });
  try {
    await apiJSON('/api/config', 'POST', payload);
    toast('Đã lưu cấu hình.');
  } catch (e) {
    toast('Lỗi lưu cấu hình: ' + e.message, true);
  }
});

// ============================================================
// TAB: CHẠY
// ============================================================
let ws = null;
let currentRunning = false;

function appendLog(line) {
  const box = $('#logConsole');
  const div = document.createElement('div');
  if (/lỗi|error/i.test(line)) div.className = 'log-err';
  else if (/^\[\d+\/\d+\]|^===/.test(line)) div.className = 'log-step';
  div.textContent = line;
  box.appendChild(div);
  box.scrollTop = box.scrollHeight;
  updateProgressFromLog(line);
}

function updateProgressFromLog(line) {
  const pctLabel = $('#progressLabel');
  const pctText = $('#progressPct');
  const m = line.match(/\[(\d+)\/(\d+)\]/);
  if (m) {
    const current = parseInt(m[1], 10);
    const total = parseInt(m[2], 10);
    const pct = Math.min(100, Math.round((current / total) * 100));
    $('#progressFill').style.width = pct + '%';
    pctText.textContent = pct + '%';
    pctLabel.textContent = `Đang chạy ${current}/${total}`;
  }
  if (/HOÀN TẤT|=== KẾT THÚC/.test(line)) {
    $('#progressFill').style.width = '100%';
    pctText.textContent = '100%';
    pctLabel.textContent = 'Hoàn tất';
  }
}

function connectWebSocket() {
  if (ws) { try { ws.close(); } catch (e) {} }
  const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
  ws = new WebSocket(`${proto}://${window.location.host}/ws/log`);
  ws.onmessage = (evt) => appendLog(evt.data);
  ws.onclose = () => { setTimeout(() => { if (document.visibilityState !== 'hidden') connectWebSocket(); }, 3000); };
}

function setStatusDot(status) {
  const dot = $('#statusDot');
  dot.className = 'status-dot ' + (status === 'running' ? 'running' : status === 'success' ? 'success' : status === 'error' ? 'error' : '');
}

function setRunBadge(status) {
  const badge = $('#runBadge');
  const map = { idle: 'chưa chạy', running: 'đang chạy', success: 'thành công', error: 'lỗi' };
  badge.className = 'badge ' + status;
  badge.textContent = map[status] || status;
}

async function refreshRunStatus() {
  try {
    const s = await api('/api/run/status');
    currentRunning = s.running;
    setStatusDot(s.running ? 'running' : s.status);
    setRunBadge(s.running ? 'running' : s.status);
    $('#btnStartRun').disabled = s.running;
    $('#btnCancelRun').disabled = !s.running;
    if (s.title) {
      $('#runMeta').textContent = `Video: "${s.title}" → ${s.output_name} | Bắt đầu: ${s.started_at || '-'} | Kết thúc: ${s.finished_at || 'đang chạy...'}`;
    }
  } catch (e) {}
}

$('#btnStartRun').addEventListener('click', async () => {
  const title = $('#runTitle').value.trim();
  if (!title) { toast('Vui lòng nhập tiêu đề video.', true); return; }
  const output = $('#runOutput').value.trim() || 'final_video.mp4';
  $('#logConsole').innerHTML = '';
  $('#progressFill').style.width = '0%';
  try {
    await apiJSON('/api/run', 'POST', { title, output_name: output });
    toast('Đã bắt đầu chạy pipeline.');
    refreshRunStatus();
  } catch (e) {
    toast('Không thể bắt đầu: ' + e.message, true);
  }
});

$('#btnCancelRun').addEventListener('click', async () => {
  if (!confirm('Huỷ tiến trình đang chạy?')) return;
  await apiJSON('/api/run/cancel', 'POST', {});
  refreshRunStatus();
});

// ============================================================
// TAB: KẾT QUẢ
// ============================================================
function humanSize(bytes) {
  if (bytes > 1024 * 1024 * 1024) return (bytes / 1024 / 1024 / 1024).toFixed(2) + ' GB';
  if (bytes > 1024 * 1024) return (bytes / 1024 / 1024).toFixed(1) + ' MB';
  if (bytes > 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return bytes + ' B';
}

async function refreshOutputs() {
  try {
    const data = await api('/api/outputs');
    const container = $('#outputsList');
    container.innerHTML = '';
    if (!data.files.length) {
      container.innerHTML = '<span class="hint">Chưa có kết quả nào.</span>';
      return;
    }
    data.files.forEach((f) => {
      const wrap = document.createElement('div');
      wrap.className = 'result-item';
      wrap.style.flexDirection = 'column';
      wrap.style.alignItems = 'stretch';
      const top = document.createElement('div');
      top.style.display = 'flex';
      top.style.justifyContent = 'space-between';
      top.innerHTML = `<b>${f.name}</b><span class="meta">${humanSize(f.size)}</span>`;
      wrap.appendChild(top);
      if (/\.mp4$/i.test(f.name)) {
        const video = document.createElement('video');
        video.className = 'result-video';
        video.controls = true;
        video.src = '/api/outputs/' + encodeURIComponent(f.name);
        wrap.appendChild(video);
      }
      const btnRow = document.createElement('div');
      btnRow.className = 'btn-row';
      const dl = document.createElement('a');
      dl.className = 'btn small secondary';
      dl.href = '/api/outputs/' + encodeURIComponent(f.name);
      dl.textContent = '⬇ Tải xuống';
      dl.setAttribute('download', f.name);
      const del = document.createElement('button');
      del.className = 'btn small danger';
      del.textContent = 'Xoá';
      del.addEventListener('click', async () => {
        if (!confirm('Xoá file này?')) return;
        await api('/api/outputs/' + encodeURIComponent(f.name), { method: 'DELETE' });
        refreshOutputs();
      });
      btnRow.appendChild(dl);
      btnRow.appendChild(del);
      wrap.appendChild(btnRow);
      container.appendChild(wrap);
    });
  } catch (e) {}
}
$('#btnRefreshOutputs').addEventListener('click', refreshOutputs);

async function refreshHistory() {
  try {
    const data = await api('/api/history');
    const container = $('#historyList');
    container.innerHTML = '';
    if (!data.jobs.length) { container.innerHTML = '<span class="hint">Chưa có lịch sử.</span>'; return; }
    data.jobs.forEach((j) => {
      const item = document.createElement('div');
      item.className = 'result-item';
      item.innerHTML = `<div><b>${j.title || '(?)'}</b><div class="meta">${j.output_name || ''} · ${j.finished_at || ''}</div></div>
        <span class="badge ${j.status}">${j.status}</span>`;
      container.appendChild(item);
    });
  } catch (e) {}
}

// ============================================================
// KHỞI TẠO
// ============================================================
async function init() {
  await loadScript();
  await loadConfig();
  await refreshServerImages();
  await refreshServerVideos();
  await refreshServerAudio();
  await refreshRunStatus();
  await refreshOutputs();
  await refreshHistory();
  connectWebSocket();
  setInterval(refreshRunStatus, 4000);
  setInterval(() => { if (!currentRunning) { refreshOutputs(); refreshHistory(); } }, 9000);
}
init();
