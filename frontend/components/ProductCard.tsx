
import React from 'react';
import { MatchResult } from '../types';

export const ProductCard: React.FC<{ result: MatchResult }> = ({ result }) => {
  const { product, verdict } = result;

  return (
    <div className="bg-white rounded-3xl overflow-hidden shadow-sm border border-slate-100 hover:shadow-xl hover:shadow-slate-200/50 transition-all duration-300 group">
      <div className="relative aspect-[3/4] overflow-hidden bg-slate-100">
        <img 
          src={product.image_url} 
          className="w-full h-full object-cover group-hover:scale-110 transition-transform duration-700" 
          alt={product.name} 
        />
        <div className={`absolute top-4 left-4 ${verdict.color} text-white text-[10px] font-black uppercase tracking-widest px-4 py-1.5 rounded-full shadow-lg backdrop-blur-sm bg-opacity-90`}>
          {verdict.label}
        </div>
        <div className="absolute top-4 right-4 bg-white/90 backdrop-blur-md px-2 py-1 rounded-xl text-[10px] font-black text-slate-800 shadow-sm border border-white/20">
          {verdict.score.toFixed(1)} <span className="text-yellow-500">★</span>
        </div>
      </div>
      
      <div className="p-6 space-y-4">
        <div>
          <h3 className="font-bold text-slate-800 text-sm line-clamp-1">{product.name}</h3>
          <p className="text-[10px] text-slate-400 font-mono mt-0.5">{product.sku}</p>
        </div>

        <div className="space-y-2 border-t border-slate-50 pt-4">
          {verdict.details.map((d, i) => (
            <div key={i} className="flex items-center justify-between text-[11px]">
              <span className="text-slate-400 font-medium uppercase tracking-tighter">{d.zone}</span>
              <div className="flex items-center gap-1.5">
                <span className={`h-1.5 w-1.5 rounded-full ${
                  d.status === 'OK' ? 'bg-green-500' : 
                  d.status === 'Tight' ? 'bg-red-500' : 'bg-blue-500'
                }`} />
                <span className={`font-bold ${
                  d.status === 'OK' ? 'text-slate-700' : 
                  d.status === 'Tight' ? 'text-red-500' : 'text-blue-500'
                }`}>
                  {d.message}
                </span>
              </div>
            </div>
          ))}
        </div>

        <div className="flex gap-2 pt-2">
          <button className="flex-1 bg-slate-50 hover:bg-slate-100 text-slate-600 py-3 rounded-xl text-[10px] font-black uppercase tracking-wider transition-colors active:scale-95">
            👍 Подошло
          </button>
          <button className="flex-1 bg-slate-50 hover:bg-slate-100 text-slate-600 py-3 rounded-xl text-[10px] font-black uppercase tracking-wider transition-colors active:scale-95">
            👎 Не то
          </button>
        </div>
      </div>
    </div>
  );
};

export default ProductCard;
