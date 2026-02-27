/* Fit Builder v3.1 (metrics.v31 only)
 * - Clean save to /api/admin/builder/upsert
 * - Matrix sizes saved to metrics.v31.size_matrix
 */

const API = {
  list: () => fetch('/api/admin/builder/list').then(r => r.json()),
  get: (sku) => fetch(`/api/admin/builder/get?sku=${encodeURIComponent(sku)}`).then(async r => {
    if (!r.ok) throw new Error((await r.text()) || 'Not found');
    return r.json();
  }),
  upsert: (payload) => fetch('/api/admin/builder/upsert', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  }).then(async r => {
    const txt = await r.text();
    if (!r.ok) throw new Error(txt || 'Save error');
    return txt ? JSON.parse(txt) : { ok: true };
  }),
  del: (sku) => fetch(`/api/admin/builder/delete?sku=${encodeURIComponent(sku)}`, { method: 'DELETE' }).then(r => r.json()),
  profiles: () => fetch('/api/profiles').then(r => r.json()),
  feedback: (payload) => fetch('/api/feedback', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  }).then(async r => {
    const txt = await r.text();
    if (!r.ok) throw new Error(txt || 'Feedback error');
    return txt ? JSON.parse(txt) : { ok: true };
  }),
};

// -----------------------------
// Helpers
// -----------------------------
const $ = (id) => document.getElementById(id);

function toast(msg, ok = true) {
  const t = $('toast');
  if (!t) return;
  t.classList.remove('hidden');
  t.textContent = msg;
  t.style.background = ok ? '#111827' : '#991B1B';
  clearTimeout(window.__toastTimer);
  window.__toastTimer = setTimeout(() => t.classList.add('hidden'), 2600);
}

function toNum(v) {
  if (v === null || v === undefined) return null;
  const s = String(v).trim().replace(',', '.');
  if (!s) return null;
  const n = Number(s);
  return Number.isFinite(n) ? n : null;
}

function setVal(id, v) {
  const el = $(id);
  if (!el) return;
  el.value = (v === null || v === undefined) ? '' : String(v);
}

function getVal(id) {
  const el = $(id);
  if (!el) return '';
  return String(el.value || '').trim();
}

function setVisible(id, visible) {
  const el = $(id);
  if (!el) return;
  el.classList.toggle('hidden', !visible);
}

function safeJson(obj) {
  return JSON.parse(JSON.stringify(obj));
}

function buildSizesGrid() {
  const sizes = ['XS','S','M','L','XL','XXL','3XL','4XL','5XL'];
  const grid = $('sizes-grid');
  grid.innerHTML = '';
  sizes.forEach(sz => {
    const id = `sz_${sz}`;
    const wrap = document.createElement('label');
    wrap.className = 'flex items-center gap-2 px-3 py-2 rounded-xl border border-gray-200 bg-white cursor-pointer select-none';
    wrap.innerHTML = `
      <input id="${id}" type="checkbox" class="w-5 h-5 rounded" />
      <span class="font-black text-sm">${sz}</span>
    `;
    grid.appendChild(wrap);
  });
}

function getSelectedSizes() {
  const grid = $('sizes-grid');
  const checks = grid.querySelectorAll('input[type=checkbox]');
  const out = [];
  checks.forEach(ch => {
    if (ch.checked) out.push(ch.id.replace('sz_', ''));
  });
  return out;
}

function setSelectedSizes(sizes) {
  const set = new Set((sizes || []).map(String));
  const grid = $('sizes-grid');
  const checks = grid.querySelectorAll('input[type=checkbox]');
  checks.forEach(ch => {
    const sz = ch.id.replace('sz_', '');
    ch.checked = set.has(sz);
  });
}

function refreshMatrixSizeOptions(availableSizes) {
  const sel = $('matrix_size');
  sel.innerHTML = '<option value="">— Выберите размер —</option>';
  (availableSizes || []).forEach(sz => {
    const opt = document.createElement('option');
    opt.value = String(sz);
    opt.textContent = String(sz);
    sel.appendChild(opt);
  });
}

