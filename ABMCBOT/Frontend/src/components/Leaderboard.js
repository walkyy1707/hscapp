import React, { useState, useEffect } from 'react';

function Leaderboard() {
  const [leaders, setLeaders] = useState([]);

  useEffect(() => {
    fetch('/leaderboard').then(res => res.json()).then(setLeaders);
  }, []);

  return (
    <div>
      <h2>Leaderboard</h2>
      <ul>
        {leaders.map((leader, index) => (
          <li key={index}>{leader.telegram_id}: {leader.points} points</li>
        ))}
      </ul>
    </div>
  );
}

export default Leaderboard;