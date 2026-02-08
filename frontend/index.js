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
        btnRunParser: qs('#btn-run-parser'),
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
      if(this.el.btnRunParser) this.el.btnRunParser.addEventListener('click', ()=> this.updateDb());

      // ✅ FIX: separate Admin page
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
      // choose active
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
          } else if(act==='edit'){
            this.loadProfileIntoForm(p);
          } else if(act==='delete'){
            this.deleteProfile(p.id, p.name).catch(err=> this.toast(err.message));
          }
        });

        this.el.profiles.appendChild(row);
      }
    }

    loadProfileIntoForm(p){
      if(!this.el.form) return;
      this.state.editProfileId = p.id;

      const set = (name, val) => {
        const el = this.el.form.querySelector(`[name="${CSS.escape(name)}"]`);
        if(el) el.value = val ?? '';
      };

      set('id', p.id);
      set('name', p.name);
      set('gender', p.gender || 'male');
      set('height', p.height);
      set('chest', p.chest);
      set('shoulders', p.shoulders);
      set('waist', p.waist);
      set('hips', p.hips);
      set('arm_length', p.arm_length);
      set('leg_length', p.leg_length);

      if(this.el.formTitle) this.el.formTitle.textContent = `Редактирование: ${p.name}`;
      show(this.el.btnCancelEdit);
      this.toast('Профиль загружен в форму');
      window.scrollTo({top: 0, behavior:'smooth'});
    }

    clearForm(){
      this.state.editProfileId = null;
      if(this.el.form) this.el.form.reset();
      const idEl = this.el.form ? this.el.form.querySelector('[name="id"]') : null;
      if(idEl) idEl.value = '';
      if(this.el.formTitle) this.el.formTitle.textContent = 'Новый профиль';
      hide(this.el.btnCancelEdit);
    }

    async saveProfileFromForm(){
      if(!this.el.form) return;
      const fd = new FormData(this.el.form);
      const payload = {};
      for(const [k,v] of fd.entries()){
        if(k === 'id') continue;
        if(['height','chest','shoulders','waist','hips','arm_length','leg_length'].includes(k)){
          payload[k] = v === '' ? null : Number(v);
          if(Number.isNaN(payload[k])) payload[k] = null;
        } else {
          payload[k] = v;
        }
      }

      if(!payload.name || !String(payload.name).trim()){
        this.toast('Имя обязательно');
        return;
      }

      // normalize
      payload.name = String(payload.name).trim();

      const res = await api(API.profiles, {method:'POST', body: JSON.stringify(payload)});
      await this.loadProfiles();
      this.renderProfiles();

      // set active to saved profile by name
      const p = this.state.profiles.find(x => x.name === payload.name) || this.state.profiles[0];
      if(p) this.setActiveProfile(p.id);

      this.clearForm();
      this.toast('Сохранено');
      await this.refreshResults();
      return res;
    }

    async deleteProfile(id, name){
      if(!confirm(`Удалить профиль "${name}"?`)) return;
      await api(`${API.profiles}/${encodeURIComponent(id)}`, {method:'DELETE'});
      await this.loadProfiles();
      this.renderProfiles();
      if(!this.state.profiles.length){
        this.setActiveProfile(null);
      }
      this.toast('Удалено');
      await this.refreshResults();
    }

    async updateDb(){
      this.toast('Обновляю базу...');
      await api(API.updateDb, {method:'POST'});
      await this.refreshResults();
      this.toast('База обновлена');
    }

    async refreshAll(){
      await this.loadProfiles();
      this.renderProfiles();
      await this.refreshResults();
    }

    async refreshResults(){
      const pid = this.state.activeProfileId;
      if(!pid){
        this.state.results = [];
        this.renderCards();
        hide(this.el.cards);
        show(this.el.emptyState);
        if(this.el.activeProfile) this.el.activeProfile.textContent = '—';
        return;
      }
      hide(this.el.emptyState);
      show(this.el.cards);

      const t0 = performance.now();
      const data = await api(API.calculate(20), {method:'POST', body: JSON.stringify({profile_id: pid})});
      const t1 = performance.now();

      this.state.results = Array.isArray(data?.results) ? data.results : (Array.isArray(data) ? data : []);
      this.renderCards();

      const p = this.state.profiles.find(x=>x.id===pid);
      if(this.el.activeProfile) this.el.activeProfile.textContent = p ? p.name : '—';
      // subtle toast for timings (only if empty)
      if(!this.state.results.length){
        this.toast(`0 карточек • ${(t1-t0).toFixed(0)}ms`);
      }
    }

    renderCards(){
      if(!this.el.cards) return;
      this.el.cards.innerHTML = '';

      const list = this.state.results || [];
      if(!list.length){
        show(this.el.emptyState);
        return;
      }
      hide(this.el.emptyState);

      for(const r of list){
        const card = document.createElement('button');
        card.type = 'button';
        card.className = 'text-left rounded-3xl border border-gray-100 bg-white shadow-sm hover:shadow-md transition overflow-hidden';

        const img = r.image_url || r.image || '';
        const score = Number(r.score ?? r.match_percent ?? 0);
        const scorePct = Number.isFinite(score) ? Math.round(score) : 0;

        card.innerHTML = `
          <div class="relative aspect-[4/5] bg-gray-50 min-h-[220px]">
            <img src="${esc(img || PLACEHOLDER_IMG)}" alt="" class="absolute inset-0 w-full h-full object-cover"
              loading="lazy" onerror="this.onerror=null; this.src='${PLACEHOLDER_IMG}';" />
            <div class="absolute top-3 left-3 px-2.5 py-1 rounded-full bg-white/90 backdrop-blur border border-gray-200 text-[11px] font-extrabold uppercase tracking-widest">
              ${scorePct}%
            </div>
          </div>
          <div class="p-4">
            <div class="font-black leading-snug line-clamp-2">${esc(r.name || '—')}</div>
            <div class="mt-2 text-xs text-gray-600">
              <span class="font-extrabold">SKU:</span> ${esc(r.sku || r.article || '—')}
              <span class="mx-2">•</span>
              <span class="font-extrabold">Размер:</span> ${esc(r.size_label || r.size || '—')}
            </div>
          </div>
        `;

        card.addEventListener('click', ()=> this.openModal(r));
        this.el.cards.appendChild(card);
      }
    }

    openModal(r){
      this.state.currentCard = r;
      if(this.el.modalTitle) this.el.modalTitle.textContent = r.name || '—';
      if(this.el.modalSubtitle) this.el.modalSubtitle.textContent = `SKU: ${r.sku || '—'} • Размер: ${r.size_label || '—'}`;
      if(this.el.modalScore) this.el.modalScore.textContent = `${Math.round(Number(r.score ?? 0) || 0)}%`;
      if(this.el.modalExplain) this.el.modalExplain.textContent = r.explanation || r.reason || '—';

      const img = r.image_url || r.image || '';
      if(this.el.modalImage){
        this.el.modalImage.src = img || PLACEHOLDER_IMG;
        this.el.modalImage.onerror = ()=> { this.el.modalImage.src = PLACEHOLDER_IMG; };
      }

      // metrics
      const m = r.metrics || r.item_metrics || r.measurements || {};
      const lines = [];
      const pick = (k,label) => {
        const v = m[k];
        if(v === undefined || v === null || v === '') return;
        lines.push(`<div class="flex items-center justify-between gap-3"><div class="text-gray-500">${esc(label)}</div><div class="font-extrabold">${esc(fmt(v))}</div></div>`);
      };
      pick('chest','Грудь');
      pick('shoulders','Плечи');
      pick('sleeve','Рукав');
      pick('length','Длина');
      pick('waist','Талия');
      pick('hips','Бёдра');

      if(this.el.modalMetrics){
        this.el.modalMetrics.innerHTML = lines.length ? `<div class="space-y-1">${lines.join('')}</div>` : `<div class="text-gray-500">Нет данных</div>`;
      }

      if(this.el.realSaveNote) this.el.realSaveNote.textContent = '';
      if(this.el.realChest) this.el.realChest.value = '';
      if(this.el.realShoulders) this.el.realShoulders.value = '';
      if(this.el.realSleeve) this.el.realSleeve.value = '';
      if(this.el.realLength) this.el.realLength.value = '';

      show(this.el.modal);
    }

    closeModal(){
      hide(this.el.modal);
      this.state.currentCard = null;
    }

    async saveRealMeasurements(){
      const r = this.state.currentCard;
      if(!r) return;

      // feedback endpoint is optional; don't crash if absent
      const payload = {
        garment_id: r.garment_id || r.id || null,
        size_selected: r.size_label || r.size || null,
        user_id: this.state.activeProfileId,
        real: {
          chest: this.el.realChest ? Number(this.el.realChest.value || 0) || null : null,
          shoulders: this.el.realShoulders ? Number(this.el.realShoulders.value || 0) || null : null,
          sleeve: this.el.realSleeve ? Number(this.el.realSleeve.value || 0) || null : null,
          length: this.el.realLength ? Number(this.el.realLength.value || 0) || null : null,
        }
      };

      try{
        await api(API.feedback, {method:'POST', body: JSON.stringify(payload)});
        if(this.el.realSaveNote) this.el.realSaveNote.textContent = 'Сохранено';
      } catch(e){
        // if endpoint not present, at least keep note locally
        if(this.el.realSaveNote) this.el.realSaveNote.textContent = 'Feedback эндпоинт не активен (можно добавить позже)';
      }
    }
  }

  // tiny polyfill for line-clamp without plugin (best effort)
  const style = document.createElement('style');
  style.textContent = `.line-clamp-2{display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;}`;
  document.head.appendChild(style);

  window.__fitApp = new App();
})();
