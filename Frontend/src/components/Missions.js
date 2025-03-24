import React, { useState, useEffect } from 'react';

function Missions({ initData }) {
  const [missions, setMissions] = useState([]);
  const [completed, setCompleted] = useState([]);

  useEffect(() => {
    fetch('/missions').then(res => res.json()).then(setMissions);
    fetch('/user_missions', { headers: { 'Authorization': `Bearer ${initData}` } })
      .then(res => res.json())
      .then(setCompleted);
  }, []);

  const completeMission = async (missionId) => {
    const response = await fetch('/complete_mission', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${initData}`
      },
      body: JSON.stringify({ mission_id: missionId })
    });
    if (response.ok) setCompleted(prev => [...prev, missionId]);
  };

  return (
    <div>
      {missions.map(m => (
        <div key={m.mission_id} className="mission">
          <p>{m.description}</p>
          <a href={m.link} target="_blank" rel="noopener noreferrer">Go</a>
          {completed.includes(m.mission_id) ? (
            <p>✔ Completed</p>
          ) : (
            <button onClick={() => completeMission(m.mission_id)}>Complete</button>
          )}
        </div>
      ))}
    </div>
  );
}

export default Missions;