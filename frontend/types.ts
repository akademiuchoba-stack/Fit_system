
export enum Category {
  UPPER = 'верх',
  LOWER = 'низ'
}

export interface UserParams {
  gender: 'male' | 'female';
  height: number;
  chest: number;
  waist: number;
  hips: number;
  shoulders: number;
  armLength: number;
  inseam: number;
}

export interface Product {
  sku: string;
  name: string;
  image_url: string;
  category: Category;
  in_stock: boolean;
  garment_chest: number;
  garment_waist: number;
  garment_hips: number;
  garment_length: number;
  sleeve_length: number;
  inseam: number;
  elasticity_percent: number;
  // Added model_info to fix "Object literal may only specify known properties" error in shops/angarsk_festival.ts
  model_info?: {
    height: number;
    chest: number;
    waist: number;
    hips: number;
    size: string;
  };
}

export interface FitVerdict {
  score: number;
  label: 'Идеально' | 'Хорошо' | 'Туго' | 'Велико' | 'Не подходит';
  color: string;
  details: {
    zone: string;
    status: string;
    message: string;
  }[];
}

export interface MatchResult {
  product: Product;
  verdict: FitVerdict;
}
