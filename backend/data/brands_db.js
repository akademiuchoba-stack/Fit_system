// backend/data/brands_db.js
// БАЗА ДАННЫХ РАЗМЕРОВ БРЕНДОВ

const BRANDS_DB = {
    "Gloria Jeans": {
        "female": {
            "default": {
                "XS": { waist: 60, hip: 86, chest: 82, height: 164 },
                "S":  { waist: 64, hip: 90, chest: 86, height: 164 },
                "M":  { waist: 68, hip: 94, chest: 90, height: 170 },
                "L":  { waist: 72, hip: 98, chest: 94, height: 170 },
                "XL": { waist: 78, hip: 104, chest: 100, height: 170 }
            }
        }
    },
    "Zarina": {
        "female": {
            "default": {
                "42": { waist: 64, hip: 90, height: 164 },
                "44": { waist: 68, hip: 94, height: 164 },
                "46": { waist: 72, hip: 98, height: 170 },
                "48": { waist: 76, hip: 102, height: 170 },
                "50": { waist: 81, hip: 107, height: 170 }
            }
        }
    },
    // Заглушка для неизвестных брендов
    "Generic": {
        "female": {
            "default": {
                "XS": { waist: 62, hip: 88, height: 164 },
                "S":  { waist: 66, hip: 92, height: 165 },
                "M":  { waist: 70, hip: 96, height: 170 },
                "L":  { waist: 76, hip: 102, height: 172 }
            }
        }
    }
};

module.exports = { BRANDS_DB };