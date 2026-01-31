// backend/services/fitLogic.js
// ЛОГИКА ПРИМЕРКИ + МАТРИЦА КРОЯ

const FIT_TYPES = {
    "skinny":   { chest: 0, waist: 0, hip: 0,  desc: "В обтяжку" },
    "slim":     { chest: 2, waist: 1, hip: 1,  desc: "По фигуре" },
    "regular":  { chest: 6, waist: 2, hip: 4,  desc: "Стандарт" },
    "loose":    { chest: 10, waist: 4, hip: 8, desc: "Свободно" },
    "oversize": { chest: 16, waist: 10, hip: 12, desc: "Оверсайз" }
};

function detectFitType(name) {
    const text = (name || "").toLowerCase();
    if (text.includes("oversize") || text.includes("оверсайз")) return "oversize";
    if (text.includes("loose") || text.includes("свободн")) return "loose";
    if (text.includes("slim") || text.includes("слим")) return "slim";
    return "regular";
}

// Проверка длины (Асимметричная)
function checkVerticalFit(userVal, itemVal) {
    if (!userVal || !itemVal) return null;
    const diff = itemVal - userVal;

    if (diff < -1.5) return { score: -100, msg: "❌ Коротко!" };
    if (diff >= -1.5 && diff <= 3) return { score: 10, msg: "✅ Идеальная длина" };
    if (diff > 3 && diff <= 12) return { score: 5, msg: "⚠️ Длинновато (подшить)" };
    return { score: 0, msg: "⚠️ Очень длинное" };
}

function analyzeFit(userBody, itemMeasurements, itemMeta) {
    let score = 0;
    let details = [];
    let isCriticalFail = false;

    // 1. Крой
    const fitTypeKey = detectFitType(itemMeta.name);
    const allowance = FIT_TYPES[fitTypeKey];

    // 2. Виртуальные замеры вещи
    const virtualItem = {
        waist: (itemMeasurements.waist || 0) + allowance.waist,
        hip: (itemMeasurements.hip || 0) + allowance.hip
    };

    // 3. Талия
    if (userBody.waist && virtualItem.waist) {
        const diff = virtualItem.waist - userBody.waist;
        if (diff < -2) {
            score -= 50; isCriticalFail = true; details.push("❌ Туго в талии");
        } else if (diff > 8) {
            score += 2; details.push("⚠️ Велико в талии");
        } else {
            score += 20;
        }
    }

    // 4. Длина / Рост
    if (userBody.leg_length && itemMeasurements.leg_inside) {
        const res = checkVerticalFit(userBody.leg_length, itemMeasurements.leg_inside);
        if (res) {
            score += res.score;
            details.push(res.msg);
            if (res.score === -100) isCriticalFail = true;
        }
    } else if (userBody.height && itemMeasurements.height) {
        // Проверка по росту, если нет длины ног
        const diff = itemMeasurements.height - userBody.height;
        if (diff < -4) { score -= 50; isCriticalFail = true; details.push("❌ На низкий рост"); }
        else if (diff > 5) details.push("⚠️ На высокий рост");
        else score += 10;
    }

    return {
        isMatch: score > 0 && !isCriticalFail,
        score: score,
        fitType: fitTypeKey,
        details: details.join(", ")
    };
}

module.exports = { analyzeFit };