// -----------------------------
// State
// -----------------------------
let state = {
  garment: null,     // {id, sku, ... , metrics}
  v31: null,         // metrics.v31
};

function resetState() {
  state.garment = null;
  state.v31 = null;
  $('current-sku-badge').textContent = 'Новый товар';
  setVal('sku', '');
  setVal('name', '');
  setVal('price', '');
  setVal('img_front', '');
  setVal('img_back', '');
  setSelectedSizes([]);
  setVal('garment_type', 'tshirt');
  setVal('in_stock', 'true');
  setVal('fabric_type', 'knit');
  setVal('elastane_pct', 0);
  setVal('stiffness', 'medium');
  setVal('model_gender', 'male');
  setVal('model_size_worn', '');
  setVal('m_height', '');

  // model
  ['m_chest','m_waist_top','m_belly','m_hips','m_bicep','m_shoulders','m_inseam'].forEach(id => setVal(id,''));

  // garment on model
  ['g_chest','g_waist_top','g_hem_top','g_bicep','g_sleeve','g_length_top','g_shoulders'].forEach(id => setVal(id,''));
  ['g_waist_bottom','g_high_hip','g_hips','g_thigh','g_leg_opening','g_inseam','g_outseam','g_front_rise','g_back_rise'].forEach(id => setVal(id,''));

  // matrix form
  clearMatrixForm();
  $('matrix_list').innerHTML = '';
  refreshMatrixSizeOptions([]);
  updateGarmentTypeUI();
  updateReadyBox();
}

function v31Template() {
  return {
    engine: { version: 'fit_v3.1' },
    product: {
      sku: '',
      garment_type: 'tshirt',
      fit_profile: 'regular',
      available_sizes: [],
    },
    fabric: {
      fabric_type: 'knit',
      elastane_pct: 0,
      stiffness: 'medium',
    },
    model: {
      gender: 'male',
      size_worn: '',
      body: {},
    },
    garment_on_model: {
      size: '',
      measurement_convention: 'flat_half',
      measurements: {},
    },
    size_matrix: {},
  };
}

// -----------------------------
// UI switching
// -----------------------------
function setActiveTab(tab) {
  const tabs = ['theory','matrix','feedback'];
  tabs.forEach(t => {
    setVisible(`tab-${t}`, t === tab);
    const btn = $(`tab-btn-${t}`);
    if (btn) {
      btn.classList.toggle('bg-white', t === tab);
      btn.classList.toggle('text-gray-900', t === tab);
      btn.classList.toggle('shadow-sm', t === tab);
      btn.classList.toggle('text-gray-500', t !== tab);
    }
  });
}

function updateGarmentTypeUI() {
  const gt = getVal('garment_type') || 'tshirt';
  const isTop = gt === 'tshirt';
  setVisible('gom_tshirt', isTop);
  setVisible('gom_trousers', !isTop);
  setVisible('matrix_tshirt', isTop);
  setVisible('matrix_trousers', !isTop);
  updateReadyBox();
}

// -----------------------------
// Readiness
// -----------------------------
function computeReady() {
  const sku = getVal('sku');
  const garmentType = getVal('garment_type') || 'tshirt';
  const sizes = getSelectedSizes();
  const modelSize = getVal('model_size_worn');
  const mChest = toNum(getVal('m_chest'));

  const gomChest = toNum(getVal('g_chest'));
  const gomWaistBottom = toNum(getVal('g_waist_bottom'));
  const gomHips = toNum(getVal('g_hips'));
  const gomInseam = toNum(getVal('g_inseam'));

  const missing = [];
  if (!sku) missing.push('SKU');
  if (!sizes.length) missing.push('Существующие размеры');
  if (!modelSize) missing.push('Размер на модели');
  if (!mChest) missing.push('Грудь модели');

  if (garmentType === 'tshirt') {
    if (!gomChest) missing.push('Вещь на модели: грудь');
  } else {
    if (!gomWaistBottom) missing.push('Вещь на модели: пояс');
    if (!gomHips) missing.push('Вещь на модели: бедра');
    if (!gomInseam) missing.push('Вещь на модели: inseam');
  }

  let matrixCount = 0;
  if (state.v31 && state.v31.size_matrix) {
    matrixCount = Object.keys(state.v31.size_matrix).length;
  }

  let level = 'NOT_READY';
  if (missing.length === 0) {
    level = matrixCount >= 2 ? 'READY' : 'PARTIAL';
  }

  return { level, missing, matrixCount };
}

