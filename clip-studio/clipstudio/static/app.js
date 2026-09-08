const $ = (id) => document.getElementById(id);

// --- backend health check ---
async function checkBackend() {
  const el = $('backend-status');
  try {
    const res = await fetch('/api/health');
    if (res.ok) {
      el.textContent = 'backend online';
      el.classList.add('ok');
    } else {
      throw new Error();
    }
  } catch {
    el.textContent = 'backend niet bereikbaar';
    el.classList.add('error');
  }
}
checkBackend();

// --- source tabs ---
document.querySelectorAll('.tab').forEach((tab) => {
  tab.addEventListener('click', () => {
    document.querySelectorAll('.tab').forEach((t) => t.classList.remove('active'));
    tab.classList.add('active');
    document.querySelectorAll('.tab-panel').forEach((p) => p.classList.add('hidden'));
    $(`tab-${tab.dataset.tab}`).classList.remove('hidden');
  });
});

// --- file dropzone ---
const dropzone = $('dropzone');
const fileInput = $('file-input');
let selectedFile = null;

dropzone.addEventListener('click', () => fileInput.click());
fileInput.addEventListener('change', (e) => setFile(e.target.files[0]));
dropzone.addEventListener('dragover', (e) => { e.preventDefault(); dropzone.classList.add('dragover'); });
dropzone.addEventListener('dragleave', () => dropzone.classList.remove('dragover'));
dropzone.addEventListener('drop', (e) => {
  e.preventDefault();
  dropzone.classList.remove('dragover');
  setFile(e.dataTransfer.files[0]);
});

function setFile(file) {
  if (!file) return;
  selectedFile = file;
  $('dropzone-text').textContent = file.name;
}

// --- start clipping ---
$('start-btn').addEventListener('click', startJob);

function currentSettings() {
  return {
    min_clips: parseInt($('min-clips').value, 10),
    max_clips: parseInt($('max-clips').value, 10),
    max_clip_seconds: parseInt($('max-clip-seconds').value, 10),
    preferred_seconds: parseInt($('preferred-seconds').value, 10),
    aspect_ratio: $('aspect-ratio').value,
    resolution: $('resolution').value,
    llm_provider: $('llm-provider').value,
    subtitles: $('subtitles').checked,
    hook: $('hook').checked,
    highest_quality: $('highest-quality').checked,
  };
}

async function startJob() {
  const errorEl = $('error-text');
  errorEl.classList.add('hidden');

  const activeTab = document.querySelector('.tab.active').dataset.tab;
  const youtubeUrl = $('youtube-url').value.trim();

  if (activeTab === 'youtube' && !youtubeUrl) {
    return showError('Vul een YouTube-link in.');
  }
  if (activeTab === 'file' && !selectedFile) {
    return showError('Kies een videobestand.');
  }

  const form = new FormData();
  if (activeTab === 'youtube') form.append('youtube_url', youtubeUrl);
  if (activeTab === 'file') form.append('file', selectedFile);
  form.append('settings', JSON.stringify(currentSettings()));

  $('start-btn').disabled = true;
  $('start-btn').textContent = 'Bezig...';
  $('progress-wrap').classList.remove('hidden');

  try {
    const res = await fetch('/api/jobs', { method: 'POST', body: form });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Onbekende fout' }));
      throw new Error(err.detail || 'Kon job niet starten.');
    }
    const { job_id } = await res.json();
    pollJob(job_id);
  } catch (e) {
    showError(e.message);
    resetStartButton();
  }
}

function showError(msg) {
  const el = $('error-text');
  el.textContent = msg;
  el.classList.remove('hidden');
}

function resetStartButton() {
  $('start-btn').disabled = false;
  $('start-btn').textContent = 'Start clipping';
}

async function pollJob(jobId) {
  const statusLabels = {
    queued: 'In wachtrij…',
    downloading: 'Video downloaden…',
    transcribing: 'Audio transcriberen…',
    selecting: 'AI kiest de beste momenten…',
    rendering: 'Clips renderen…',
    done: 'Klaar!',
    error: 'Fout opgetreden',
  };

  const poll = async () => {
    const res = await fetch(`/api/jobs/${jobId}`);
    const job = await res.json();

    $('progress-fill').style.width = `${job.progress}%`;
    $('progress-status').textContent = job.message || statusLabels[job.status] || job.status;

    if (job.status === 'error') {
      showError(job.error || 'Er ging iets mis.');
      resetStartButton();
      return;
    }

    if (job.status === 'done') {
      renderClips(jobId, job.clips);
      resetStartButton();
      return;
    }

    setTimeout(poll, 2000);
  };

  poll();
}

function renderClips(jobId, clips) {
  const grid = $('clip-grid');
  $('empty-state').classList.add('hidden');
  $('queue-count').textContent = `${clips.length} clips gemaakt`;

  grid.innerHTML = '';
  clips.forEach((clip) => {
    const url = `/api/clips/${jobId}/${clip.filename}`;
    const card = document.createElement('div');
    card.className = 'clip-card';
    card.innerHTML = `
      <video src="${url}" controls preload="metadata"></video>
      <div class="clip-card-body">
        <p class="clip-card-title">${escapeHtml(clip.title)}</p>
        <p class="clip-card-meta">${formatTime(clip.start)} – ${formatTime(clip.end)}</p>
        <a class="clip-card-download" href="${url}" download>Download</a>
      </div>
    `;
    grid.appendChild(card);
  });
}

function formatTime(s) {
  const m = Math.floor(s / 60);
  const sec = Math.floor(s % 60);
  return `${m}:${sec.toString().padStart(2, '0')}`;
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}
