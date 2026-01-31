const express = require('express');
const fs = require('fs');
const path = require('path');
const xml2js = require('xml2js');
const cors = require('cors');

const app = express();
app.use(cors());
app.use(express.json());

// БАЗА ДАННЫХ (Кеш в памяти)
let shopInventory = [];

// СЛОВАРЬ РАЗМЕРОВ (Маппинг для тех товаров, что в XML)
// В реале это берется из brands_db, но магазин должен отдать "готовые" замеры
const SIZE_MAPPING = {
    "Gloria Jeans_M": { waist: 70, hip: 96, height: 170, leg_inside: 76 },
    "Zarina_46":      { waist: 72, hip: 98, height: 170 }, // Оверсайз добавится логикой
    "O'stin_S":       { waist: 66, hip: 94, height: 164, leg_inside: 68 } // Короткие!
};

// ФУНКЦИЯ ЗАГРУЗКИ XML
async function loadXMLFeed() {
    const parser = new xml2js.Parser();
    const filePath = path.join(__dirname, 'data', 'feed.xml');

    try {
        const data = fs.readFileSync(filePath);
        const result = await parser.parseStringPromise(data);
        
        const offers = result.yml_catalog.shop[0].offers[0].offer;
        
        // Превращаем XML в наш формат
        shopInventory = offers.map(offer => {
            const vendor = offer.vendor[0];
            const sizeParam = offer.param.find(p => p.$.name === "Размер")?._;
            
            // Ищем замеры в маппинге
            const mappingKey = `${vendor}_${sizeParam}`;
            const measurements = SIZE_MAPPING[mappingKey] || { waist: 70, hip: 96 }; // Дефолт если не нашли

            return {
                id: offer.$.id,
                name: offer.name[0],
                brand: vendor,
                gender: "female",
                price: Number(offer.price[0]),
                description: offer.description ? offer.description[0] : "",
                image: offer.picture ? offer.picture[0] : "",
                link: `http://myshop.ru/item/${offer.$.id}`,
                measurements: measurements
            };
        });
        
        console.log(`✅ XML загружен! Товаров в базе: ${shopInventory.length}`);
    } catch (err) {
        console.error("Ошибка чтения XML:", err);
    }
}

// Загружаем при старте
loadXMLFeed();

app.post('/api/search', (req, res) => {
    // ЭМУЛЯЦИЯ КОНКУРЕНЦИИ (Агрегатор)
    // Мы берем товары из XML и делаем вид, что они есть везде
    let multiShopInventory = [];

    shopInventory.forEach(item => {
        // 1. Оригинал (из XML)
        multiShopInventory.push({
            ...item,
            shop_name: "Официальный магазин",
            delivery_days: 5
        });

        // 2. Wildberries (Дешевле)
        multiShopInventory.push({
            ...item,
            id: item.id + "_wb",
            shop_name: "Wildberries",
            price: Math.floor(item.price * 0.9), // Скидка 10%
            delivery_days: 2,
            link: item.link + "?shop=wb"
        });

        // 3. Ozon (Быстрее)
        multiShopInventory.push({
            ...item,
            id: item.id + "_oz",
            shop_name: "Ozon",
            price: item.price + 100,
            delivery_days: 1, // Завтра
            link: item.link + "?shop=ozon"
        });
    });

    res.json(multiShopInventory);
});

app.listen(5001, '0.0.0.0', () => console.log('🛒 SHOP running on 5001'));