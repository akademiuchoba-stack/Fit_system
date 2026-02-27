(() => {
  const API = {
    stats: '/api/admin/stats',
    garments: '/api/admin/garments',
    del: (sku) => `/api/admin/builder/delete?sku=${encodeURIComponent(sku)}`,
  };

  const $ = (id) => document.getElementById(id);

  function toast(msg, ok=true){
    const t = $('toast');
    if(!t) return;
    t.classList.remove('hidden');
    t.textContent = msg;
    t.style.background = ok ? '#111827' : '#991B1B';
    clearTimeout(window.__toastTimer);
    window.__toastTimer = setTimeout(() => t.classList.add('hidden'), 2600);
  }

  function esc(s){ return String(s ?? '').replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m])); }

  async function api(url, opts={}){
    const res = await fetch(url, { headers: {'Content-Type':'application/json', ...(opts.headers||{})}, ...opts });
    if(!res.ok){
      const txt = await res.text().catch(()=> '');
      throw new Error(`${res.status} ${res.statusText}${txt?`: ${txt}`:''}`);
    }
    const ct = res.headers.get('content-type') || '';
    return ct.includes('application/json') ? res.json() : res.text();
  }

  function isV31(metrics){
    return metrics && typeof metrics === 'object' && metrics.schema_version === 'v3.1' && metrics.v31 && typeof metrics.v31 === 'object';
  }

  function computeReadyFromMetrics(metrics){
    if(!isV31(metrics)) return { level: 'LEGACY', reason: 'не v3.1' };
    const v31 = metrics.v31;
    const prod = v31.product || {};
    const gt = (prod.garment_type || '').toLowerCase();
    const sizes = Array.isArray(prod.available_sizes) ? prod.available_sizes : [];
    const sm = (v31.size_matrix && typeof v31.size_matrix === 'object') ? v31.size_matrix : {};
    const matrixCount = Object.keys(sm).length;

    if(!prod.sku || !gt || !sizes.length) return { level: 'NOT_READY', reason: 'нет sku/type/sizes' };

    const model = v31.model || {};
    const body = model.body || {};
    const gom = (v31.garment_on_model && v31.garment_on_model.measurements) ? v31.garment_on_model.measurements : {};
    if(!model.size_worn) return { level: 'NOT_READY', reason: 'нет размера на модели' };
    if(!body.chest_circ) return { level: 'NOT_READY', reason: 'нет груди модели' };

    if(gt === 'tshirt'){
      if(!gom.chest) return { level: 'NOT_READY', reason: 'нет chest вещи на модели' };
      if(matrixCount >= 2) return { level: 'READY', reason: `матрица ${matrixCount}` };
      if(matrixCount >= 1) return { level: 'PARTIAL', reason: `матрица ${matrixCount}` };
      return { level: 'NOT_READY', reason: 'матрица пустая' };
    }

    if(gt === 'trousers'){
      if(!gom.waist_bottom || !gom.hips || !gom.inseam) return { level: 'NOT_READY', reason: 'нет пояс/бедра/inseam на модели' };
      if(matrixCount >= 2) return { level: 'READY', reason: `матрица ${matrixCount}` };
      if(matrixCount >= 1) return { level: 'PARTIAL', reason: `матрица ${matrixCount}` };
      return { level: 'NOT_READY', reason: 'матрица пустая' };
    }

    return { level: 'PARTIAL', reason: `матрица ${matrixCount}` };
  }

  function badge(text, cls){
    return `<span class="px-3 py-1.5 rounded-xl border text-xs font-black ${cls}">${esc(text)}</span>`;
  }

  function levelBadge(level, reason){
    if(level === 'READY') return badge(`READY • ${reason}`, 'bg-green-50 text-green-700 border-green-200');
    if(level === 'PARTIAL') return badge(`PARTIAL • ${reason}`, 'bg-amber-50 text-amber-800 border-amber-200');
    if(level === 'NOT_READY') return badge(`NOT READY • ${reason}`, 'bg-red-50 text-red-700 border-red-200');
    return badge(`LEGACY • ${reason}`, 'bg-gray-50 text-gray-700 border-gray-200');
  }

  let allGarments = [];

  function renderStats(s){
    const box = $('stats');
    if(!box) return;
    box.innerHTML = [
      badge(`Товары: ${s.garments ?? 0}`, 'bg-gray-50 text-gray-900 border-gray-200'),
      badge(`Профили: ${s.profiles ?? 0}`, 'bg-gray-50 text-gray-900 border-gray-200'),
      badge(`Фидбек: ${s.feedback ?? 0}`, 'bg-gray-50 text-gray-900 border-gray-200'),
    ].join('');
  }

  function renderList(){
    const list = $('list');
    const empty = $('empty');
    const q = (($('q')?.value || '').trim().toLowerCase());

    const items = allGarments.filter(g => {
      if(!q) return true;
      const sku = String(g.sku || '').toLowerCase();
      const name = String(g.name || '').toLowerCase();
      return sku.includes(q) || name.includes(q);
    });

    list.innerHTML = '';
    if(!items.length){
      empty.classList.remove('hidden');
      return;
    }
    empty.classList.add('hidden');

    for(const g of items){
      const metrics = g.metrics || {};
      const ready = computeReadyFromMetrics(metrics);
      const v31 = isV31(metrics) ? metrics.v31 : null;
      const prod = v31?.product || {};
      const gt = prod?.garment_type || '—';
      const sizes = Array.isArray(prod.available_sizes) ? prod.available_sizes : [];
      const matrixCount = v31?.size_matrix ? Object.keys(v31.size_matrix).length : 0;

      const card = document.createElement('div');
      card.className = 'p-4 rounded-2xl border border-gray-200 bg-white flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3';

      card.innerHTML = `
        <div class="min-w-0">
          <div class="font-black text-lg truncate">${esc(g.name || g.sku || '—')}</div>
          <div class="text-[10px] text-gray-400 mt-1 uppercase tracking-widest font-extrabold">
            SKU ${esc(g.sku)} • ${esc(gt)} • sizes ${sizes.length} • matrix ${matrixCount}
          </div>
          <div class="mt-3 flex flex-wrap gap-2">
            ${levelBadge(ready.level, ready.reason)}
            ${isV31(metrics) ? badge('v3.1', 'bg-indigo-50 text-indigo-700 border-indigo-200') : badge('legacy', 'bg-gray-50 text-gray-700 border-gray-200')}
          </div>
        </div>

        <div class="flex gap-2 flex-wrap justify-end">
          <a href="/builder?sku=${encodeURIComponent(g.sku || '')}" class="px-3 py-2 rounded-xl bg-indigo-600 text-white text-xs font-black hover:bg-indigo-700">Builder</a>
          <a href="/?profile=1" class="hidden"></a>
          <button data-del="1" class="px-3 py-2 rounded-xl border border-red-200 bg-white text-xs font-bold text-red-600 hover:bg-red-50">Удалить</button>
        </div>
      `;

      card.querySelector('button[data-del]').addEventListener('click', async () => {
        const sku = g.sku;
        if(!sku) return;
        if(!confirm(`Удалить товар ${sku}?`)) return;
        try {
          await api(API.del(sku), { method: 'DELETE' });
          toast('Удалено');
          await loadAll();
        } catch(e){
          toast('Ошибка удаления', false);
        }
      });

      list.appendChild(card);
    }
  }

  async function loadAll(){
    const [s, gs] = await Promise.all([
      api(API.stats),
      api(API.garments),
    ]);
    renderStats(s);
    allGarments = Array.isArray(gs) ? gs : [];
    renderList();
  }

  function bind(){
    $('btn-refresh')?.addEventListener('click', ()=> loadAll().catch(()=> toast('Ошибка обновления', false)));
    $('btn-clear')?.addEventListener('click', ()=> { $('q').value=''; renderList(); });
    $('q')?.addEventListener('input', ()=> renderList());
  }

  window.addEventListener('DOMContentLoaded', async () => {
    bind();
    try { await loadAll(); }
    catch(e){ toast('Ошибка загрузки', false); }
  });
})();