function updateReadyBox() {
  const box = $('ready-box');
  if (!box) return;

  const { level, missing, matrixCount } = computeReady();
  const garmentType = getVal('garment_type') || 'tshirt';

  if (level === 'READY') {
    box.className = 'p-4 rounded-2xl border border-green-200 bg-green-50 text-sm';
    box.innerHTML = `✅ <b>READY</b> — можно считать. Матрица: <b>${matrixCount}</b> размеров.`;
  } else if (level === 'PARTIAL') {
    box.className = 'p-4 rounded-2xl border border-amber-200 bg-amber-50 text-sm';
    box.innerHTML = `⚠️ <b>PARTIAL</b> — теория заполнена, но матрица пока слабая (размеров: <b>${matrixCount}</b>).<br>
      Минимум для ${garmentType === 'tshirt' ? 'футболки' : 'брюк'}: сохранить хотя бы <b>2 размера</b> в матрицу.`;
  } else {
    box.className = 'p-4 rounded-2xl border border-red-200 bg-red-50 text-sm';
    box.innerHTML = `❌ <b>NOT READY</b> — не хватает: <b>${missing.join(', ')}</b>.`;
  }
}

// -----------------------------
// Collect / Apply
// -----------------------------
function collectV31FromForm() {
  const v31 = state.v31 ? safeJson(state.v31) : v31Template();

  const sku = getVal('sku');
  const garmentType = getVal('garment_type') || 'tshirt';

  v31.product = {
    sku,
    garment_type: garmentType,
    fit_profile: 'regular',
    available_sizes: getSelectedSizes(),
  };

  v31.fabric = {
    fabric_type: getVal('fabric_type') || 'knit',
    elastane_pct: toNum(getVal('elastane_pct')) ?? 0,
    stiffness: getVal('stiffness') || 'medium',
  };

  // model
  const modelGender = getVal('model_gender') || 'male';
  const modelSize = getVal('model_size_worn');
  const body = {};
  const mHeight = toNum(getVal('m_height')); if (mHeight !== null) body.height_cm = mHeight;

  const mChest = toNum(getVal('m_chest')); if (mChest !== null) body.chest_circ = mChest;
  const mWaist = toNum(getVal('m_waist_top')); if (mWaist !== null) body.waist_top_circ = mWaist;
  const mBelly = toNum(getVal('m_belly')); if (mBelly !== null) body.belly_circ = mBelly;
  const mHips = toNum(getVal('m_hips')); if (mHips !== null) body.hips_circ = mHips;
  const mBicep = toNum(getVal('m_bicep')); if (mBicep !== null) body.bicep_circ = mBicep;
  const mShoulders = toNum(getVal('m_shoulders')); if (mShoulders !== null) body.shoulders_len = mShoulders;
  const mInseam = toNum(getVal('m_inseam')); if (mInseam !== null) body.inseam_len = mInseam;

  v31.model = {
    gender: modelGender,
    size_worn: modelSize,
    body,
  };

  // garment_on_model
  const gom = {};
  if (garmentType === 'tshirt') {
    const chest = toNum(getVal('g_chest')); if (chest !== null) gom.chest = chest;
    const waist = toNum(getVal('g_waist_top')); if (waist !== null) gom.waist_top = waist;
    const hem = toNum(getVal('g_hem_top')); if (hem !== null) gom.hem_top = hem;
    const bicep = toNum(getVal('g_bicep')); if (bicep !== null) gom.bicep = bicep;
    const sleeve = toNum(getVal('g_sleeve')); if (sleeve !== null) gom.sleeve = sleeve;
    const len = toNum(getVal('g_length_top')); if (len !== null) gom.length_top = len;
    const sh = toNum(getVal('g_shoulders')); if (sh !== null) gom.shoulders = sh;
  } else {
    const waist = toNum(getVal('g_waist_bottom')); if (waist !== null) gom.waist_bottom = waist;
    const hh = toNum(getVal('g_high_hip')); if (hh !== null) gom.high_hip = hh;
    const hips = toNum(getVal('g_hips')); if (hips !== null) gom.hips = hips;
    const thigh = toNum(getVal('g_thigh')); if (thigh !== null) gom.thigh = thigh;
    const leg = toNum(getVal('g_leg_opening')); if (leg !== null) gom.leg_opening = leg;
    const inseam = toNum(getVal('g_inseam')); if (inseam !== null) gom.inseam = inseam;
    const outseam = toNum(getVal('g_outseam')); if (outseam !== null) gom.outseam = outseam;
    const fr = toNum(getVal('g_front_rise')); if (fr !== null) gom.front_rise = fr;
    const br = toNum(getVal('g_back_rise')); if (br !== null) gom.back_rise = br;
  }

  v31.garment_on_model = {
    size: modelSize,
    measurement_convention: 'flat_half',
    measurements: gom,
  };

  if (!v31.size_matrix || typeof v31.size_matrix !== 'object') v31.size_matrix = {};

  return v31;
}

