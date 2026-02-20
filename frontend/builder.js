function qs(id){ return document.getElementById(id); }
function val(id){ return (qs(id)?.value || "").trim(); }
function valNum(id){
  const v = val(id);
  if(!v) return null;
  const n = Number(String(v).replace(",", "."));
  return Number.isFinite(n) ? n : null;
}
function setMsg(t){ qs("msg").textContent = t || ""; }

function currentSkuFromUrl(){
  const u = new URL(window.location.href);
  return (u.searchParams.get("sku") || "").trim();
}

async function apiJSON(url, opts={}){
  const res = await fetch(url, opts);
  const text = await res.text();
  let data = null;
  try { data = JSON.parse(text); } catch { data = { raw: text }; }
  if(!res.ok) throw new Error(data?.detail || data?.error || text);
  return data;
}

function fillFormFromGarment(g){
  qs("sku").value = g.sku || "";
  qs("name").value = g.name || "";
  qs("price").value = g.price ?? "";
  qs("image_url").value = g.image_url || "";
  qs("platform").value = g.platform || "manual";
  qs("in_stock").checked = !!g.in_stock;

  const metrics = g.metrics || {};
  const keys = Object.keys(metrics);
  const firstSize = keys.length ? keys[0] : "M";
  qs("size_label").value = firstSize;

  const block = metrics[firstSize] || {};
  const rm = block.real_measurements || {};
  qs("g_chest").value = rm.chest ?? "";
  qs("g_waist").value = rm.waist ?? "";
  qs("g_hips").value = rm.hips ?? "";
  qs("g_length").value = rm.length ?? "";
  qs("g_sleeve").value = rm.sleeve ?? "";
  qs("g_shoulders").value = rm.shoulders ?? "";

  const t = block.try_on || {};
  qs("fit_score").value = (t.fit_score_real ?? "");
  qs("ideal").checked = !!t.ideal_for_me;
  qs("notes").value = t.notes || "";

  qs("btnDelete").classList.remove("hidden");
}

function clearForm(){
  for(const id of [
    "sku","name","price","image_url","platform","size_label","notes",
    "g_chest","g_waist","g_hips","g_length","g_sleeve","g_shoulders"
  ]) qs(id).value = "";
  qs("fit_score").value = "";
  qs("ideal").checked = false;
  qs("in_stock").checked = true;
  qs("btnDelete").classList.add("hidden");
}

async function loadOneIfSkuInUrl(){
  const sku = currentSkuFromUrl();
  if(!sku) return;
  setMsg("Загружаю товар " + sku + " …");
  try{
    const g = await apiJSON(`/api/admin/builder/get?sku=${encodeURIComponent(sku)}`);
    fillFormFromGarment(g);
    setMsg("Открыт товар: " + sku);
  }catch(e){
    setMsg("Не найден товар по SKU из ссылки: " + sku);
  }
}

async function saveItem(){
  const sku = val("sku");
  if(!sku){
    setMsg("SKU обязателен");
    return;
  }

  const payload = {
    sku,
    name: val("name"),
    price: valNum("price"),
    image_url: val("image_url"),
    platform: val("platform") || "manual",
    size_label: (val("size_label") || "M").toUpperCase(),
    in_stock: qs("in_stock").checked,

    real_measurements: {
      chest: valNum("g_chest"),
      waist: valNum("g_waist"),
      hips: valNum("g_hips"),
      length: valNum("g_length"),
      sleeve: valNum("g_sleeve"),
      shoulders: valNum("g_shoulders")
    },

    try_on: {
      fit_score_real: valNum("fit_score"),
      ideal_for_me: qs("ideal").checked,
      notes: val("notes")
    }
  };

  setMsg("Сохраняю…");
  try{
    const r = await apiJSON("/api/admin/builder/upsert", {
      method: "POST",
      headers: {"Content-Type":"application/json"},
      body: JSON.stringify(payload)
    });
    setMsg(`Сохранено: ${r.action} ${r.sku}`);
    qs("btnDelete").classList.remove("hidden");
    await loadItems();
  }catch(e){
    setMsg("Ошибка: " + e.message);
  }
}

async function deleteItem(){
  const sku = val("sku");
  if(!sku){
    setMsg("Нечего удалять: SKU пустой");
    return;
  }
  if(!confirm(`Удалить товар ${sku} из базы?`)) return;

  setMsg("Удаляю…");
  try{
    await apiJSON(`/api/admin/builder/delete?sku=${encodeURIComponent(sku)}`, {method:"DELETE"});
    setMsg("Удалено: " + sku);
    clearForm();
    await loadItems();
  }catch(e){
    setMsg("Ошибка: " + e.message);
  }
}

async function loadItems(){
  const box = qs("items");
  box.innerHTML = "<div class='text-slate-400'>Загрузка…</div>";
  try{
    const data = await apiJSON("/api/admin/builder/list?limit=20");
    const items = data.items || [];
    if(!items.length){
      box.innerHTML = "<div class='text-slate-400'>Пока пусто</div>";
      return;
    }
    box.innerHTML = items.map(it => {
      const url = `/builder?sku=${encodeURIComponent(it.sku)}`;
      return `
        <div class="border border-slate-800 rounded-xl p-3">
          <div class="font-semibold">${it.sku} — ${it.name || ""}</div>
          <div class="text-sm text-slate-400">Цена: ${it.price ?? 0} • ${it.in_stock ? "в наличии" : "нет"}</div>
          <a class="inline-block mt-2 text-sky-300 text-sm" href="${url}">✎ Редактировать</a>
        </div>
      `;
    }).join("");
  }catch(e){
    box.innerHTML = `<div class='text-red-300'>Ошибка: ${e.message}</div>`;
  }
}

qs("btnSave").addEventListener("click", saveItem);
qs("btnDelete").addEventListener("click", deleteItem);
qs("btnNew").addEventListener("click", ()=>{ history.replaceState(null,"", "/builder"); clearForm(); setMsg(""); });
qs("btnRefresh").addEventListener("click", loadItems);

loadItems();
loadOneIfSkuInUrl();

