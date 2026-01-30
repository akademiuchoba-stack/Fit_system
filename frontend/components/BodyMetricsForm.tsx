
import React from 'react';
import { UserParams } from '../types';

interface Props {
  onSearch: (params: UserParams) => void;
}

interface MeasurementDetail {
  label: string;
  description: string;
}

const MEASUREMENT_INFO: Record<string, MeasurementDetail> = {
  height: {
    label: 'Рост',
    description: 'Измеряется стоя ровно, от макушки до пола без обуви.'
  },
  chest: {
    label: 'Обхват груди',
    description: 'Сантиметровая лента проходит горизонтально по самым выступающим точкам груди и лопаткам.'
  },
  waist: {
    label: 'Обхват талии',
    description: 'По самому узкому месту туловища. Не втягивайте живот при замере.'
  },
  hips: {
    label: 'Обхват бедер',
    description: 'Лента проходит горизонтально по наиболее выступающим точкам ягодиц.'
  },
  shoulders: {
    label: 'Ширина плеч',
    description: 'Расстояние между крайними точками плечевых суставов по спине.'
  },
  armLength: {
    label: 'Длина руки',
    description: 'От плечевого сустава через локоть до запястья (рука слегка согнута).'
  },
  inseam: {
    label: 'Внутр. шов',
    description: 'Длина от пахового шва до пола по внутренней стороне ноги.'
  }
};

const BodyMetricsForm: React.FC<Props> = ({ onSearch }) => {
  const [params, setParams] = React.useState<UserParams>({
    gender: 'male',
    height: 180,
    chest: 100,
    waist: 85,
    hips: 100,
    shoulders: 46,
    armLength: 62,
    inseam: 80,
  });

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setParams(prev => ({
      ...prev,
      [name]: name === 'gender' ? value : Number(value)
    }));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    onSearch(params);
  };

  const InputField = ({ name, info }: { name: string, info: MeasurementDetail }) => (
    <div className="flex flex-col">
      <div className="flex items-center gap-1.5 mb-1.5 px-1">
        <label className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">
          {info.label}
        </label>
        <div className="group relative cursor-help">
          <div className="w-3.5 h-3.5 rounded-full border border-slate-300 flex items-center justify-center text-[8px] font-bold text-slate-400 group-hover:border-indigo-400 group-hover:text-indigo-500 transition-colors">
            ?
          </div>
          <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-48 p-2 bg-slate-800 text-white text-[10px] rounded-lg opacity-0 pointer-events-none group-hover:opacity-100 transition-opacity z-50 shadow-xl leading-relaxed">
            {info.description}
            <div className="absolute top-full left-1/2 -translate-x-1/2 border-8 border-transparent border-t-slate-800"></div>
          </div>
        </div>
      </div>
      <div className="relative">
        <input
          type="number"
          name={name}
          value={(params as any)[name]}
          onChange={handleChange}
          className="w-full bg-white border border-slate-200 rounded-xl px-4 py-3 text-sm font-bold text-slate-800 focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none transition-all duration-200"
        />
        <span className="absolute right-4 top-3.5 text-slate-400 text-[10px] font-bold">СМ</span>
      </div>
    </div>
  );

  return (
    <form onSubmit={handleSubmit} className="bg-white p-8 rounded-3xl shadow-xl shadow-slate-200/50 border border-white space-y-8">
      <div className="flex items-center justify-between border-b border-slate-50 pb-6">
        <div>
          <h2 className="text-2xl font-black text-slate-800 tracking-tight">Ваши замеры</h2>
          <p className="text-slate-400 text-xs mt-1">Используйте сантиметровую ленту для точности</p>
        </div>
        <div className="bg-slate-100 p-1 rounded-xl flex gap-1">
          {(['male', 'female'] as const).map((g) => (
            <button
              key={g}
              type="button"
              onClick={() => setParams(p => ({ ...p, gender: g }))}
              className={`px-4 py-2 rounded-lg text-xs font-bold transition-all ${
                params.gender === g 
                ? 'bg-white text-indigo-600 shadow-md' 
                : 'text-slate-500 hover:text-slate-700'
              }`}
            >
              {g === 'male' ? 'Мужчина' : 'Женщина'}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-x-4 gap-y-6">
        {Object.entries(MEASUREMENT_INFO).map(([key, info]) => (
          <InputField 
            key={key} 
            name={key} 
            info={info} 
          />
        ))}
      </div>

      <button
        type="submit"
        className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-black py-4 px-8 rounded-2xl transition-all shadow-lg shadow-indigo-100 hover:shadow-indigo-200 active:scale-[0.98] flex items-center justify-center gap-3"
      >
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor" className="w-5 h-5">
          <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
        </svg>
        Найти мой размер в O'stin
      </button>
    </form>
  );
};

export default BodyMetricsForm;
