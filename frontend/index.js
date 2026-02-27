(() => {
  const PLACEHOLDER_IMG = `data:image/svg+xml;charset=utf-8,<svg xmlns='http://www.w3.org/2000/svg' width='600' height='750'><rect width='100%25' height='100%25' fill='%23f3f4f6'/><text x='50%25' y='50%25' dominant-baseline='middle' text-anchor='middle' fill='%239ca3af' font-family='Inter,Arial' font-size='28'>no image</text></svg>`;

  const API = {
    profiles: '/api/profiles',
    calculate: (limit = 50) => `/api/calculate?limit=${encodeURIComponent(limit)}`
  };

  const qs = (sel, root = document) => root.querySelector(sel);
  function show(el) { if (el) el.classList.remove('hidden'); }
  function hide(el) { if (el) el.classList.add('hidden'); }
  function esc(s) { return String(s ?? '').replace(/[&<>"']/g, m => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[m])); }
  function fmt(n) { const x = Number(n); return Number.isFinite(x) ? String(Math.round(x * 10) / 10) : '—'; }
  function fmtSign(n) {
    const x = Number(n);
    if (!Number.isFinite(x)) return '—';
    const v = Math.round(x * 10) / 10;
    return (v > 0 ? `+${v}` : `${v}`);
  }

  async function api(url, opts = {}) {
    const res = await fetch(url, { headers: { 'Content-Type': 'application/json', ...(opts.headers || {}) }, ...opts });
    if (!res.ok) {
      const txt = await res.text().catch(() => '');
      throw new Error(`${res.status} ${res.statusText}${txt ? `: ${txt}` : ''}`);
    }
    const ct = res.headers.get('content-type') || '';
    return ct.includes('application/json') ? res.json() : res.text();
  }

  class App {
    constructor() {
      this.state = {
        profiles: [],
        activeProfileId: Number(localStorage.getItem('fit_active_profile_id') || 0) || null,
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
        height: qs('#height'),
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

    toast(msg, ok = true) {
      if (!this.el.toast) return;
      this.el.toast.classList.remove('hidden');
      this.el.toast.textContent = msg;
      this.el.toast.style.background = ok ? '#111827' : '#991B1B';
      clearTimeout(this._toastTimer);
      this._toastTimer = setTimeout(() => this.el.toast.classList.add('hidden'), 2600);
    }

    bind() {
      this.el.btnOpenCabinet?.addEventListener('click', () => this.openCabinet());
      this.el.btnCabinet?.addEventListener('click', () => this.openCabinet());
      this.el.btnBack?.addEventListener('click', () => this.closeCabinet());
      this.el.btnRefresh?.addEventListener('click', () => this.refreshResults());

      this.el.activeProfile?.addEventListener('change', () => {
        const id = Number(this.el.activeProfile.value || 0) || null;
        this.state.activeProfileId = id;
        localStorage.setItem('fit_active_profile_id', String(id || 0));
        this.refreshResults();
      });

      this.el.btnSaveProfile?.addEventListener('click', () => this.saveProfile());
      this.el.btnClearForm?.addEventListener('click', () => this.clearForm());
      this.el.btnCancelEdit?.addEventListener('click', () => this.clearForm());

      this.el.btnCloseModal?.addEventListener('click', () => this.closeModal());
      this.el.modal?.addEventListener('click', (e) => { if (e.target === this.el.modal) this.closeModal(); });
    }

    async init() {
      await this.loadProfiles();
      this.syncActiveProfileSelect();
      await this.refreshResults();
    }

    async loadProfiles() {
      try {
        const data = await api(API.profiles);
        this.state.profiles = Array.isArray(data) ? data : [];
        this.renderProfiles();
        this.renderActiveProfileSelect();
      } catch (e) {
        this.toast('Ошибка загрузки профилей', false);
      }
    }

    renderActiveProfileSelect() {
      const sel = this.el.activeProfile;
      if (!sel) return;
      sel.innerHTML = '';

      const opt0 = document.createElement('option');
      opt0.value = '';
      opt0.textContent = '— Выберите профиль —';
      sel.appendChild(opt0);

      for (const p of this.state.profiles) {
        const opt = document.createElement('option');
        opt.value = String(p.id);
        const h = (p.height != null && p.height !== '') ? ` • рост ${fmt(p.height)}см` : '';
        opt.textContent = `${p.name || ('Profile ' + p.id)} (${p.gender || 'n/a'}${h})`;
        sel.appendChild(opt);
      }
      this.syncActiveProfileSelect();
    }

    syncActiveProfileSelect() {
      if (!this.el.activeProfile) return;
      const id = this.state.activeProfileId;
      if (id) this.el.activeProfile.value = String(id);
    }

    openCabinet() { hide(this.el.mainView); show(this.el.cabinetView); }
    closeCabinet() { hide(this.el.cabinetView); show(this.el.mainView); }

    renderProfiles() {
      if (!this.el.profiles) return;
      this.el.profiles.innerHTML = '';
      if (!this.state.profiles.length) {
        show(this.el.profilesEmpty); return;
      }
      hide(this.el.profilesEmpty);

      for (const p of this.state.profiles) {
        const card = document.createElement('div');
        card.className = 'p-4 rounded-2xl border border-gray-200 bg-white flex items-center justify-between gap-2';
        const heightTxt = (p.height != null && p.height !== '') ? ` • рост ${fmt(p.height)}см` : '';
        card.innerHTML = `
          <div>
            <div class="font-black">${esc(p.name || ('Profile ' + p.id))}</div>
            <div class="text-xs text-gray-500 mt-0.5">ID ${p.id} • ${esc(p.gender || '—')}${heightTxt}</div>
          </div>
          <div class="flex gap-2">
            <button data-act="use" data-id="${p.id}" class="px-3 py-2 rounded-xl bg-indigo-600 text-white text-xs font-black hover:bg-indigo-700">Активировать</button>
          </div>
        `;
        card.querySelector('[data-act="use"]').addEventListener('click', () => {
          this.state.activeProfileId = Number(p.id);
          localStorage.setItem('fit_active_profile_id', String(p.id));
          this.renderActiveProfileSelect();
          this.closeCabinet();
          this.refreshResults();
        });
        this.el.profiles.appendChild(card);
      }
    }

    _problemZonesFromForm() {
      const zones = [];
      if (this.el.pz_belly?.checked) zones.push('belly');
      if (this.el.pz_sleeve?.checked) zones.push('sleeve');
      if (this.el.pz_waist_bottom?.checked) zones.push('waist_bottom');
      return zones;
    }

    clearForm() {
      if (this.el.formTitle) this.el.formTitle.textContent = 'Новый профиль';
      this.el.btnCancelEdit?.classList.add('hidden');

      const ids = ['name', 'height', 'chest', 'waist_top', 'belly', 'hips', 'waist_bottom', 'high_hip', 'thigh', 'bicep', 'shoulders', 'arm_length', 'inseam', 'leg_length'];
      ids.forEach(id => { const el = qs('#' + id); if (el) el.value = ''; });

      if (this.el.gender) this.el.gender.value = 'male';
      if (this.el.pz_belly) this.el.pz_belly.checked = false;
      if (this.el.pz_sleeve) this.el.pz_sleeve.checked = false;
      if (this.el.pz_waist_bottom) this.el.pz_waist_bottom.checked = false;
      this.toast('Форма очищена');
    }

    async saveProfile() {
      const name = (this.el.name?.value || '').trim();
      if (!name) { this.toast('Укажите имя профиля', false); return; }

      const toNullableNum = (v) => {
        const x = Number(v || 0);
        return Number.isFinite(x) && x > 0 ? x : null;
      };

      const payload = {
        name,
        gender: this.el.gender?.value || 'male',
        height: toNullableNum(this.el.height?.value),
        chest: toNullableNum(this.el.chest?.value),
        waist_top: toNullableNum(this.el.waist_top?.value),
        belly: toNullableNum(this.el.belly?.value),
        hips: toNullableNum(this.el.hips?.value),
        waist_bottom: toNullableNum(this.el.waist_bottom?.value),
        high_hip: toNullableNum(this.el.high_hip?.value),
        thigh: toNullableNum(this.el.thigh?.value),
        bicep: toNullableNum(this.el.bicep?.value),
        shoulders: toNullableNum(this.el.shoulders?.value),
        arm_length: toNullableNum(this.el.arm_length?.value),
        inseam: toNullableNum(this.el.inseam?.value),
        leg_length: toNullableNum(this.el.leg_length?.value),
        problem_zones: this._problemZonesFromForm(),
        comfort_C: {}
      };

      try {
        await api(API.profiles, { method: 'POST', body: JSON.stringify(payload) });
        this.toast('Профиль сохранён');
        await this.loadProfiles();
      } catch (e) {
        this.toast('Ошибка сохранения профиля', false);
      }
    }

    async refreshResults() {
      if (!this.state.activeProfileId) {
        this.state.results = [];
        this.renderCards();
        show(this.el.emptyState);
        return;
      }

      try {
        const data = await api(API.calculate(50), { method: 'POST', body: JSON.stringify({ profile_id: this.state.activeProfileId }) });
        // backend can return {items:[...]} or [...]
        this.state.results = Array.isArray(data) ? data : (Array.isArray(data?.items) ? data.items : []);
        this.renderCards();
        if (!this.state.results.length) show(this.el.emptyState);
        else hide(this.el.emptyState);
      } catch (e) {
        this.toast('Ошибка расчёта /api/calculate', false);
        this.state.results = [];
        this.renderCards();
        show(this.el.emptyState);
      }
    }

    _resultToCardData(r) {
      // tolerate different payload shapes
      const g = r.garment || r.item || r;
      const fit = r.fit || r.result || r;
      const sku = g.sku || r.sku || '—';
      const name = g.name || r.name || '—';
      const price = (g.price != null) ? g.price : r.price;
      const img = g.image_url || g.image || r.image_url || r.image || '';
      const platform = g.platform || r.platform || '';
      const in_stock = (g.in_stock != null) ? g.in_stock : (r.in_stock != null ? r.in_stock : true);

      const score = (fit.score != null) ? fit.score : (r.score != null ? r.score : null);
      const best_size = fit.best_size || r.best_size || r.size || null;
      const confidence = (fit.confidence != null) ? fit.confidence : (r.confidence != null ? r.confidence : null);
      const mode = fit.mode || r.mode || null;
      const all_results = fit.all_results || r.all_results || r.results || [];

      return { sku, name, price, img, platform, in_stock, score, best_size, confidence, mode, all_results, raw: r };
    }

    renderCards() {
      const root = this.el.cards;
      if (!root) return;
      root.innerHTML = '';

      const list = this.state.results || [];
      if (!list.length) return;

      for (const r of list) {
        const d = this._resultToCardData(r);
        const card = document.createElement('div');
        card.className = 'bg-white rounded-3xl border border-gray-100 shadow-sm overflow-hidden';

        const img = d.img || PLACEHOLDER_IMG;
        const scoreTxt = (d.score == null) ? '—' : `${Math.round(Number(d.score))}%`;
        const sizeTxt = d.best_size ? esc(d.best_size) : '—';
        const confTxt = (d.confidence == null) ? '—' : `${Math.round(Number(d.confidence))}%`;

        card.innerHTML = `
          <div class="bg-gray-50">
            <img src="${esc(img)}" onerror="this.onerror=null;this.src='${PLACEHOLDER_IMG}'" class="w-full aspect-[4/5] object-cover" alt="">
          </div>
          <div class="p-4">
            <div class="flex items-start justify-between gap-2">
              <div>
                <div class="font-black leading-tight">${esc(d.name)}</div>
                <div class="text-xs text-gray-500 mt-1">SKU: ${esc(d.sku)}${d.platform ? ` • ${esc(d.platform)}` : ''}</div>
              </div>
              <div class="text-right">
                <div class="text-xs text-gray-500">Score</div>
                <div class="text-xl font-black">${scoreTxt}</div>
              </div>
            </div>

            <div class="mt-3 grid grid-cols-3 gap-2 text-center">
              <div class="p-2 rounded-2xl bg-gray-50 border border-gray-100">
                <div class="text-[10px] uppercase tracking-widest text-gray-400 font-extrabold">Размер</div>
                <div class="font-black">${sizeTxt}</div>
              </div>
              <div class="p-2 rounded-2xl bg-gray-50 border border-gray-100">
                <div class="text-[10px] uppercase tracking-widest text-gray-400 font-extrabold">Увер.</div>
                <div class="font-black">${confTxt}</div>
              </div>
              <div class="p-2 rounded-2xl bg-gray-50 border border-gray-100">
                <div class="text-[10px] uppercase tracking-widest text-gray-400 font-extrabold">Наличие</div>
                <div class="font-black">${d.in_stock ? 'Да' : 'Нет'}</div>
              </div>
            </div>

            <div class="mt-3 flex items-center justify-between gap-2">
              <div class="text-sm font-bold text-gray-700">${d.price != null ? `${Math.round(Number(d.price))} ₽` : ''}</div>
              <button data-open="1" class="px-3 py-2 rounded-xl bg-indigo-600 text-white text-xs font-black hover:bg-indigo-700">Детали</button>
            </div>
          </div>
        `;

        card.querySelector('[data-open="1"]').addEventListener('click', () => this.openModal(d));
        root.appendChild(card);
      }
    }

    openModal(d) {
      this.state.currentCard = d;

      if (this.el.modalTitle) this.el.modalTitle.textContent = d.name || '—';
      if (this.el.modalSubtitle) this.el.modalSubtitle.textContent = `SKU ${d.sku}${d.platform ? ` • ${d.platform}` : ''}`;

      const scoreTxt = (d.score == null) ? '—' : `${Math.round(Number(d.score))}%`;
      const confTxt = (d.confidence == null) ? '—' : `${Math.round(Number(d.confidence))}%`;
      if (this.el.modalScore) this.el.modalScore.textContent = scoreTxt;

      if (this.el.modalImage) {
        this.el.modalImage.src = d.img || PLACEHOLDER_IMG;
        this.el.modalImage.onerror = () => { this.el.modalImage.src = PLACEHOLDER_IMG; };
      }

      // explain
      const mode = d.mode ? `Режим: <b>${esc(d.mode)}</b>` : '';
      const size = d.best_size ? `Рекомендуемый размер: <b>${esc(d.best_size)}</b>` : '';
      const conf = d.confidence != null ? `Уверенность: <b>${esc(confTxt)}</b>` : '';
      const bits = [size, mode, conf].filter(Boolean).join('<br>');
      if (this.el.modalExplain) this.el.modalExplain.innerHTML = bits || '<div class="text-sm text-gray-500">Нет деталей.</div>';

      // metrics table
      if (this.el.modalMetrics) {
        const rows = Array.isArray(d.all_results) ? d.all_results : [];
        if (!rows.length) {
          this.el.modalMetrics.innerHTML = '';
        } else {
          const head = `
            <div class="text-[11px] font-extrabold uppercase tracking-widest text-gray-400">Результаты по размерам</div>
            <div class="mt-2 overflow-auto border border-gray-100 rounded-2xl">
              <table class="min-w-full text-sm">
                <thead class="bg-gray-50">
                  <tr>
                    <th class="text-left px-3 py-2">Размер</th>
                    <th class="text-left px-3 py-2">Score</th>
                    <th class="text-left px-3 py-2">Увер.</th>
                    <th class="text-left px-3 py-2">Статус</th>
                  </tr>
                </thead>
                <tbody>
          `;
          const body = rows.map(r => {
            const sz = esc(r.size_label ?? r.size ?? '—');
            const sc = (r.score != null) ? `${Math.round(Number(r.score))}%` : '—';
            const cf = (r.confidence != null) ? `${Math.round(Number(r.confidence))}%` : '—';
            const st = esc(r.global_status ?? r.status ?? '');
            return `<tr class="border-t border-gray-100">
              <td class="px-3 py-2 font-bold">${sz}</td>
              <td class="px-3 py-2">${sc}</td>
              <td class="px-3 py-2">${cf}</td>
              <td class="px-3 py-2">${st}</td>
            </tr>`;
          }).join('');
          const tail = `</tbody></table></div>`;
          this.el.modalMetrics.innerHTML = head + body + tail;
        }
      }

      show(this.el.modal);
    }

    closeModal() {
      hide(this.el.modal);
      this.state.currentCard = null;
    }
  }

  window.addEventListener('DOMContentLoaded', () => new App());
})();
