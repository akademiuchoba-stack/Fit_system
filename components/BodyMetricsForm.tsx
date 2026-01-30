
import React from 'react';
import { UserParams } from '../types';

interface Props {
  onSearch: (params: UserParams) => void;
}

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

  const InputField = ({ label, name, value, unit = 'см' }: any) => (
    <div className="flex flex-col">
      <label className="text-xs font-semibold text-slate-500 uppercase mb-1">{label}</label>
      <div className="relative">
        <input
          type="number"
          name={name}
          value={value}
          onChange={handleChange}
          className="w-full bg-white border border-slate-200 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-indigo-500 outline-none transition-all"
        />
        <span className="absolute right-3 top-2 text-slate-400 text-xs">{unit}</span>
      </div>
    </div>
  );

  return (
    <form onSubmit={handleSubmit} className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 space-y-6">
      <div className="flex items-center justify-between mb-4 border-b border-slate-50 pb-4">
        <h2 className="text-xl font-bold text-slate-800">Ваши параметры</h2>
        <select 
          name="gender" 
          value={params.gender} 
          onChange={handleChange}
          className="bg-slate-50 border-none text-sm font-medium rounded-full px-4 py-1 text-slate-600 focus:ring-0"
        >
          <option value="male">Мужской</option>
          <option value="female">Женский</option>
        </select>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <InputField label="Рост" name="height" value={params.height} />
        <InputField label="Обхват груди" name="chest" value={params.chest} />
        <InputField label="Обхват талии" name="waist" value={params.waist} />
        <InputField label="Обхват бедер" name="hips" value={params.hips} />
        <InputField label="Плечи" name="shoulders" value={params.shoulders} />
        <InputField label="Длина руки" name="armLength" value={params.armLength} />
        <InputField label="Внутр. шов" name="inseam" value={params.inseam} />
      </div>

      <button
        type="submit"
        className="w-full bg-indigo-600 hover:bg-indigo-700 text-white font-bold py-3 px-6 rounded-xl transition-colors shadow-lg shadow-indigo-200 flex items-center justify-center gap-2"
      >
        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-5 h-5">
          <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
        </svg>
        Найти в магазине O'stin
      </button>
    </form>
  );
};

export default BodyMetricsForm;