function applyGarmentToForm(g) {
  state.garment = g;
  const metrics = (g && g.metrics) ? g.metrics : null;
  const v31 = (metrics && metrics.schema_version === 'v3.1') ? metrics.v31 : null;

  state.v31 = v31 && typeof v31 === 'object' ? safeJson(v31) : null;

  setVal('sku', g.sku || '');
  setVal('name', g.name || '');
  setVal('price', g.price ?? '');
  setVal('img_front', g.image_url || '');
  setVal('img_back', g.image_url_back || '');
  setVal('in_stock', String(g.in_stock ?? true));

  $('current-sku-badge').textContent = g.sku || 'Новый товар';

  const v = state.v31;
  if (!v) {
    toast('Товар загружен, но не v3.1. Пересоздайте через Builder.', false);
    setSelectedSizes([]);
    refreshMatrixSizeOptions([]);
    $('matrix_list').innerHTML = '';
    updateReadyBox();
    return;
  }

  setVal('garment_type', (v.product && v.product.garment_type) ? v.product.garment_type : 'tshirt');
  setSelectedSizes((v.product && v.product.available_sizes) ? v.product.available_sizes : []);

  setVal('fabric_type', (v.fabric && v.fabric.fabric_type) ? v.fabric.fabric_type : 'knit');
  setVal('elastane_pct', (v.fabric && v.fabric.elastane_pct !== undefined) ? v.fabric.elastane_pct : 0);
  setVal('stiffness', (v.fabric && v.fabric.stiffness) ? v.fabric.stiffness : 'medium');

  setVal('model_gender', (v.model && v.model.gender) ? v.model.gender : 'male');
  setVal('model_size_worn', (v.model && v.model.size_worn) ? v.model.size_worn : '');
  const body = (v.model && v.model.body) ? v.model.body : {};
  setVal('m_height', body.height_cm ?? '');
  setVal('m_chest', body.chest_circ ?? '');
  setVal('m_waist_top', body.waist_top_circ ?? '');
  setVal('m_belly', body.belly_circ ?? '');
  setVal('m_hips', body.hips_circ ?? '');
  setVal('m_bicep', body.bicep_circ ?? '');
  setVal('m_shoulders', body.shoulders_len ?? '');
  setVal('m_inseam', body.inseam_len ?? '');

  const gom = (v.garment_on_model && v.garment_on_model.measurements) ? v.garment_on_model.measurements : {};
  setVal('g_chest', gom.chest ?? '');
  setVal('g_waist_top', gom.waist_top ?? '');
  setVal('g_hem_top', gom.hem_top ?? '');
  setVal('g_bicep', gom.bicep ?? '');
  setVal('g_sleeve', gom.sleeve ?? '');
  setVal('g_length_top', gom.length_top ?? '');
  setVal('g_shoulders', gom.shoulders ?? '');

  setVal('g_waist_bottom', gom.waist_bottom ?? '');
  setVal('g_high_hip', gom.high_hip ?? '');
  setVal('g_hips', gom.hips ?? '');
  setVal('g_thigh', gom.thigh ?? '');
  setVal('g_leg_opening', gom.leg_opening ?? '');
  setVal('g_inseam', gom.inseam ?? '');
  setVal('g_outseam', gom.outseam ?? '');
  setVal('g_front_rise', gom.front_rise ?? '');
  setVal('g_back_rise', gom.back_rise ?? '');

  updateGarmentTypeUI();
  refreshMatrixSizeOptions((v.product && v.product.available_sizes) ? v.product.available_sizes : []);
  renderMatrixList();
  updateReadyBox();
}

