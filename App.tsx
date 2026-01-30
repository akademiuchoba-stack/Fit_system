
import React from 'react';
import BodyMetricsForm from './components/BodyMetricsForm';
import ProductCard from './components/ProductCard';
import { UserParams, MatchResult } from './types';
import { MOCK_PRODUCTS } from './services/mockData';
import { calculateMatch } from './services/matchingAlgorithm';

const App: React.FC = () => {
  const [results, setResults] = React.useState<MatchResult[]>([]);
  const [hasSearched, setHasSearched] = React.useState(false);

  const handleSearch = (params: UserParams) => {
    // Perform "Ideal Ease" calculation
    const matches: MatchResult[] = MOCK_PRODUCTS.map(product => ({
      product,
      verdict: calculateMatch(params, product)
    }));

    // Sort by score (best fit first)
    matches.sort((a, b) => b.verdict.score - a.verdict.score);
    
    setResults(matches);
    setHasSearched(true);

    // Scroll to results
    setTimeout(() => {
      document.getElementById('results')?.scrollIntoView({ behavior: 'smooth' });
    }, 100);
  };

  return (
    <div className="min-h-screen pb-20">
      {/* Header */}
      <header className="bg-indigo-900 text-white pt-12 pb-24 px-6 relative overflow-hidden">
        <div className="absolute top-0 right-0 w-64 h-64 bg-indigo-500 opacity-20 rounded-full -translate-y-1/2 translate-x-1/2 blur-3xl"></div>
        <div className="max-w-4xl mx-auto relative z-10">
          <div className="flex items-center gap-3 mb-2">
            <div className="bg-white p-2 rounded-lg shadow-xl">
              <svg className="w-6 h-6 text-indigo-900" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12,2L4.5,20.29L5.21,21L12,18L18.79,21L19.5,20.29L12,2Z" />
              </svg>
            </div>
            <h1 className="text-2xl font-black tracking-tight">FIT_SYSTEM</h1>
          </div>
          <p className="text-indigo-100 text-sm opacity-80 max-w-lg">
            Умная примерка на базе алгоритма «Идеальный припуск». 
            Находим одежду в O'stin (ТРЦ Фестиваль, Ангарск), которая сядет на вас безупречно.
          </p>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-4xl mx-auto px-6 -mt-16 relative z-20">
        <BodyMetricsForm onSearch={handleSearch} />

        {hasSearched && (
          <div id="results" className="mt-12 space-y-8 animate-in fade-in slide-in-from-bottom-4 duration-700">
            <div className="flex items-center justify-between border-b border-slate-200 pb-4">
              <h2 className="text-xl font-bold text-slate-800">
                Результаты подбора <span className="text-indigo-500 text-sm ml-2 font-normal">Найдено {results.length} товаров</span>
              </h2>
              <div className="flex items-center gap-2 text-xs font-medium text-slate-500">
                <span className="w-3 h-3 rounded-full bg-green-500"></span> Идеально
                <span className="w-3 h-3 rounded-full bg-blue-500 ml-2"></span> Хорошо
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
              {results.map((res, index) => (
                <ProductCard key={res.product.sku} result={res} />
              ))}
            </div>

            {results.length === 0 && (
              <div className="text-center py-20">
                <div className="bg-slate-100 w-16 h-16 rounded-full flex items-center justify-center mx-auto mb-4 text-slate-400">
                   <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-8 h-8">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 15.75l-2.489-2.489m0 0a3.375 3.375 0 10-4.773-4.773 3.375 3.375 0 004.774 4.774zM21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
                <h3 className="text-lg font-bold text-slate-700">Ничего не найдено</h3>
                <p className="text-slate-500 text-sm">Попробуйте скорректировать параметры или выбрать другой размер.</p>
              </div>
            )}
          </div>
        )}
      </main>

      {/* Footer / Location Info */}
      <footer className="mt-20 border-t border-slate-200 bg-white py-12">
        <div className="max-w-4xl mx-auto px-6 flex flex-col md:flex-row items-center justify-between gap-6 text-slate-400 text-xs">
          <div className="flex flex-col gap-1">
            <p className="font-bold text-slate-600">Локация</p>
            <p>Ангарск, ТРЦ «Фестиваль»</p>
            <p>Магазин: O'stin</p>
          </div>
          <div className="text-center md:text-right">
            <p>© 2024 Fit_system MVP</p>
            <p>Proprietary Algorithm "Ideal Ease" v1.2</p>
            <p className="text-indigo-400 mt-2 font-medium">Защищено от копирования</p>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default App;
