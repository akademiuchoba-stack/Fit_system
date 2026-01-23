import { useState } from 'react'

function App() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);

  const handleSearch = async () => {
    setLoading(true);
    try {
      // ⚠️ ВНИМАНИЕ: ЗАМЕНИТЕ 92.XX.XX.XX НА ВАШ IP АДРЕС СЕРВЕРА
      const response = await fetch('http://109.73.193.225:5000/api/recommend', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: query, maxPrice: 5000 })
      });
      const data = await response.json();
      setResults(data);
    } catch (error) {
      alert("Не могу связаться с сервером. Проверьте IP адрес в коде.");
      console.error(error);
    }
    setLoading(false);
  };

  return (
    <div style={{ maxWidth: '800px', margin: '0 auto', padding: '20px', fontFamily: 'Arial' }}>
      <h1>👖 Fit System MVP</h1>
      
      <div style={{ display: 'flex', gap: '10px', marginBottom: '20px' }}>
        <input 
          type="text" 
          placeholder="Что ищем? (например: джинсы)" 
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          style={{ flex: 1, padding: '10px', fontSize: '16px' }}
        />
        <button 
          onClick={handleSearch}
          style={{ padding: '10px 20px', background: '#007bff', color: 'white', border: 'none', cursor: 'pointer' }}
        >
          {loading ? "Ищем..." : "Подобрать"}
        </button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(250px, 1fr))', gap: '20px' }}>
        {results.map((item) => (
          <div key={item.id} style={{ border: '1px solid #ddd', padding: '15px', borderRadius: '8px' }}>
            <h3>{item.name}</h3>
            <p style={{ fontWeight: 'bold' }}>{item.price} ₽</p>
            <hr />
            <p>Результат примерки:</p>
            <div style={{ 
              background: item.fit_result.includes("ИДЕАЛЬНО") ? '#d4edda' : '#f8d7da', 
              padding: '10px', 
              borderRadius: '5px',
              textAlign: 'center'
            }}>
              <b>{item.fit_result}</b>
              <br/>
              <small>{item.fit_details}</small>
            </div>
            <a href={item.link} target="_blank" style={{ display: 'block', marginTop: '10px', color: 'blue' }}>
              Купить в магазине
            </a>
          </div>
        ))}
      </div>
    </div>
  )
}

export default App