// -----------------------------
// Matrix
// -----------------------------
function clearMatrixForm() {
  setVal('matrix_size', '');
  ['mx_chest','mx_waist_top','mx_hem_top','mx_bicep','mx_sleeve','mx_length_top','mx_shoulders'].forEach(id => setVal(id,''));
  ['mx_waist_bottom','mx_high_hip','mx_hips','mx_thigh','mx_leg_opening','mx_inseam','mx_outseam','mx_front_rise','mx_back_rise'].forEach(id => setVal(id,''));
}

function collectMatrixMeasurements() {
  const garmentType = getVal('garment_type') || 'tshirt';
  const m = {};
  if (garmentType === 'tshirt') {
    const chest = toNum(getVal('mx_chest')); if (chest !== null) m.chest = chest;
    const waist = toNum(getVal('mx_waist_top')); if (waist !== null) m.waist_top = waist;
    const hem = toNum(getVal('mx_hem_top')); if (hem !== null) m.hem_top = hem;
    const bicep = toNum(getVal('mx_bicep')); if (bicep !== null) m.bicep = bicep;
    const sleeve = toNum(getVal('mx_sleeve')); if (sleeve !== null) m.sleeve = sleeve;
    const len = toNum(getVal('mx_length_top')); if (len !== null) m.length_top = len;
    const sh = toNum(getVal('mx_shoulders')); if (sh !== null) m.shoulders = sh;
  } else {
    const waist = toNum(getVal('mx_waist_bottom')); if (waist !== null) m.waist_bottom = waist;
    const hh = toNum(getVal('mx_high_hip')); if (hh !== null) m.high_hip = hh;
    const hips = toNum(getVal('mx_hips')); if (hips !== null) m.hips = hips;
    const thigh = toNum(getVal('mx_thigh')); if (thigh !== null) m.thigh = thigh;
    const leg = toNum(getVal('mx_leg_opening')); if (leg !== null) m.leg_opening = leg;
    const inseam = toNum(getVal('mx_inseam')); if (inseam !== null) m.inseam = inseam;
    const outseam = toNum(getVal('mx_outseam')); if (outseam !== null) m.outseam = outseam;
    const fr = toNum(getVal('mx_front_rise')); if (fr !== null) m.front_rise = fr;
    const br = toNum(getVal('mx_back_rise')); if (br !== null) m.back_rise = br;
  }
  return m;
}

