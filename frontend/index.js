(() => {
  const PLACEHOLDER_IMG = `data:image/svg+xml;charset=utf-8,<svg xmlns='http://www.w3.org/2000/svg' width='600' height='750'><rect width='100%25' height='100%25' fill='%23f3f4f6'/><text x='50%25' y='50%25' dominant-baseline='middle' text-anchor='middle' fill='%239ca3af' font-family='Inter,Arial' font-size='28'>no image</text></svg>`;

  const API = { profiles: '/api/profiles', calculate: (limit=50) => `/api/calculate?limit=${encodeURIComponent(limit)}` };

  const qs = (sel, root=document) => root.querySelector(sel);
  function show(el){ if(el) el.classList.remove('hidden'); }
  function hide(el){ if(el) el.classList.add('hidden'); }
  function esc(s){ return String(s ?? '').replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m])); }
  function fmt(n){ const x = Number(n); return Number.isFinite(x) ? String(Math.round(x*10)/10) : '—'; }

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
      this.state = { profiles: [], activeProfileId: Number(localStorage.getItem('fit_active_profile_id') || 0) || null, editProfileId: null, results: [], currentCard: null };

      this.el = {
        toast: qs('#toast'), activeProfile: qs('#active-profile'), mainView: qs('#main-view'), cabinetView: qs('#cabinet-view'),
        cards: qs('#cards'), emptyState: qs('#empty-state'), btnOpenCabinet: qs('#btn-open-cabinet'), btnRefresh: qs('#btn-refresh'),
        btnCabinet: qs('#btn-cabinet'), btnBack: qs('#btn-back'), btnAdmin: qs('#btn-admin'), profiles: qs('#profiles'), profilesEmpty: qs('#profiles-empty'),
        form: qs('#profile-form'), formTitle: qs('#form-title'), btnClearForm: qs('#btn-clear-form'), btnCancelEdit: qs('#btn-cancel-edit'),
        genderSelect: qs('#gender_select'), wrapUnderbust: qs('#wrap_underbust'), wrapLengthDress: qs('#wrap_length_dress'),
        modal: qs('#modal'), btnCloseModal: qs('#btn-close-modal'), modalTitle: qs('#modal-title'), modalSubtitle: qs('#modal-subtitle'),
        modalImage: qs('#modal-image'), modalScore: qs('#modal-score'), modalExplain: qs('#modal-explain'), modalMetrics: qs('#modal-metrics')
      };

      this.bind(); this.init();
    }

    toast(msg){
      if(!this.el.toast) return;
      this.el.toast.textContent = msg; show(this.el.toast);
      setTimeout(()=> hide(this.el.toast), 2500);
    }

    bind(){
      if(this.el.btnCabinet) this.el.btnCabinet.addEventListener('click', ()=> this.showCabinet());
      if(this.el.btnOpenCabinet) this.el.btnOpenCabinet.addEventListener('click', ()=> this.showCabinet());
      if(this.el.btnBack) this.el.btnBack.addEventListener('click', ()=> this.showMain());
      if(this.el.btnRefresh) this.el.btnRefresh.addEventListener('click', ()=> this.refreshResults());
      if(this.el.btnAdmin) this.el.btnAdmin.addEventListener('click', ()=> { window.location.href = '/admin'; });
      if(this.el.btnCloseModal) this.el.btnCloseModal.addEventListener('click', ()=> this.closeModal());
      if(this.el.modal) this.el.modal.addEventListener('click', (e)=> { if(e.target === this.el.modal) this.closeModal(); });
      if(this.el.btnClearForm) this.el.btnClearForm.addEventListener('click', ()=> this.clearForm());
      if(this.el.btnCancelEdit) this.el.btnCancelEdit.addEventListener('click', ()=> this.clearForm());

      if(this.el.genderSelect) {
          this.el.genderSelect.addEventListener('change', () => this.toggleGenderFields());
      }

      if(this.el.form){
        this.el.form.addEventListener('submit', (e)=> {
          e.preventDefault(); this.saveProfileFromForm().catch(err=> this.toast(err.message));
        });
      }
    }

    async init(){ await this.loadProfiles(); await this.refreshResults(); this.toggleGenderFields(); }

    toggleGenderFields() {
        if (!this.el.genderSelect) return;
        const isFemale = this.el.genderSelect.value === 'female';
        if (isFemale) { show(this.el.wrapUnderbust); show(this.el.wrapLengthDress); } 
        else { hide(this.el.wrapUnderbust); hide(this.el.wrapLengthDress); }
    }

    showCabinet(){ hide(this.el.mainView); show(this.el.cabinetView); this.renderProfiles(); this.clearForm(); }
    showMain(){ hide(this.el.cabinetView); show(this.el.mainView); }

    setActiveProfile(id){
      this.state.activeProfileId = id; localStorage.setItem('fit_active_profile_id', String(id || ''));
      const p = this.state.profiles.find(x=> x.id === id);
      if(this.el.activeProfile) this.el.activeProfile.textContent = p ? p.name : '—';
    }

    async loadProfiles(){
      const list = await api(API.profiles); this.state.profiles = Array.isArray(list) ? list : [];
      const exists = this.state.activeProfileId && this.state.profiles.some(p=>p.id===this.state.activeProfileId);
      if(!exists) this.state.activeProfileId = this.state.profiles[0]?.id || null;
      this.setActiveProfile(this.state.activeProfileId);
    }

    renderProfiles(){
      if(!this.el.profiles) return;
      this.el.profiles.innerHTML = ''; const items = this.state.profiles;
      if(!items.length) { show(this.el.profilesEmpty); return; }
      hide(this.el.profilesEmpty);

      for(const p of items){
        const isActive = p.id === this.state.activeProfileId;
        const row = document.createElement('div');
        row.className = `p-4 rounded-2xl border ${isActive ? 'border-indigo-200 bg-indigo-50/50' : 'border-gray-100 bg-white'} hover:border-indigo-200 transition cursor-pointer`;
        row.innerHTML = `
          <div class="flex items-start justify-between gap-3">
            <div class="min-w-0">
              <div class="flex items-center gap-2">
                <div class="font-black text-lg truncate">${esc(p.name)}</div>
                ${isActive ? `<span class="text-[10px] font-extrabold uppercase tracking-widest px-2 py-1 rounded-full bg-indigo-600 text-white">активен</span>` : ''}
              </div>
              <div class="text-xs text-gray-500 mt-1">Рост: ${fmt(p.height)}см | Грудь: ${fmt(p.chest)}см</div>
            </div>
          </div>
          <div class="mt-4 flex flex-wrap gap-2">
            <button data-act="activate" class="px-4 py-2 rounded-xl bg-gray-900 text-white font-extrabold text-[11px] uppercase tracking-widest hover:bg-indigo-600 transition shadow-sm">Выбрать</button>
            <button data-act="edit" class="px-4 py-2 rounded-xl bg-white border border-gray-200 text-gray-700 font-extrabold text-[11px] uppercase tracking-widest hover:bg-gray-50 transition shadow-sm">Изменить</button>
            <button data-act="delete" class="px-4 py-2 rounded-xl bg-white border border-rose-200 text-rose-700 font-extrabold text-[11px] uppercase tracking-widest hover:bg-rose-50 transition shadow-sm">Удалить</button>
          </div>`;
        row.addEventListener('click', (e)=> {
          const btn = e.target?.closest('button[data-act]');
          if(!btn) { this.setActiveProfile(p.id); this.refreshResults().catch(()=>{}); return; }
          e.preventDefault(); e.stopPropagation();
          const act = btn.getAttribute('data-act');
          if(act==='activate'){ this.setActiveProfile(p.id); this.toast(`Активен: ${p.name}`); this.refreshResults().catch(()=>{}); }
          else if(act==='edit'){ this.loadProfileIntoForm(p); }
          else if(act==='delete'){ if(confirm('Удалить профиль?')) this.deleteProfile(p.id).catch(err=> this.toast(err.message)); }
        });
        this.el.profiles.appendChild(row);
      }
    }

    loadProfileIntoForm(p){
      this.state.editProfileId = p.id;
      if(this.el.formTitle) this.el.formTitle.textContent = `Редактирование: ${p.name}`;
      const f = this.el.form; if(!f) return;
      
      f.name.value = p.name ?? ''; f.gender.value = p.gender ?? 'male'; f.height.value = p.height ?? '';
      f.b_neck.value = p.neck ?? ''; f.b_shoulders.value = p.shoulders ?? ''; f.b_back_width.value = p.back_width ?? '';
      f.b_chest.value = p.chest ?? ''; f.b_underbust.value = p.underbust ?? ''; f.b_waist_top.value = p.waist_top ?? ''; 
      f.b_bicep.value = p.bicep ?? ''; f.b_arm_length.value = p.arm_length ?? ''; f.b_length_dress.value = p.length_dress ?? '';
      f.b_waist_bottom.value = p.waist_bottom ?? ''; f.b_belly.value = p.belly ?? ''; f.b_high_hip.value = p.high_hip ?? ''; 
      f.b_hips.value = p.hips ?? ''; f.b_thigh.value = p.thigh ?? ''; f.b_knee.value = p.knee ?? ''; f.b_calf.value = p.calf ?? ''; 
      f.b_outseam.value = p.leg_length ?? ''; f.b_inseam.value = p.inseam ?? ''; f.id.value = p.id ?? '';

      this.toggleGenderFields();

      const pz = p.problem_zones || [];
      ['shoulders', 'chest', 'belly', 'hips', 'thigh', 'bicep'].forEach(z => {
          if (f['pz_'+z]) f['pz_'+z].checked = pz.includes(z);
      });

      const c = p.comfort_C || {};
      if(c.top) {
          f.c_top_shoulders.value = c.top.shoulders ?? ''; f.c_top_back.value = c.top.back_width ?? '';
          f.c_top_chest.value = c.top.chest ?? ''; f.c_top_waist.value = c.top.waist_top ?? '';
          f.c_top_hem.value = c.top.hem_top ?? ''; f.c_top_length.value = c.top.length_top ?? '';
          f.c_top_sleeve.value = c.top.sleeve ?? ''; f.c_top_bicep.value = c.top.bicep ?? '';
      } else {
          f.c_top_shoulders.value = ''; f.c_top_back.value = ''; f.c_top_chest.value = ''; f.c_top_waist.value = '';
          f.c_top_hem.value = ''; f.c_top_length.value = ''; f.c_top_sleeve.value = ''; f.c_top_bicep.value = '';
      }
      
      if(c.bottom) {
          f.c_bot_waist.value = c.bottom.waist_bottom ?? ''; f.c_bot_high_hip.value = c.bottom.high_hip ?? '';
          f.c_bot_hips.value = c.bottom.hips ?? ''; f.c_bot_thigh.value = c.bottom.thigh ?? '';
          f.c_bot_knee.value = c.bottom.knee ?? ''; f.c_bot_opening.value = c.bottom.leg_opening ?? '';
          f.c_bot_inseam.value = c.bottom.inseam ?? ''; f.c_bot_outseam.value = c.bottom.outseam ?? '';
          f.c_bot_front_rise.value = c.bottom.front_rise ?? ''; f.c_bot_back_rise.value = c.bottom.back_rise ?? '';
      } else {
          f.c_bot_waist.value = ''; f.c_bot_high_hip.value = ''; f.c_bot_hips.value = ''; f.c_bot_thigh.value = '';
          f.c_bot_knee.value = ''; f.c_bot_opening.value = ''; f.c_bot_inseam.value = ''; f.c_bot_outseam.value = '';
          f.c_bot_front_rise.value = ''; f.c_bot_back_rise.value = '';
      }
      show(this.el.btnCancelEdit);
    }

    clearForm(){
      this.state.editProfileId = null;
      if(this.el.formTitle) this.el.formTitle.textContent = 'Новый профиль';
      const f = this.el.form; if(!f) return;
      f.reset(); f.id.value = ''; this.toggleGenderFields();
      hide(this.el.btnCancelEdit);
    }

    async saveProfileFromForm(){
      const f = this.el.form; if(!f) return;
      
      const problem_zones = [];
      ['shoulders', 'chest', 'belly', 'hips', 'thigh', 'bicep'].forEach(z => {
          if (f['pz_'+z] && f['pz_'+z].checked) problem_zones.push(z);
      });

      const comfort_C = {};
      const tKeys = ['shoulders', 'back', 'chest', 'waist', 'hem', 'length', 'sleeve', 'bicep'];
      const tMap = {'back':'back_width', 'waist':'waist_top', 'hem':'hem_top', 'length':'length_top'};
      let hasTop = false; comfort_C.top = {};
      tKeys.forEach(k => { const val = Number(f['c_top_'+k]?.value); if (val) { comfort_C.top[tMap[k] || k] = val; hasTop = true; } });
      if (!hasTop) delete comfort_C.top;

      const bKeys = ['waist', 'high_hip', 'hips', 'thigh', 'knee', 'opening', 'inseam', 'outseam', 'front_rise', 'back_rise'];
      const bMap = {'waist':'waist_bottom', 'opening':'leg_opening'};
      let hasBot = false; comfort_C.bottom = {};
      bKeys.forEach(k => { const val = Number(f['c_bot_'+k]?.value); if (val) { comfort_C.bottom[bMap[k] || k] = val; hasBot = true; } });
      if (!hasBot) delete comfort_C.bottom;

      const payload = {
        name: f.name.value.trim(), gender: f.gender.value, height: Number(f.height.value || 0),
        neck: Number(f.b_neck.value || 0) || null, shoulders: Number(f.b_shoulders.value || 0) || null,
        back_width: Number(f.b_back_width.value || 0) || null, chest: Number(f.b_chest.value || 0) || null,
        underbust: Number(f.b_underbust.value || 0) || null, waist_top: Number(f.b_waist_top.value || 0) || null, 
        belly: Number(f.b_belly.value || 0) || null, bicep: Number(f.b_bicep.value || 0) || null,
        arm_length: Number(f.b_arm_length.value || 0) || null, length_dress: Number(f.b_length_dress.value || 0) || null,
        waist_bottom: Number(f.b_waist_bottom.value || 0) || null, high_hip: Number(f.b_high_hip.value || 0) || null, 
        hips: Number(f.b_hips.value || 0) || null, thigh: Number(f.b_thigh.value || 0) || null, 
        knee: Number(f.b_knee.value || 0) || null, calf: Number(f.b_calf.value || 0) || null, 
        leg_length: Number(f.b_outseam.value || 0) || null, inseam: Number(f.b_inseam.value || 0) || null,
        problem_zones: problem_zones, comfort_C: Object.keys(comfort_C).length > 0 ? comfort_C : null
      };

      if(!payload.name) throw new Error('Имя профиля обязательно');

      if(this.state.editProfileId){
        await api(`/api/profiles/${this.state.editProfileId}`, {method:'PUT', body: JSON.stringify(payload)});
        this.toast('Профиль обновлён');
      } else {
        await api(`/api/profiles`, {method:'POST', body: JSON.stringify(payload)});
        this.toast('Профиль создан');
      }
      await this.loadProfiles(); this.renderProfiles(); this.clearForm(); await this.refreshResults();
    }

    async deleteProfile(id){
      await api(`/api/profiles/${id}`, {method:'DELETE'}); this.toast('Удалено');
      await this.loadProfiles(); this.renderProfiles(); await this.refreshResults();
    }

    async refreshResults(){
      if(!this.state.activeProfileId){ this.state.results = []; this.renderCards(); return; }
      try {
        const data = await api(API.calculate(50), { method: 'POST', body: JSON.stringify({ profile_id: this.state.activeProfileId }) });
        this.state.results = Array.isArray(data) ? data : []; this.renderCards();
      } catch (e) { this.toast('Ошибка загрузки рекомендаций'); }
    }

    renderCards(){
      if(!this.el.cards) return; this.el.cards.innerHTML = ''; const list = this.state.results;
      if(!list.length){ show(this.el.emptyState); return; }
      hide(this.el.emptyState);

      for(const r of list){
        const card = document.createElement('div');
        card.className = 'bg-white rounded-3xl border border-gray-100 shadow-sm overflow-hidden hover:shadow-xl transition-all cursor-pointer flex flex-col transform hover:-translate-y-1';

        const img = r?.image_url || PLACEHOLDER_IMG; const scoreVal = Number(r?.score ?? 0);
        let scoreColor = 'text-green-600 bg-green-50 border-green-200';
        if (scoreVal < 80) scoreColor = 'text-cyan-600 bg-cyan-50 border-cyan-200';
        if (scoreVal < 60) scoreColor = 'text-yellow-600 bg-yellow-50 border-yellow-200';
        if (scoreVal < 40) scoreColor = 'text-red-600 bg-red-50 border-red-200';

        const explainParts = (r?.explain || '').split('|').map(s => s.trim()).filter(Boolean);
        const mainVerdict = explainParts[0] || 'Нет данных';

        card.innerHTML = `
          <div class="aspect-[4/5] bg-gray-50 overflow-hidden relative">
            <img src="${esc(img)}" onerror="this.src='${PLACEHOLDER_IMG}'" class="w-full h-full object-cover"/>
            <div class="absolute top-3 right-3 px-3 py-1.5 rounded-xl border font-black text-sm shadow-md backdrop-blur-md ${scoreColor}">${Math.round(scoreVal)}%</div>
          </div>
          <div class="p-5 flex flex-col flex-1">
            <div class="font-black text-lg truncate">${esc(r?.name || r?.sku || '—')}</div>
            <div class="text-[10px] text-gray-400 mt-1 uppercase tracking-widest font-extrabold">${esc(r?.platform || '')} • SKU ${esc(r?.sku)}</div>
            <div class="mt-4 text-sm font-bold text-gray-700 flex-1 leading-snug">${esc(mainVerdict)}</div>
            <div class="mt-4 pt-4 border-t border-gray-100 flex items-center justify-between">
              <div class="text-[10px] text-gray-400 uppercase tracking-widest font-extrabold">Размер: <span class="text-black text-lg ml-1">${esc(r?.best_size || '—')}</span></div>
            </div>
          </div>`;
        card.addEventListener('click', ()=> this.openModal(r)); this.el.cards.appendChild(card);
      }
    }

    openModal(r){
      this.state.currentCard = r;
      if(this.el.modalTitle) this.el.modalTitle.textContent = r?.name || r?.sku || '—';
      if(this.el.modalSubtitle) this.el.modalSubtitle.textContent = `${r?.platform || ''} • SKU ${r?.sku} • Рекомендация: ${r?.best_size || '—'}`;
      if(this.el.modalImage) this.el.modalImage.src = r?.image_url || PLACEHOLDER_IMG;
      if(this.el.modalScore) this.el.modalScore.textContent = Math.round(Number(r?.score ?? 0)) + '%';

      if(this.el.modalExplain) {
        this.el.modalExplain.innerHTML = `
          <div class="mt-2 pt-4 border-t border-gray-100 flex gap-2">
            <a href="/builder?sku=${encodeURIComponent(r?.sku || '')}" class="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-50 border border-indigo-200 text-indigo-700 font-extrabold text-[11px] uppercase tracking-widest hover:bg-indigo-100 transition">
              ✎ Настроить (Builder)
            </a>
          </div>`;
      }

      let xrayHtml = `
        <div class="text-[11px] uppercase tracking-widest text-gray-400 font-extrabold mb-2">Размеры в наличии:</div>
        <div class="flex gap-2 flex-wrap mb-6">
            ${(r.available_sizes || []).map(sz => `<span class="px-3 py-1 bg-white border border-gray-200 text-gray-800 font-black text-xs rounded-lg shadow-sm">${sz}</span>`).join('')}
        </div>
        <div class="text-[11px] uppercase tracking-widest text-indigo-600 font-extrabold mb-3">Рентген посадки (Матрица IP 2.0)</div>
        <div class="space-y-4">`;
      
      (r.xray || []).forEach(sz => {
          let isRec = sz.size_label === r.best_size;
          let colorClass = 'border-gray-200 bg-white';
          if (sz.hard_fit === 'FAIL') colorClass = 'border-red-200 bg-red-50 text-red-900 opacity-60';
          else if (isRec) colorClass = 'border-indigo-300 bg-indigo-50/50 shadow-md ring-2 ring-indigo-100';
          
          let zonesHtml = (sz.xray_zones || []).map(z => `
              <div class="flex flex-col sm:flex-row sm:justify-between text-[11px] py-1.5 border-b border-gray-100/50 last:border-0 hover:bg-gray-50/50 transition px-1 rounded">
                  <span class="sm:w-1/3 truncate font-bold text-gray-700 flex items-center gap-1">
                      ${z.zone_name} 
                      ${z.inferred ? '<span class="text-[8px] bg-orange-100 text-orange-600 px-1.5 py-0.5 rounded uppercase tracking-wider">Inferred</span>' : ''}
                  </span>
                  <span class="sm:w-1/3 text-gray-500 font-mono text-[10px]">C:${fmt(z.target_val)} → В:${fmt(z.garment_val)}</span>
                  <span class="sm:w-1/3 sm:text-right font-bold ${z.penalty > 0 ? 'text-red-500' : 'text-green-600'}">${z.status} (${fmt(z.delta_eff)}см)</span>
              </div>
          `).join('');

          xrayHtml += `
              <div class="rounded-2xl border ${colorClass} p-4 transition-all overflow-hidden">
                  <div class="flex justify-between items-center mb-3 pb-3 border-b border-gray-100/50">
                      <div class="font-black text-base flex items-center gap-2">
                          Размер ${sz.size_label} 
                          ${!sz.is_available ? '<span class="text-[9px] uppercase tracking-widest bg-gray-200 text-gray-500 px-2 py-1 rounded-md">Теория</span>' : ''}
                      </div>
                      <div class="font-black text-sm ${sz.hard_fit === 'FAIL' ? 'text-red-600' : 'text-indigo-600'}">${Math.round(sz.score)}% - ${sz.global_status}</div>
                  </div>
                  <div>${zonesHtml}</div>
                  ${(sz.warnings || []).length ? `<div class="mt-3 text-[10px] text-red-600 font-bold bg-white p-2 rounded-xl border border-red-100 shadow-sm leading-relaxed">${sz.warnings.join('<br>')}</div>` : ''}
              </div>`;
      });
      xrayHtml += `</div>`;
      if(this.el.modalMetrics) this.el.modalMetrics.innerHTML = xrayHtml;
      show(this.el.modal);
    }

    closeModal(){ hide(this.el.modal); }
  }

  new App();
})();