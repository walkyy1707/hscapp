import React, { useState, useEffect } from 'react';

function Home({ initData }) {
  const [userData, setUserData] = useState(null);

  useEffect(() => {
    fetchUser();
  }, []);

  const fetchUser = async () => {
    const response = await fetch(`/user?start_param=${encodeURIComponent(Telegram.WebApp.initDataUnsafe.start_param || '')}`, {
      headers: { 'Authorization': `Bearer ${initData}` }
    });
    setUserData(await response.json());
  };

  const claimTicket = async () => {
    const response = await fetch('/claim_ticket', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${initData}` }
    });
    const data = await response.json();
    setUserData(prev => ({ ...prev, tickets: data.tickets }));
  };

  if (!userData) return <p>Loading...</p>;

  return (
    <div>
      <p>Points: {userData.points}</p>
      <p>Tickets: {userData.tickets}/7</p>
      <button onClick={claimTicket} disabled={userData.tickets >= 7 || userData.last_ticket_date === new Date().toISOString().split('T')[0]}>
        Claim Daily Ticket
      </button>
    </div>
  );
}

export default Home;