function validateMatrix(size, measurements) {
  const garmentType = getVal('garment_type') || 'tshirt';
  if (!state.v31) return 'Сначала сохраните v3.1 (вкладка База)';
  if (!size) return 'Выберите размер';

  if (garmentType === 'tshirt') {
    if (measurements.chest === undefined) return 'Для футболки обязателен замер Грудь (half)';
  } else {
    if (measurements.waist_bottom === undefined) return 'Для брюк обязателен замер Пояс (half)';
    if (measurements.hips === undefined) return 'Для брюк обязателен замер Бедра (half)';
    if (measurements.inseam === undefined) return 'Для брюк обязателен замер Inseam (длина)';
  }

  const sizes = (state.v31.product && state.v31.product.available_sizes) ? state.v31.product.available_sizes.map(String) : [];
  if (!sizes.includes(String(size))) return 'Этот размер не отмечен в "Существующие размеры"';

  return null;
}

function renderMatrixList() {
  const list = $('matrix_list');
  list.innerHTML = '';

  if (!state.v31 || !state.v31.size_matrix) {
    list.innerHTML = '<div class="text-sm text-gray-500">Нет данных</div>';
    updateReadyBox();
    return;
  }

  const entries = Object.entries(state.v31.size_matrix);
  if (!entries.length) {
    list.innerHTML = '<div class="text-sm text-gray-500">Матрица пустая</div>';
    updateReadyBox();
    return;
  }

  const garmentType = getVal('garment_type') || 'tshirt';
  entries.sort((a,b) => String(a[0]).localeCompare(String(b[0])));

  entries.forEach(([sz, node]) => {
    const meas = (node && node.measurements) ? node.measurements : {};

    const important = [];
    if (garmentType === 'tshirt') {
      if (meas.chest != null) important.push(`Грудь: <b>${meas.chest}</b>`);
      if (meas.waist_top != null) important.push(`Талия: ${meas.waist_top}`);
      if (meas.hem_top != null) important.push(`Низ: ${meas.hem_top}`);
      if (meas.sleeve != null) important.push(`Рукав: ${meas.sleeve}`);
      if (meas.length_top != null) important.push(`Длина: ${meas.length_top}`);
    } else {
      if (meas.waist_bottom != null) important.push(`Пояс: <b>${meas.waist_bottom}</b>`);
      if (meas.hips != null) important.push(`Бедра: <b>${meas.hips}</b>`);
      if (meas.inseam != null) important.push(`Inseam: <b>${meas.inseam}</b>`);
      if (meas.thigh != null) important.push(`Бедро: ${meas.thigh}`);
      if (meas.leg_opening != null) important.push(`Низ: ${meas.leg_opening}`);
    }

    const card = document.createElement('div');
    card.className = 'p-4 rounded-2xl border border-gray-200 bg-white flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3';

    card.innerHTML = `
      <div>
        <div class="font-black text-lg">${sz}</div>
        <div class="text-sm text-gray-600 mt-1">${important.join(' • ') || '—'}</div>
      </div>
      <div class="flex gap-2">
        <button data-act="edit" class="px-3 py-2 rounded-xl border border-gray-200 bg-white text-xs font-bold hover:bg-gray-50">Правка</button>
        <button data-act="del" class="px-3 py-2 rounded-xl border border-red-200 bg-white text-xs font-bold text-red-600 hover:bg-red-50">Удалить</button>
      </div>
    `;

    card.querySelector('[data-act="edit"]').addEventListener('click', () => {
      setVal('matrix_size', sz);
      clearMatrixForm();
      setVal('matrix_size', sz);
      // apply measurements into form
      if (garmentType === 'tshirt') {
        setVal('mx_chest', meas.chest ?? '');
        setVal('mx_waist_top', meas.waist_top ?? '');
        setVal('mx_hem_top', meas.hem_top ?? '');
        setVal('mx_bicep', meas.bicep ?? '');
        setVal('mx_sleeve', meas.sleeve ?? '');
        setVal('mx_length_top', meas.length_top ?? '');
        setVal('mx_shoulders', meas.shoulders ?? '');
      } else {
        setVal('mx_waist_bottom', meas.waist_bottom ?? '');
        setVal('mx_high_hip', meas.high_hip ?? '');
        setVal('mx_hips', meas.hips ?? '');
        setVal('mx_thigh', meas.thigh ?? '');
        setVal('mx_leg_opening', meas.leg_opening ?? '');
        setVal('mx_inseam', meas.inseam ?? '');
        setVal('mx_outseam', meas.outseam ?? '');
        setVal('mx_front_rise', meas.front_rise ?? '');
        setVal('mx_back_rise', meas.back_rise ?? '');
      }
      setActiveTab('matrix');
      toast(`Размер ${sz}: загружен в форму`);
    });

    card.querySelector('[data-act="del"]').addEventListener('click', () => {
      if (!state.v31 || !state.v31.size_matrix) return;
      delete state.v31.size_matrix[sz];
      renderMatrixList();
      updateReadyBox();
      toast(`Размер ${sz}: удалён`);
    });

    list.appendChild(card);
  });

  updateReadyBox();
}

