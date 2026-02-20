(() => {
  let currentGarment = null;
  let groundTruthData = {}; // Локальное хранилище замеров { "L": {chest: 100, ...} }

  const el = {
    msg: document.getElementById('msg'),
    skuDisplay: document.getElementById('current-sku-display'),
    
    // Tabs
    btnTheory: document.getElementById('tab-btn-theory'),
    btnPractice: document.getElementById('tab-btn-practice'),
    tabTheory: document.getElementById('tab-theory'),
    tabPractice: document.getElementById('tab-practice'),

    // Theory Inputs
    sku: document.getElementById('sku'),
    price: document.getElementById('price'),
    name: document.getElementById('name'),
    imgFront: document.getElementById('img_front'),
    imgBack: document.getElementById('img_back'),
    catType: document.getElementById('cat_type'),
    fitProfile: document.getElementById('fit_profile'),
    elastane: document.getElementById('elastane'),
    platform: document.getElementById('platform'),
    mSize: document.getElementById('m_size'),
    mHeight: document.getElementById('m_height'),
    mChest: document.getElementById('m_chest'),
    mWaist: document.getElementById('m_waist'),
    mHips: document.getElementById('m_hips'),
    btnSaveTheory: document.getElementById('btn-save-theory'),

    // Practice Inputs (Ground Truth)
    gtSize: document.getElementById('gt_size'),
    gtChest: document.getElementById('gt_chest'),
    gtWaist: document.getElementById('gt_waist'),
    gtHips: document.getElementById('gt_hips'),
    gtSleeve: document.getElementById('gt_sleeve'),
    gtInseam: document.getElementById('gt_inseam'),
    gtLength: document.getElementById('gt_length'),
    btnAddGt: document.getElementById('btn-add-gt'),
    gtList: document.getElementById('gt_list'),

    // Feedback Inputs
    fbProfile: document.getElementById('fb_profile'),
    fbSize: document.getElementById('fb_size'),
    fbPointZero: document.getElementById('fb_point_zero'),
    fbChest: document.getElementById('fb_chest'),
    fbLength: document.getElementById('fb_length'),
    fbBelly: document.getElementById('fb_belly'),
    btnSaveFb: document.getElementById('btn-save-fb'),
  };

  function showMsg(text, isError=false) {
    el.msg.textContent = text;
    el.msg.className = `mb-4 p-3 rounded-2xl text-white text-sm shadow-lg ${isError ? 'bg-red-600' : 'bg-green-600'}`;
    el.msg.classList.remove('hidden');
    setTimeout(() => el.msg.classList.add('hidden'), 3000);
  }

  function switchTab(tab) {
    if (tab === 'theory') {
      el.tabTheory.classList.remove('hidden');
      el.tabPractice.classList.add('hidden');
      el.btnTheory.className = 'flex-1 py-2.5 rounded-xl font-black text-sm transition shadow-sm bg-white text-gray-900';
      el.btnPractice.className = 'flex-1 py-2.5 rounded-xl font-black text-sm text-gray-500 transition hover:text-gray-900';
    } else {
      el.tabTheory.classList.add('hidden');
      el.tabPractice.classList.remove('hidden');
      el.btnPractice.className = 'flex-1 py-2.5 rounded-xl font-black text-sm transition shadow-sm bg-white text-gray-900';
      el.btnTheory.className = 'flex-1 py-2.5 rounded-xl font-black text-sm text-gray-500 transition hover:text-gray-900';
    }
  }

  async function api(url, options = {}) {
    const res = await fetch(url, { headers: { 'Content-Type': 'application/json' }, ...options });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || 'API Error');
    return data;
  }

  function getSkuFromUrl() {
    return new URL(window.location.href).searchParams.get("sku") || "";
  }

  async function loadProfiles() {
    try {
      const profiles = await api('/api/profiles');
      el.fbProfile.innerHTML = '<option value="">-- Выбери профиль --</option>' + 
        profiles.map(p => `<option value="${p.id}">${p.name} (${p.height}см)</option>`).join('');
    } catch (e) { console.error("Profiles error", e); }
  }

  function populateForm(g) {
    currentGarment = g;
    el.skuDisplay.textContent = g.sku || 'Новый товар';
    
    // 1. Основное
    el.sku.value = g.sku || '';
    el.name.value = g.name || '';
    el.price.value = g.price || '';
    el.imgFront.value = g.image_url || '';
    el.imgBack.value = g.image_url_back || '';
    el.platform.value = g.platform || 'manual';

    const metrics = g.metrics || {};
    const theory = metrics.theory || {};
    groundTruthData = metrics.ground_truth || {};

    // 2. Теория
    el.catType.value = theory.category_type || 'top';
    el.fitProfile.value = theory.fit_profile || 'regular';
    el.elastane.value = theory.elastane_pct || 0;
    el.mSize.value = theory.model_size || '';
    el.mHeight.value = theory.height || '';
    el.mChest.value = theory.chest || '';
    el.mWaist.value = theory.waist || '';
    el.mHips.value = theory.hips || '';

    renderGtList();
  }

  async function init() {
    switchTab('theory');
    el.btnTheory.addEventListener('click', () => switchTab('theory'));
    el.btnPractice.addEventListener('click', () => switchTab('practice'));

    await loadProfiles();

    const sku = getSkuFromUrl();
    if (sku) {
      try {
        const data = await api(`/api/admin/builder/get?sku=${encodeURIComponent(sku)}`);
        populateForm(data);
      } catch (e) { showMsg("Товар не найден, создаем новый", true); }
    }
  }

  // --- СОХРАНЕНИЕ ТЕОРИИ ---
  el.btnSaveTheory.addEventListener('click', async () => {
    const sku = el.sku.value.trim();
    if (!sku) return showMsg("SKU обязателен!", true);

    const payload = {
      sku,
      name: el.name.value.trim(),
      price: Number(el.price.value) || null,
      image_url: el.imgFront.value.trim(),
      image_url_back: el.imgBack.value.trim(),
      platform: el.platform.value,
      theory: {
        category_type: el.catType.value,
        fit_profile: el.fitProfile.value,
        elastane_pct: Number(el.elastane.value) || 0,
        model_size: el.mSize.value.trim(),
        height: Number(el.mHeight.value) || null,
        chest: Number(el.mChest.value) || null,
        waist: Number(el.mWaist.value) || null,
        hips: Number(el.mHips.value) || null,
      }
    };

    try {
      await api('/api/admin/builder/upsert', { method: 'POST', body: JSON.stringify(payload) });
      showMsg("Товар и Теория успешно сохранены!");
      el.skuDisplay.textContent = sku;
      if (!currentGarment) currentGarment = { id: 999 }; // Dummy ID to allow feedback
    } catch (e) { showMsg(e.message, true); }
  });

  // --- ЛОГИКА GROUND TRUTH (Рулетка) ---
  function renderGtList() {
    const sizes = Object.keys(groundTruthData);
    if (!sizes.length) {
      el.gtList.innerHTML = '<div class="text-xs text-gray-400">Пока нет реальных замеров.</div>';
      return;
    }
    el.gtList.innerHTML = sizes.map(size => {
      const d = groundTruthData[size];
      return `<div class="p-3 bg-gray-50 border border-gray-100 rounded-xl text-sm flex justify-between items-center">
        <div><strong class="text-indigo-600">Размер ${size}</strong>: ${JSON.stringify(d).replace(/[{""}]/g,'')}</div>
        <button onclick="deleteGt('${size}')" class="text-red-500 font-bold text-xs ml-2">X</button>
      </div>`;
    }).join('');
  }

  window.deleteGt = async function(size) {
    delete groundTruthData[size];
    renderGtList();
    await saveGroundTruthOnly();
  };

  el.btnAddGt.addEventListener('click', async () => {
    const sku = el.sku.value.trim();
    if (!sku) return showMsg("Сначала сохрани теорию (SKU нужен)!", true);

    const size = el.gtSize.value.trim().toUpperCase();
    if (!size) return showMsg("Укажи размер (Например L)!", true);

    const m = {};
    if (el.gtChest.value) m.chest = Number(el.gtChest.value);
    if (el.gtWaist.value) m.waist = Number(el.gtWaist.value);
    if (el.gtHips.value) m.hips = Number(el.gtHips.value);
    if (el.gtSleeve.value) m.sleeve = Number(el.gtSleeve.value);
    if (el.gtInseam.value) m.inseam = Number(el.gtInseam.value);
    if (el.gtLength.value) m.length = Number(el.gtLength.value);

    if (Object.keys(m).length === 0) return showMsg("Введи хотя бы один замер!", true);

    groundTruthData[size] = m;
    
    // Очищаем инпуты рулетки
    [el.gtSize, el.gtChest, el.gtWaist, el.gtHips, el.gtSleeve, el.gtInseam, el.gtLength].forEach(i => i.value = '');
    
    renderGtList();
    await saveGroundTruthOnly();
  });

  async function saveGroundTruthOnly() {
    const sku = el.sku.value.trim();
    if (!sku) return;
    try {
      await api('/api/admin/builder/upsert', { 
        method: 'POST', 
        body: JSON.stringify({ sku: sku, ground_truth: groundTruthData }) 
      });
      showMsg("Замер добавлен в матрицу!");
    } catch (e) { showMsg(e.message, true); }
  }

  // --- ОТПРАВКА ФИДБЕКА ---
  el.btnSaveFb.addEventListener('click', async () => {
    if (!currentGarment || !currentGarment.id) return showMsg("Сначала сохрани товар (Теорию)!", true);
    
    const userId = el.fbProfile.value;
    if (!userId) return showMsg("Выбери профиль (кто меряет)!", true);

    const sizeSelected = el.fbSize.value.trim().toUpperCase();
    if (!sizeSelected) return showMsg("Укажи размер, который мерял!", true);

    const matrix = {};
    if (el.fbChest.value) matrix.width = el.fbChest.value;
    if (el.fbLength.value) matrix.length = el.fbLength.value;
    if (el.fbBelly.value) matrix.belly = el.fbBelly.value;

    const payload = {
      garment_id: currentGarment.id,
      user_id: userId,
      size_selected: sizeSelected,
      is_point_zero: el.fbPointZero.checked,
      fit_matrix: Object.keys(matrix).length ? matrix : null
    };

    try {
      await api('/api/feedback', { method: 'POST', body: JSON.stringify(payload) });
      showMsg("Примерка успешно отправлена!");
      
      // Сброс формы фидбека
      el.fbSize.value = '';
      el.fbPointZero.checked = false;
      [el.fbChest, el.fbLength, el.fbBelly].forEach(i => i.value = '');

    } catch (e) { showMsg(e.message, true); }
  });

  init();
})();

