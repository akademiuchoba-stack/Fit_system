const express = require('express');
const axios = require('axios');
const cors = require('cors');
const fs = require('fs');
const path = require('path');
const bcrypt = require('bcryptjs');
const jwt = require('jsonwebtoken');

const app = express();
const { analyzeFit } = require('./services/fitLogic');
const { aggregateOffers } = require('./services/aggregator');

app.use(cors());
app.use(express.json());

const JWT_SECRET = "my_super_secret_key_123";
const DATA_DIR = path.join(__dirname, 'data');
const MODELS_DB_PATH = path.join(DATA_DIR, 'models_db.json');
const USERS_DB_PATH = path.join(DATA_DIR, 'users_db.json');

if (!fs.existsSync(DATA_DIR)) fs.mkdirSync(DATA_DIR);
if (!fs.existsSync(MODELS_DB_PATH)) fs.writeFileSync(MODELS_DB_PATH, JSON.stringify([]));
if (!fs.existsSync(USERS_DB_PATH)) fs.writeFileSync(USERS_DB_PATH, JSON.stringify([]));

function readUsers() { return JSON.parse(fs.readFileSync(USERS_DB_PATH)); }
function saveUsers(data) { fs.writeFileSync(USERS_DB_PATH, JSON.stringify(data, null, 2)); }

// === АВТОРИЗАЦИЯ ===
app.post('/api/auth/register', async (req, res) => {
    const { email, password, measurements } = req.body;
    const users = readUsers();
    if (users.find(u => u.email === email)) return res.status(400).json({ error: "Пользователь уже существует" });
    const hashedPassword = await bcrypt.hash(password, 10);
    const newUser = {
        id: "u_" + Date.now(),
        email,
        password: hashedPassword,
        measurements: measurements || { waist: 0, height: 0, leg_length: 0 },
        isModel: false
    };
    users.push(newUser);
    saveUsers(users);
    const token = jwt.sign({ id: newUser.id }, JWT_SECRET);
    res.json({ token, user: { email: newUser.email, measurements: newUser.measurements } });
});

app.post('/api/auth/login', async (req, res) => {
    const { email, password } = req.body;
    const users = readUsers();
    const user = users.find(u => u.email === email);
    if (!user) return res.status(400).json({ error: "Пользователь не найден" });
    const isMatch = await bcrypt.compare(password, user.password);
    if (!isMatch) return res.status(400).json({ error: "Неверный пароль" });
    const token = jwt.sign({ id: user.id }, JWT_SECRET);
    res.json({ token, user: { email: user.email, measurements: user.measurements, isModel: user.isModel } });
});

app.get('/api/auth/me', (req, res) => {
    const authHeader = req.headers.authorization;
    if (!authHeader) return res.status(401).json({ error: "Нет токена" });
    const token = authHeader.split(' ')[1];
    try {
        const decoded = jwt.verify(token, JWT_SECRET);
        const users = readUsers();
        const user = users.find(u => u.id === decoded.id);
        if (!user) return res.status(404).json({ error: "User not found" });
        res.json({ user: { email: user.email, measurements: user.measurements, isModel: user.isModel } });
    } catch (e) { res.status(401).json({ error: "Неверный токен" }); }
});

app.post('/api/user/update', (req, res) => {
    const { token, measurements } = req.body;
    try {
        const decoded = jwt.verify(token, JWT_SECRET);
        const users = readUsers();
        const userIndex = users.findIndex(u => u.id === decoded.id);
        if (userIndex === -1) return res.status(404).json({ error: "User not found" });
        users[userIndex].measurements = measurements;
        saveUsers(users);
        res.json({ status: "success", measurements });
    } catch (e) { res.status(401).json({ error: "Не авторизован" }); }
});

// === ОСНОВНОЙ ФУНКЦИОНАЛ ===
app.post('/api/recommend', async (req, res) => {
    const { query, maxPrice, userMeasurements } = req.body;
    if (!userMeasurements || userMeasurements.waist === 0) return res.status(400).json({ error: "Заполните размеры в профиле!" });
    try {
        const shopResponse = await axios.post('http://127.0.0.1:5001/api/search', {
            query, gender: "female", max_price: maxPrice
        });
        const uniqueProducts = aggregateOffers(shopResponse.data);
        const finalProducts = uniqueProducts.map(item => {
            const fit = analyzeFit(userMeasurements, item.measurements, item);
            return { ...item, fit_result: fit.isMatch ? "✅ ПОДХОДИТ" : "❌ НЕТ", fit_details: fit.details, fit_score: fit.score };
        });
        finalProducts.sort((a, b) => b.fit_score - a.fit_score);
        res.json(finalProducts);
    } catch (error) { res.status(500).json({ error: "Ошибка поиска" }); }
});

// --- ИСПРАВЛЕННЫЙ БЛОК: СТАТЬ МОДЕЛЬЮ ---
app.post('/api/become-model', (req, res) => {
    const { token, measurements, isModel } = req.body; // Получаем токен и статус галочки
    
    try {
        // 1. Проверяем токен
        const decoded = jwt.verify(token, JWT_SECRET);
        const users = readUsers();
        const userIndex = users.findIndex(u => u.id === decoded.id);
        
        if (userIndex === -1) return res.status(404).json({ error: "User not found" });

        // 2. Обновляем статус в ПРОФИЛЕ ПОЛЬЗОВАТЕЛЯ (users_db)
        users[userIndex].isModel = isModel; // true или false
        users[userIndex].measurements = measurements; // Заодно обновляем размеры
        saveUsers(users);

        // 3. Обновляем БАЗУ МОДЕЛЕЙ (models_db)
        const models = JSON.parse(fs.readFileSync(MODELS_DB_PATH));
        
        if (isModel) {
            // Добавляем, если галочка стоит
            models.push({
                id: users[userIndex].id,
                measurements: measurements,
                joined_at: new Date().toISOString()
            });
        } 
        // Если галочка снята (isModel=false), можно было бы удалять из models,
        // но для MVP пока просто оставим историю. Главное, что в профиле статус обновился.
        
        fs.writeFileSync(MODELS_DB_PATH, JSON.stringify(models, null, 2));

        res.json({ status: "success" });
    } catch (e) {
        console.error(e);
        res.status(401).json({ error: "Не авторизован" }); 
    }
});

app.get('/api/admin/stats', (req, res) => {
    try {
        const models = JSON.parse(fs.readFileSync(MODELS_DB_PATH));
        const users = JSON.parse(fs.readFileSync(USERS_DB_PATH));
        let totalWaist = 0;
        models.forEach(m => totalWaist += (m.measurements.waist || 0));
        res.json({
            count: models.length,
            users_count: users.length,
            avg_waist: models.length > 0 ? Math.round(totalWaist / models.length) : 0,
            list: models.reverse()
        });
    } catch (e) { res.status(500).json({ error: "Error" }); }
});

app.listen(5000, '0.0.0.0', () => console.log('🧠 BACKEND running on 5000'));