// -----------------------------
// Events
// -----------------------------
async function refreshList() {
  try {
    const list = await API.list();
    const sel = $('select-existing');
    sel.innerHTML = '<option value="">— Выберите из списка —</option>';
    (list || []).forEach(g => {
      const opt = document.createElement('option');
      opt.value = g.sku;
      opt.textContent = `${g.sku}${g.name ? ` — ${g.name}` : ''}`;
      sel.appendChild(opt);
    });
    toast('Список обновлён');
  } catch (e) {
    toast('Ошибка списка', false);
  }
}

async function loadSku(sku) {
  if (!sku) return;
  try {
    const g = await API.get(sku);
    applyGarmentToForm(g);
    toast(`Загружено: ${sku}`);
  } catch (e) {
    toast(`Не найдено: ${sku}`, false);
  }
}

async function saveTheory() {
  try {
    const v31 = collectV31FromForm();
    state.v31 = safeJson(v31);

    const payload = {
      sku: getVal('sku'),
      name: getVal('name') || null,
      price: toNum(getVal('price')),
      image_url: getVal('img_front') || null,
      image_url_back: getVal('img_back') || null,
      in_stock: String(getVal('in_stock')) === 'true',
      metrics: { schema_version: 'v3.1', v31 }
    };

    const res = await API.upsert(payload);
    toast('Сохранено v3.1');
    await refreshList();
    // keep badge
    $('current-sku-badge').textContent = payload.sku || 'Новый товар';
    return res;
  } catch (e) {
    toast(String(e.message || e), false);
  }
}

async function deleteGarment() {
  const sku = getVal('sku');
  if (!sku) { toast('Нет SKU', false); return; }
  try {
    const r = await API.del(sku);
    toast('Удалено');
    resetState();
    await refreshList();
    return r;
  } catch (e) {
    toast('Ошибка удаления', false);
  }
}

function fillMatrixFromGom() {
  const garmentType = getVal('garment_type') || 'tshirt';
  if (garmentType === 'tshirt') {
    setVal('mx_chest', getVal('g_chest'));
    setVal('mx_waist_top', getVal('g_waist_top'));
    setVal('mx_hem_top', getVal('g_hem_top'));
    setVal('mx_bicep', getVal('g_bicep'));
    setVal('mx_sleeve', getVal('g_sleeve'));
    setVal('mx_length_top', getVal('g_length_top'));
    setVal('mx_shoulders', getVal('g_shoulders'));
  } else {
    setVal('mx_waist_bottom', getVal('g_waist_bottom'));
    setVal('mx_high_hip', getVal('g_high_hip'));
    setVal('mx_hips', getVal('g_hips'));
    setVal('mx_thigh', getVal('g_thigh'));
    setVal('mx_leg_opening', getVal('g_leg_opening'));
    setVal('mx_inseam', getVal('g_inseam'));
    setVal('mx_outseam', getVal('g_outseam'));
    setVal('mx_front_rise', getVal('g_front_rise'));
    setVal('mx_back_rise', getVal('g_back_rise'));
  }
  toast('Скопировано из "вещь на модели"');
}

