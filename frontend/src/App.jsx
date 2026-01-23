import { useState } from 'react'

function App() {
  const [query, setQuery] = useState("джинсы");
  
  const [measurements, setMeasurements] = useState({
    waist: 70, hip: 96, leg_length: 82, height: 175
  });

  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [isModel, setIsModel] = useState(false);

  // --- АДМИНСКАЯ ЧАСТЬ ---
  const [showAdmin, setShowAdmin] = useState(false);
  const [adminData, setAdminData] = useState(null);

  const IP = "109.73.193.225"; // Ваш IP

  const handleSearch = async () => {
    setLoading(true);
    try {
      const response = await fetch(`http://${IP}:5000/api/recommend`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, maxPrice: 10000, userMeasurements: measurements })
      });
      const data = await response.json();
      setResults(data);
    } catch (error) { alert("Ошибка сети"); }
    setLoading(false);
  };

  const handleBecomeModel = async (e) => {
    const checked = e.target.checked;
    setIsModel(checked);
    if (checked) {
        try {
            await fetch(`http://${IP}:5000/api/become-model`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ measurements })
            });
            alert("Спасибо! Вы добавлены в базу.");
        } catch (error) { alert("Ошибка сохранения"); }
    }
  };

  // Вход в админку
  const openAdmin = async () => {
    const password = prompt("Введите пароль администратора:");
    if (password === "1234") {
        const res = await fetch(`http://${IP}:5000/api/admin/stats`);
        const data = await res.json();
        setAdminData(data);
        setShowAdmin(true);
    } else {
        alert("Неверный пароль");
    }
  };

  const updateMeasure = (key, val) => setMeasurements(p => ({ ...p, [key]: Number(val) }));

  // Если открыта админка - показываем только её
  if (showAdmin && adminData) {
      return (
          <div style={{ padding: '40px', fontFamily: 'Arial', maxWidth: '800px', margin: '0 auto' }}>
              <div style={{display:'flex', justifyContent:'space-between', alignItems:'center'}}>
                <h1>📊 Панель Инвестора</h1>
                <button onClick={() => setShowAdmin(false)} style={{padding:'10px', background:'#666', color:'white', border:'none'}}>Закрыть</button>
              </div>

              <div style={{ display: 'flex', gap: '20px', marginTop: '20px' }}>
                  <div style={{ background: '#007bff', color: 'white', padding: '20px', borderRadius: '10px', flex: 1 }}>
                      <h2>{adminData.count}</h2>
                      <p>Всего моделей</p>
                  </div>
                  <div style={{ background: '#28a745', color: 'white', padding: '20px', borderRadius: '10px', flex: 1 }}>
                      <h2>{adminData.avg_waist} см</h2>
                      <p>Средняя талия</p>
                  </div>
              </div>

              <h3>Последние регистрации:</h3>
              <table style={{ width: '100%', borderCollapse: 'collapse', marginTop: '10px' }}>
                  <thead>
                      <tr style={{background:'#eee', textAlign:'left'}}>
                          <th style={{padding:'10px'}}>ID</th>
                          <th style={{padding:'10px'}}>Дата</th>
                          <th style={{padding:'10px'}}>Параметры (Т / Б / Р)</th>
                      </tr>
                  </thead>
                  <tbody>
                      {adminData.list.map(m => (
                          <tr key={m.id} style={{borderBottom:'1px solid #ddd'}}>
                              <td style={{padding:'10px'}}>{m.id}</td>
                              <td style={{padding:'10px'}}>{new Date(m.joined_at).toLocaleString()}</td>
                              <td style={{padding:'10px'}}>
                                  {m.measurements.waist} / {m.measurements.hip} / {m.measurements.height}
                              </td>
                          </tr>
                      ))}
                  </tbody>
              </table>
          </div>
      )
  }

  // Обычный интерфейс
  return (
    <div style={{ maxWidth: '1000px', margin: '0 auto', padding: '20px', fontFamily: 'Arial', display: 'flex', gap: '30px' }}>
      
      <div style={{ flex: '0 0 250px' }}>
        <div style={{ background: '#f8f9fa', padding: '20px', borderRadius: '10px', marginBottom: '20px' }}>
          <h3>📏 Мои замеры</h3>
          <div style={{marginBottom:'10px'}}><label>Рост:</label><input type="number" value={measurements.height} onChange={(e)=>updateMeasure('height',e.target.value)} style={{width:'100%'}} /></div>
          <div style={{marginBottom:'10px'}}><label>Талия:</label><input type="number" value={measurements.waist} onChange={(e)=>updateMeasure('waist',e.target.value)} style={{width:'100%'}} /></div>
          <div style={{marginBottom:'10px'}}><label>Ноги:</label><input type="number" value={measurements.leg_length} onChange={(e)=>updateMeasure('leg_length',e.target.value)} style={{width:'100%'}} /></div>
        </div>

        <div style={{ background: isModel ? '#d4edda' : '#e9ecef', padding: '15px', borderRadius: '10px', border: isModel ? '1px solid green' : '1px solid #ccc' }}>
            <label style={{display:'flex', alignItems:'center', cursor:'pointer', fontWeight:'bold'}}>
                <input type="checkbox" checked={isModel} onChange={handleBecomeModel} style={{width:'20px', height:'20px', marginRight:'10px'}} />
                Хочу быть моделью
            </label>
        </div>

        {/* СЕКРЕТНАЯ КНОПКА ВНИЗУ */}
        <button onClick={openAdmin} style={{ marginTop: '50px', background: 'none', border: 'none', color: '#ccc', fontSize: '12px', cursor: 'pointer' }}>
            🔒 Admin Login
        </button>
      </div>

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
                <div style={{ background: item.fit_result.includes("ПОДХОДИТ") ? '#d4edda' : '#f8d7da', padding: '5px 10px', borderRadius: '4px', display: 'inline-block', marginBottom: '10px' }}>
                  <b>{item.fit_result}</b> <small>{item.fit_details}</small>
                </div>
                <details style={{ marginTop: '10px', background: '#f9f9f9', padding: '10px', borderRadius: '5px', cursor: 'pointer' }}>
                    <summary style={{ fontWeight: 'bold', color: '#007bff' }}>
                        🛒 Сравнить цены ({item.offers.length} магазина) — от {item.price} ₽
                    </summary>
                    <div style={{ marginTop: '10px', borderTop: '1px solid #ddd', paddingTop: '10px' }}>
                        {item.offers.map((offer, idx) => (
                            <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', padding: '5px 0' }}>
                                <a href={offer.link} target="_blank" style={{ color: '#333', textDecoration:'none' }}>{offer.shop_name}</a>
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