
import { Product, Category } from '../frontend/types';

/**
 * Эти данные имитируют результат работы backend/parser.py 
 * после сохранения в shop.db
 */
export const STORE_INVENTORY: Product[] = [
  {
    sku: 'OST-10234-WH',
    name: 'Рубашка Slim Fit (Хлопок)',
    image_url: 'https://picsum.photos/seed/shirt1/400/500',
    category: Category.UPPER,
    in_stock: true,
    garment_chest: 104,
    garment_waist: 98,
    garment_hips: 106,
    garment_length: 74,
    sleeve_length: 64,
    inseam: 0,
    elasticity_percent: 2,
    model_info: {
      height: 185,
      chest: 98,
      waist: 84,
      hips: 96,
      size: 'L'
    }
  },
  {
    sku: 'OST-88921-DN',
    name: 'Джинсы Regular (Denim)',
    image_url: 'https://picsum.photos/seed/jeans1/400/500',
    category: Category.LOWER,
    in_stock: true,
    garment_chest: 0,
    garment_waist: 92,
    garment_hips: 108,
    garment_length: 105,
    sleeve_length: 0,
    inseam: 82,
    elasticity_percent: 5,
    model_info: {
      height: 182,
      chest: 0,
      waist: 86,
      hips: 100,
      size: '32/32'
    }
  },
  {
    sku: 'OST-44512-TS',
    name: 'Футболка Heavy Oversize',
    image_url: 'https://picsum.photos/seed/tshirt2/400/500',
    category: Category.UPPER,
    in_stock: true,
    garment_chest: 122,
    garment_waist: 120,
    garment_hips: 122,
    garment_length: 76,
    sleeve_length: 24,
    inseam: 0,
    elasticity_percent: 0,
    model_info: {
      height: 188,
      chest: 100,
      waist: 85,
      hips: 98,
      size: 'XL'
    }
  }
];
