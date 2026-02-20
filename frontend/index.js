(() => {
  const PLACEHOLDER_IMG = `data:image/svg+xml;charset=utf-8,<svg xmlns='http://www.w3.org/2000/svg' width='600' height='750'><rect width='100%25' height='100%25' fill='%23f3f4f6'/><text x='50%25' y='50%25' dominant-baseline='middle' text-anchor='middle' fill='%239ca3af' font-family='Inter,Arial' font-size='28'>no image</text></svg>`;

  const API = {
    profiles: '/api/profiles',
    calculate: (limit=20) => `/api/calculate?limit=${encodeURIComponent(limit)}`,
    updateDb: '/api/admin/update-db',
    adminStats: '/api/admin/stats',
    feedback: '/api/feedback'
  };

  const qs = (sel, root=document) => root.querySelector(sel);
  const qsa = (sel, root=document) => Array.from(root.querySelectorAll(sel));

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

        adminPanel: qs('#admin-panel'),
        btnAdminClose: qs('#btn-admin-close'),
        adminStats: qs('#admin-stats'),

        modal: qs('#modal'),
        btnCloseModal: qs('#btn-close-modal'),
        modalTitle: qs('#modal-title'),
        modalSubtitle: qs('#modal-subtitle'),
        modalImage: qs('#modal-image'),
        modalScore: qs('#modal-score'),
        modalExplain: qs('#modal-explain'),
        modalMetrics: qs('#modal-metrics'),
        realChest: qs('#real-chest'),
        realShoulders: qs('#real-shoulders'),
        realSleeve: qs('#real-sleeve'),
        realLength: qs('#real-length'),
        btnSaveReal: qs('#btn-save-real'),
        realSaveNote: qs('#real-save-note'),
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
      if(this.el.btnRefresh) this.el.btnRefresh.addEventListener('click', ()=> this.refreshAll());

      // Admin отдельной страницей
      if(this.el.btnAdmin) this.el.btnAdmin.addEventListener('click', ()=> { window.location.href = '/admin'; });

      if(this.el.btnAdminClose) this.el.btnAdminClose.addEventListener('click', ()=> this.toggleAdmin(false));
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

      if(this.el.btnSaveReal){
        this.el.btnSaveReal.addEventListener('click', ()=> {
          this.saveRealMeasurements().catch(err=> this.toast(err.message));
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
      hide(this.el.adminPanel);
      show(this.el.mainView);
    }

    toggleAdmin(on){
      if(!this.el.adminPanel) return;
      if(on){
        show(this.el.adminPanel);
        this.refreshAdmin().catch(err=> this.toast(err.message));
      } else {
        hide(this.el.adminPanel);
      }
    }

    async refreshAdmin(){
      if(!this.el.adminStats) return;
      this.el.adminStats.textContent = 'Загрузка...';
      const data = await api(API.adminStats);
      const c = data?.counts || {};
      const db = data?.db || {};
      const parts = [
        `Товары: ${c.garments ?? 0}`,
        `Профили: ${c.profiles ?? 0}`,
        `Feedback: ${c.feedback ?? 0}`,
        `Priors: ${c.priors ?? 0}`,
        db.path ? `DB: ${db.path}` : null,
        Number.isFinite(db.size_bytes) ? `DB size: ${Math.round(db.size_bytes/1024)} KB` : null,
      ].filter(Boolean);

      this.el.adminStats.innerHTML = `<div class="grid grid-cols-1 sm:grid-cols-2 gap-2">${parts.map(p=>`<div class="p-3 rounded-2xl border border-gray-100 bg-gray-50">${esc(p)}</div>`).join('')}</div>`;
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
        row.className = `p-4 rounded-2xl border ${isActive ? 'border-indigo-200 bg-indigo-50' : 'border-gray-100 bg-white'} hover:border-indigo-200 transition`;

        row.innerHTML = `
          <div class="flex items-start justify-between gap-3">
            <div class="min-w-0">
              <div class="flex items-center gap-2">
                <div class="font-black truncate">${esc(p.name)}</div>
                ${isActive ? `<span class="text-[10px] font-extrabold uppercase tracking-widest px-2 py-1 rounded-full bg-gray-900 text-white">active</span>` : ''}
              </div>
              <div class="text-xs text-gray-600 mt-1">
                H ${fmt(p.height)} • C ${fmt(p.chest)} • S ${fmt(p.shoulders)} • W ${fmt(p.waist)} • Hips ${fmt(p.hips)}
              </div>
            </div>
          </div>

          <div class="mt-3 flex flex-wrap gap-2">
            <button data-act="activate" class="px-2.5 py-2 rounded-xl bg-gray-900 text-white font-extrabold text-[11px] uppercase tracking-widest">Активировать</button>
            <button data-act="edit" class="px-2.5 py-2 rounded-xl bg-gray-50 border border-gray-200 text-gray-700 font-extrabold text-[11px] uppercase tracking-widest">Редактировать</button>
            <button data-act="delete" class="px-2.5 py-2 rounded-xl bg-white border border-rose-200 text-rose-700 font-extrabold text-[11px] uppercase tracking-widest">Удалить</button>
          </div>
        `;

        row.addEventListener('click', (e)=> {
          const btn = e.target?.closest('button[data-act]');
          if(!btn) return;
          e.preventDefault();
          e.stopPropagation();
          const act = btn.getAttribute('data-act');
          if(act==='activate'){
            this.setActiveProfile(p.id);
            this.toast(`Активен: ${p.name}`);
            // ✅ сразу обновляем ленту
            this.refreshResults().catch(()=>{});
          } else if(act==='edit'){
            this.loadProfileIntoForm(p);
          } else if(act==='delete'){
            this.deleteProfile(p.id).catch(err=> this.toast(err.message));
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

      // ✅ FIX: calculate — это POST и нужен profile_id
      const payload = { profile_id: this.state.activeProfileId };
      const data = await api(API.calculate(30), {
        method: 'POST',
        body: JSON.stringify(payload)
      });

      this.state.results = Array.isArray(data) ? data : [];
      this.renderCards();
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
        card.className = 'bg-white rounded-3xl border border-gray-100 shadow-sm overflow-hidden hover:shadow-md transition cursor-pointer';

        const img = r?.image_url || PLACEHOLDER_IMG;
        const score = Number(r?.score ?? 0);
        const scoreTxt = Number.isFinite(score) ? Math.round(score) : 0;
        const sku = r?.sku || '';
        const builderUrl = `/builder?sku=${encodeURIComponent(sku)}`;

        card.innerHTML = `
          <div class="aspect-[4/5] bg-gray-50 overflow-hidden">
            <img src="${esc(img)}" onerror="this.src='${PLACEHOLDER_IMG}'" class="w-full h-full object-cover"/>
          </div>

          <div class="p-4">
            <div class="font-black truncate">${esc(r?.name || r?.sku || '—')}</div>
            <div class="text-xs text-gray-500 mt-1">${esc(r?.platform || '')} • SKU ${esc(sku)}</div>

            <div class="mt-3 flex items-center justify-between">
              <div class="text-[11px] uppercase tracking-widest text-gray-500 font-extrabold">Score</div>
              <div class="text-lg font-black">${esc(scoreTxt)}</div>
            </div>

            <div class="mt-2 text-sm text-gray-700 line-clamp-2">${esc(r?.explain || '')}</div>

            <div class="mt-3 flex items-center justify-between gap-2">
              <div class="text-xs text-gray-500">size: <span class="font-black">${esc(r?.best_size || '—')}</span></div>
              <a href="${builderUrl}"
                 class="text-xs px-3 py-2 rounded-xl bg-gray-50 border border-gray-200 font-extrabold uppercase tracking-widest"
                 onclick="event.stopPropagation();">✎ Builder</a>
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
      if(this.el.modalSubtitle) this.el.modalSubtitle.textContent = `${r?.platform || ''} • SKU ${sku} • size ${r?.best_size || '—'}`;
      if(this.el.modalImage) this.el.modalImage.src = r?.image_url || PLACEHOLDER_IMG;

      if(this.el.modalScore) this.el.modalScore.textContent = String(Math.round(Number(r?.score ?? 0)));
      if(this.el.modalExplain) {
        // добавим ссылку на Builder прямо в explain блок (не ломая верстку)
        this.el.modalExplain.innerHTML = `
          <div>${esc(r?.explain || '—')}</div>
          <div class="mt-3">
            <a href="${builderUrl}" class="inline-block px-3 py-2 rounded-xl bg-gray-900 text-white font-extrabold text-[11px] uppercase tracking-widest">
              ✎ Редактировать в Builder
            </a>
          </div>
        `;
      }

      const m = r?.metrics || {};
      const rows = Object.entries(m).map(([k,v])=> `
        <div class="flex items-center justify-between gap-3 border-b border-gray-100 py-1">
          <div class="text-xs text-gray-500">${esc(k)}</div>
          <div class="text-xs font-black">${esc(typeof v==='number'?fmt(v):JSON.stringify(v))}</div>
        </div>
      `).join('');
      if(this.el.modalMetrics) this.el.modalMetrics.innerHTML = rows || `<div class="text-sm text-gray-500">Нет данных</div>`;

      if(this.el.realChest) this.el.realChest.value = '';
      if(this.el.realShoulders) this.el.realShoulders.value = '';
      if(this.el.realSleeve) this.el.realSleeve.value = '';
      if(this.el.realLength) this.el.realLength.value = '';
      if(this.el.realSaveNote) this.el.realSaveNote.textContent = '';

      show(this.el.modal);
    }

    closeModal(){
      hide(this.el.modal);
    }

    async saveRealMeasurements(){
      const r = this.state.currentCard;
      if(!r) return;

      const rm = {};
      const chest = Number(this.el.realChest?.value || 0);
      const shoulders = Number(this.el.realShoulders?.value || 0);
      const sleeve = Number(this.el.realSleeve?.value || 0);
      const length = Number(this.el.realLength?.value || 0);

      if(chest) rm.chest = chest;
      if(shoulders) rm.shoulders = shoulders;
      if(sleeve) rm.sleeve = sleeve;
      if(length) rm.length = length;

      const payload = {
        garment_id: r.id,
        user_id: this.state.activeProfileId,
        size_selected: r.best_size || '',
        judgment: 'ok',
        real_measurements: Object.keys(rm).length ? rm : null
      };

      await api(API.feedback, {method:'POST', body: JSON.stringify(payload)});
      if(this.el.realSaveNote) this.el.realSaveNote.textContent = 'Сохранено';
      this.toast('Feedback сохранён');
    }

    async updateDb(){
      await api(API.updateDb, {method:'POST'});
      this.toast('База обновлена');
      await this.refreshResults();
    }

    async refreshAll(){
      await this.loadProfiles();
      this.renderProfiles();
      await this.refreshResults();
    }
  }

  new App();
})();

