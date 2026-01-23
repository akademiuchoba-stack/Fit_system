import { useState } from 'react'

function App() {
  const [query, setQuery] = useState("джинсы");
  // Тестовые размеры (Рост 175, Нога 82, Талия 70)
  const [measurements, setMeasurements] = useState({
    waist: 70, hip: 96, leg_length: 82, height: 175
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
        body: JSON.stringify({ query, maxPrice: 10000, userMeasurements: measurements })
      });
      const data = await response.json();
      setResults(data);
    } catch (error) { alert("Ошибка сети"); }
    setLoading(false);
  };

  const updateMeasure = (key, val) => setMeasurements(p => ({ ...p, [key]: Number(val) }));

  return (
    <div style={{ maxWidth: '900px', margin: '0 auto', padding: '20px', fontFamily: 'Arial', display: 'flex', gap: '20px' }}>
      
      {/* ЛЕВО: Размеры */}
      <div style={{ flex: '0 0 200px', background: '#f4f4f4', padding: '15px', borderRadius: '8px', height: 'fit-content' }}>
        <h3>📏 Мои замеры</h3>
        <label>Рост (см): <input type="number" value={measurements.height} onChange={(e)=>updateMeasure('height',e.target.value)} style={{width:'100%'}} /></label>
        <br/><br/>
        <label>Талия (см): <input type="number" value={measurements.waist} onChange={(e)=>updateMeasure('waist',e.target.value)} style={{width:'100%'}} /></label>
        <br/><br/>
        <label>Дл. ноги (см): <input type="number" value={measurements.leg_length} onChange={(e)=>updateMeasure('leg_length',e.target.value)} style={{width:'100%'}} /></label>
      </div>

      {/* ПРАВО: Выдача */}
      <div style={{ flex: 1 }}>
        <div style={{ display: 'flex', gap: '10px', marginBottom: '20px' }}>
          <input type="text" value={query} onChange={(e) => setQuery(e.target.value)} style={{ flex: 1, padding: '10px' }} />
          <button onClick={handleSearch} style={{ padding: '10px 20px', background: '#007bff', color: 'white', border: 'none' }}>
            {loading ? "..." : "Найти"}
          </button>
        </div>

        <div style={{ display: 'grid', gap: '20px' }}>
          {results.map((item) => (
            <div key={item.id} style={{ border: '1px solid #ddd', padding: '15px', borderRadius: '8px', display: 'flex', gap: '20px' }}>
              <div style={{flex: '0 0 100px', background: '#eee', height: '100px'}}></div>
              
              <div style={{ flex: 1 }}>
                <h3 style={{margin: '0 0 5px 0'}}>{item.brand} / {item.name}</h3>
                
                {/* Результат примерки */}
                <div style={{ 
                  background: item.fit_result.includes("ПОДХОДИТ") ? '#d4edda' : '#f8d7da', 
                  padding: '5px 10px', borderRadius: '4px', display: 'inline-block', marginBottom: '10px' 
                }}>
                  <b>{item.fit_result}</b> <small>{item.fit_details}</small>
                </div>

                {/* СПИСОК МАГАЗИНОВ */}
                <div style={{ background: '#f9f9f9', padding: '10px', borderRadius: '5px' }}>
                    <small style={{color: '#666'}}>Где купить:</small>
                    {item.offers.map((offer, idx) => (
                        <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', padding: '5px 0', borderBottom: '1px solid #eee' }}>
                            <a href={offer.link} target="_blank" style={{ color: '#007bff' }}>
                                {offer.shop_name} ({offer.delivery_days} дн.)
                            </a>
                            <b style={{ color: idx === 0 ? 'green' : 'black' }}>{offer.price} ₽</b>
                        </div>
                    ))}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
export default App