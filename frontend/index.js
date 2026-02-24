(() => {
  const PLACEHOLDER_IMG = `data:image/svg+xml;charset=utf-8,<svg xmlns='http://www.w3.org/2000/svg' width='600' height='750'><rect width='100%25' height='100%25' fill='%23f3f4f6'/><text x='50%25' y='50%25' dominant-baseline='middle' text-anchor='middle' fill='%239ca3af' font-family='Inter,Arial' font-size='28'>no image</text></svg>`;

  const API = {
    profiles: '/api/profiles',
    calculate: (limit=50) => `/api/calculate?limit=${encodeURIComponent(limit)}`
  };

  const qs = (sel, root=document) => root.querySelector(sel);

  function show(el){ if(el) el.classList.remove('hidden'); }
  function hide(el){ if(el) el.classList.add('hidden'); }
  function esc(s){ return String(s ?? '').replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m])); }
  function fmt(n){ const x = Number(n); return Number.isFinite(x) ? String(Math.round(x*10)/10) : '—'; }

  async function api(url, opts={}){
    const res = await fetch(url, {
      headers: {'Content-Type':'application/json', ...(opts.headers||{})},
      ...opts
    });
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
        currentCard: null,
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
        btnAdmin: qs('#btn-admin'),
        profiles: qs('#profiles'),
        profilesEmpty: qs('#profiles-empty'),
        form: qs('#profile-form'),
        formTitle: qs('#form-title'),
        btnClearForm: qs('#btn-clear-form'),
        btnCancelEdit: qs('#btn-cancel-edit'),
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

    toast(msg){
      if(!this.el.toast) return;
      this.el.toast.textContent = msg;
      show(this.el.toast);
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

      if(this.el.form){
        this.el.form.addEventListener('submit', (e)=> {
          e.preventDefault();
          this.saveProfileFromForm().catch(err=> this.toast(err.message));
        });
      }
    }

    async init(){
      await this.loadProfiles();
      await this.refreshResults();
    }

    showCabinet(){
      hide(this.el.mainView);
      show(this.el.cabinetView);
      this.renderProfiles();
      this.clearForm();
    }

    showMain(){
      hide(this.el.cabinetView);
      show(this.el.mainView);
    }

    setActiveProfile(id){
      this.state.activeProfileId = id;
      localStorage.setItem('fit_active_profile_id', String(id || ''));
      const p = this.state.profiles.find(x=> x.id === id);
      if(this.el.activeProfile) this.el.activeProfile.textContent = p ? p.name : '—';
    }

    async loadProfiles(){
      const list = await api(API.profiles);
      this.state.profiles = Array.isArray(list) ? list : [];
      const exists = this.state.activeProfileId && this.state.profiles.some(p=>p.id===this.state.activeProfileId);
      if(!exists){
        this.state.activeProfileId = this.state.profiles[0]?.id || null;
      }
      this.setActiveProfile(this.state.activeProfileId);
    }

    renderProfiles(){
      if(!this.el.profiles) return;
      this.el.profiles.innerHTML = '';
      const items = this.state.profiles;

      if(!items.length){
        show(this.el.profilesEmpty);
        return;
      }
      hide(this.el.profilesEmpty);

      for(const p of items){
        const isActive = p.id === this.state.activeProfileId;
        const row = document.createElement('div');
        row.className = `p-4 rounded-2xl border ${isActive ? 'border-indigo-200 bg-indigo-50' : 'border-gray-100 bg-white'} hover:border-indigo-200 transition cursor-pointer`;

        row.innerHTML = `
          <div class="flex items-start justify-between gap-3">
            <div class="min-w-0">
              <div class="flex items-center gap-2">
                <div class="font-black truncate">${esc(p.name)}</div>
                ${isActive ? `<span class="text-[10px] font-extrabold uppercase tracking-widest px-2 py-1 rounded-full bg-indigo-600 text-white">активен</span>` : ''}
              </div>
              <div class="text-xs text-gray-600 mt-1">
                Рост ${fmt(p.height)} • Г ${fmt(p.chest)} • Т ${fmt(p.waist)} • Б ${fmt(p.hips)} • ШШ ${fmt(p.inseam)}
              </div>
            </div>
          </div>

          <div class="mt-3 flex flex-wrap gap-2">
            <button data-act="activate" class="px-3 py-2 rounded-xl bg-gray-900 text-white font-extrabold text-[11px] uppercase tracking-widest hover:bg-gray-800 transition">Выбрать</button>
            <button data-act="edit" class="px-3 py-2 rounded-xl bg-gray-50 border border-gray-200 text-gray-700 font-extrabold text-[11px] uppercase tracking-widest hover:bg-gray-100 transition">Изменить</button>
            <button data-act="delete" class="px-3 py-2 rounded-xl bg-white border border-rose-200 text-rose-700 font-extrabold text-[11px] uppercase tracking-widest hover:bg-rose-50 transition">Удалить</button>
          </div>
        `;

        row.addEventListener('click', (e)=> {
          const btn = e.target?.closest('button[data-act]');
          if(!btn) {
              this.setActiveProfile(p.id);
              this.refreshResults().catch(()=>{});
              return;
          }
          e.preventDefault();
          e.stopPropagation();
          const act = btn.getAttribute('data-act');
          if(act==='activate'){
            this.setActiveProfile(p.id);
            this.toast(`Активен: ${p.name}`);
            this.refreshResults().catch(()=>{});
          } else if(act==='edit'){
            this.loadProfileIntoForm(p);
          } else if(act==='delete'){
            if(confirm('Точно удалить профиль?')) {
                this.deleteProfile(p.id).catch(err=> this.toast(err.message));
            }
          }
        });

        this.el.profiles.appendChild(row);
      }
    }

    loadProfileIntoForm(p){
      this.state.editProfileId = p.id;
      if(this.el.formTitle) this.el.formTitle.textContent = `Редактирование: ${p.name}`;
      const f = this.el.form;
      if(!f) return;
      f.name.value = p.name ?? '';
      f.gender.value = p.gender ?? 'male';
      f.height.value = p.height ?? '';
      f.chest.value = p.chest ?? '';
      f.shoulders.value = p.shoulders ?? '';
      f.waist.value = p.waist ?? '';
      f.hips.value = p.hips ?? '';
      f.arm_length.value = p.arm_length ?? '';
      f.leg_length.value = p.leg_length ?? '';
      f.inseam.value = p.inseam ?? '';
      f.id.value = p.id ?? '';
      show(this.el.btnCancelEdit);
    }

    clearForm(){
      this.state.editProfileId = null;
      if(this.el.formTitle) this.el.formTitle.textContent = 'Новый профиль';
      const f = this.el.form;
      if(!f) return;
      f.reset();
      f.id.value = '';
      hide(this.el.btnCancelEdit);
    }

    async saveProfileFromForm(){
      const f = this.el.form;
      if(!f) return;
      const payload = {
        name: f.name.value.trim(),
        gender: f.gender.value,
        height: Number(f.height.value || 0),
        chest: Number(f.chest.value || 0),
        shoulders: Number(f.shoulders.value || 0),
        waist: Number(f.waist.value || 0),
        hips: Number(f.hips.value || 0),
        arm_length: Number(f.arm_length.value || 0),
        leg_length: Number(f.leg_length.value || 0),
        inseam: Number(f.inseam.value || 0),
      };

      if(!payload.name) throw new Error('Имя профиля обязательно');

      if(this.state.editProfileId){
        await api(`/api/profiles/${this.state.editProfileId}`, {method:'PUT', body: JSON.stringify(payload)});
        this.toast('Профиль обновлён');
      } else {
        await api(`/api/profiles`, {method:'POST', body: JSON.stringify(payload)});
        this.toast('Профиль создан');
      }

      await this.loadProfiles();
      this.renderProfiles();
      this.clearForm();
      await this.refreshResults();
    }

    async deleteProfile(id){
      await api(`/api/profiles/${id}`, {method:'DELETE'});
      this.toast('Удалено');
      await this.loadProfiles();
      this.renderProfiles();
      await this.refreshResults();
    }

    async refreshResults(){
      if(!this.state.activeProfileId){
        this.state.results = [];
        this.renderCards();
        return;
      }

      const payload = { profile_id: this.state.activeProfileId };
      try {
        const data = await api(API.calculate(50), {
            method: 'POST',
            body: JSON.stringify(payload)
        });
        this.state.results = Array.isArray(data) ? data : [];
        this.renderCards();
      } catch (e) {
          this.toast('Ошибка загрузки рекомендаций');
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
        card.className = 'bg-white rounded-3xl border border-gray-100 shadow-sm overflow-hidden hover:shadow-lg transition-shadow cursor-pointer flex flex-col';

        const img = r?.image_url || PLACEHOLDER_IMG;
        const scoreVal = Number(r?.score ?? 0);
        const scoreTxt = Number.isFinite(scoreVal) ? Math.round(scoreVal) + '%' : '0%';
        
        let scoreColor = 'text-green-600 bg-green-50 border-green-200';
        if (scoreVal < 85) scoreColor = 'text-cyan-600 bg-cyan-50 border-cyan-200';
        if (scoreVal < 65) scoreColor = 'text-yellow-600 bg-yellow-50 border-yellow-200';
        if (scoreVal < 45) scoreColor = 'text-red-600 bg-red-50 border-red-200';

        const sku = r?.sku || '';
        const explainParts = (r?.explain || '').split('|').map(s => s.trim()).filter(Boolean);
        const mainVerdict = explainParts[0] || 'Нет данных';

        card.innerHTML = `
          <div class="aspect-[4/5] bg-gray-50 overflow-hidden relative">
            <img src="${esc(img)}" onerror="this.src='${PLACEHOLDER_IMG}'" class="w-full h-full object-cover"/>
            <div class="absolute top-3 right-3 px-3 py-1.5 rounded-xl border font-black text-sm shadow-sm backdrop-blur-sm ${scoreColor}">
                ${esc(scoreTxt)}
            </div>
          </div>

          <div class="p-4 flex flex-col flex-1">
            <div class="font-black text-lg truncate">${esc(r?.name || sku || '—')}</div>
            <div class="text-xs text-gray-500 mt-1 uppercase tracking-widest font-extrabold">${esc(r?.platform || '')} • SKU ${esc(sku)}</div>

            <div class="mt-4 text-sm font-semibold text-gray-800 flex-1">${esc(mainVerdict)}</div>

            <div class="mt-4 pt-4 border-t border-gray-100 flex items-center justify-between gap-2">
              <div class="text-xs text-gray-500 uppercase tracking-widest font-extrabold">Рекомендуемый размер: <span class="text-black text-sm ml-1">${esc(r?.best_size || '—')}</span></div>
            </div>
          </div>
        `;

        card.addEventListener('click', ()=> this.openModal(r));
        this.el.cards.appendChild(card);
      }
    }

openModal(r){
      this.state.currentCard = r;
      const sku = r?.sku || '';
      const builderUrl = `/builder?sku=${encodeURIComponent(sku)}`;

      if(this.el.modalTitle) this.el.modalTitle.textContent = r?.name || r?.sku || '—';
      if(this.el.modalSubtitle) this.el.modalSubtitle.textContent = `${r?.platform || ''} • SKU ${sku} • Рекомендация: ${r?.best_size || '—'}`;
      if(this.el.modalImage) this.el.modalImage.src = r?.image_url || PLACEHOLDER_IMG;

      const scoreVal = Number(r?.score ?? 0);
      if(this.el.modalScore) this.el.modalScore.textContent = Math.round(scoreVal) + '%';

      if(this.el.modalExplain) {
        let html = `
          <div class="mt-2 pt-4 border-t border-gray-100">
            <a href="${builderUrl}" class="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-50 border border-indigo-200 text-indigo-700 font-extrabold text-[11px] uppercase tracking-widest hover:bg-indigo-100 transition">
              ✎ Настроить в Builder (X-RAY)
            </a>
          </div>
        `;
        this.el.modalExplain.innerHTML = html;
      }

      // --- ПАНЕЛЬ РЕНТГЕНА ---
      let xrayHtml = `
        <div class="text-[11px] uppercase tracking-widest text-gray-500 font-extrabold mb-2">Существующие размеры (в наличии):</div>
        <div class="flex gap-2 flex-wrap mb-6">
            ${(r.available_sizes || []).map(sz => `<span class="px-3 py-1 bg-gray-100 text-gray-800 font-black text-sm rounded-lg">${sz}</span>`).join('')}
        </div>
        
        <div class="text-[11px] uppercase tracking-widest text-indigo-600 font-extrabold mb-3">Детальный рентген посадки (Все размеры)</div>
        <div class="space-y-4">
      `;
      
      (r.xray || []).forEach(sz => {
          let isRec = sz.size_label === r.best_size;
          let colorClass = 'border-gray-200 bg-white';
          if (sz.hard_fit === 'FAIL') colorClass = 'border-red-200 bg-red-50 text-red-900 opacity-70';
          else if (isRec) colorClass = 'border-green-300 bg-green-50 shadow-md';
          
          let zonesHtml = sz.xray_zones.map(z => `
              <div class="flex flex-col sm:flex-row sm:justify-between text-[11px] py-1 border-b border-gray-100/50 last:border-0">
                  <span class="sm:w-1/3 truncate font-bold text-gray-700">${z.zone_name}</span>
                  <span class="sm:w-1/3 text-gray-500">Цель: ${fmt(z.target_val)} → Вещь: ${fmt(z.garment_val)}</span>
                  <span class="sm:w-1/3 sm:text-right font-bold ${z.penalty > 0 ? 'text-red-500' : 'text-green-600'}">${z.status} (${fmt(z.delta_eff)}см)</span>
              </div>
          `).join('');

          xrayHtml += `
              <div class="rounded-xl border ${colorClass} p-3 transition-all">
                  <div class="flex justify-between items-center mb-2 pb-2 border-b border-gray-100/30">
                      <div class="font-black text-sm flex items-center gap-2">
                          Размер ${sz.size_label} 
                          ${!sz.is_available ? '<span class="text-[9px] uppercase tracking-widest bg-gray-200 text-gray-500 px-1.5 py-0.5 rounded">Теория</span>' : ''}
                      </div>
                      <div class="font-bold text-xs ${sz.hard_fit === 'FAIL' ? 'text-red-600' : ''}">${Math.round(sz.score)}% - ${sz.global_status}</div>
                  </div>
                  <div>${zonesHtml}</div>
                  ${sz.warnings.length ? `<div class="mt-2 text-[10px] text-red-600 font-bold bg-white p-2 rounded border border-red-100">${sz.warnings.join('<br>')}</div>` : ''}
              </div>
          `;
      });
      xrayHtml += `</div>`;

      if(this.el.modalMetrics) this.el.modalMetrics.innerHTML = xrayHtml;

      show(this.el.modal);
    }

    closeModal(){
      hide(this.el.modal);
    }
  }

  new App();
})();