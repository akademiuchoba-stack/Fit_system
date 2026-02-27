(() => {
  const PLACEHOLDER_IMG = `data:image/svg+xml;charset=utf-8,<svg xmlns='http://www.w3.org/2000/svg' width='600' height='750'><rect width='100%25' height='100%25' fill='%23f3f4f6'/><text x='50%25' y='50%25' dominant-baseline='middle' text-anchor='middle' fill='%239ca3af' font-family='Inter,Arial' font-size='28'>no image</text></svg>`;

  const API = { profiles: '/api/profiles', calculate: (limit=50) => `/api/calculate?limit=${encodeURIComponent(limit)}` };

  const qs = (sel, root=document) => root.querySelector(sel);
  function show(el){ if(el) el.classList.remove('hidden'); }
  function hide(el){ if(el) el.classList.add('hidden'); }
  function esc(s){ return String(s ?? '').replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m])); }
  function fmt(n){ const x = Number(n); return Number.isFinite(x) ? String(Math.round(x*10)/10) : '—'; }
  function fmtSign(n){
    const x = Number(n);
    if(!Number.isFinite(x)) return '—';
    const v = Math.round(x*10)/10;
    return (v>0?`+${v}`:`${v}`);
  }

  async function api(url, opts={}){
    const res = await fetch(url, { headers: {'Content-Type':'application/json', ...(opts.headers||{})}, ...opts });
    if(!res.ok){
      const txt = await res.text().catch(()=> '');
      throw new Error(`${res.status} ${res.statusText}${txt?`: ${txt}`:''}`);
    }
    const ct = res.headers.get('content-type') || '';
    return ct.includes('application/json') ? res.json() : res.text();
  }

  class App {
    constructor(){
      this.state = {
        profiles: [],
        activeProfileId: Number(localStorage.getItem('fit_active_profile_id') || 0) || null,
        editProfileId: null,
        results: [],
        currentCard: null
      };

      this.el = {
        toast: qs('#toast'),
        activeProfile: qs('#active-profile'),
        mainView: qs('#main-view'),
        cabinetView: qs('#cabinet-view'),
        cards: qs('#cards'),
        emptyState: qs('#empty-state'),
        btnOpenCabinet: qs('#btn-open-cabinet'),
        btnRefresh: qs('#btn-refresh'),
        btnCabinet: qs('#btn-cabinet'),
        btnBack: qs('#btn-back'),
        profiles: qs('#profiles'),
        profilesEmpty: qs('#profiles-empty'),

        // form
        formTitle: qs('#form-title'),
        name: qs('#name'),
        gender: qs('#gender_select'),
        chest: qs('#chest'),
        waist_top: qs('#waist_top'),
        belly: qs('#belly'),
        hips: qs('#hips'),
        waist_bottom: qs('#waist_bottom'),
        high_hip: qs('#high_hip'),
        thigh: qs('#thigh'),
        bicep: qs('#bicep'),
        shoulders: qs('#shoulders'),
        arm_length: qs('#arm_length'),
        inseam: qs('#inseam'),
        leg_length: qs('#leg_length'),
        pz_belly: qs('#pz_belly'),
        pz_sleeve: qs('#pz_sleeve'),
        pz_waist_bottom: qs('#pz_waist_bottom'),
        btnSaveProfile: qs('#btn-save-profile'),
        btnClearForm: qs('#btn-clear-form'),
        btnCancelEdit: qs('#btn-cancel-edit'),

        // modal
        modal: qs('#modal'),
        btnCloseModal: qs('#btn-close-modal'),
        modalTitle: qs('#modal-title'),
        modalSubtitle: qs('#modal-subtitle'),
        modalImage: qs('#modal-image'),
        modalScore: qs('#modal-score'),
        modalExplain: qs('#modal-explain'),
        modalMetrics: qs('#modal-metrics'),
      };

      this.bind();
      this.init();
    }

    toast(msg, ok=true){
      if(!this.el.toast) return;
      this.el.toast.classList.remove('hidden');
      this.el.toast.textContent = msg;
      this.el.toast.style.background = ok ? '#111827' : '#991B1B';
      clearTimeout(this._toastTimer);
      this._toastTimer = setTimeout(()=> this.el.toast.classList.add('hidden'), 2600);
    }

    bind(){
      this.el.btnOpenCabinet?.addEventListener('click', ()=> this.openCabinet());
      this.el.btnCabinet?.addEventListener('click', ()=> this.openCabinet());
      this.el.btnBack?.addEventListener('click', ()=> this.closeCabinet());
      this.el.btnRefresh?.addEventListener('click', ()=> this.refreshResults());

      this.el.activeProfile?.addEventListener('change', () => {
        const id = Number(this.el.activeProfile.value || 0) || null;
        this.state.activeProfileId = id;
        localStorage.setItem('fit_active_profile_id', String(id || 0));
        this.refreshResults();
      });

      this.el.btnSaveProfile?.addEventListener('click', ()=> this.saveProfile());
      this.el.btnClearForm?.addEventListener('click', ()=> this.clearForm());
      this.el.btnCancelEdit?.addEventListener('click', ()=> this.cancelEdit());

      this.el.btnCloseModal?.addEventListener('click', ()=> this.closeModal());
      this.el.modal?.addEventListener('click', (e)=> { if(e.target === this.el.modal) this.closeModal(); });
    }

    async init(){
      await this.loadProfiles();
      this.syncActiveProfileSelect();
      await this.refreshResults();
    }

    async loadProfiles(){
      try {
        const data = await api(API.profiles);
        this.state.profiles = Array.isArray(data) ? data : [];
        this.renderProfiles();
        this.renderActiveProfileSelect();
      } catch(e){
        this.toast('Ошибка загрузки профилей', false);
      }
    }

    renderActiveProfileSelect(){
      const sel = this.el.activeProfile;
      if(!sel) return;
      sel.innerHTML = '';
      const opt0 = document.createElement('option');
      opt0.value = '';
      opt0.textContent = '— Выберите профиль —';
      sel.appendChild(opt0);

      for(const p of this.state.profiles){
        const opt = document.createElement('option');
        opt.value = String(p.id);
        opt.textContent = `${p.name || ('Profile ' + p.id)} (${p.gender || 'n/a'})`;
        sel.appendChild(opt);
      }
      this.syncActiveProfileSelect();
    }

    syncActiveProfileSelect(){
      if(!this.el.activeProfile) return;
      const id = this.state.activeProfileId;
      if(id) this.el.activeProfile.value = String(id);
    }

    openCabinet(){ hide(this.el.mainView); show(this.el.cabinetView); }
    closeCabinet(){ hide(this.el.cabinetView); show(this.el.mainView); }

    renderProfiles(){
      if(!this.el.profiles) return;
      this.el.profiles.innerHTML = '';
      if(!this.state.profiles.length){
        show(this.el.profilesEmpty); return;
      }
      hide(this.el.profilesEmpty);

      for(const p of this.state.profiles){
        const card = document.createElement('div');
        card.className = 'p-4 rounded-2xl border border-gray-200 bg-white flex items-center justify-between gap-2';
        card.innerHTML = `
          <div>
            <div class="font-black">${esc(p.name || ('Profile ' + p.id))}</div>
            <div class="text-xs text-gray-500 mt-0.5">ID ${p.id} • ${esc(p.gender || '—')}</div>
          </div>
          <div class="flex gap-2">
            <button data-act="use" data-id="${p.id}" class="px-3 py-2 rounded-xl bg-indigo-600 text-white text-xs font-black hover:bg-indigo-700">Активировать</button>
          </div>
        `;
        card.querySelector('[data-act="use"]').addEventListener('click', ()=>{
          this.state.activeProfileId = Number(p.id);
          localStorage.setItem('fit_active_profile_id', String(p.id));
          this.renderActiveProfileSelect();
          this.closeCabinet();
          this.refreshResults();
        });
        this.el.profiles.appendChild(card);
      }
    }

    _problemZonesFromForm(){
      const zones = [];
      if(this.el.pz_belly?.checked) zones.push('belly');
      if(this.el.pz_sleeve?.checked) zones.push('sleeve');
      if(this.el.pz_waist_bottom?.checked) zones.push('waist_bottom');
      return zones;
    }

    clearForm(){
      this.state.editProfileId = null;
      this.el.formTitle.textContent = 'Новый профиль';
      this.el.btnCancelEdit.classList.add('hidden');
      ['name','chest','waist_top','belly','hips','waist_bottom','high_hip','thigh','bicep','shoulders','arm_length','inseam','leg_length'].forEach(id=>{
        const el = qs('#'+id);
        if(el) el.value = '';
      });
      this.el.gender.value = 'male';
      this.el.pz_belly.checked = false;
      this.el.pz_sleeve.checked = false;
      this.el.pz_waist_bottom.checked = false;
    }

    cancelEdit(){
      this.clearForm();
      this.toast('Отмена');
    }

    async saveProfile(){
      const name = (this.el.name.value || '').trim();
      if(!name){ this.toast('Укажите имя профиля', false); return; }
      const payload = {
        name,
        gender: this.el.gender.value,
        chest: Number(this.el.chest.value || 0) || null,
        waist_top: Number(this.el.waist_top.value || 0) || null,
        belly: Number(this.el.belly.value || 0) || null,
        hips: Number(this.el.hips.value || 0) || null,
        waist_bottom: Number(this.el.waist_bottom.value || 0) || null,
        high_hip: Number(this.el.high_hip.value || 0) || null,
        thigh: Number(this.el.thigh.value || 0) || null,
        bicep: Number(this.el.bicep.value || 0) || null,
        shoulders: Number(this.el.shoulders.value || 0) || null,
        arm_length: Number(this.el.arm_length.value || 0) || null,
        inseam: Number(this.el.inseam.value || 0) || null,
        leg_length: Number(this.el.leg_length.value || 0) || null,
        problem_zones: this._problemZonesFromForm(),
        comfort_C: {}
      };
      try {
        await api('/api/profiles', { method:'POST', body: JSON.stringify(payload) });
        this.toast('Профиль сохранён');
        await this.loadProfiles();
      } catch(e){
        this.toast('Ошибка сохранения профиля', false);
      }
    }

    async refreshResults(){
      if(!this.state.activeProfileId){
        this.state.results = [];
        this.renderCards();
        show(this.el.emptyState);
        return;
      }
      try {
        const data = await api(API.calculate(50), { method: 'POST', body: JSON.stringify({ profile_id: this.state.activeProfileId }) });
        this.state.results = Array.isArray(data) ? data : [];
        this.renderCards();
      } catch (e) {
        this.toast('Ошибка загрузки рекомендаций', false);
      }
    }

    renderCards(){
      if(!this.el.cards) return;
      this.el.cards.innerHTML = '';
      const list = this.state.results;
      if(!list.length){
        show(this.el.emptyState);
        return;
      }
      hide(this.el.emptyState);

      for(const r of list){
        const card = document.createElement('div');
        card.className = 'bg-white rounded-3xl border border-gray-100 shadow-sm overflow-hidden hover:shadow-xl transition-all cursor-pointer flex flex-col transform hover:-translate-y-1';

        const img = r?.image_url || PLACEHOLDER_IMG;
        const scoreVal = Number(r?.score ?? 0);
        const confVal = Number(r?.confidence ?? 0);

        let scoreColor = 'text-green-600 bg-green-50 border-green-200';
        if (scoreVal < 80) scoreColor = 'text-cyan-600 bg-cyan-50 border-cyan-200';
        if (scoreVal < 60) scoreColor = 'text-yellow-600 bg-yellow-50 border-yellow-200';
        if (scoreVal < 40) scoreColor = 'text-red-600 bg-red-50 border-red-200';

        let confColor = 'text-green-700 bg-green-50 border-green-200';
        if (confVal < 80) confColor = 'text-cyan-700 bg-cyan-50 border-cyan-200';
        if (confVal < 60) confColor = 'text-yellow-700 bg-yellow-50 border-yellow-200';
        if (confVal < 40) confColor = 'text-red-700 bg-red-50 border-red-200';

        const explainParts = (r?.explain || '').split('|').map(s => s.trim()).filter(Boolean);
        const mainVerdict = explainParts[0] || 'Нет данных';

        card.innerHTML = `
          <div class="aspect-[4/5] bg-gray-50 overflow-hidden relative">
            <img src="${esc(img)}" onerror="this.src='${PLACEHOLDER_IMG}'" class="w-full h-full object-cover"/>
            <div class="absolute top-3 right-3 flex flex-col gap-2 items-end">
              <div class="px-3 py-1.5 rounded-xl border font-black text-sm shadow-md backdrop-blur-md ${scoreColor}">${Math.round(scoreVal)}%</div>
              <div class="px-3 py-1 rounded-xl border font-extrabold text-[11px] shadow-md backdrop-blur-md ${confColor}">conf ${Math.round(confVal)}%</div>
            </div>
          </div>
          <div class="p-5 flex flex-col flex-1">
            <div class="font-black text-lg truncate">${esc(r?.name || r?.sku || '—')}</div>
            <div class="text-[10px] text-gray-400 mt-1 uppercase tracking-widest font-extrabold">${esc(r?.platform || '')} • SKU ${esc(r?.sku)}</div>
            <div class="mt-4 text-sm font-bold text-gray-700 flex-1 leading-snug">${esc(mainVerdict)}</div>
            <div class="mt-4 pt-4 border-t border-gray-100 flex items-center justify-between">
              <div class="text-[10px] text-gray-400 uppercase tracking-widest font-extrabold">Размер: <span class="text-black text-lg ml-1">${esc(r?.best_size || '—')}</span></div>
            </div>
          </div>`;

        card.addEventListener('click', ()=> this.openModal(r));
        this.el.cards.appendChild(card);
      }
    }

    openModal(r){
      this.state.currentCard = r;

      if(this.el.modalTitle) this.el.modalTitle.textContent = r?.name || r?.sku || '—';
      if(this.el.modalSubtitle) {
        const mode = (r?.explain || '').split('(')[1]?.split(')')[0] || '—';
        this.el.modalSubtitle.textContent = `${r?.platform || ''} • SKU ${r?.sku} • Рекомендация: ${r?.best_size || '—'} • ${mode}`;
      }
      if(this.el.modalImage) this.el.modalImage.src = r?.image_url || PLACEHOLDER_IMG;
      if(this.el.modalScore) this.el.modalScore.textContent = Math.round(Number(r?.score ?? 0)) + '%';

      const confVal = Number(r?.confidence ?? 0);
      const modeStr = (r?.explain || '').split('(')[1]?.split(')')[0] || 'STANDARD';

      if(this.el.modalExplain) {
        this.el.modalExplain.innerHTML = `
          <div class="flex flex-wrap gap-2 items-center">
            <span class="px-3 py-1.5 rounded-xl border border-gray-200 bg-gray-50 text-xs font-black">Confidence: ${Math.round(confVal)}%</span>
            <span class="px-3 py-1.5 rounded-xl border border-indigo-200 bg-indigo-50 text-xs font-black text-indigo-700">Mode: ${esc(modeStr)}</span>
            <a href="/builder?sku=${encodeURIComponent(r?.sku || '')}" class="inline-flex items-center gap-2 px-3 py-1.5 rounded-xl bg-indigo-600 text-white font-black text-xs hover:bg-indigo-700 transition">
              ✎ Builder
            </a>
          </div>
        `;
      }

      // v31 xray rendering
      const sizesChips = (r.available_sizes || []).map(sz =>
        `<span class="px-3 py-1 bg-white border border-gray-200 text-gray-800 font-black text-xs rounded-lg shadow-sm">${esc(sz)}</span>`
      ).join('');

      let xrayHtml = `
        <div class="text-[11px] uppercase tracking-widest text-gray-400 font-extrabold mb-2">Размеры в наличии:</div>
        <div class="flex gap-2 flex-wrap mb-6">${sizesChips || '<span class="text-sm text-gray-500">—</span>'}</div>

        <div class="text-[11px] uppercase tracking-widest text-indigo-600 font-extrabold mb-3">Рентген посадки (v3.1)</div>
      `;

      const all = Array.isArray(r.xray) ? r.xray : [];
      if(!all.length){
        xrayHtml += `<div class="text-sm text-gray-500">Нет данных матрицы.</div>`;
        this.el.modalMetrics.innerHTML = xrayHtml;
        show(this.el.modal);
        return;
      }

      const bestSize = r.best_size;

      xrayHtml += `<div class="space-y-4">`;

      for(const sz of all){
        const isRec = String(sz.size_label) === String(bestSize);
        const hardFail = !!sz.hard_fail;

        let boxClass = 'border-gray-200 bg-white';
        if (hardFail) boxClass = 'border-red-200 bg-red-50 text-red-900 opacity-80';
        else if (isRec) boxClass = 'border-indigo-300 bg-indigo-50/50 shadow-md ring-2 ring-indigo-100';

        const score = Math.round(Number(sz.score ?? 0));
        const conf = Math.round(Number(sz.confidence ?? 0));
        const status = esc(sz.global_status || '');

        const warnings = (sz.warnings || []).slice(0,4).map(w =>
          `<div class="text-[11px] text-red-700">• ${esc(w)}</div>`
        ).join('');

        const details = Array.isArray(sz.details) ? sz.details : [];
        const rows = details.map(d => {
          const st = String(d.status || '');
          let stBadge = 'bg-green-50 text-green-700 border-green-200';
          if (st === 'TIGHT') stBadge = 'bg-red-50 text-red-700 border-red-200';
          if (st === 'LOOSE') stBadge = 'bg-amber-50 text-amber-800 border-amber-200';

          return `
            <div class="grid grid-cols-12 gap-2 text-[11px] py-1.5 border-b border-gray-100/60 last:border-0">
              <div class="col-span-5 font-bold text-gray-700 flex items-center gap-2">
                <span class="truncate">${esc(d.label || d.zone)}</span>
                ${d.inferred ? `<span class="text-[9px] bg-orange-100 text-orange-700 px-2 py-0.5 rounded-full border border-orange-200 font-extrabold uppercase">inferred</span>` : ``}
              </div>
              <div class="col-span-2 text-gray-600">Тело: <b>${fmt(d.body)}</b></div>
              <div class="col-span-2 text-gray-600">Вещь: <b>${fmt(d.garment)}</b></div>
              <div class="col-span-2 text-gray-600">Δ: <b>${fmtSign(d.delta)}</b></div>
              <div class="col-span-1 flex justify-end">
                <span class="px-2 py-0.5 rounded-full border ${stBadge} font-extrabold">${esc(st)}</span>
              </div>
            </div>
          `;
        }).join('');

        xrayHtml += `
          <div class="p-4 rounded-2xl border ${boxClass}">
            <div class="flex items-start justify-between gap-3">
              <div>
                <div class="font-black text-lg">Размер ${esc(sz.size_label)}</div>
                <div class="text-xs text-gray-600 mt-0.5">${status}</div>
              </div>
              <div class="flex gap-2">
                <span class="px-3 py-1 rounded-xl border border-gray-200 bg-white text-xs font-black">${score}%</span>
                <span class="px-3 py-1 rounded-xl border border-gray-200 bg-white text-xs font-extrabold">conf ${conf}%</span>
              </div>
            </div>

            ${warnings ? `<div class="mt-3">${warnings}</div>` : ``}

            <div class="mt-4 rounded-xl border border-gray-200 bg-white p-3">
              <div class="text-[10px] uppercase tracking-widest text-gray-400 font-extrabold mb-2">Зоны</div>
              ${rows || `<div class="text-sm text-gray-500">Нет деталей</div>`}
            </div>
          </div>
        `;
      }

      xrayHtml += `</div>`;

      this.el.modalMetrics.innerHTML = xrayHtml;
      show(this.el.modal);
    }

    closeModal(){ hide(this.el.modal); }
  }

  new App();
})();