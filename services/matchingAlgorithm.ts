
import { UserParams, Product, FitVerdict, Category } from '../types';
import { IDEAL_EASE_NORMS } from '../constants';

/**
 * CORE PROPRIETARY ALGORITHM
 * Protected Logic: This would typically reside on the backend.
 * Implementing here for the MVP frontend demonstration.
 */
export const calculateMatch = (user: UserParams, product: Product): FitVerdict => {
  const details: FitVerdict['details'] = [];
  let totalScore = 5;

  // 1. Calculate Effective Ease (A_eff) for Chest
  const chestEase = product.garment_chest - user.chest;
  const isStretch = product.elasticity_percent > 3;
  
  // Stretch logic (Negative Ease)
  const stretchFactor = product.elasticity_percent / 100;
  const maxStretchComfort = user.chest * (1 + stretchFactor * 0.5); // 50% of total stretch is comfortable
  
  if (product.category === Category.UPPER) {
    if (chestEase >= IDEAL_EASE_NORMS.CHEST.min && chestEase <= IDEAL_EASE_NORMS.CHEST.max) {
      details.push({ zone: 'Грудь', status: 'OK', message: 'Идеальный объем' });
    } else if (chestEase < 0) {
      if (isStretch && product.garment_chest >= user.chest * 0.95) {
        details.push({ zone: 'Грудь', status: 'Slim', message: 'Плотная посадка (Stretch)' });
        totalScore -= 0.5;
      } else {
        details.push({ zone: 'Грудь', status: 'Tight', message: 'Будет тесно в груди' });
        totalScore -= 2;
      }
    } else if (chestEase > IDEAL_EASE_NORMS.CHEST.max + 10) {
      details.push({ zone: 'Грудь', status: 'Loose', message: 'Сильный оверсайз' });
      totalScore -= 1;
    } else {
      details.push({ zone: 'Грудь', status: 'OK', message: 'Свободно' });
    }
  }

  // 2. Calculate Waist Ease
  const waistEase = product.garment_waist - user.waist;
  if (waistEase < 2) {
    details.push({ zone: 'Талия', status: 'Tight', message: 'Тесно в поясе' });
    totalScore -= 1.5;
  } else if (waistEase > 15) {
    details.push({ zone: 'Талия', status: 'Loose', message: 'Потребуется ремень' });
    totalScore -= 0.5;
  } else {
    details.push({ zone: 'Талия', status: 'OK', message: 'Комфортно' });
  }

  // 3. Height / Sleeves
  if (product.category === Category.UPPER) {
    const sleeveDiff = product.sleeve_length - user.armLength;
    if (Math.abs(sleeveDiff) < 2) {
      details.push({ zone: 'Рукав', status: 'OK', message: 'Идеальная длина' });
    } else if (sleeveDiff < -3) {
      details.push({ zone: 'Рукав', status: 'Short', message: 'Рукав коротковат' });
      totalScore -= 1;
    } else {
      details.push({ zone: 'Рукав', status: 'OK', message: 'ОК' });
    }
  } else {
    // Lower category - Inseam
    const inseamDiff = product.inseam - user.inseam;
    if (Math.abs(inseamDiff) < 3) {
      details.push({ zone: 'Длина', status: 'OK', message: 'Подшивать не нужно' });
    } else if (inseamDiff < -4) {
      details.push({ zone: 'Длина', status: 'Short', message: 'Короткие брюки' });
      totalScore -= 2.5;
    } else if (inseamDiff > 5) {
      details.push({ zone: 'Длина', status: 'Long', message: 'Длинные, нужно подшить' });
      totalScore -= 0.5;
    }
  }

  // Final Logic
  const finalScore = Math.max(0, totalScore);
  let label: FitVerdict['label'] = 'Идеально';
  let color = 'bg-green-500';

  if (finalScore >= 4.5) { label = 'Идеально'; color = 'bg-green-600'; }
  else if (finalScore >= 3.5) { label = 'Хорошо'; color = 'bg-blue-500'; }
  else if (finalScore >= 2.5) { label = 'Туго'; color = 'bg-yellow-500'; }
  else if (finalScore >= 1.5) { label = 'Велико'; color = 'bg-orange-500'; }
  else { label = 'Не подходит'; color = 'bg-red-500'; }

  return { score: finalScore, label, color, details };
};
