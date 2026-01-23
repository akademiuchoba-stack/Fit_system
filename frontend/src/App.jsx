import { useState } from 'react'

function App() {
  // Состояние для поиска
  const [query, setQuery] = useState("джинсы");
  
  // Состояние для размеров пользователя (по умолчанию - Модель Мария)
  const [measurements, setMeasurements] = useState({
    waist: 66,
    hip: 91,
    leg_length: 99,
    shoulder: 38
  });

  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);

  const handleSearch = async () => {
    setLoading(true);
    try {
      // ⚠️ ВСТАВЬТЕ СЮДА ВАШ IP
      const response = await fetch('http://109.73.193.225:5000/api/recommend', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
            query: query, 
            maxPrice: 10000,
            userMeasurements: measurements // ОТПРАВЛЯЕМ РАЗМЕРЫ
        })
      });
      const data = await response.json();
      setResults(data);
    } catch (error) {
      alert("Ошибка. Проверьте консоль.");
    }
    setLoading(false);
  };

  // Функция для обновления конкретного размера
  const updateMeasure = (key, value) => {
    setMeasurements(prev => ({ ...prev, [key]: Number(value) }));
  };

  return (
    <div style={{ maxWidth: '1000px', margin: '0 auto', padding: '20px', fontFamily: 'Arial', display: 'flex', gap: '40px' }}>
      
      {/* ЛЕВАЯ КОЛОНКА: Профиль пользователя */}
      <div style={{ flex: '0 0 250px', background: '#f8f9fa', padding: '20px', borderRadius: '10px', height: 'fit-content' }}>
        <h2>📏 Мои размеры</h2>
        <div style={{ marginBottom: '15px' }}>
          <label>Талия (см):</label>
          <input type="number" value={measurements.waist} onChange={(e) => updateMeasure('waist', e.target.value)} style={{ width: '100%', padding: '5px' }} />
        </div>
        <div style={{ marginBottom: '15px' }}>
          <label>Бёдра (см):</label>
          <input type="number" value={measurements.hip} onChange={(e) => updateMeasure('hip', e.target.value)} style={{ width: '100%', padding: '5px' }} />
        </div>
        <div style={{ marginBottom: '15px' }}>
          <label>Длина ноги (см):</label>
          <input type="number" value={measurements.leg_length} onChange={(e) => updateMeasure('leg_length', e.target.value)} style={{ width: '100%', padding: '5px' }} />
        </div>
        <div style={{ marginBottom: '15px' }}>
          <label>Плечи (см):</label>
          <input type="number" value={measurements.shoulder} onChange={(e) => updateMeasure('shoulder', e.target.value)} style={{ width: '100%', padding: '5px' }} />
        </div>
      </div>

      {/* ПРАВАЯ КОЛОНКА: Поиск и результаты */}
      <div style={{ flex: 1 }}>
        <h1>👖 Fit System MVP</h1>
        
        <div style={{ display: 'flex', gap: '10px', marginBottom: '20px' }}>
          <input 
            type="text" 
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            style={{ flex: 1, padding: '10px', fontSize: '16px' }}
          />
          <button 
            onClick={handleSearch}
            style={{ padding: '10px 20px', background: '#007bff', color: 'white', border: 'none', cursor: 'pointer', fontSize: '16px' }}
          >
            {loading ? "Примеряем..." : "Подобрать"}
          </button>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))', gap: '20px' }}>
          {results.map((item) => (
            <div key={item.id} style={{ border: '1px solid #ddd', padding: '15px', borderRadius: '8px' }}>
              <h3>{item.name}</h3>
              <p style={{ fontWeight: 'bold' }}>{item.price} ₽</p>
              
              {/* Блок результата примерки */}
              <div style={{ 
                background: item.fit_result.includes("ПОДХОДИТ") ? '#d4edda' : '#f8d7da', 
                padding: '10px', 
                borderRadius: '5px', 
                marginTop: '10px',
                border: item.fit_result.includes("ПОДХОДИТ") ? '1px solid #c3e6cb' : '1px solid #f5c6cb'
              }}>
                <b style={{ color: item.fit_result.includes("ПОДХОДИТ") ? '#155724' : '#721c24' }}>
                    {item.fit_result}
                </b>
                <div style={{ fontSize: '13px', marginTop: '5px' }}>{item.fit_details}</div>
              </div>

              <a href={item.link} target="_blank" style={{ display: 'block', marginTop: '10px', color: 'blue', textDecoration: 'none' }}>
                Купить в магазине →
              </a>
            </div>
          ))}
        </div>
      </div>

    </div>
  )
}

export default App