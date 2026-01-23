const express = require('express');
const axios = require('axios');
const cors = require('cors');
const app = express();

const { analyzeFit } = require('./services/fitLogic');
const { aggregateOffers } = require('./services/aggregator');

app.use(cors());
app.use(express.json());

app.post('/api/recommend', async (req, res) => {
    const { query, maxPrice, userMeasurements } = req.body;
    console.log(`[BACKEND] Запрос: ${query}`, userMeasurements);

    if (!userMeasurements) return res.status(400).json({ error: "Нет размеров" });

    try {
        // 1. Идем в магазины
        const shopResponse = await axios.post('http://127.0.0.1:5001/api/search', {
            query, gender: "female", max_price: maxPrice
        });

        // 2. Склеиваем одинаковые товары (Агрегатор)
        const uniqueProducts = aggregateOffers(shopResponse.data);

        // 3. Примерка
        const finalProducts = uniqueProducts.map(item => {
            const fit = analyzeFit(userMeasurements, item.measurements, item);
            return {
                ...item,
                fit_result: fit.isMatch ? "✅ ПОДХОДИТ" : "❌ НЕТ",
                fit_details: fit.details,
                fit_score: fit.score
            };
        });

        // 4. Сортировка (Лучшие сверху)
        finalProducts.sort((a, b) => b.fit_score - a.fit_score);

        res.json(finalProducts);

    } catch (error) {
        console.error(error);
        res.status(500).json({ error: "Ошибка сервера" });
    }
});

app.listen(5000, '0.0.0.0', () => console.log('🧠 BACKEND running on 5000'));