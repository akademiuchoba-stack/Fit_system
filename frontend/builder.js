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

    sku: document.getElementById('sku'), price: document.getElementById('price'), name: document.getElementById('name'),
    imgFront: document.getElementById('img_front'), imgBack: document.getElementById('img_back'),
    catType: document.getElementById('cat_type'), fitProfile: document.getElementById('fit_profile'),
    stiffnessClass: document.getElementById('stiffness_class'), elastane: document.getElementById('elastane'),
    platform: document.getElementById('platform'),
    
    // Wrappers for visibility toggle
    wrapSleeve: document.getElementById('wrap_sleeve_type'),
    wrapLeg: document.getElementById('wrap_leg_type'),
    wrapRise: document.getElementById('wrap_rise_class'),
    theoryTopFields: document.getElementById('theory_top_fields'),
    theoryBotFields: document.getElementById('theory_bot_fields'),
    gtTopFields: document.getElementById('gt_top_fields'),
    gtBotFields: document.getElementById('gt_bot_fields'),

    sleeveType: document.getElementById('sleeve_type'), legType: document.getElementById('leg_type'), riseClass: document.getElementById('rise_class'),
    
    // Theory Fields
    gShoulders: document.getElementById('g_shoulders'), gBackWidth: document.getElementById('g_back_width'),
    gChest: document.getElementById('g_chest'), gWaistTop: document.getElementById('g_waist_top'),
    gHemTop: document.getElementById('g_hem_top'), gBicep: document.getElementById('g_bicep'),
    gSleeve: document.getElementById('g_sleeve'), gLength: document.getElementById('g_length'),
    gWaistBot: document.getElementById('g_waist_bot'), gBelly: document.getElementById('g_belly'),
    gHips: document.getElementById('g_hips'), gThigh: document.getElementById('g_thigh'),
    gKnee: document.getElementById('g_knee'), gLegOpening: document.getElementById('g_leg_opening'),
    gFrontRise: document.getElementById('g_front_rise'), gBackRise: document.getElementById('g_back_rise'),
    gInseam: document.getElementById('g_inseam'), gOutseam: document.getElementById('g_outseam'),

    mSize: document.getElementById('m_size'), mHeight: document.getElementById('m_height'),
    mChest: document.getElementById('m_chest'), mWaist: document.getElementById('m_waist'), mHips: document.getElementById('m_hips'),
    btnSaveTheory: document.getElementById('btn-save-theory'),

    // GT Fields
    gtSize: document.getElementById('gt_size'),
    gtShoulders: document.getElementById('gt_shoulders'), gtBackWidth: document.getElementById('gt_back_width'),
    gtChest: document.getElementById('gt_chest'), gtWaistTop: document.getElementById('gt_waist_top'),
    gtHemTop: document.getElementById('gt_hem_top'), gtBicep: document.getElementById('gt_bicep'),
    gtSleeve: document.getElementById('gt_sleeve'), gtLengthTop: document.getElementById('gt_length_top'),
    gtWaistBot: document.getElementById('gt_waist_bot'), gtBelly: document.getElementById('gt_belly'),
    gtHips: document.getElementById('gt_hips'), gtThigh: document.getElementById('gt_thigh'),
    gtKnee: document.getElementById('gt_knee'), gtLegOpening: document.getElementById('gt_leg_opening'),
    gtFrontRise: document.getElementById('gt_front_rise'), gtBackRise: document.getElementById('gt_back_rise'),
    gtInseam: document.getElementById('gt_inseam'), gtOutseam: document.getElementById('gt_outseam'),
    btnAddGt: document.getElementById('btn-add-gt'), gtList: document.getElementById('gt_list'),

    fbProfile: document.getElementById('fb_profile'), fbSize: document.getElementById('fb_size'),
    fbPointZero: document.getElementById('fb_point_zero'), btnSaveFb: document.getElementById('btn-save-fb'),
    analysisResult: document.getElementById('analysis-result'), resTheory: document.getElementById('res-theory'),
    resGt: document.getElementById('res-gt'), resVerdict: document.getElementById('res-verdict')
  };

  function showMsg(text, isError=false) {
    el.msg.textContent = text;
    el.msg.className = `mb-4 p-3 rounded-2xl text-white text-sm shadow-lg fixed top-5 right-5 z-50 ${isError ? 'bg-red-600' : 'bg-green-600'}`;
    el.msg.classList.remove('hidden');
    setTimeout(() => el.msg.classList.add('hidden'), 3000);
  }

  function toggleCatFields() {
    const cat = el.catType.value;
    if (cat === 'top' || cat === 'full') {
      el.wrapSleeve.classList.remove('hidden'); el.theoryTopFields.classList.remove('hidden'); el.gtTopFields.classList.remove('hidden');
    } else {
      el.wrapSleeve.classList.add('hidden'); el.theoryTopFields.classList.add('hidden'); el.gtTopFields.classList.add('hidden');
    }

    if (cat === 'bottom' || cat === 'full') {
      el.wrapLeg.classList.remove('hidden'); el.wrapRise.classList.remove('hidden'); el.theoryBotFields.classList.remove('hidden'); el.gtBotFields.classList.remove('hidden');
    } else {
      el.wrapLeg.classList.add('hidden'); el.wrapRise.classList.add('hidden'); el.theoryBotFields.classList.add('hidden'); el.gtBotFields.classList.add('hidden');
    }
  }

  function switchTab(tab) {
    if (tab === 'theory') {
      el.tabTheory.classList.remove('hidden'); el.tabPractice.classList.add('hidden');
      el.btnTheory.className = 'flex-1 py-2.5 rounded-xl font-black text-sm transition shadow-sm bg-white text-gray-900';
      el.btnPractice.className = 'flex-1 py-2.5 rounded-xl font-black text-sm text-gray-500 transition hover:text-gray-900';
    } else {
      el.tabTheory.classList.add('hidden'); el.tabPractice.classList.remove('hidden');
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

  function getSkuFromUrl() { return new URL(window.location.href).searchParams.get("sku") || ""; }

  async function loadProfiles() {
    try {
      const profiles = await api('/api/profiles');
      el.fbProfile.innerHTML = '<option value="">-- Выбери профиль --</option>' + 
        profiles.map(p => `<option value="${p.id}">${p.name} (${p.height}см)</option>`).join('');
    } catch (e) {}
  }

  function populateForm(g) {
    currentGarment = g;
    el.skuDisplay.textContent = g.sku || 'Новый товар';
    el.sku.value = g.sku || ''; el.name.value = g.name || ''; el.price.value = g.price || '';
    el.imgFront.value = g.image_url || ''; el.imgBack.value = g.image_url_back || ''; el.platform.value = g.platform || 'manual';

    const theory = (g.metrics || {}).theory || {};
    groundTruthData = (g.metrics || {}).ground_truth || {};

    el.catType.value = theory.category_type || 'top';
    el.fitProfile.value = theory.fit_profile || 'regular';
    el.stiffnessClass.value = theory.stiffness_class || 'medium';
    el.elastane.value = theory.elastane_pct || 0;
    
    el.sleeveType.value = theory.sleeve_type || 'long';
    el.legType.value = theory.leg_type || 'long';
    el.riseClass.value = theory.rise_class || 'mid';
    
    el.gShoulders.value = theory.g_shoulders || ''; el.gBackWidth.value = theory.g_back_width || '';
    el.gChest.value = theory.g_chest || ''; el.gWaistTop.value = theory.g_waist_top || '';
    el.gHemTop.value = theory.g_hem_top || ''; el.gBicep.value = theory.g_bicep || '';
    el.gSleeve.value = theory.g_sleeve || ''; el.gLength.value = theory.g_length || '';
    
    el.gWaistBot.value = theory.g_waist_bot || ''; el.gBelly.value = theory.g_belly || '';
    el.gHips.value = theory.g_hips || ''; el.gThigh.value = theory.g_thigh || '';
    el.gKnee.value = theory.g_knee || ''; el.gLegOpening.value = theory.g_leg_opening || '';
    el.gFrontRise.value = theory.g_front_rise || ''; el.gBackRise.value = theory.g_back_rise || '';
    el.gInseam.value = theory.g_inseam || ''; el.gOutseam.value = theory.g_outseam || '';

    el.mSize.value = theory.model_size || ''; el.mHeight.value = theory.height || '';
    el.mChest.value = theory.chest || ''; el.mWaist.value = theory.waist || ''; el.mHips.value = theory.hips || '';

    toggleCatFields();
    renderGtList();
  }

  async function init() {
    switchTab('theory');
    el.btnTheory.addEventListener('click', () => switchTab('theory'));
    el.btnPractice.addEventListener('click', () => switchTab('practice'));
    el.catType.addEventListener('change', toggleCatFields);

    await loadProfiles();
    const sku = getSkuFromUrl();
    if (sku) {
      try { const data = await api(`/api/admin/builder/get?sku=${encodeURIComponent(sku)}`); populateForm(data); } 
      catch (e) { toggleCatFields(); }
    } else { toggleCatFields(); }
  }

  el.btnSaveTheory.addEventListener('click', async () => {
    const sku = el.sku.value.trim();
    if (!sku) return showMsg("SKU обязателен!", true);

    const payload = {
      sku, name: el.name.value.trim(), price: Number(el.price.value) || null,
      image_url: el.imgFront.value.trim(), image_url_back: el.imgBack.value.trim(), platform: el.platform.value,
      theory: {
        category_type: el.catType.value, fit_profile: el.fitProfile.value,
        stiffness_class: el.stiffnessClass.value, elastane_pct: Number(el.elastane.value) || 0,
        sleeve_type: el.sleeveType.value, leg_type: el.legType.value, rise_class: el.riseClass.value,
        
        g_shoulders: Number(el.gShoulders.value) || null, g_back_width: Number(el.gBackWidth.value) || null,
        g_chest: Number(el.gChest.value) || null, g_waist_top: Number(el.gWaistTop.value) || null,
        g_hem_top: Number(el.gHemTop.value) || null, g_bicep: Number(el.gBicep.value) || null,
        g_sleeve: Number(el.gSleeve.value) || null, g_length: Number(el.gLength.value) || null,
        g_waist_bot: Number(el.gWaistBot.value) || null, g_belly: Number(el.gBelly.value) || null,
        g_hips: Number(el.gHips.value) || null, g_thigh: Number(el.gThigh.value) || null,
        g_knee: Number(el.gKnee.value) || null, g_leg_opening: Number(el.gLegOpening.value) || null,
        g_front_rise: Number(el.gFrontRise.value) || null, g_back_rise: Number(el.gBackRise.value) || null,
        g_inseam: Number(el.gInseam.value) || null, g_outseam: Number(el.gOutseam.value) || null,

        model_size: el.mSize.value.trim(), height: Number(el.mHeight.value) || null,
        chest: Number(el.mChest.value) || null, waist: Number(el.mWaist.value) || null, hips: Number(el.mHips.value) || null,
      }
    };

    try {
      await api('/api/admin/builder/upsert', { method: 'POST', body: JSON.stringify(payload) });
      showMsg("Теория успешно сохранена!"); el.skuDisplay.textContent = sku;
      if (!currentGarment) currentGarment = { id: 999, metrics: {theory: payload.theory} };
      else currentGarment.metrics.theory = payload.theory;
    } catch (e) { showMsg(e.message, true); }
  });

  function renderGtList() {
    const sizes = Object.keys(groundTruthData);
    if (!sizes.length) { el.gtList.innerHTML = '<div class="text-xs text-gray-400">Пока нет замеров.</div>'; return; }
    el.gtList.innerHTML = sizes.map(size => {
      const d = groundTruthData[size];
      return `<div class="p-3 bg-gray-50 border border-gray-100 rounded-xl text-sm flex justify-between items-center">
        <div class="truncate w-[90%]"><strong class="text-indigo-600">Размер ${size}</strong>: ${JSON.stringify(d).replace(/[{""}]/g,'')}</div>
        <button onclick="deleteGt('${size}')" class="text-red-500 font-bold text-xs ml-2 px-2 py-1 bg-red-50 rounded hover:bg-red-100">X</button>
      </div>`;
    }).join('');
  }

  window.deleteGt = async function(size) {
    delete groundTruthData[size]; renderGtList(); await saveGroundTruthOnly();
  };

  el.btnAddGt.addEventListener('click', async () => {
    const sku = el.sku.value.trim();
    if (!sku) return showMsg("Сначала сохрани теорию!", true);
    const size = el.gtSize.value.trim().toUpperCase();
    if (!size) return showMsg("Укажи размер (Например L)!", true);

    const m = {};
    const extract = (id, key) => { const val = Number(document.getElementById(id).value); if(val) m[key] = val; };
    
    extract('gt_shoulders', 'shoulders'); extract('gt_back_width', 'back_width');
    extract('gt_chest', 'chest'); extract('gt_waist_top', 'waist_top'); extract('gt_hem_top', 'hem_top');
    extract('gt_bicep', 'bicep'); extract('gt_sleeve', 'sleeve'); extract('gt_length_top', 'length_top');
    
    extract('gt_waist_bot', 'waist_bottom'); extract('gt_belly', 'belly'); extract('gt_hips', 'hips');
    extract('gt_thigh', 'thigh'); extract('gt_knee', 'knee'); extract('gt_leg_opening', 'leg_opening');
    extract('gt_front_rise', 'front_rise'); extract('gt_back_rise', 'back_rise');
    extract('gt_inseam', 'inseam'); extract('gt_outseam', 'outseam');

    if (Object.keys(m).length === 0) return showMsg("Введи хотя бы один замер!", true);
    groundTruthData[size] = m;
    
    document.querySelectorAll('#gt_top_fields input, #gt_bot_fields input').forEach(i => i.value = '');
    el.gtSize.value = '';
    
    renderGtList(); await saveGroundTruthOnly();
  });

  async function saveGroundTruthOnly() {
    const sku = el.sku.value.trim(); if (!sku) return;
    try { await api('/api/admin/builder/upsert', { method: 'POST', body: JSON.stringify({ sku: sku, ground_truth: groundTruthData }) }); showMsg("Замер добавлен!"); } 
    catch (e) { showMsg(e.message, true); }
  }

  el.btnSaveFb.addEventListener('click', async () => {
    if (!currentGarment || !currentGarment.id) return showMsg("Сначала сохрани товар!", true);
    const userId = el.fbProfile.value; if (!userId) return showMsg("Выбери профиль!", true);
    const sizeSelected = el.fbSize.value.trim().toUpperCase(); if (!sizeSelected) return showMsg("Укажи размер!", true);

    const payload = {
      garment_id: currentGarment.id, user_id: userId, size_selected: sizeSelected,
      is_point_zero: el.fbPointZero.checked, fit_matrix: null
    };

    try {
      const data = await api('/api/feedback', { method: 'POST', body: JSON.stringify(payload) });
      showMsg("Примерка отправлена!");
      
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

        let xrayHtml = `<div class="mt-4 border-t border-indigo-200/50 pt-4"><h4 class="text-[11px] uppercase tracking-widest text-indigo-500 font-extrabold mb-3">Рентген по данным сайта:</h4><div class="space-y-3">`;
        (data.analysis.xray || []).forEach(sz => {
            xrayHtml += `
            <div class="bg-white p-2 rounded-xl border ${sz.hard_fit === 'FAIL' ? 'border-red-200 opacity-60' : 'border-indigo-100'} text-xs">
                <div class="font-black mb-1 text-gray-800 border-b border-gray-100 pb-1">Размер ${sz.size_label} <span class="font-bold ${sz.hard_fit === 'FAIL' ? 'text-red-500' : 'text-indigo-600'} float-right">${Math.round(sz.score)}%</span></div>
                ${sz.xray_zones.map(z => `<div class="flex justify-between py-0.5"><span class="text-gray-500">${z.zone_name}</span> <span class="font-bold ${z.penalty > 0 ? 'text-red-500' : 'text-green-600'}">${z.status}</span></div>`).join('')}
            </div>`;
        });
        xrayHtml += `</div></div>`;
        
        let existingXray = document.getElementById('builder-xray');
        if (existingXray) existingXray.remove();
        let xrayContainer = document.createElement('div');
        xrayContainer.id = 'builder-xray'; xrayContainer.innerHTML = xrayHtml;
        el.resVerdict.parentNode.appendChild(xrayContainer);
      }
    } catch (e) { showMsg(e.message, true); }
  });

  init();
})();

