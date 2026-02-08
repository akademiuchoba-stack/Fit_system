(() => {
  const API = {
    stats: '/api/admin/stats',
    garments: (q='', limit=50) => `/api/admin/garments?search=${encodeURIComponent(q)}&limit=${encodeURIComponent(limit)}`,
    profiles: '/api/profiles',
    feedback: '/api/admin/feedback?limit=100',
    tables: '/api/admin/tables',
    table: (name, limit=50) => `/api/admin/table/${encodeURIComponent(name)}?limit=${encodeURIComponent(limit)}`
  };

  const qs = (s, r=document) => r.querySelector(s);
  const esc = (s) => String(s ?? '').replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
  function show(el){ if(el) el.classList.remove('hidden'); }
  function hide(el){ if(el) el.classList.add('hidden'); }

  function toast(msg){
    const el = qs('#toast');
    if(!el) return;
    el.textContent = msg;
    show(el);
    setTimeout(()=> hide(el), 2500);
  }

  async function api(url, opts={}){
    const res = await fetch(url, {headers:{'Content-Type':'application/json'}, ...opts});
    if(!res.ok){
      const t = await res.text().catch(()=> '');
      throw new Error(`${res.status} ${res.statusText}${t?`: ${t}`:''}`);
    }
    return res.json();
  }

  function renderTable(container, rows){
    if(!container) return;
    if(!rows || !rows.length){
      container.innerHTML = `<div class="p-4 text-sm text-gray-500">Пусто</div>`;
      return;
    }
    const cols = Object.keys(rows[0]);
    container.innerHTML = `
      <table class="min-w-full text-sm">
        <thead class="bg-gray-50 text-gray-600">
          <tr>${cols.map(c=>`<th class="text-left font-extrabold px-3 py-2 whitespace-nowrap">${esc(c)}</th>`).join('')}</tr>
        </thead>
        <tbody>
          ${rows.map(r=>`<tr class="border-t border-gray-100 hover:bg-gray-50">${cols.map(c=>`<td class="px-3 py-2 align-top whitespace-nowrap max-w-[280px] overflow-hidden text-ellipsis">${esc(typeof r[c]==='object'?JSON.stringify(r[c]):r[c])}</td>`).join('')}</tr>`).join('')}
        </tbody>
      </table>
    `;
  }

  async function loadOverview(){
    const data = await api(API.stats);
    const c = data?.counts || {};
    const db = data?.db || {};
    const overview = qs('#overview');
    if(overview){
      const items = [
        ['Товары', c.garments ?? 0],
        ['Профили', c.profiles ?? 0],
        ['Feedback', c.feedback ?? 0],
        ['Priors', c.priors ?? 0],
      ];
      overview.innerHTML = items.map(([k,v])=>`
        <div class="p-4 rounded-2xl border border-gray-100 bg-gray-50">
          <div class="text-[11px] uppercase tracking-widest text-gray-500 font-extrabold">${esc(k)}</div>
          <div class="mt-1 text-2xl font-black">${esc(v)}</div>
          ${k==='Товары' && db.path ? `<div class="mt-2 text-xs text-gray-500 truncate">DB: ${esc(db.path)}</div>`:''}
        </div>
      `).join('');
    }
  }

  async function loadGarments(q=''){
    const box = qs('#garments');
    if(box) box.innerHTML = `<div class="p-4 text-sm text-gray-500">Загрузка...</div>`;
    const data = await api(API.garments(q, 50));
    renderTable(box, data?.items || []);
  }

  async function loadProfiles(){
    const box = qs('#profiles');
    if(box) box.innerHTML = `<div class="p-4 text-sm text-gray-500">Загрузка...</div>`;
    const data = await api(API.profiles);
    renderTable(box, data || []);
  }

  async function loadFeedback(){
    const box = qs('#feedback');
    if(box) box.innerHTML = `<div class="p-4 text-sm text-gray-500">Загрузка...</div>`;
    const data = await api(API.feedback);
    renderTable(box, data?.items || []);
  }

  async function loadTables(){
    const grid = qs('#tables');
    if(!grid) return;
    grid.innerHTML = `<div class="p-4 text-sm text-gray-500">Загрузка...</div>`;
    const data = await api(API.tables);
    const items = data?.tables || [];
    grid.innerHTML = items.map(t=>`
      <button data-table="${esc(t.name)}" class="text-left p-4 rounded-2xl border border-gray-100 bg-white hover:border-indigo-200 hover:shadow-sm transition">
        <div class="font-black truncate">${esc(t.name)}</div>
        <div class="mt-1 text-xs text-gray-500">rows: ${esc(t.rows)}</div>
      </button>
    `).join('');

    grid.addEventListener('click', async (e) => {
      const btn = e.target.closest('button[data-table]');
      if(!btn) return;
      const name = btn.getAttribute('data-table');
      await openTablePreview(name);
    }, {once:true});
  }

  async function openTablePreview(name){
    const wrap = qs('#table-preview');
    const title = qs('#table-title');
    const rowsBox = qs('#table-rows');
    if(title) title.textContent = name;
    show(wrap);
    if(rowsBox) rowsBox.innerHTML = `<div class="p-4 text-sm text-gray-500">Загрузка...</div>`;
    const data = await api(API.table(name, 50));
    renderTable(rowsBox, data?.rows || []);
  }

  async function refreshAll(){
    await Promise.allSettled([loadOverview(), loadProfiles(), loadFeedback(), loadTables()]);
    await loadGarments(qs('#garment-search')?.value || '');
  }

  qs('#btn-refresh')?.addEventListener('click', ()=> refreshAll().catch(e=>toast(e.message)));
  qs('#btn-garment-search')?.addEventListener('click', ()=> loadGarments(qs('#garment-search')?.value || '').catch(e=>toast(e.message)));
  qs('#garment-search')?.addEventListener('keydown', (e)=> { if(e.key==='Enter'){ e.preventDefault(); loadGarments(qs('#garment-search')?.value || '').catch(err=>toast(err.message)); } });
  qs('#btn-close-preview')?.addEventListener('click', ()=> hide(qs('#table-preview')));

  refreshAll().catch(e=>toast(e.message));
})();