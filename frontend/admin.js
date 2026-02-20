(() => {
  const API = {
    stats: '/api/admin/stats',
    updateDb: '/api/admin/update-db',
    garments: (q='', limit=50) => `/api/admin/garments?search=${encodeURIComponent(q)}&limit=${encodeURIComponent(limit)}`,
    profiles: '/api/profiles',
    builderDelete: (sku) => `/api/admin/builder/delete?sku=${encodeURIComponent(sku)}`,
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
    setTimeout(()=> hide(el), 3000);
  }

  async function api(url, opts={}){
    const res = await fetch(url, {headers:{'Content-Type':'application/json'}, ...opts});
    const ct = res.headers.get('content-type') || '';
    const body = ct.includes('application/json') ? await res.json().catch(()=> ({})) : await res.text().catch(()=> '');
    if(!res.ok){
      const msg = typeof body === 'string' ? body : (body?.detail || JSON.stringify(body));
      throw new Error(`${res.status} ${res.statusText}: ${msg}`);
    }
    return body;
  }

  async function updateDb(){
    const btn = qs('#btn-update-db');
    if(btn) btn.disabled = true;
    toast('Очищаю кэш сервера...');
    try{
      const r = await api(API.updateDb, {method:'POST'});
      toast(`Кэш очищен. Всего товаров в БД: ${r?.garments_total ?? '—'}`);
      await refreshAll();
    } finally {
      if(btn) btn.disabled = false;
    }
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

  function renderGarmentsTable(container, items){
    if(!container) return;
    if(!items || !items.length){
      container.innerHTML = `<div class="p-4 text-sm text-gray-500">Пусто</div>`;
      return;
    }

    container.innerHTML = `
      <table class="min-w-full text-sm">
        <thead class="bg-gray-50 text-gray-600">
          <tr>
            <th class="text-left font-extrabold px-3 py-2 whitespace-nowrap">SKU</th>
            <th class="text-left font-extrabold px-3 py-2 whitespace-nowrap">Название</th>
            <th class="text-left font-extrabold px-3 py-2 whitespace-nowrap">Платформа</th>
            <th class="text-left font-extrabold px-3 py-2 whitespace-nowrap">Цена</th>
            <th class="text-left font-extrabold px-3 py-2 whitespace-nowrap">В наличии</th>
            <th class="text-left font-extrabold px-3 py-2 whitespace-nowrap">Действия</th>
          </tr>
        </thead>
        <tbody>
          ${items.map(it => {
            const sku = it?.sku || '';
            const name = it?.name || '';
            const platform = it?.platform || '';
            const price = (it?.price ?? '');
            const inStock = !!it?.in_stock;
            const builderUrl = `/builder?sku=${encodeURIComponent(sku)}`;

            return `
              <tr class="border-t border-gray-100 hover:bg-gray-50">
                <td class="px-3 py-2 align-top whitespace-nowrap font-black">${esc(sku)}</td>
                <td class="px-3 py-2 align-top max-w-[420px] overflow-hidden text-ellipsis">${esc(name)}</td>
                <td class="px-3 py-2 align-top whitespace-nowrap">${esc(platform)}</td>
                <td class="px-3 py-2 align-top whitespace-nowrap">${esc(price)}</td>
                <td class="px-3 py-2 align-top whitespace-nowrap">${inStock ? '✅' : '—'}</td>
                <td class="px-3 py-2 align-top whitespace-nowrap">
                  <a href="${builderUrl}" class="inline-flex items-center gap-1 px-2.5 py-2 rounded-xl bg-indigo-50 border border-indigo-200 text-indigo-700 font-extrabold text-[11px] uppercase tracking-widest hover:bg-indigo-100 transition">
                    ✎ Builder
                  </a>
                  <button data-del="${esc(sku)}" class="ml-2 inline-flex items-center gap-1 px-2.5 py-2 rounded-xl bg-white border border-rose-200 text-rose-700 font-extrabold text-[11px] uppercase tracking-widest hover:bg-rose-50 transition">
                    🗑 Удалить
                  </button>
                </td>
              </tr>
            `;
          }).join('')}
        </tbody>
      </table>
    `;

    container.addEventListener('click', async (e) => {
      const btn = e.target.closest('button[data-del]');
      if(!btn) return;
      const sku = btn.getAttribute('data-del') || '';
      if(!sku) return;

      if(!confirm(`Удалить товар ${sku} из базы?`)) return;

      btn.disabled = true;
      try{
        await api(API.builderDelete(sku), {method:'DELETE'});
        toast(`Удалено: ${sku}`);
        await loadGarments(qs('#garment-search')?.value || '');
      }catch(err){
        toast(err.message);
      }finally{
        btn.disabled = false;
      }
    }, { once: true });
  }

  async function loadOverview(){
    const data = await api(API.stats);
    const c = data?.counts || {};
    const overview = qs('#overview');
    if(overview){
      const items = [
        ['Товары', c.garments ?? 0],
        ['Профили', c.profiles ?? 0],
      ];
      overview.innerHTML = items.map(([k,v])=>`
        <div class="p-4 rounded-2xl border border-gray-100 bg-gray-50 shadow-sm">
          <div class="text-[11px] uppercase tracking-widest text-gray-500 font-extrabold">${esc(k)}</div>
          <div class="mt-1 text-2xl font-black">${esc(v)}</div>
        </div>
      `).join('');
    }
  }

  async function loadGarments(q=''){
    const box = qs('#garments');
    if(box) box.innerHTML = `<div class="p-4 text-sm text-gray-500">Загрузка...</div>`;
    const data = await api(API.garments(q, 50));
    renderGarmentsTable(box, data?.items || []);
  }

  async function loadProfiles(){
    const box = qs('#profiles');
    if(box) box.innerHTML = `<div class="p-4 text-sm text-gray-500">Загрузка...</div>`;
    const data = await api(API.profiles);
    renderTable(box, data || []);
  }

  async function refreshAll(){
    await Promise.allSettled([loadOverview(), loadProfiles()]);
    await loadGarments(qs('#garment-search')?.value || '');
  }

  qs('#btn-refresh')?.addEventListener('click', ()=> refreshAll().catch(e=>toast(e.message)));
  qs('#btn-update-db')?.addEventListener('click', ()=> updateDb().catch(e=>toast(e.message)));
  qs('#btn-garment-search')?.addEventListener('click', ()=> loadGarments(qs('#garment-search')?.value || '').catch(e=>toast(e.message)));
  qs('#garment-search')?.addEventListener('keydown', (e)=> {
    if(e.key==='Enter'){
      e.preventDefault();
      loadGarments(qs('#garment-search')?.value || '').catch(err=>toast(err.message));
    }
  });

  refreshAll().catch(e=>toast(e.message));
})();
