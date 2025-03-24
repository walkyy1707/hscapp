import React, { useState, useEffect } from 'react';
import Home from './components/Home';
import Game from './components/Game';
import Missions from './components/Missions';
import Referral from './components/Referral';
import Leaderboard from './components/Leaderboard';
import './styles.css';

function App() {
  const [tab, setTab] = useState('home');
  const [initData, setInitData] = useState('');
  const [user, setUser] = useState(null);

  useEffect(() => {
    if (window.Telegram && window.Telegram.WebApp) {
      const webApp = window.Telegram.WebApp;
      webApp.ready();
      setInitData(webApp.initData);
      setUser(webApp.initDataUnsafe.user);
    }
  }, []);

  if (!user) return <div>Loading...</div>;

  return (
    <div className="app">
      <h1>ABMC by HSC</h1>
      <nav>
        <button onClick={() => setTab('home')}>Home</button>
        <button onClick={() => setTab('game')}>Game</button>
        <button onClick={() => setTab('missions')}>Missions</button>
        <button onClick={() => setTab('referral')}>Referral</button>
        <button onClick={() => setTab('leaderboard')}>Leaderboard</button>
      </nav>
      {tab === 'home' && <Home initData={initData} />}
      {tab === 'game' && <Game initData={initData} />}
      {tab === 'missions' && <Missions initData={initData} />}
      {tab === 'referral' && <Referral initData={initData} userId={user.id} />}
      {tab === 'leaderboard' && <Leaderboard />}
    </div>
  );
}

export default App;