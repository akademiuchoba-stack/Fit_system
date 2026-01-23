const express = require('express');
const app = express();
const cors = require('cors');

app.use(cors());
app.use(express.json());

// ИМИТАЦИЯ ТОВАРОВ (БЕЗ XML ДЛЯ ПРОСТОТЫ ПОКА)
// Но с правильными полями для нашего парсера
const baseInventory = [
    {
        id: "gj_jeans_001",
        name: "Джинсы Mom Fit",
        brand: "Gloria Jeans",
        gender: "female",
        price: 2500,
        // Имитируем, что мы знаем размер "M"
        measurements: { waist: 70, hip: 96, height: 170, leg_inside: 76 }, 
        image: "https://via.placeholder.com/200?text=Jeans+Mom",
        link: "http://shop.com/gj_001"
    },
    {
        id: "zar_pants_002",
        name: "Брюки классика",
        brand: "Zarina",
        gender: "female",
        price: 1800,
        measurements: { waist: 72, hip: 98, height: 170 }, // Аналог 46/M
        image: "https://via.placeholder.com/200?text=Pants+Classic",
        link: "http://shop.com/zar_002"
    }
];

app.post('/api/search', (req, res) => {
    // Генерируем 3 магазина для каждого товара
    let multiShopInventory = [];

    baseInventory.forEach(item => {
        // 1. Ozon
        multiShopInventory.push({
            ...item,
            shop_name: "Ozon",
            delivery_days: 5,
            price: item.price
        });
        // 2. Wildberries (Дешевле и быстрее)
        multiShopInventory.push({
            ...item,
            id: item.id + "_wb",
            shop_name: "Wildberries",
            delivery_days: 1,
            price: item.price - 300,
            link: item.link + "?shop=wb"
        });
        // 3. Lamoda (Дороже)
        multiShopInventory.push({
            ...item,
            id: item.id + "_lm",
            shop_name: "Lamoda",
            delivery_days: 3,
            price: item.price + 500,
            link: item.link + "?shop=lamoda"
        });
    });

    res.json(multiShopInventory);
});

app.listen(5001, '0.0.0.0', () => console.log('🛒 SHOP running on 5001'));