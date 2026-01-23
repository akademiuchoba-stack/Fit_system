const express = require('express');
const axios = require('axios');
const cors = require('cors');
const fs = require('fs');
const path = require('path');
const app = express();

const { analyzeFit } = require('./services/fitLogic');
const { aggregateOffers } = require('./services/aggregator');

app.use(cors());
app.use(express.json());

// ПУТЬ К БАЗЕ МОДЕЛЕЙ
const MODELS_DB_PATH = path.join(__dirname, 'data', 'models_db.json');

// Проверяем и создаем базу при старте
if (!fs.existsSync(MODELS_DB_PATH)) {
    if (!fs.existsSync(path.join(__dirname, 'data'))) {
        fs.mkdirSync(path.join(__dirname, 'data'));
    }
    fs.writeFileSync(MODELS_DB_PATH, JSON.stringify([]));
}

// 1. ПОИСК
app.post('/api/recommend', async (req, res) => {
    const { query, maxPrice, userMeasurements } = req.body;
    
    if (!userMeasurements) return res.status(400).json({ error: "Нет размеров" });

    try {
        const shopResponse = await axios.post('http://127.0.0.1:5001/api/search', {
            query, gender: "female", max_price: maxPrice
        });

        const uniqueProducts = aggregateOffers(shopResponse.data);

        const finalProducts = uniqueProducts.map(item => {
            const fit = analyzeFit(userMeasurements, item.measurements, item);
            return {
                ...item,
                fit_result: fit.isMatch ? "✅ ПОДХОДИТ" : "❌ НЕТ",
                fit_details: fit.details,
                fit_score: fit.score
            };
        });

        finalProducts.sort((a, b) => b.fit_score - a.fit_score);
        res.json(finalProducts);

    } catch (error) {
        console.error(error);
        res.status(500).json({ error: "Ошибка сервера" });
    }
});

// 2. РЕГИСТРАЦИЯ МОДЕЛИ
app.post('/api/become-model', (req, res) => {
    const { measurements } = req.body;
    if (!measurements) return res.status(400).json({ status: "error" });

    try {
        const currentData = JSON.parse(fs.readFileSync(MODELS_DB_PATH));
        const newModel = {
            id: "model_" + Date.now(),
            measurements: measurements,
            joined_at: new Date().toISOString() // Дата регистрации
        };
        currentData.push(newModel);
        fs.writeFileSync(MODELS_DB_PATH, JSON.stringify(currentData, null, 2));
        
        console.log("➕ Новая модель:", newModel.id);
        res.json({ status: "success", model_id: newModel.id });
    } catch (e) {
        res.status(500).json({ error: "Ошибка сохранения" });
    }
});

// 3. АДМИНКА (СТАТИСТИКА) - НОВОЕ!
app.get('/api/admin/stats', (req, res) => {
    try {
        const models = JSON.parse(fs.readFileSync(MODELS_DB_PATH));
        
        // Считаем простую аналитику
        const totalModels = models.length;
        
        // Считаем среднюю талию (просто для примера аналитики)
        let totalWaist = 0;
        models.forEach(m => totalWaist += (m.measurements.waist || 0));
        const avgWaist = totalModels > 0 ? Math.round(totalWaist / totalModels) : 0;

        res.json({
            count: totalModels,
            avg_waist: avgWaist,
            list: models.reverse() // Показываем новых сверху
        });
    } catch (e) {
        res.status(500).json({ error: "Ошибка чтения БД" });
    }
});

app.listen(5000, '0.0.0.0', () => console.log('🧠 BACKEND running on 5000'));