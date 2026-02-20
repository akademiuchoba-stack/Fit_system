async function saveItem() {

  const payload = {
    sku: val("sku"),
    name: val("name"),
    price: val("price"),
    image_url: val("image_url"),

    size_label: val("size_label") || "M",
    model_size: val("model_size"),
    fit_profile: val("fit_profile"),
    fabric: val("fabric"),
    elastane_pct: val("elastane_pct"),

    model_metrics: {
      chest: valNum("model_chest"),
      waist: valNum("model_waist"),
      hips: valNum("model_hips"),
      height: valNum("model_height")
    },

    real_measurements: {
      chest: valNum("g_chest"),
      waist: valNum("g_waist"),
      hips: valNum("g_hips"),
      length: valNum("g_length"),
      sleeve: valNum("g_sleeve")
    },

    try_on: {
      fit_score_real: valNum("fit_score"),
      ideal_for_me: document.getElementById("ideal").checked,
      notes: val("notes")
    }
  };

  await fetch("/api/admin/builder/upsert", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(payload)
  });

  alert("Сохранено");
  loadItems();
}

function val(id) {
  return document.getElementById(id).value.trim();
}

function valNum(id) {
  const v = document.getElementById(id).value;
  return v ? Number(v) : null;
}

async function loadItems() {
  const res = await fetch("/api/admin/builder/list?limit=20");
  const data = await res.json();

  const box = document.getElementById("items");
  box.innerHTML = "";

  data.items.forEach(item => {
    const div = document.createElement("div");
    div.className = "border border-slate-800 p-2 rounded";
    div.innerHTML = `
      <div><b>${item.sku}</b> — ${item.name}</div>
      <div class="text-sm text-slate-400">Цена: ${item.price || 0}</div>
    `;
    box.appendChild(div);
  });
}

loadItems();

