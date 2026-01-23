import { useState, useEffect } from 'react'

const IP = "109.73.193.225"; 

function App() {
  const [user, setUser] = useState(null); 
  const [token, setToken] = useState(localStorage.getItem('token')); 
  const [authMode, setAuthMode] = useState('login'); 
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const [query, setQuery] = useState("джинсы");
  const [measurements, setMeasurements] = useState({ waist: 0, hip: 0, leg_length: 0, height: 0 });
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [isModel, setIsModel] = useState(false);
  const [showAdmin, setShowAdmin] = useState(false);
  const [adminData, setAdminData] = useState(null);

  useEffect(() => {
    if (token && !user) {
        fetch(`http://${IP}:5000/api/auth/me`, {
            method: 'GET',
            headers: { 'Authorization': `Bearer ${token}` }
        })
        .then(res => res.json())
        .then(data => {
            if (data.error) { logout(); } 
            else {
                setUser(data.user);
                setMeasurements(data.user.measurements || { waist: 0, hip: 0, leg_length: 0, height: 0 });
                // ВОТ ТУТ МЫ ТЕПЕРЬ ПОЛУЧАЕМ СТАТУС ГАЛОЧКИ ИЗ БАЗЫ
                setIsModel(data.user.isModel || false);
            }
        })
        .catch(() => console.error("Ошибка загрузки профиля"));
    }
  }, [token]);

  const handleAuth = async () => {
    const endpoint = authMode === 'login' ? '/api/auth/login' : '/api/auth/register';
    try {
        const res = await fetch(`http://${IP}:5000${endpoint}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password, measurements: authMode === 'register' ? measurements : undefined })
        });
        const data = await res.json();
        if (data.error) { alert(data.error); } 
        else {
            localStorage.setItem('token', data.token);
            setToken(data.token);
            setUser(data.user);
            if (data.user.measurements) setMeasurements(data.user.measurements);
            setIsModel(data.user.isModel || false);
        }
    } catch (e) { alert("Ошибка сервера"); }
  };

  const logout = () => {
    localStorage.removeItem('token');
    setToken(null);
    setUser(null);
    setResults([]);
  };

  const updateMeasure = async (key, val) => {
    const newVal = Number(val);
    const newMeasurements = { ...measurements, [key]: newVal };
    setMeasurements(newMeasurements);
    if (token) {
        await fetch(`http://${IP}:5000/api/user/update`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ token, measurements: newMeasurements })
        });
    }
  };

  const handleSearch = async () => {
    if (!measurements.waist) return alert("Пожалуйста, заполните размеры слева!");
    setLoading(true);
    try {
      const response = await fetch(`http://${IP}:5000/api/recommend`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, maxPrice: 10000, userMeasurements: measurements })
      });
      const data = await response.json();
      if (data.error) alert(data.error);
      else setResults(data);
    } catch (error) { alert("Ошибка сети"); }
    setLoading(false);
  };

  // ИСПРАВЛЕННАЯ ФУНКЦИЯ
  const handleBecomeModel = async (e) => {
    const checked = e.target.checked;
    setIsModel(checked);
    if (token) {
        try {
            await fetch(`http://${IP}:5000/api/become-model`, {
                method: 'POST', 
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ token, measurements, isModel: checked })
            });
            if (checked) alert("Спасибо! Статус модели сохранен.");
        } catch (error) {
            alert("Ошибка сохранения");
            setIsModel(!checked);
        }
    } else {
        alert("Войдите в аккаунт");
        setIsModel(false);
    }
  };

  const openAdmin = async () => {
    if (prompt("Пароль:") === "1234") {
        const res = await fetch(`http://${IP}:5000/api/admin/stats`);
        setAdminData(await res.json());
        setShowAdmin(true);
    } else alert("Неверно");
  };

  if (!token) {
      return (
          <div className="auth-container">
              <div className="auth-card">
                  <h2 className="auth-title">{authMode === 'login' ? 'Вход в Fit System' : 'Регистрация'}</h2>
                  <input className="auth-input" type="email" placeholder="Email" value={email} onChange={e=>setEmail(e.target.value)} />
                  <input className="auth-input" type="password" placeholder="Пароль" value={password} onChange={e=>setPassword(e.target.value)} />
                  {authMode === 'register' && (
                      <div style={{textAlign:'left', marginBottom:'20px'}}>
                          <small>Укажите базовые размеры:</small>
                          <input className="auth-input" style={{marginTop:'5px'}} type="number" placeholder="Талия (см)" value={measurements.waist || ''} onChange={e=>setMeasurements({...measurements, waist: Number(e.target.value)})} />
                      </div>
                  )}
                  <button className="btn-primary" style={{width:'100%'}} onClick={handleAuth}>{authMode === 'login' ? 'Войти' : 'Создать аккаунт'}</button>
                  <span className="auth-link" onClick={() => setAuthMode(authMode === 'login' ? 'register' : 'login')}>
                      {authMode === 'login' ? 'Нет аккаунта? Зарегистрироваться' : 'Уже есть аккаунт? Войти'}
                  </span>
              </div>
          </div>
      )
  }

  if (showAdmin && adminData) {
      return (
          <div className="admin-overlay">
              <div className="admin-header"><h1>📊 Панель Инвестора</h1><button onClick={() => setShowAdmin(false)} className="btn-primary" style={{background:'#4b5563'}}>Закрыть</button></div>
              <div className="stat-grid">
                  <div className="stat-card" style={{ background: '#2563eb' }}><h2>{adminData.users_count}</h2><p>Пользователей</p></div>
                  <div className="stat-card" style={{ background: '#10b981' }}><h2>{adminData.count}</h2><p>Моделей</p></div>
              </div>
              <table className="data-table"><thead><tr><th>ID</th><th>Параметры</th></tr></thead><tbody>{adminData.list.map(m => <tr key={m.id}><td>{m.id}</td><td>{m.measurements.waist} / {m.measurements.height}</td></tr>)}</tbody></table>
          </div>
      )
  }

  return (
    <div className="app-container">
      <div className="sidebar">
        <div className="panel-card">
            <div style={{display:'flex', justifyContent:'space-between', alignItems:'center', marginBottom:'15px'}}>
                <h2 style={{margin:0, fontSize:'1.2rem'}}>👤 Профиль</h2>
                <button onClick={logout} style={{background:'none', border:'none', color:'#ef4444', cursor:'pointer', fontSize:'0.9rem'}}>Выйти</button>
            </div>
            <div className="input-group"><label>Рост</label><input type="number" value={measurements.height} onChange={(e)=>updateMeasure('height',e.target.value)} /></div>
            <div className="input-group"><label>Талия</label><input type="number" value={measurements.waist} onChange={(e)=>updateMeasure('waist',e.target.value)} /></div>
            <div className="input-group"><label>Ноги</label><input type="number" value={measurements.leg_length} onChange={(e)=>updateMeasure('leg_length',e.target.value)} /></div>
        </div>
        <div className={`panel-card model-card ${isModel ? 'active' : ''}`}>
            <label style={{display:'flex', alignItems:'center', cursor:'pointer', fontWeight:'bold'}}>
                <input type="checkbox" checked={isModel} onChange={handleBecomeModel} style={{width:'20px', height:'20px', marginRight:'12px'}} />
                Хочу быть моделью
            </label>
        </div>
        <button onClick={openAdmin} style={{ marginTop: 'auto', background: 'none', border: 'none', color: '#9ca3af' }}>🔒 Admin</button>
      </div>
      <div className="main-content">
        <div className="search-bar">
          <input type="text" className="search-input" value={query} onChange={(e) => setQuery(e.target.value)} />
          <button onClick={handleSearch} className="btn-primary">{loading ? "..." : "Подобрать"}</button>
        </div>
        <div className="products-grid">
          {results.map((item) => (
            <div key={item.id} className="product-card">
              <img src={item.image} className="product-image" />
              <div className="product-info">
                <div className="product-brand">{item.brand}</div>
                <div className="product-name">{item.name}</div>
                <div className={`fit-badge ${item.fit_result.includes("ПОДХОДИТ") ? 'success' : 'error'}`}>
                  {item.fit_result} <span style={{marginLeft:'5px', fontWeight:'normal'}}>• {item.fit_details}</span>
                </div>
                <div className="price-list">
                    <details>
                        <summary className="price-summary">Цены от {item.price} ₽</summary>
                        <div style={{marginTop:'10px'}}>
                            {item.offers.map((offer, i) => <div key={i} className="price-row"><span>{offer.shop_name}</span><b>{offer.price} ₽</b></div>)}
                        </div>
                    </details>
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