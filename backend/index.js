const express = require('express');
const axios = require('axios');
const cors = require('cors');
const app = express();

app.use(cors());
app.use(express.json());

const currentUser = {
    id: 1,
    measurements: { waist: 66, hip: 91 } 
};

app.get('/', (req, res) => res.send('Fit System Backend работает! 🚀'));

app.post('/api/recommend', async (req, res) => {
    const { query, maxPrice } = req.body;
    try {
        // Запрос к магазину (обращаемся к локальному адресу сервера)
        const shopResponse = await axios.post('http://127.0.0.1:5001/api/search', {
            query,
            gender: "female",
            max_price: maxPrice
        });

        // Простой алгоритм подбора
        const products = shopResponse.data.map(item => {
            const diff = item.measurements.waist - currentUser.measurements.waist;
            const isFit = diff >= 0 && diff <= 4;
            return {
                ...item,
                fit_result: isFit ? "✅ ИДЕАЛЬНО" : "❌ Не подходит",
                fit_details: isFit ? `Запас ${diff}см` : `Разница ${diff}см`
            };
        });
        res.json(products);
    } catch (error) {
        res.status(500).json({ error: "Ошибка связи" });
    }
});

app.listen(5000, '0.0.0.0', () => console.log('🧠 BACKEND running on 5000'));