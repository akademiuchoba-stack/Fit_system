async function save() {
  const payload = {
    sku: document.getElementById("sku").value,
    name: document.getElementById("name").value,
    price: document.getElementById("price").value,
    model_size: document.getElementById("model_size").value,
    fit_profile: document.getElementById("fit_profile").value,
    text: document.getElementById("text").value,
    real_measurements: {
      chest: document.getElementById("chest_g").value,
      waist: document.getElementById("waist_g").value,
      hips: document.getElementById("hips_g").value
    },
    try_on: {
      fit_score_real: document.getElementById("fit_score").value,
      notes: document.getElementById("notes").value
    }
  };

  await fetch("/api/admin/builder/upsert", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify(payload)
  });

  alert("Сохранено");
}
