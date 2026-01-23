const express = require('express');
const axios = require('axios');
const cors = require('cors');
const app = express();

app.use(cors());
app.use(express.json());

// 1. Тестовый пользователь (пока зашит жестко)
const currentUser = {
    id: 1,
    name: "Мария",
    measurements: { 
        waist: 66,       // Талия
        hip: 91,         // Бедра
        leg_length: 99,  // Длина ноги
        shoulder: 38     // Плечи
    }
};

// 2. Идеальные припуски (сколько см свободы должно быть)
const idealAllowance = {
    waist: 2,      // Талия: +2 см к телу
    hip: 4,        // Бедра: +4 см к телу
    leg_length: 3, // Длина: +3 см (запас на обувь/сборки)
    shoulder: 1    // Плечи: +1 см
};

// 3. Функция умной проверки с компенсацией
function calculateSmartFit(userBody, itemMeasurements) {
    let score = 0; 
    let issues = []; 

    // --- ПРОВЕРКА ТАЛИИ ---
    // Формула: Размер вещи - (Тело + Припуск)
    const waistDiff = itemMeasurements.waist - (userBody.waist + idealAllowance.waist);
    
    if (waistDiff < -2) issues.push("Очень туго в талии");
    else if (waistDiff > 6) issues.push("Велико в талии");
    else score += 10; // Попали в диапазон

    // --- ПРОВЕРКА ДЛИНЫ НОГ (с логикой подшива) ---
    const legDiff = itemMeasurements.leg_length - userBody.leg_length;
    
    if (legDiff >= 0 && legDiff <= 5) {
        score += 10; // Идеальная длина
    } else if (legDiff > 5) {
        issues.push("Длинные (нужно подшить)");
        score += 5; // Это не страшно, можно брать
    } else if (legDiff < 0) {
        issues.push("Короткие!"); 
        score = -50; // Критично
    }

    // Итог
    return {
        isMatch: score > 0,
        score: score,
        reason: issues.length > 0 ? issues.join(", ") : "🔥 Идеальная посадка"
    };
}

app.get('/', (req, res) => res.send('Fit System Backend v2 (Smart Algo) 🚀'));

// backend/index.js
// (Верхняя часть с require и allowance остается той же)

// ... код allowance ...

app.post('/api/recommend', async (req, res) => {
    // ТЕПЕРЬ МЫ ПОЛУЧАЕМ РАЗМЕРЫ ОТ ПОЛЬЗОВАТЕЛЯ
    const { query, maxPrice, userMeasurements } = req.body;
    
    console.log(`[BACKEND] Поиск: "${query}" для размеров:`, userMeasurements);

    if (!userMeasurements) {
        return res.status(400).json({ error: "Не переданы размеры тела" });
    }

    try {
        // 1. Идем в магазин
        const shopResponse = await axios.post('http://127.0.0.1:5001/api/search', {
            query, gender: "female", max_price: maxPrice
        });

        // 2. Считаем посадку под КОНКРЕТНОГО пользователя
        const products = shopResponse.data.map(item => {
            // Передаем пришедшие от фронтенда размеры в функцию
            const fitAnalysis = calculateSmartFit(userMeasurements, item.measurements);
            
            return {
                ...item,
                fit_result: fitAnalysis.isMatch ? "✅ ПОДХОДИТ" : "❌ НЕТ",
                fit_details: fitAnalysis.reason,
                match_score: fitAnalysis.score
            };
        });

        // Сортировка
        products.sort((a, b) => b.match_score - a.match_score);

        res.json(products);

    } catch (error) {
        console.error(error);
        res.status(500).json({ error: "Ошибка сервера" });
    }
});

app.listen(5000, '0.0.0.0', () => console.log('🧠 BACKEND running on 5000'));