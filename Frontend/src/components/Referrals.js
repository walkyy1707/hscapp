import React, { useState, useEffect } from 'react';

function Referral({ initData, userId }) {
  const [referrals, setReferrals] = useState(0);
  const referralLink = `https://t.me/officialabmcbot/app?startapp=ref_${userId}`;

  useEffect(() => {
    fetch('/referrals', { headers: { 'Authorization': `Bearer ${initData}` } })
      .then(res => res.json())
      .then(data => setReferrals(data.referrals));
  }, []);

  return (
    <div>
      <p>Referral Link: <input type="text" value={referralLink} readOnly /></p>
      <p>Referrals: {referrals}</p>
    </div>
  );
}

export default Referral;