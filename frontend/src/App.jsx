import { useState } from 'react'

function App() {
  const [query, setQuery] = useState("джинсы");
  
  const [measurements, setMeasurements] = useState({
    waist: 70, hip: 96, leg_length: 82, height: 175
  });

  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [isModel, setIsModel] = useState(false); // Статус модели

  const handleSearch = async () => {
    setLoading(true);
    try {
      // ⚠️ ВСТАВЬТЕ СЮДА ВАШ IP
      const response = await fetch('http://ВАШ_IP_АДРЕС:5000/api/recommend', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, maxPrice: 10000, userMeasurements: measurements })
      });
      const data = await response.json();
      setResults(data);
    } catch (error) { alert("Ошибка сети"); }
    setLoading(false);
  };

  // Логика "Стать моделью"
  const handleBecomeModel = async (e) => {
    const checked = e.target.checked;
    setIsModel(checked);
    if (checked) {
        try {
            // ⚠️ ВСТАВЬТЕ СЮДА ВАШ IP
            await fetch('http://109.73.193.225:5000/api/become-model', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ measurements })
            });
            alert("Спасибо! Ваши данные помогут другим пользователям.");
        } catch (error) { alert("Ошибка сохранения"); }
    }
  };

  const updateMeasure = (key, val) => setMeasurements(p => ({ ...p, [key]: Number(val) }));

  return (
    <div style={{ maxWidth: '1000px', margin: '0 auto', padding: '20px', fontFamily: 'Arial', display: 'flex', gap: '30px' }}>
      
      {/* ЛЕВАЯ ПАНЕЛЬ */}
      <div style={{ flex: '0 0 250px' }}>
        <div style={{ background: '#f8f9fa', padding: '20px', borderRadius: '10px', marginBottom: '20px' }}>
          <h3>📏 Мои замеры</h3>
          <div style={{marginBottom: '10px'}}><label>Рост:</label><input type="number" value={measurements.height} onChange={(e)=>updateMeasure('height',e.target.value)} style={{width:'100%'}} /></div>
          <div style={{marginBottom: '10px'}}><label>Талия:</label><input type="number" value={measurements.waist} onChange={(e)=>updateMeasure('waist',e.target.value)} style={{width:'100%'}} /></div>
          <div style={{marginBottom: '10px'}}><label>Ноги (внутр):</label><input type="number" value={measurements.leg_length} onChange={(e)=>updateMeasure('leg_length',e.target.value)} style={{width:'100%'}} /></div>
        </div>

        {/* КНОПКА "ХОЧУ БЫТЬ МОДЕЛЬЮ" */}
        <div style={{ 
            background: isModel ? '#d4edda' : '#e9ecef', 
            padding: '15px', borderRadius: '10px', border: isModel ? '1px solid green' : '1px solid #ccc' 
        }}>
            <label style={{display:'flex', alignItems:'center', cursor:'pointer', fontWeight:'bold'}}>
                <input type="checkbox" checked={isModel} onChange={handleBecomeModel} style={{width:'20px', height:'20px', marginRight:'10px'}} />
                Хочу быть моделью
            </label>
            <p style={{fontSize:'12px', color:'#555', marginTop:'5px'}}>
                {isModel ? "Вы помогаете улучшать алгоритм!" : "Анонимно поделиться замерами для статистики."}
            </p>
        </div>
      </div>

      {/* ПРАВАЯ ПАНЕЛЬ */}
      <div style={{ flex: 1 }}>
        <div style={{ display: 'flex', gap: '10px', marginBottom: '20px' }}>
          <input type="text" value={query} onChange={(e) => setQuery(e.target.value)} style={{ flex: 1, padding: '10px' }} />
          <button onClick={handleSearch} style={{ padding: '10px 20px', background: '#007bff', color: 'white', border: 'none' }}>Подобрать</button>
        </div>

        <div style={{ display: 'grid', gap: '20px' }}>
          {results.map((item) => (
            <div key={item.id} style={{ border: '1px solid #ddd', padding: '15px', borderRadius: '8px', display: 'flex', gap: '20px' }}>
              <img src={item.image} style={{width:'120px', height:'150px', objectFit:'cover', background:'#eee'}} />
              
              <div style={{ flex: 1 }}>
                <h3 style={{margin: '0 0 5px 0'}}>{item.brand} / {item.name}</h3>
                
                {/* Результат примерки */}
                <div style={{ background: item.fit_result.includes("ПОДХОДИТ") ? '#d4edda' : '#f8d7da', padding: '5px 10px', borderRadius: '4px', display: 'inline-block', marginBottom: '10px' }}>
                  <b>{item.fit_result}</b> <small>{item.fit_details}</small>
                </div>

                {/* ВЫПАДАЮЩИЙ СПИСОК МАГАЗИНОВ (Скрыт по умолчанию) */}
                <details style={{ marginTop: '10px', background: '#f9f9f9', padding: '10px', borderRadius: '5px', cursor: 'pointer' }}>
                    <summary style={{ fontWeight: 'bold', color: '#007bff' }}>
                        🛒 Сравнить цены ({item.offers.length} магазина) — от {item.price} ₽
                    </summary>
                    
                    <div style={{ marginTop: '10px', borderTop: '1px solid #ddd', paddingTop: '10px' }}>
                        {item.offers.map((offer, idx) => (
                            <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', padding: '5px 0' }}>
                                <a href={offer.link} target="_blank" style={{ color: '#333', textDecoration:'none' }}>
                                    {offer.shop_name} ({offer.delivery_days} дн.)
                                </a>
                                <b style={{ color: idx === 0 ? 'green' : 'black' }}>{offer.price} ₽</b>
                            </div>
                        ))}
                    </div>
                </details>

              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

export default App