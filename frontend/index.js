/*
  Fit — lightweight internal tool UI
  - Profiles stored on server (SQLite)
  - Main page shows 20 best matching items for active profile
  - Cabinet: CRUD profiles, set active, run DB update/parser
  - Admin: quick stats + recent feedback (for research)
*/

const API = {
  profiles: '/api/profiles',
  profileById: (id) => `/api/profiles/${id}`,
  calculate: '/api/calculate?limit=20',
  feedback: '/api/feedback',
  updateDb: '/api/admin/update-db',
  adminStats: '/api/admin/stats',
};

function qs(sel) { return document.querySelector(sel); }
function qsa(sel) { return Array.from(document.querySelectorAll(sel)); }

function formField(form, name) {
  if (!form) return null;
  return form.querySelector(`[name="${name}"]`);
}

function fmtPct(n) {
  if (n === null || n === undefined || Number.isNaN(Number(n))) return '—';
  const v = Math.max(0, Math.min(100, Math.round(Number(n))));
  return `${v}%`;
}

function safeNum(v) {
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

function debounce(fn, ms = 250) {
  let t = null;
  return (...args) => {
    clearTimeout(t);
    t = setTimeout(() => fn(...args), ms);
  };
}

class FitApp {
  constructor() {
    this.activeProfileId = null;
    this.activeProfile = null;
    this.results = [];
    this.adminLast = null;

    this.bindUI();
    this.bootstrap();
  }

  bindUI() {
    // header
    const hRefresh = qs('#btn-refresh');
    if (hRefresh) hRefresh.addEventListener('click', () => this.refreshResults());
    const hCabinet = qs('#btn-cabinet');
    if (hCabinet) hCabinet.addEventListener('click', () => this.showCabinet());
    const hAdmin = qs('#btn-admin');
    if (hAdmin) hAdmin.addEventListener('click', () => this.showAdmin());

    // mobile bottom nav (если есть)
    const mRefresh = qs('#m-refresh');
    const mCabinet = qs('#m-cabinet');
    if (mRefresh) mRefresh.addEventListener('click', () => this.refreshResults());
    if (mCabinet) mCabinet.addEventListener('click', () => this.showCabinet());

    // cabinet
    const cabBack = qs('#btn-back');
    if (cabBack) cabBack.addEventListener('click', () => this.showMain());
    const cabUpdate = qs('#btn-run-parser');
    if (cabUpdate) cabUpdate.addEventListener('click', () => this.updateDB());

    // profile form
    const pForm = qs('#profile-form');
    if (pForm) pForm.addEventListener('submit', (e) => {
      e.preventDefault();
      this.saveProfileFromForm();
    });
    const pCancel = qs('#btn-clear-form');
    if (pCancel) pCancel.addEventListener('click', () => this.resetProfileForm());

    // admin
    const aBack = qs('#btn-admin-back');
    if (aBack) aBack.addEventListener('click', () => this.showMain());
    const aRefresh = qs('#btn-admin-refresh');
    if (aRefresh) aRefresh.addEventListener('click', () => this.refreshAdmin());
    const dl = qs('#btn-admin-download');
    if (dl) dl.addEventListener('click', () => this.downloadAdminJSON());

    // modal close on backdrop click
    const modal = qs('#modal');
    if (modal) modal.addEventListener('click', (e) => {
      if (e.target && e.target.id === 'modal') this.closeModal();
    });
    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape') this.closeModal();
    });

    // auto refresh results when measurement form changes (only for edit mode)
    const auto = debounce(() => {
      // do nothing if no active profile
      if (!this.activeProfileId) return;
      // only when on main
      if (qs('#cabinet-section').classList.contains('hidden') === false) return;
      if (qs('#admin-section').classList.contains('hidden') === false) return;
    }, 400);
    qsa('input,select').forEach((el) => el.addEventListener('change', auto));
  }

  async bootstrap() {
    // restore active profile id from localStorage
    const savedId = localStorage.getItem('fit_active_profile_id');
    if (savedId) this.activeProfileId = Number(savedId);

    await this.loadProfilesAndRender();

    if (this.activeProfileId) {
      await this.loadActiveProfile();
      await this.refreshResults();
      this.showMain();
    } else {
      // first time: go to cabinet
      this.showCabinet();
    }
  }

  // --------------------
  // UI navigation
  // --------------------
  showMain() {
    qs('#cabinet-section').classList.add('hidden');
    qs('#admin-section').classList.add('hidden');
    qs('#results-section').classList.remove('hidden');
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  showCabinet() {
    qs('#admin-section').classList.add('hidden');
    qs('#results-section').classList.add('hidden');
    qs('#cabinet-section').classList.remove('hidden');
    this.loadProfilesAndRender();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  showAdmin() {
    qs('#cabinet-section').classList.add('hidden');
    qs('#results-section').classList.add('hidden');
    qs('#admin-section').classList.remove('hidden');
    this.refreshAdmin();
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  // --------------------
  // Profiles
  // --------------------
  async loadProfilesAndRender() {
    const listEl = qs('#profiles-list');
    const statusEl = qs('#cabinet-status');
    listEl.innerHTML = '';

    let profiles = [];
    try {
      const r = await fetch(API.profiles);
      if (!r.ok) throw new Error('profiles fetch failed');
      profiles = await r.json();
    } catch (e) {
      if (statusEl) statusEl.classList.remove('hidden');
      if (statusEl) statusEl.innerText = 'Не удалось загрузить профили (проверь, запущен ли backend).';
      return;
    }

    if (!profiles.length) {
      if (statusEl) statusEl.classList.remove('hidden');
      if (statusEl) statusEl.innerText = 'Профилей пока нет — добавь новый ниже.';
      return;
    }

    if (statusEl) statusEl.classList.add('hidden');

    profiles.forEach((p) => {
      const isActive = this.activeProfileId === p.id;
      const row = document.createElement('div');
      row.className = `flex items-center justify-between gap-3 p-4 rounded-2xl border ${isActive ? 'border-indigo-200 bg-indigo-50' : 'border-gray-100 bg-white'} hover:border-indigo-200 transition`;

      row.innerHTML = `
        <div class="min-w-0">
          <div class="flex items-center gap-2 min-w-0">
            <span class="w-2.5 h-2.5 rounded-full ${isActive ? 'bg-emerald-500' : 'bg-gray-300'}"></span>
            <div class="font-black text-base truncate">${this.escape(p.name)}</div>
            <div class="text-[10px] uppercase tracking-widest font-extrabold text-gray-400">${this.escape(p.gender || '—')}</div>
          </div>
          <div class="text-xs text-gray-500 mt-1 font-mono">Рост ${p.height ?? '—'} • Грудь ${p.chest ?? '—'} • Плечи ${p.shoulders ?? '—'} • Талия ${p.waist ?? '—'}</div>
        </div>
        <div class="flex items-center gap-2 shrink-0">
          <button data-act="use" data-id="${p.id}" class="px-3 py-2 rounded-xl bg-gray-900 text-white font-extrabold text-xs uppercase tracking-widest hover:bg-indigo-600 transition">Активировать</button>
          <button data-act="edit" data-id="${p.id}" class="px-3 py-2 rounded-xl bg-white border border-gray-200 text-gray-700 font-extrabold text-xs uppercase tracking-widest hover:border-indigo-300 hover:text-indigo-700 transition">Редакт</button>
          <button data-act="del" data-id="${p.id}" class="px-3 py-2 rounded-xl bg-white border border-gray-200 text-rose-600 font-extrabold text-xs uppercase tracking-widest hover:border-rose-300 transition">Удалить</button>
        </div>
      `;

      listEl.appendChild(row);
    });

    // bind actions
    qsa('[data-act]').forEach((btn) => {
      btn.addEventListener('click', async () => {
        const act = btn.getAttribute('data-act');
        const id = Number(btn.getAttribute('data-id'));
        if (act === 'use') return this.setActiveProfile(id);
        if (act === 'edit') return this.loadProfileIntoForm(id);
        if (act === 'del') return this.deleteProfile(id);
      });
    });
  }

  async setActiveProfile(id) {
    this.activeProfileId = id;
    localStorage.setItem('fit_active_profile_id', String(id));
    await this.loadActiveProfile();
    await this.refreshResults();
    await this.loadProfilesAndRender();
    this.showMain();
  }

  async loadActiveProfile() {
    if (!this.activeProfileId) {
      this.activeProfile = null;
      this.renderActiveHeader();
      return;
    }
    try {
      const r = await fetch(API.profileById(this.activeProfileId));
      if (!r.ok) throw new Error('profile fetch failed');
      this.activeProfile = await r.json();
    } catch (e) {
      // if profile deleted on server
      this.activeProfileId = null;
      this.activeProfile = null;
      localStorage.removeItem('fit_active_profile_id');
    }
    this.renderActiveHeader();
  }

  renderActiveHeader() {
    const nameEl = qs('#active-profile');
    const dotEl = qs('#active-dot');

    if (!this.activeProfile) {
      nameEl.textContent = '—';
      dotEl.className = 'w-2.5 h-2.5 rounded-full bg-gray-300';
      return;
    }
    nameEl.textContent = this.activeProfile.name;
    dotEl.className = 'w-2.5 h-2.5 rounded-full bg-emerald-500';
  }

  resetProfileForm() {
    const form = qs('#profile-form');
    const titleEl = qs('#profile-form-title');
    if (titleEl) titleEl.textContent = 'Новый профиль';

    const idEl = formField(form, 'id');
    const nameEl = formField(form, 'name');
    const genderEl = formField(form, 'gender');
    if (idEl) idEl.value = '';
    if (nameEl) nameEl.value = '';
    if (genderEl) genderEl.value = 'male';

    ['height','chest','shoulders','waist','hips','arm_length','leg_length'].forEach((k) => {
      const el = formField(form, k);
      if (el) el.value = '';
    });
  }

  async loadProfileIntoForm(id) {
    let p;
    try {
      const r = await fetch(API.profileById(id));
      if (!r.ok) throw new Error('profile fetch failed');
      p = await r.json();
    } catch (e) {
      alert('Не удалось загрузить профиль.');
      return;
    }

    const form = qs('#profile-form');
    const titleEl = qs('#profile-form-title');
    if (titleEl) titleEl.textContent = 'Редактирование профиля';

    const idEl = formField(form, 'id');
    const nameEl = formField(form, 'name');
    const genderEl = formField(form, 'gender');
    if (idEl) idEl.value = String(p.id);
    if (nameEl) nameEl.value = p.name ?? '';
    if (genderEl) genderEl.value = p.gender ?? 'male';

    ['height','chest','shoulders','waist','hips','arm_length','leg_length'].forEach((k) => {
      const el = formField(form, k);
      if (el) el.value = p[k] ?? '';
    });

    // scroll to form
    const pf = qs('#profile-form');
    if (pf) pf.scrollIntoView({ behavior: 'smooth', block: 'start' });
  }

  async saveProfileFromForm() {
    const form = qs('#profile-form');
    const id = (formField(form, 'id')?.value ?? '').trim();
    const payload = {
      name: (formField(form, 'name')?.value ?? '').trim(),
      gender: formField(form, 'gender')?.value ?? 'male',
      height: safeNum(formField(form, 'height')?.value),
      chest: safeNum(formField(form, 'chest')?.value),
      shoulders: safeNum(formField(form, 'shoulders')?.value),
      waist: safeNum(formField(form, 'waist')?.value),
      hips: safeNum(formField(form, 'hips')?.value),
      arm_length: safeNum(formField(form, 'arm_length')?.value),
      leg_length: safeNum(formField(form, 'leg_length')?.value),
    };

    if (!payload.name) {
      alert('Укажи имя профиля (уникальное).');
      return;
    }

    const isUpdate = Boolean(id);
    const url = isUpdate ? API.profileById(Number(id)) : API.profiles;
    const method = isUpdate ? 'PUT' : 'POST';

    try {
      const r = await fetch(url, {
        method,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      const data = await r.json().catch(() => ({}));
      if (!r.ok) {
        alert(data?.detail || 'Не удалось сохранить профиль.');
        return;
      }

      this.resetProfileForm();
      await this.loadProfilesAndRender();
      // если активный профиль редактировали — перезагрузить
      if (this.activeProfileId && Number(id) === this.activeProfileId) {
        await this.loadActiveProfile();
        await this.refreshResults();
      }
    } catch (e) {
      alert('Сервер недоступен (backend).');
    }
  }

  async deleteProfile(id) {
    if (!confirm('Удалить профиль?')) return;
    try {
      const r = await fetch(API.profileById(id), { method: 'DELETE' });
      if (!r.ok) throw new Error('delete failed');
    } catch (e) {
      alert('Не удалось удалить профиль.');
      return;
    }

    if (this.activeProfileId === id) {
      this.activeProfileId = null;
      this.activeProfile = null;
      localStorage.removeItem('fit_active_profile_id');
      this.renderActiveHeader();
      this.results = [];
      this.renderResults();
    }

    await this.loadProfilesAndRender();
  }

  // --------------------
  // Results
  // --------------------
  async refreshResults() {
    if (!this.activeProfileId) {
      this.renderResults();
      return;
    }

    await this.loadActiveProfile();
    if (!this.activeProfile) {
      this.renderResults();
      return;
    }

    const t0 = performance.now();
    qs('#calc-meta').textContent = 'Расчёт…';

    try {
      const r = await fetch(API.calculate, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ profile_id: this.activeProfileId }),
      });
      if (!r.ok) {
        const d = await r.json().catch(() => ({}));
        throw new Error(d?.detail || 'calculate failed');
      }
      this.results = await r.json();
    } catch (e) {
      qs('#calc-meta').textContent = 'Ошибка расчёта. Проверь backend/https.';
      this.results = [];
      this.renderResults();
      return;
    }

    const t1 = performance.now();
    qs('#calc-meta').textContent = `calc ${(t1 - t0).toFixed(0)}ms • cards ${this.results.length}`;
    this.renderResults();
  }

  renderResults() {
    const empty = qs('#results-empty');
    const grid = qs('#results-grid');
    grid.innerHTML = '';

    if (!this.activeProfileId) {
      empty.classList.remove('hidden');
      return;
    }

    if (!this.results || !this.results.length) {
      empty.classList.remove('hidden');
      empty.querySelector('.font-black').textContent = 'Нет результатов';
      empty.querySelector('.text-gray-500').textContent = 'Проверь базу магазина или обнови её в “Кабинет”.';
      return;
    }

    empty.classList.add('hidden');

    this.results.forEach((res) => {
      const card = document.createElement('button');
      card.type = 'button';
      card.className = 'text-left bg-white border border-gray-100 rounded-3xl overflow-hidden shadow-sm hover:shadow-md transition focus:ring-2 focus:ring-indigo-400';
      card.addEventListener('click', () => this.openDetail(res));

      const score = safeNum(res?.fit?.score);
      const scoreLabel = fmtPct(score);

      card.innerHTML = `
        <div class="relative aspect-[4/5] bg-gray-50">
          <img src="${this.escape(res.image || '')}" alt="" class="w-full h-full object-cover" loading="lazy" onerror="this.style.display='none'" />
          <div class="absolute top-3 right-3 bg-white/95 border border-gray-100 rounded-full px-3 py-1 text-xs font-black">${scoreLabel}</div>
        </div>
        <div class="p-4">
          <div class="font-black leading-tight line-clamp-2">${this.escape(res.name || '—')}</div>
          <div class="mt-2 flex flex-wrap items-center gap-2 text-[11px] font-mono text-gray-500">
            <span class="px-2 py-1 rounded-lg bg-gray-50 border border-gray-100">SKU ${this.escape(res.sku || '—')}</span>
            <span class="px-2 py-1 rounded-lg bg-gray-50 border border-gray-100">Размер ${this.escape(res.size || '—')}</span>
          </div>
        </div>
      `;
      grid.appendChild(card);
    });
  }

  // --------------------
  // Detail modal + feedback
  // --------------------
  openDetail(res) {
    const modal = qs('#modal');
    const content = qs('#modal-content');
    if (!modal || !content) return;

    const score = safeNum(res?.fit?.score);
    const mc = res?.fit?.metrics_comparison || {};

    const garmentMetrics = res?.fit?.garment_metrics || res?.fit?.metrics || null;
    const garmentMetricsRows = garmentMetrics
      ? Object.entries(garmentMetrics).map(([k, v]) => {
          const vv = safeNum(v);
          return `
            <div class="flex items-end justify-between border-b border-gray-50 pb-3">
              <span class="text-sm text-gray-600 font-medium">${this.escape(k)}</span>
              <span class="font-mono text-lg font-bold text-indigo-700">${vv === null ? '—' : `${vv} см`}</span>
            </div>
          `;
        }).join('')
      : '<div class="text-sm text-gray-500">Нет замеров для этого размера в базе.</div>';

    // real measurement inputs (for store)
    const realFields = [
      { key: 'sleeve', label: 'Рукав (реал, см)' },
      { key: 'chest', label: 'Грудь (реал, см)' },
      { key: 'shoulder', label: 'Плечи (реал, см)' },
      { key: 'length', label: 'Длина (реал, см)' },
    ];

    const realInputs = realFields.map((f) => `
      <div class="space-y-1">
        <label class="text-[10px] font-black uppercase text-gray-400 tracking-widest ml-1">${f.label}</label>
        <input id="real-${f.key}" inputmode="decimal" type="number" step="0.5" class="w-full p-3 bg-gray-50 rounded-2xl border-2 border-transparent focus:border-indigo-500 focus:bg-white transition font-bold" placeholder="—" />
      </div>
    `).join('');

    content.innerHTML = `
      <div class="flex items-start justify-between gap-4 mb-6">
        <div class="min-w-0">
          <div class="text-2xl sm:text-3xl font-black truncate">${this.escape(res.name || '—')}</div>
          <div class="mt-1 text-xs font-mono text-gray-500">SKU ${this.escape(res.sku || '—')} • Размер ${this.escape(res.size || '—')}</div>
        </div>
        <button id="btn-modal-close" class="shrink-0 p-3 rounded-2xl bg-gray-50 border border-gray-100 hover:border-indigo-200 hover:text-indigo-700 transition" aria-label="Закрыть">✕</button>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div class="space-y-4">
          <div class="aspect-[4/5] rounded-3xl overflow-hidden bg-gray-50 border border-gray-100">
            <img src="${this.escape(res.image || '')}" alt="" class="w-full h-full object-cover" loading="lazy" onerror="this.style.display='none'" />
          </div>
          <div class="p-5 rounded-3xl bg-indigo-50 border border-indigo-100">
            <div class="text-[11px] uppercase tracking-widest font-extrabold text-indigo-700">Соответствие</div>
            <div class="mt-2 text-4xl font-black text-indigo-900">${fmtPct(score)}</div>
            <div class="mt-2 text-sm text-indigo-700">${this.escape(res?.fit?.verdict || '')}</div>
            <div class="mt-3 text-xs text-indigo-600/90 leading-relaxed">${this.escape(res?.fit?.details || '')}</div>
          </div>
        </div>

        <div class="space-y-6">
          <div class="bg-white border border-gray-100 rounded-3xl p-5">
            <div class="text-[11px] uppercase tracking-widest font-extrabold text-gray-400">Замеры из базы (этот размер)</div>
            <div class="mt-4 space-y-3">${garmentMetricsRows}</div>
          </div>

          <div class="bg-white border border-gray-100 rounded-3xl p-5">
            <div class="text-[11px] uppercase tracking-widest font-extrabold text-gray-400">Ввести реальные замеры в магазине</div>
            <div class="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-3">${realInputs}</div>
            <div class="mt-4 flex items-center gap-2">
              <button id="btn-save-real" class="px-4 py-3 rounded-2xl bg-gray-900 text-white font-extrabold text-xs uppercase tracking-widest hover:bg-indigo-600 transition">Сохранить в анализ</button>
              <div id="real-status" class="text-xs font-mono text-gray-500"></div>
            </div>
          </div>

          <div class="bg-white border border-gray-100 rounded-3xl p-5">
            <div class="text-[11px] uppercase tracking-widest font-extrabold text-gray-400">Быстрый вердикт (обучение)</div>
            <div class="mt-3 grid grid-cols-3 gap-2">
              <button data-jud="0" class="py-3 rounded-2xl bg-emerald-50 text-emerald-700 font-extrabold text-xs uppercase tracking-widest hover:ring-2 hover:ring-emerald-300 transition">В точку</button>
              <button data-jud="1" class="py-3 rounded-2xl bg-amber-50 text-amber-700 font-extrabold text-xs uppercase tracking-widest hover:ring-2 hover:ring-amber-300 transition">Маловато</button>
              <button data-jud="-1" class="py-3 rounded-2xl bg-rose-50 text-rose-700 font-extrabold text-xs uppercase tracking-widest hover:ring-2 hover:ring-rose-300 transition">Велико</button>
            </div>
          </div>
        </div>
      </div>
    `;

    qs('#btn-modal-close').addEventListener('click', () => this.closeModal());

    // feedback buttons
    qsa('[data-jud]').forEach((b) => {
      b.addEventListener('click', async () => {
        const j = Number(b.getAttribute('data-jud'));
        await this.submitFeedback(res, j, null);
      });
    });

    // save real measurements
    qs('#btn-save-real').addEventListener('click', async () => {
      const real = {};
      realFields.forEach((f) => {
        const v = safeNum(qs(`#real-${f.key}`).value);
        if (v !== null) real[f.key] = v;
      });
      if (Object.keys(real).length === 0) {
        qs('#real-status').textContent = 'Введите хотя бы 1 замер.';
        return;
      }
      qs('#real-status').textContent = 'Сохраняю…';
      await this.submitFeedback(res, 0, real);
    });

    modal.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
  }

  closeModal() {
    const modal = qs('#modal');
    if (modal) modal.classList.add('hidden');
    document.body.style.overflow = 'auto';
  }

  async submitFeedback(res, judgment, real_measurements) {
    if (!this.activeProfile) {
      alert('Нет активного профиля.');
      return;
    }
    const payload = {
      garment_id: res.item_id,
      user_id: this.activeProfile.name,
      size_selected: res.size,
      judgment,
      real_measurements,
    };

    try {
      const r = await fetch(API.feedback, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });
      const d = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(d?.detail || 'feedback failed');

      const status = qs('#real-status');
      if (status) status.textContent = 'Сохранено ✔';
    } catch (e) {
      const status = qs('#real-status');
      if (status) status.textContent = 'Ошибка сохранения';
      alert('Не удалось сохранить анализ (feedback).');
    }
  }

  // --------------------
  // Admin
  // --------------------
  async refreshAdmin() {
    const box = qs('#admin-json');
    box.textContent = 'Загрузка…';
    try {
      const r = await fetch(API.adminStats);
      if (!r.ok) throw new Error('stats failed');
      this.adminLast = await r.json();
      box.textContent = JSON.stringify(this.adminLast, null, 2);
    } catch (e) {
      box.textContent = 'Не удалось загрузить admin/stats.';
      this.adminLast = null;
    }
  }

  downloadAdminJSON() {
    if (!this.adminLast) return;
    const blob = new Blob([JSON.stringify(this.adminLast, null, 2)], { type: 'application/json;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `fit_admin_${new Date().toISOString().slice(0,19).replaceAll(':','-')}.json`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }

  // --------------------
  // DB update
  // --------------------
  async updateDB() {
    const status = qs('#cabinet-status');
    status.textContent = 'Запуск…';
    try {
      const r = await fetch(API.updateDb, { method: 'POST' });
      const d = await r.json().catch(() => ({}));
      if (!r.ok) throw new Error(d?.detail || 'update failed');
      status.textContent = d?.status || 'OK';
      // after update: refresh results
      if (this.activeProfileId) await this.refreshResults();
    } catch (e) {
      status.textContent = 'Ошибка запуска обновления.';
    }
  }

  escape(s) {
    return String(s ?? '')
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;')
      .replaceAll("'", '&#039;');
  }
}

window.app = new FitApp();