function saveMatrixSize() {
  const size = getVal('matrix_size');
  const measurements = collectMatrixMeasurements();
  const err = validateMatrix(size, measurements);
  if (err) { toast(err, false); return; }

  if (!state.v31.size_matrix) state.v31.size_matrix = {};
  state.v31.size_matrix[String(size)] = {
    measurement_convention: 'flat_half',
    measurements
  };

  renderMatrixList();
  clearMatrixForm();
  setVal('matrix_size', '');
  toast(`Матрица: сохранён размер ${size}`);
}

async function loadProfilesToFeedback() {
  try {
    const profiles = await API.profiles();
    const sel = $('fb_profile');
    sel.innerHTML = '<option value="">— Выберите профиль —</option>';
    (profiles || []).forEach(p => {
      const opt = document.createElement('option');
      opt.value = String(p.id);
      opt.textContent = `${p.name || ('Profile ' + p.id)} (${p.gender || '—'})`;
      sel.appendChild(opt);
    });
  } catch (e) {
    // ignore
  }
}

async function sendFeedback() {
  if (!state.garment?.id && !state.garment?.garment_id) {
    toast('Сначала сохраните товар (вкладка База)', false);
    return;
  }
  const garmentId = state.garment.id || state.garment.garment_id;
  const profileId = Number(getVal('fb_profile') || 0) || null;
  if (!profileId) { toast('Выберите профиль', false); return; }

  const payload = {
    garment_id: garmentId,
    user_id: profileId,
    size_selected: getVal('fb_size') || null,
    is_point_zero: !!$('fb_point_zero')?.checked,
    fit_matrix: state.v31 ? { schema_version: 'v3.1', v31: state.v31 } : null
  };

  try {
    await API.feedback(payload);
    toast('Фидбек отправлен');
  } catch (e) {
    toast(String(e.message || e), false);
  }
}

// -----------------------------
// Init
// -----------------------------
function bindEvents() {
  $('tab-btn-theory')?.addEventListener('click', () => setActiveTab('theory'));
  $('tab-btn-matrix')?.addEventListener('click', () => setActiveTab('matrix'));
  $('tab-btn-feedback')?.addEventListener('click', () => setActiveTab('feedback'));

  $('btn-refresh-list')?.addEventListener('click', refreshList);
  $('btn-new')?.addEventListener('click', () => { resetState(); toast('Новый товар'); });
  $('btn-load')?.addEventListener('click', () => loadSku(getVal('load_sku')));
  $('select-existing')?.addEventListener('change', (e) => loadSku(e.target.value));
  $('btn-sizes-all')?.addEventListener('click', () => {
    const grid = $('sizes-grid');
    const checks = grid.querySelectorAll('input[type=checkbox]');
    checks.forEach(ch => ch.checked = true);
    updateReadyBox();
  });

  $('garment_type')?.addEventListener('change', updateGarmentTypeUI);

  // update readiness on key inputs
  [
    'sku','model_size_worn','m_chest','g_chest','g_waist_bottom','g_hips','g_inseam'
  ].forEach(id => $(id)?.addEventListener('input', updateReadyBox));

  $('btn-save-theory')?.addEventListener('click', saveTheory);
  $('btn-delete')?.addEventListener('click', deleteGarment);

  $('btn-fill-from-gom')?.addEventListener('click', fillMatrixFromGom);
  $('btn-save-size')?.addEventListener('click', saveMatrixSize);
  $('btn-clear-matrix-form')?.addEventListener('click', () => { clearMatrixForm(); toast('Форма матрицы очищена'); });

  $('btn-send-feedback')?.addEventListener('click', sendFeedback);
}

function init() {
  buildSizesGrid();
  bindEvents();
  resetState();
  refreshList();
  loadProfilesToFeedback();
  setActiveTab('theory');
}

window.addEventListener('DOMContentLoaded', init);


