
import { UserParams, Product, FitVerdict, Category } from '../frontend/types';

export const IDEAL_EASE_NORMS = {
  CHEST: { min: 4, max: 8 },
  WAIST: { min: 2, max: 5 },
  HIPS: { min: 2, max: 6 }
};

/**
 * CORE PROPRIETARY ALGORITHM "IDEAL EASE"
 * Location: Backend (Protected)
 */
export const calculateMatch = (user: UserParams, product: Product): FitVerdict => {
  const details: FitVerdict['details'] = [];
  let totalScore = 5;

  const chestEase = product.garment_chest - user.chest;
  const isStretch = product.elasticity_percent > 3;
  
  if (product.category === Category.UPPER) {
    if (chestEase >= IDEAL_EASE_NORMS.CHEST.min && chestEase <= IDEAL_EASE_NORMS.CHEST.max) {
      details.push({ zone: 'Грудь', status: 'OK', message: 'Идеальный объем' });
    } else if (chestEase < 0) {
      if (isStretch && product.garment_chest >= user.chest * 0.95) {
        details.push({ zone: 'Грудь', status: 'Slim', message: 'Плотная посадка (Stretch)' });
        totalScore -= 0.5;
      } else {
        details.push({ zone: 'Грудь', status: 'Tight', message: 'Будет тесно' });
        totalScore -= 2;
      }
    } else {
      details.push({ zone: 'Грудь', status: 'OK', message: chestEase > 10 ? 'Оверсайз' : 'Свободно' });
    }
  }

  const waistEase = product.garment_waist - user.waist;
  if (waistEase < 2) {
    details.push({ zone: 'Талия', status: 'Tight', message: 'Тесно' });
    totalScore -= 1.5;
  } else {
    details.push({ zone: 'Талия', status: 'OK', message: 'Комфортно' });
  }

  const finalScore = Math.max(0, totalScore);
  let label: FitVerdict['label'] = 'Идеально';
  let color = 'bg-green-600';

  if (finalScore < 4.5 && finalScore >= 3.5) { label = 'Хорошо'; color = 'bg-blue-500'; }
  else if (finalScore < 3.5 && finalScore >= 2.5) { label = 'Туго'; color = 'bg-yellow-500'; }
  else if (finalScore < 2.5) { label = 'Не подходит'; color = 'bg-red-500'; }

  return { score: finalScore, label, color, details };
};
