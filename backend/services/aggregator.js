// backend/services/aggregator.js
// АГРЕГАТОР ПРЕДЛОЖЕНИЙ

function aggregateOffers(rawProducts) {
    const grouped = {};

    rawProducts.forEach(product => {
        // Ключ: бренд + название
        const cleanName = product.name.trim().toLowerCase();
        const cleanBrand = (product.brand || "nobrand").trim().toLowerCase();
        const uniqueKey = `${cleanBrand}_${cleanName}`;

        if (!grouped[uniqueKey]) {
            grouped[uniqueKey] = {
                id: product.id,
                name: product.name,
                brand: product.brand,
                measurements: product.measurements, // Берем замеры первого
                image: product.image,
                link: product.link, // Ссылка по умолчанию
                price: product.price, // Цена по умолчанию
                offers: []
            };
        }

        grouped[uniqueKey].offers.push({
            shop_name: product.shop_name || "Магазин",
            price: product.price,
            link: product.link,
            delivery_days: product.delivery_days || 3
        });
    });

    // Сортируем цены внутри каждого товара
    const resultList = Object.values(grouped);
    resultList.forEach(item => {
        item.offers.sort((a, b) => a.price - b.price);
        item.price = item.offers[0].price; // Показываем лучшую цену
    });

    return resultList;
}

module.exports = { aggregateOffers };