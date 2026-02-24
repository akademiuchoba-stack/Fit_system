(() => {
  // Robust Builder script that works when some optional fields are absent in the HTML.
  // Fixes:
  //  - No crash if element is missing (e.g. platform input absent in builder.html)
  //  - "Save theory" shows message and actually saves
  //  - "Save measurements" (ground_truth) sends base fields too (name/price/images) so card is not SKU-only
  //  - Feedback works even if currentGarment wasn't loaded yet (tries to load by SKU)

  let currentGarment = null;
  let groundTruthData = {};

  // ---------- DOM helpers ----------
  const $ = (id) => document.getElementById(id);

  const getVal = (id, def = "") => {
    const e = $(id);
    return e ? (e.value ?? def) : def;
  };

  const setText = (id, v) => {
    const e = $(id);
    if (e) e.textContent = (v ?? "");
  };

  // Parse numbers, supports comma decimals "92,5"
  const num = (v) => {
    const s = String(v ?? "").trim().replace(",", ".");
    if (!s) return null;
    const n = Number(s);
    return Number.isFinite(n) ? n : null;
  };

  // ---------- Required elements ----------
  const el = {
    msg: $("msg"),
    skuDisplay: $("current-sku-display"),
    btnTheory: $("tab-btn-theory"),
    btnPractice: $("tab-btn-practice"),
    tabTheory: $("tab-theory"),
    tabPractice: $("tab-practice"),

    // identification
    sku: $("sku"),
    price: $("price"),
    name: $("name"),
    imgFront: $("img_front"),
    imgBack: $("img_back"),

    // theory blocks
    catType: $("cat_type"),
    fitProfile: $("fit_profile"),
    stiffnessClass: $("stiffness_class"),
    elastane: $("elastane"),
    wrapSleeve: $("wrap_sleeve_type"),
    wrapLeg: $("wrap_leg_type"),
    wrapRise: $("wrap_rise_class"),
    theoryTopFields: $("theory_top_fields"),
    theoryBotFields: $("theory_bot_fields"),
    gtTopFields: $("gt_top_fields"),
    gtBotFields: $("gt_bot_fields"),

    sleeveType: $("sleeve_type"),
    legType: $("leg_type"),
    riseClass: $("rise_class"),

    gShoulders: $("g_shoulders"),
    gBackWidth: $("g_back_width"),
    gChest: $("g_chest"),
    gWaistTop: $("g_waist_top"),
    gHemTop: $("g_hem_top"),
    gBicep: $("g_bicep"),
    gSleeve: $("g_sleeve"),
    gLength: $("g_length"),
    gWaistBot: $("g_waist_bot"),
    gBelly: $("g_belly"),
    gHips: $("g_hips"),
    gThigh: $("g_thigh"),
    gKnee: $("g_knee"),
    gLegOpening: $("g_leg_opening"),
    gFrontRise: $("g_front_rise"),
    gBackRise: $("g_back_rise"),
    gInseam: $("g_inseam"),
    gOutseam: $("g_outseam"),

    mSize: $("m_size"),
    mHeight: $("m_height"),
    mChest: $("m_chest"),
    mWaist: $("m_waist"),
    mHips: $("m_hips"),

    btnSaveTheory: $("btn-save-theory"),

    // ground truth
    gtSize: $("gt_size"),
    btnAddGt: $("btn-add-gt"),
    gtList: $("gt_list"),

    // feedback
    fbProfile: $("fb_profile"),
    fbSize: $("fb_size"),
    fbPointZero: $("fb_point_zero"),
    btnSaveFb: $("btn-save-fb"),

    analysisResult: $("analysis-result"),
    resTheory: $("res-theory"),
    resGt: $("res-gt"),
    resVerdict: $("res-verdict"),
  };

  function showMsg(text, isError = false) {
    if (!el.msg) return;
    el.msg.textContent = text;
    el.msg.className = `mb-4 p-3 rounded-2xl text-white text-sm shadow-lg fixed top-5 right-5 z-50 ${
      isError ? "bg-red-600" : "bg-green-600"
    }`;
    el.msg.classList.remove("hidden");
    setTimeout(() => el.msg.classList.add("hidden"), 3200);
  }

  function toggleCatFields() {
    const cat = el.catType ? el.catType.value : "top";

    const showTop = (cat === "top" || cat === "full");
    const showBot = (cat === "bottom" || cat === "full");

    if (el.wrapSleeve) el.wrapSleeve.classList.toggle("hidden", !showTop);
    if (el.theoryTopFields) el.theoryTopFields.classList.toggle("hidden", !showTop);
    if (el.gtTopFields) el.gtTopFields.classList.toggle("hidden", !showTop);

    if (el.wrapLeg) el.wrapLeg.classList.toggle("hidden", !showBot);
    if (el.wrapRise) el.wrapRise.classList.toggle("hidden", !showBot);
    if (el.theoryBotFields) el.theoryBotFields.classList.toggle("hidden", !showBot);
    if (el.gtBotFields) el.gtBotFields.classList.toggle("hidden", !showBot);
  }

  function switchTab(tab) {
    if (!el.tabTheory || !el.tabPractice || !el.btnTheory || !el.btnPractice) return;
    if (tab === "theory") {
      el.tabTheory.classList.remove("hidden");
      el.tabPractice.classList.add("hidden");
      el.btnTheory.className = "flex-1 py-2.5 rounded-xl font-black text-sm transition shadow-sm bg-white text-gray-900";
      el.btnPractice.className = "flex-1 py-2.5 rounded-xl font-black text-sm text-gray-500 transition hover:text-gray-900";
    } else {
      el.tabTheory.classList.add("hidden");
      el.tabPractice.classList.remove("hidden");
      el.btnPractice.className = "flex-1 py-2.5 rounded-xl font-black text-sm transition shadow-sm bg-white text-gray-900";
      el.btnTheory.className = "flex-1 py-2.5 rounded-xl font-black text-sm text-gray-500 transition hover:text-gray-900";
    }
  }

  async function api(url, options = {}) {
    const res = await fetch(url, { headers: { "Content-Type": "application/json" }, ...options });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || `API error (${res.status})`);
    return data;
  }

  function getSkuFromUrl() {
    return new URL(window.location.href).searchParams.get("sku") || "";
  }

  async function loadProfiles() {
    if (!el.fbProfile) return;
    try {
      const profiles = await api("/api/profiles");
      el.fbProfile.innerHTML =
        '<option value="">-- Выбери профиль --</option>' +
        profiles.map((p) => `<option value="${p.id}">${p.name} (${p.height}см)</option>`).join("");
    } catch (_) {
      // ignore
    }
  }

  function populateForm(g) {
    currentGarment = g;
    setText("current-sku-display", g?.sku || "Новый товар");

    if (el.sku) el.sku.value = g?.sku || "";
    if (el.name) el.name.value = g?.name || "";
    if (el.price) el.price.value = (g?.price ?? "");
    if (el.imgFront) el.imgFront.value = g?.image_url || "";
    if (el.imgBack) el.imgBack.value = g?.image_url_back || "";

    const theory = (g?.metrics || {}).theory || {};
    groundTruthData = (g?.metrics || {}).ground_truth || {};

    if (el.catType) el.catType.value = theory.category_type || "top";
    if (el.fitProfile) el.fitProfile.value = theory.fit_profile || "regular";
    if (el.stiffnessClass) el.stiffnessClass.value = theory.stiffness_class || "medium";
    if (el.elastane) el.elastane.value = (theory.elastane_pct ?? 0);

    if (el.sleeveType) el.sleeveType.value = theory.sleeve_type || "long";
    if (el.legType) el.legType.value = theory.leg_type || "long";
    if (el.riseClass) el.riseClass.value = theory.rise_class || "mid";

    // garment measurements (theory)
    const map = [
      ["gShoulders", "g_shoulders"], ["gBackWidth", "g_back_width"],
      ["gChest", "g_chest"], ["gWaistTop", "g_waist_top"],
      ["gHemTop", "g_hem_top"], ["gBicep", "g_bicep"],
      ["gSleeve", "g_sleeve"], ["gLength", "g_length"],
      ["gWaistBot", "g_waist_bot"], ["gBelly", "g_belly"],
      ["gHips", "g_hips"], ["gThigh", "g_thigh"],
      ["gKnee", "g_knee"], ["gLegOpening", "g_leg_opening"],
      ["gFrontRise", "g_front_rise"], ["gBackRise", "g_back_rise"],
      ["gInseam", "g_inseam"], ["gOutseam", "g_outseam"],
    ];
    for (const [key, tkey] of map) {
      if (el[key]) el[key].value = (theory[tkey] ?? "");
    }

    if (el.mSize) el.mSize.value = theory.model_size || "";
    if (el.mHeight) el.mHeight.value = (theory.height ?? "");
    if (el.mChest) el.mChest.value = (theory.chest ?? "");
    if (el.mWaist) el.mWaist.value = (theory.waist ?? "");
    if (el.mHips) el.mHips.value = (theory.hips ?? "");

    toggleCatFields();
    renderGtList();
  }

  async function tryLoadGarmentBySku() {
    const sku = (el.sku ? el.sku.value : "").trim();
    if (!sku) return null;
    try {
      const data = await api(`/api/admin/builder/get?sku=${encodeURIComponent(sku)}`);
      populateForm(data);
      return data;
    } catch (_) {
      return null;
    }
  }

  // ---------- Ground truth list ----------
  function renderGtList() {
    if (!el.gtList) return;
    const sizes = Object.keys(groundTruthData || {});
    if (!sizes.length) {
      el.gtList.innerHTML = '<div class="text-xs text-gray-400">Пока нет замеров.</div>';
      return;
    }
    el.gtList.innerHTML = sizes
      .map((size) => {
        const d = groundTruthData[size];
        return `<div class="p-3 bg-gray-50 border border-gray-100 rounded-xl text-sm flex justify-between items-center">
          <div class="truncate w-[90%]"><strong class="text-indigo-600">Размер ${size}</strong>: ${JSON.stringify(d).replace(/[{""}]/g, "")}</div>
          <button data-del-size="${size}" class="text-red-500 font-bold text-xs ml-2 px-2 py-1 bg-red-50 rounded hover:bg-red-100">X</button>
        </div>`;
      })
      .join("");

    // attach handlers
    el.gtList.querySelectorAll("button[data-del-size]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const size = btn.getAttribute("data-del-size");
        if (!size) return;
        delete groundTruthData[size];
        renderGtList();
        try {
          await saveGroundTruth();
          showMsg("Замер удалён!");
        } catch (e) {
          showMsg(e.message || "Ошибка при удалении замера", true);
        }
      });
    });
  }

  async function saveGroundTruth() {
    const sku = (el.sku ? el.sku.value : "").trim();
    if (!sku) {
      showMsg("SKU обязателен!", true);
      return;
    }

    // platform field may not exist in HTML -> default
    const platform = getVal("platform", "manual");

    const payload = {
      sku,
      // send base fields too to prevent SKU-only cards
      name: (el.name ? el.name.value : "").trim(),
      price: num(el.price ? el.price.value : null),
      image_url: (el.imgFront ? el.imgFront.value : "").trim(),
      image_url_back: (el.imgBack ? el.imgBack.value : "").trim(),
      platform,
      ground_truth: groundTruthData,
    };

    const resp = await api("/api/admin/builder/upsert", { method: "POST", body: JSON.stringify(payload) });
    if (resp?.item) populateForm(resp.item);
  }

  // ---------- Init ----------
  async function init() {
    switchTab("theory");

    if (el.btnTheory) el.btnTheory.addEventListener("click", () => switchTab("theory"));
    if (el.btnPractice) el.btnPractice.addEventListener("click", () => switchTab("practice"));
    if (el.catType) el.catType.addEventListener("change", toggleCatFields);

    // Auto-load by SKU when changed
    if (el.sku) {
      el.sku.addEventListener("change", async () => {
        const val = el.sku.value.trim();
        if (!val) return;
        const g = await tryLoadGarmentBySku();
        if (g) showMsg("Данные вещи загружены из базы!");
      });
    }

    await loadProfiles();

    const sku = getSkuFromUrl();
    if (sku && el.sku) el.sku.value = sku;

    if (sku) {
      const g = await tryLoadGarmentBySku();
      if (!g) toggleCatFields();
    } else {
      toggleCatFields();
    }
  }

  // ---------- Save Theory ----------
  if (el.btnSaveTheory) {
    el.btnSaveTheory.addEventListener("click", async () => {
      const sku = (el.sku ? el.sku.value : "").trim();
      if (!sku) return showMsg("SKU обязателен!", true);

      const platform = getVal("platform", "manual");

      const payload = {
        sku,
        name: (el.name ? el.name.value : "").trim(),
        price: num(el.price ? el.price.value : null),
        image_url: (el.imgFront ? el.imgFront.value : "").trim(),
        image_url_back: (el.imgBack ? el.imgBack.value : "").trim(),
        platform,
        theory: {
          category_type: el.catType ? el.catType.value : "top",
          fit_profile: el.fitProfile ? el.fitProfile.value : "regular",
          stiffness_class: el.stiffnessClass ? el.stiffnessClass.value : "medium",
          elastane_pct: num(el.elastane ? el.elastane.value : null) || 0,

          sleeve_type: el.sleeveType ? el.sleeveType.value : "long",
          leg_type: el.legType ? el.legType.value : "long",
          rise_class: el.riseClass ? el.riseClass.value : "mid",

          g_shoulders: num(getVal("g_shoulders", "")),
          g_back_width: num(getVal("g_back_width", "")),
          g_chest: num(getVal("g_chest", "")),
          g_waist_top: num(getVal("g_waist_top", "")),
          g_hem_top: num(getVal("g_hem_top", "")),
          g_bicep: num(getVal("g_bicep", "")),
          g_sleeve: num(getVal("g_sleeve", "")),
          g_length: num(getVal("g_length", "")),

          g_waist_bot: num(getVal("g_waist_bot", "")),
          g_belly: num(getVal("g_belly", "")),
          g_hips: num(getVal("g_hips", "")),
          g_thigh: num(getVal("g_thigh", "")),
          g_knee: num(getVal("g_knee", "")),
          g_leg_opening: num(getVal("g_leg_opening", "")),
          g_front_rise: num(getVal("g_front_rise", "")),
          g_back_rise: num(getVal("g_back_rise", "")),
          g_inseam: num(getVal("g_inseam", "")),
          g_outseam: num(getVal("g_outseam", "")),

          model_size: (el.mSize ? el.mSize.value : "").trim(),
          height: num(el.mHeight ? el.mHeight.value : null),
          chest: num(el.mChest ? el.mChest.value : null),
          waist: num(el.mWaist ? el.mWaist.value : null),
          hips: num(el.mHips ? el.mHips.value : null),
        },
      };

      try {
        const resp = await api("/api/admin/builder/upsert", { method: "POST", body: JSON.stringify(payload) });
        showMsg("Теория успешно сохранена!");
        if (resp?.item) populateForm(resp.item);
        else await tryLoadGarmentBySku();
      } catch (e) {
        showMsg(e.message || "Ошибка сохранения", true);
        console.error("SAVE THEORY ERROR:", e);
      }
    });
  }

  // ---------- Add Ground Truth ----------
  if (el.btnAddGt) {
    el.btnAddGt.addEventListener("click", async () => {
      const sku = (el.sku ? el.sku.value : "").trim();
      if (!sku) return showMsg("SKU обязателен!", true);

      const size = (el.gtSize ? el.gtSize.value : "").trim().toUpperCase();
      if (!size) return showMsg("Укажи размер (например L)!", true);

      const m = {};
      const extract = (id, key) => {
        const v = num(getVal(id, ""));
        if (v !== null) m[key] = v;
      };

      // Top
      extract("gt_shoulders", "shoulders");
      extract("gt_back_width", "back_width");
      extract("gt_chest", "chest");
      extract("gt_waist_top", "waist_top");
      extract("gt_hem_top", "hem_top");
      extract("gt_bicep", "bicep");
      extract("gt_sleeve", "sleeve");
      extract("gt_length_top", "length_top");

      // Bottom
      extract("gt_waist_bot", "waist_bottom");
      extract("gt_belly", "belly");
      extract("gt_hips", "hips");
      extract("gt_thigh", "thigh");
      extract("gt_knee", "knee");
      extract("gt_leg_opening", "leg_opening");
      extract("gt_front_rise", "front_rise");
      extract("gt_back_rise", "back_rise");
      extract("gt_inseam", "inseam");
      extract("gt_outseam", "outseam");

      if (Object.keys(m).length === 0) return showMsg("Введи хотя бы один замер!", true);

      groundTruthData[size] = m;

      // clear inputs
      document.querySelectorAll('#gt_top_fields input, #gt_bot_fields input').forEach((i) => (i.value = ""));
      if (el.gtSize) el.gtSize.value = "";

      renderGtList();

      try {
        await saveGroundTruth();
        showMsg("Замер сохранён!");
      } catch (e) {
        showMsg(e.message || "Ошибка сохранения замера", true);
      }
    });
  }

  // ---------- Send Feedback ----------
  if (el.btnSaveFb) {
    el.btnSaveFb.addEventListener("click", async () => {
      // Ensure we have garment id
      if (!currentGarment || !currentGarment.id) {
        await tryLoadGarmentBySku();
      }
      if (!currentGarment || !currentGarment.id) {
        return showMsg("Сначала сохраните товар!", true);
      }

      const userId = el.fbProfile ? el.fbProfile.value : "";
      if (!userId) return showMsg("Выбери профиль!", true);

      const sizeSelected = (el.fbSize ? el.fbSize.value : "").trim().toUpperCase();
      if (!sizeSelected) return showMsg("Укажи размер!", true);

      const payload = {
        garment_id: currentGarment.id,
        user_id: userId,
        size_selected: sizeSelected,
        is_point_zero: !!(el.fbPointZero && el.fbPointZero.checked),
        fit_matrix: null,
      };

      try {
        const data = await api("/api/feedback", { method: "POST", body: JSON.stringify(payload) });
        showMsg("Фидбек отправлен!");

        if (data.analysis && el.analysisResult) {
          el.analysisResult.classList.remove("hidden");
          if (el.resTheory) el.resTheory.textContent = data.analysis.theory_size ? `${data.analysis.theory_size} (${data.analysis.theory_score}%)` : "Нет данных";
          if (el.resGt) el.resGt.textContent = data.analysis.gt_size ? `${data.analysis.gt_size} (${data.analysis.gt_score}%)` : "Нет данных";

          if (el.resVerdict) {
            if (data.analysis.match === true) {
              el.resVerdict.className = "mt-3 p-3 rounded-xl font-bold text-center bg-green-100 text-green-800";
              el.resVerdict.textContent = "Совпадение! Данные магазина верны.";
            } else if (data.analysis.match === false) {
              el.resVerdict.className = "mt-3 p-3 rounded-xl font-bold text-center bg-red-100 text-red-800";
              el.resVerdict.textContent = `Ошибка магазина! Реальный размер: ${data.analysis.gt_size}`;
            } else {
              el.resVerdict.className = "mt-3 p-3 rounded-xl font-bold text-center bg-gray-100 text-gray-800";
              el.resVerdict.textContent = "Недостаточно данных для сравнения.";
            }
          }
        }
      } catch (e) {
        showMsg(e.message || "Ошибка отправки фидбека", true);
        console.error("SAVE FEEDBACK ERROR:", e);
      }
    });
  }

  init();
})();

