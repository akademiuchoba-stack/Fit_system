(() => {
  let currentGarment = null;
  let groundTruthData = {};

  const el = {
    msg: document.getElementById('msg'),
    skuDisplay: document.getElementById('current-sku-display'),
    btnTheory: document.getElementById('tab-btn-theory'),
    btnPractice: document.getElementById('tab-btn-practice'),
    tabTheory: document.getElementById('tab-theory'),
    tabPractice: document.getElementById('tab-practice'),

    sku: document.getElementById('sku'),
    price: document.getElementById('price'),
    name: document.getElementById('name'),
    imgFront: document.getElementById('img_front'),
    imgBack: document.getElementById('img_back'),
    catType: document.getElementById('cat_type'),
    fitProfile: document.getElementById('fit_profile'),
    elastane: document.getElementById('elastane'),
    platform: document.getElementById('platform'),
    
    // Новые поля
    sleeveType: document.getElementById('sleeve_type'),
    legType: document.getElementById('leg_type'),
    gLength: document.getElementById('g_length'),
    gSleeve: document.getElementById('g_sleeve'),
    gInseam: document.getElementById('g_inseam'),
    gOutseam: document.getElementById('g_outseam'),

    mSize: document.getElementById('m_size'),
    mHeight: document.getElementById('m_height'),
    mChest: document.getElementById('m_chest'),
    mWaist: document.getElementById('m_waist'),
    mHips: document.getElementById('m_hips'),
    btnSaveTheory: document.getElementById('btn-save-theory'),

    gtSize: document.getElementById('gt_size'),
    gtChest: document.getElementById('gt_chest'),
    gtWaist: document.getElementById('gt_waist'),
    gtHips: document.getElementById('gt_hips'),
    gtSleeve: document.getElementById('gt_sleeve'),
    gtInseam: document.getElementById('gt_inseam'),
    gtLength: document.getElementById('gt_length'),
    btnAddGt: document.getElementById('btn-add-gt'),
    gtList: document.getElementById('gt_list'),

    fbProfile: document.getElementById('fb_profile'),
    fbSize: document.getElementById('fb_size'),
    fbPointZero: document.getElementById('fb_point_zero'),
    fbChest: document.getElementById('fb_chest'),
    fbLength: document.getElementById('fb_length'),
    fbBelly: document.getElementById('fb_belly'),
    btnSaveFb: document.getElementById('btn-save-fb'),

    analysisResult: document.getElementById('analysis-result'),
    resTheory: document.getElementById('res-theory'),
    resGt: document.getElementById('res-gt'),
    resVerdict: document.getElementById('res-verdict')
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
    
    el.sku.value = g.sku || '';
    el.name.value = g.name || '';
    el.price.value = g.price || '';
    el.imgFront.value = g.image_url || '';
    el.imgBack.value = g.image_url_back || '';
    el.platform.value = g.platform || 'manual';

    const metrics = g.metrics || {};
    const theory = metrics.theory || {};
    groundTruthData = metrics.ground_truth || {};

    el.catType.value = theory.category_type || 'top';
    el.fitProfile.value = theory.fit_profile || 'regular';
    el.elastane.value = theory.elastane_pct || 0;
    
    // Новые поля
    el.sleeveType.value = theory.sleeve_type || 'long';
    el.legType.value = theory.leg_type || 'long';
    el.gLength.value = theory.g_length || '';
    el.gSleeve.value = theory.g_sleeve || '';
    el.gInseam.value = theory.g_inseam || '';
    el.gOutseam.value = theory.g_outseam || '';

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
      } catch (e) {} // Новый товар
    }
  }

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
        
        sleeve_type: el.sleeveType.value,
        leg_type: el.legType.value,
        g_length: el.gLength.value ? Number(el.gLength.value) : null,
        g_sleeve: el.gSleeve.value ? Number(el.gSleeve.value) : null,
        g_inseam: el.gInseam.value ? Number(el.gInseam.value) : null,
        g_outseam: el.gOutseam.value ? Number(el.gOutseam.value) : null,

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
      if (!currentGarment) currentGarment = { id: 999 };
    } catch (e) { showMsg(e.message, true); }
  });

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
      const data = await api('/api/feedback', { method: 'POST', body: JSON.stringify(payload) });
      showMsg("Примерка успешно отправлена!");
      
      if(data.analysis) {
        el.analysisResult.classList.remove('hidden');
        el.resTheory.textContent = data.analysis.theory_size ? `${data.analysis.theory_size} (${data.analysis.theory_score}%)` : 'Нет данных';
        el.resGt.textContent = data.analysis.gt_size ? `${data.analysis.gt_size} (${data.analysis.gt_score}%)` : 'Нет данных';
        
        if (data.analysis.match === true) {
            el.resVerdict.className = "mt-3 p-3 rounded-xl font-bold text-center bg-green-100 text-green-800";
            el.resVerdict.textContent = "Совпадение! Данные магазина верны.";
        } else if (data.analysis.match === false) {
            el.resVerdict.className = "mt-3 p-3 rounded-xl font-bold text-center bg-red-100 text-red-800";
            el.resVerdict.textContent = `Ошибка магазина! Реальный размер: ${data.analysis.gt_size}`;
        } else {
            el.resVerdict.className = "mt-3 p-3 rounded-xl font-bold text-center bg-gray-100 text-gray-800";
            el.resVerdict.textContent = "Недостаточно данных для сравнения.";
        }

        // Рендер рентгена в Builder
        let xrayHtml = `<div class="mt-4 border-t border-indigo-200/50 pt-4"><h4 class="text-[11px] uppercase tracking-widest text-indigo-500 font-extrabold mb-3">Рентген по данным сайта (Теория):</h4><div class="space-y-3">`;
        (data.analysis.xray || []).forEach(sz => {
            xrayHtml += `
            <div class="bg-white p-2 rounded-xl border ${sz.hard_fit === 'FAIL' ? 'border-red-200' : 'border-indigo-100'} text-xs">
                <div class="font-black mb-1">Размер ${sz.size_label} <span class="font-normal text-gray-500 float-right">${Math.round(sz.score)}%</span></div>
                ${sz.xray_zones.map(z => `<div class="flex justify-between"><span class="text-gray-500">${z.zone_name}</span> <span class="${z.penalty > 0 ? 'text-red-500' : 'text-green-600'}">${z.status}</span></div>`).join('')}
            </div>`;
        });
        xrayHtml += `</div></div>`;
        
        // Добавляем рентген под вердикт
        let existingXray = document.getElementById('builder-xray');
        if (existingXray) existingXray.remove();
        
        let xrayContainer = document.createElement('div');
        xrayContainer.id = 'builder-xray';
        xrayContainer.innerHTML = xrayHtml;
        el.resVerdict.parentNode.appendChild(xrayContainer);
      }

    } catch (e) { showMsg(e.message, true); }
  });

  init();
})();

