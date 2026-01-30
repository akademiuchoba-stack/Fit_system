
import React from 'react';
import { MatchResult } from '../types';
import { Icons } from '../constants';

interface Props {
  result: MatchResult;
}

const ProductCard: React.FC<Props> = ({ result }) => {
  const { product, verdict } = result;

  return (
    <div className="bg-white rounded-2xl overflow-hidden shadow-sm border border-slate-100 hover:shadow-md transition-shadow group">
      <div className="relative aspect-[4/5] overflow-hidden">
        <img 
          src={product.image_url} 
          alt={product.name}
          className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
        />
        <div className={`absolute top-4 left-4 ${verdict.color} text-white text-[10px] font-bold uppercase px-3 py-1 rounded-full shadow-lg`}>
          {verdict.label}
        </div>
        <div className="absolute top-4 right-4 bg-white/90 backdrop-blur-sm p-1 rounded-lg text-xs font-bold shadow-sm">
          {verdict.score.toFixed(1)} <span className="text-yellow-500">★</span>
        </div>
      </div>

      <div className="p-4 space-y-3">
        <div>
          <h3 className="font-bold text-slate-800 line-clamp-1">{product.name}</h3>
          <p className="text-[10px] text-slate-400 font-mono">{product.sku}</p>
        </div>

        <div className="space-y-1.5 border-t border-slate-50 pt-3">
          {verdict.details.map((detail, idx) => (
            <div key={idx} className="flex items-center justify-between text-xs">
              <span className="text-slate-500">{detail.zone}:</span>
              <span className={`font-medium ${
                detail.status === 'OK' ? 'text-green-600' : 
                detail.status === 'Tight' ? 'text-red-500' : 'text-blue-500'
              }`}>
                {detail.message}
              </span>
            </div>
          ))}
        </div>

        <div className="flex gap-2 pt-2">
          <button className="flex-1 bg-slate-50 hover:bg-slate-100 text-slate-700 py-2 rounded-lg text-xs font-semibold transition-colors">
            👍 Подошло
          </button>
          <button className="flex-1 bg-slate-50 hover:bg-slate-100 text-slate-700 py-2 rounded-lg text-xs font-semibold transition-colors">
            👎 Нет
          </button>
        </div>
      </div>
    </div>
  );
};

export default ProductCard;
