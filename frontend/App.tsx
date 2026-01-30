import React from 'react';
import BodyMetricsForm from './components/BodyMetricsForm';
import ProductCard from './components/ProductCard';
import { UserParams, MatchResult } from './types';

// В продакшене URL будет браться из конфига или окружения
// Для локальной разработки Docker Compose это обычно localhost:8000
const API_BASE_URL = 'http://localhost:8000';

const App: React.FC = () => {
  const [results, setResults] = React.useState<MatchResult[]>([]);
  const [hasSearched, setHasSearched] = React.useState(false);
  const [isLoading, setIsLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const handleSearch = async (params: UserParams) => {
    setIsLoading(true);
    setHasSearched(true);
    setError(null);
    
    try {
      const response = await fetch(`${API_BASE_URL}/api/search`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(params),
      });

      if (!response.ok) {
        throw new Error(`Ошибка сервера: ${response.status}`);
      }

      const data = await response.json();
      setResults(data);
    } catch (err) {
      console.error("Ошибка при поиске:", err);
      setError("Не удалось соединиться с сервером. Проверьте запуск бэкенда.");
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

            {error && (
              <div className="bg-red-50 border border-red-100 text-red-600 p-4 rounded-2xl text-sm font-medium flex items-center gap-3">
                <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
                  <path fillRule="evenodd" d="M9.401 3.003c1.155-2 4.043-2 5.197 0l7.355 12.748c1.154 2-.29 4.5-2.599 4.5H4.645c-2.309 0-3.752-2.5-2.598-4.5L9.4 3.003zM12 8.25a.75.75 0 01.75.75v3.75a.75.75 0 01-1.5 0V9a.75.75 0 01.75-.75zm0 8.25a.75.75 0 100-1.5.75.75 0 000 1.5z" clipRule="evenodd" />
                </svg>
                {error}
              </div>
            )}

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

            {!isLoading && !error && results.length === 0 && (
              <div className="text-center py-20 bg-white rounded-3xl border border-slate-100">
                <p className="text-slate-400 font-medium">К сожалению, ничего не подошло под ваши параметры.</p>
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
