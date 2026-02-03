
/**
 * Fit_system Frontend Logic
 * Handling UI state, API calls, and reactive rendering.
 */

interface FitResult {
    item_id: number;
    sku: string;
    name: string;
    image: string;
    platform: string;
    size: string;
    fit: {
        score: number;
        verdict: string;
        details: string;
        metrics_comparison: any;
    };
}

class FitApp {
    private currentUser: any = null;
    private results: FitResult[] = [];

    constructor() {
        this.initEventListeners();
    }

    private initEventListeners() {
        const form = document.getElementById('metrics-form') as HTMLFormElement;
        if (form) {
            form.onsubmit = async (e) => {
                e.preventDefault();
                await this.handleFormSubmit(form);
            };
        }
    }

    private async handleFormSubmit(form: HTMLFormElement) {
        const formData = new FormData(form);
        const data = Object.fromEntries(formData.entries());
        
        // Преобразование типов
        this.currentUser = {};
        for (let k in data) {
            this.currentUser[k] = (k !== 'name' && k !== 'gender') ? parseFloat(data[k] as string) : data[k];
        }

        try {
            const response = await fetch('/api/calculate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ user: this.currentUser })
            });

            if (!response.ok) throw new Error('Ошибка расчета');
            
            this.results = await response.json();
            this.renderResults();
        } catch (error) {
            alert('Не удалось связаться с сервером. Убедитесь, что Backend запущен.');
            console.error(error);
        }
    }

    private renderResults() {
        const grid = document.getElementById('results-grid');
        const inputSec = document.getElementById('input-section');
        const resultSec = document.getElementById('results-section');

        if (!grid || !inputSec || !resultSec) return;

        grid.innerHTML = '';
        this.results.forEach(res => {
            const card = document.createElement('div');
            card.className = 'bg-white rounded-3xl overflow-hidden shadow-sm hover:shadow-xl transition-all duration-300 transform hover:-translate-y-1 cursor-pointer border border-gray-100';
            card.onclick = () => this.openDetail(res);

            const scoreColor = res.fit.score > 85 ? 'bg-emerald-500' : (res.fit.score > 70 ? 'bg-amber-500' : 'bg-rose-500');

            card.innerHTML = `
                <div class="relative aspect-[3/4] overflow-hidden">
                    <img src="${res.image}" class="w-full h-full object-cover transition-transform duration-500 hover:scale-105" loading="lazy">
                    <div class="absolute top-4 right-4 ${scoreColor} text-white px-3 py-1 rounded-full text-[10px] font-bold uppercase tracking-widest shadow-lg">
                        ${res.fit.verdict}
                    </div>
                    <div class="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/60 to-transparent p-6 text-white">
                        <div class="text-[10px] opacity-80 font-bold uppercase">${res.platform}</div>
                        <div class="font-bold text-lg leading-tight truncate">${res.name}</div>
                    </div>
                </div>
                <div class="p-5">
                    <div class="flex items-center justify-between mb-3">
                        <span class="text-indigo-600 font-black text-xl">Размер ${res.size}</span>
                        <div class="flex flex-col items-end">
                            <span class="text-[10px] text-gray-400 font-bold uppercase">Fit Score</span>
                            <span class="text-lg font-mono font-bold ${res.fit.score > 70 ? 'text-gray-800' : 'text-rose-600'}">${res.fit.score}%</span>
                        </div>
                    </div>
                    <div class="w-full bg-gray-100 h-1.5 rounded-full overflow-hidden">
                        <div class="${scoreColor} h-full transition-all duration-1000" style="width: ${res.fit.score}%"></div>
                    </div>
                </div>
            `;
            grid.appendChild(card);
        });

        inputSec.classList.add('hidden');
        resultSec.classList.remove('hidden');
        window.scrollTo({ top: 0, behavior: 'smooth' });
    }

    public openDetail(res: FitResult) {
        const modal = document.getElementById('modal');
        const content = document.getElementById('modal-content');
        if (!modal || !content) return;

        content.innerHTML = `
            <div class="flex justify-between items-start mb-8">
                <div>
                    <h2 class="text-3xl font-black text-gray-900">${res.name}</h2>
                    <p class="text-gray-400 font-mono text-sm tracking-tighter uppercase mt-1">SKU: ${res.sku} | Location: Angarsk, Festival</p>
                </div>
                <button onclick="window.app.closeModal()" class="p-3 bg-gray-50 hover:bg-gray-100 rounded-full transition-colors">
                    <svg class="w-6 h-6 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path></svg>
                </button>
            </div>

            <div class="grid grid-cols-1 md:grid-cols-2 gap-10">
                <div class="space-y-4">
                    <img src="${res.image}" class="w-full rounded-3xl shadow-2xl border border-gray-100">
                    <div class="p-6 bg-indigo-50 rounded-2xl border border-indigo-100">
                        <h4 class="text-indigo-900 font-bold text-sm uppercase mb-2">Технический Вердикт</h4>
                        <p class="text-indigo-700 leading-relaxed">${res.fit.details}</p>
                    </div>
                </div>
                
                <div class="flex flex-col h-full">
                    <h3 class="font-black text-gray-400 uppercase text-[11px] tracking-widest mb-6">Computational Geometry Analysis</h3>
                    <div class="space-y-6 flex-grow">
                        ${this.renderMetricRow('Полуобхват груди (Вещь)', res.fit.metrics_comparison.garment_chest, 'см')}
                        ${this.renderMetricRow('Ваш полуобхват (Тело)', res.fit.metrics_comparison.user_chest_half, 'см', true)}
                        ${this.renderMetricRow('Рукав (Dropped Shoulder Corr.)', res.fit.metrics_comparison.effective_sleeve, 'см')}
                        ${this.renderMetricRow('Ваша длина руки', res.fit.metrics_comparison.user_arm, 'см', true)}
                    </div>

                    <div class="mt-10 pt-8 border-t border-gray-100">
                        <h3 class="font-bold text-gray-900 mb-4">Байесовская калибровка</h3>
                        <p class="text-xs text-gray-500 mb-6 leading-relaxed">Ваш отзыв поможет алгоритму точнее рассчитывать посадку для жителей Ангарска.</p>
                        <div class="grid grid-cols-3 gap-3">
                            <button onclick="window.app.submitFeedback(${res.item_id}, '${res.size}', 0)" class="flex flex-col items-center py-4 bg-emerald-50 text-emerald-700 rounded-2xl border-2 border-transparent hover:border-emerald-500 transition-all group">
                                <span class="text-2xl mb-1 group-hover:scale-125 transition-transform">🎯</span>
                                <span class="text-[10px] font-bold uppercase">В точку</span>
                            </button>
                            <button onclick="window.app.submitFeedback(${res.item_id}, '${res.size}', 1)" class="flex flex-col items-center py-4 bg-amber-50 text-amber-700 rounded-2xl border-2 border-transparent hover:border-amber-500 transition-all group">
                                <span class="text-2xl mb-1 group-hover:scale-125 transition-transform">🤏</span>
                                <span class="text-[10px] font-bold uppercase">Маловато</span>
                            </button>
                            <button onclick="window.app.submitFeedback(${res.item_id}, '${res.size}', -1)" class="flex flex-col items-center py-4 bg-rose-50 text-rose-700 rounded-2xl border-2 border-transparent hover:border-rose-500 transition-all group">
                                <span class="text-2xl mb-1 group-hover:scale-125 transition-transform">🧥</span>
                                <span class="text-[10px] font-bold uppercase">Велико</span>
                            </button>
                        </div>
                        <div class="mt-6">
                            <label class="block text-[10px] font-bold text-gray-400 uppercase mb-2">Уточнить замер (опционально)</label>
                            <input id="real-chest" type="number" step="0.5" class="w-full p-3 bg-gray-50 border-none rounded-xl focus:ring-2 focus:ring-indigo-500" placeholder="Введите реальную ширину в см...">
                        </div>
                    </div>
                </div>
            </div>
        `;
        modal.classList.remove('hidden');
        document.body.style.overflow = 'hidden';
    }

    private renderMetricRow(label: string, value: number, unit: string, isUser: boolean = false) {
        return `
            <div class="flex items-end justify-between border-b border-gray-50 pb-3">
                <span class="text-sm ${isUser ? 'text-gray-400' : 'text-gray-600 font-medium'}">${label}</span>
                <span class="font-mono text-lg font-bold ${isUser ? 'text-gray-400' : 'text-indigo-600'}">${value}${unit}</span>
            </div>
        `;
    }

    public closeModal() {
        document.getElementById('modal')?.classList.add('hidden');
        document.body.style.overflow = 'auto';
    }

    public async submitFeedback(itemId: number, size: string, judgment: number) {
        const realChest = (document.getElementById('real-chest') as HTMLInputElement)?.value;
        const payload = {
            garment_id: itemId,
            user_id: this.currentUser?.name || "anonymous",
            size_selected: size,
            judgment: judgment,
            real_measurements: realChest ? { chest: parseFloat(realChest) } : null
        };

        try {
            await fetch('/api/feedback', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            alert('Данные приняты. Алгоритм откалиброван!');
            this.closeModal();
        } catch (e) {
            console.error(e);
        }
    }

    public showInput() {
        document.getElementById('input-section')?.classList.remove('hidden');
        document.getElementById('results-section')?.classList.add('hidden');
        document.getElementById('admin-section')?.classList.add('hidden');
    }

    public showAdmin() {
        document.getElementById('input-section')?.classList.add('hidden');
        document.getElementById('results-section')?.classList.add('hidden');
        document.getElementById('admin-section')?.classList.remove('hidden');
    }

    public async updateDB() {
        const status = document.getElementById('admin-status');
        if (status) status.innerText = 'Запуск кластеризации и парсинга...';
        const response = await fetch('/api/admin/update-db', { method: 'POST' });
        const data = await response.json();
        if (status) status.innerText = data.status;
    }
}

// Global exposure for HTML onclicks
(window as any).app = new FitApp();
(window as any).showInput = () => (window as any).app.showInput();
(window as any).showAdmin = () => (window as any).app.showAdmin();
(window as any).updateDB = () => (window as any).app.updateDB();
