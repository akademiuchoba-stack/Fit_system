const express = require('express');
const app = express();
const cors = require('cors');
app.use(cors());
app.use(express.json());

// Имитация базы данных магазина
const mockInventory = [
    {
        id: 101,
        name: "Джинсы Slim Blue",
        price: 1800,
        gender: "female",
        measurements: { waist: 65, hip: 90, leg_length: 100 }, 
        link: "https://shop1.com/item/101"
    },
    {
        id: 102,
        name: "Платье Summer",
        price: 2500,
        gender: "female",
        measurements: { waist: 70, hip: 98, leg_length: 102 },
        link: "https://shop1.com/item/102"
    }
];

app.post('/api/search', (req, res) => {
    const { gender, max_price } = req.body;
    const filtered = mockInventory.filter(item => 
        item.gender === gender && item.price <= max_price
    );
    res.json(filtered);
});

app.listen(5001, '0.0.0.0', () => console.log('🛒 SHOP running on 5001'));