
import React from 'react';
import BodyMetricsForm from './components/BodyMetricsForm';
import ProductCard from './components/ProductCard';
import { UserParams, MatchResult } from './types';
import { STORE_INVENTORY } from '../shops/angarsk_festival';
import { calculateMatch } from '../backend/matchingAlgorithm';

const App: React.FC = () => {
  const [results, setResults] = React.useState<MatchResult[]>([]);
  const [hasSearched, setHasSearched] = React.useState(false);
  const [isLoading, setIsLoading] = React.useState(false);

  const handleSearch = async (params: UserParams) => {
    setIsLoading(true);
    setHasSearched(true);
    
    // Имитация "умного" анализа на сервере
    await new Promise(resolve => setTimeout(resolve, 1500));

    try {
      // Здесь в будущем будет fetch к вашему FastAPI на Timeweb
      const matches: MatchResult[] = STORE_INVENTORY.map(product => ({
        product,
        verdict: calculateMatch(params, product)
      }));
      
      matches.sort((a, b) => b.verdict.score - a.verdict.score);
      setResults(matches);
    } catch (error) {
      console.error("Ошибка API:", error);
    } finally {
      setIsLoading(false);
      setTimeout(() => {
        document.getElementById('results-section')?.scrollIntoView({ behavior: 'smooth' });
      }, 100);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 pb-20 font-sans selection:bg-indigo-100">
      <header className="bg-indigo-950 text-white pt-16 pb-32 relative overflow-hidden">
        <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-indigo-500/10 blur-[120px] rounded-full translate-x-1/2 -translate-y-1/2"></div>
        <div className="max-w-4xl mx-auto px-6 relative z-10">
          <div className="flex items-center gap-4 mb-6">
            <div className="bg-white p-2.5 rounded-2xl shadow-2xl shadow-indigo-500/20 rotate-3">
              <svg className="w-8 h-8 text-indigo-950" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12,2L4.5,20.29L5.21,21L12,18L18.79,21L19.5,20.29L12,2Z" />
              </svg>
            </div>
            <div>
              <h1 className="text-3xl font-black tracking-tighter">FIT_SYSTEM</h1>
              <p className="text-indigo-400 text-[10px] font-bold uppercase tracking-[0.2em] mt-1">Angarsk • Festival Mall</p>
            </div>
          </div>
          <h2 className="text-4xl font-bold leading-tight max-w-xl">
             Найдите свой идеальный размер за 30 секунд.
          </h2>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-6 -mt-20 relative z-20">
        <BodyMetricsForm onSearch={handleSearch} />

        {hasSearched && (
          <section id="results-section" className="mt-16 space-y-12">
            <div className="flex items-end justify-between border-b border-slate-200 pb-6">
              <div>
                <h3 className="text-2xl font-black text-slate-800 tracking-tight">Ваш умный гардероб</h3>
                <p className="text-slate-400 text-xs mt-1">
                  {isLoading ? 'Алгоритм "Идеальный припуск" анализирует наличие...' : `Подобрано специально для вас: ${results.length} моделей`}
                </p>
              </div>
            </div>

            {isLoading ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-8">
                {[1, 2].map(i => (
                  <div key={i} className="bg-white h-[450px] rounded-3xl animate-pulse border border-slate-100 shadow-sm"></div>
                ))}
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-8">
                {results.map((res) => (
                  <ProductCard key={res.product.sku} result={res} />
                ))}
              </div>
            )}
          </section>
        )}
      </main>

      <footer className="mt-40 py-16 border-t border-slate-200 bg-white">
        <div className="max-w-4xl mx-auto px-6 flex flex-col md:flex-row justify-between items-center gap-8 text-slate-400 text-[11px] font-bold uppercase tracking-widest">
          <div className="text-center md:text-left">
            <p className="text-slate-800 mb-1">Fit_system MVP v1.2</p>
            <p>O'stin Inventory: Festival Mall, Angarsk</p>
          </div>
          <div className="flex gap-8">
             <span className="text-green-500">Backend Secured</span>
             <span className="text-indigo-500">Timeweb Cloud Deployment</span>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default App;
