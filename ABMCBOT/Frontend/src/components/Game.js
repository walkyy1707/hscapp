import React, { useState, useEffect, useRef } from 'react';

function Game({ initData }) {
  const [tickets, setTickets] = useState(0);
  const [playing, setPlaying] = useState(false);
  const [score, setScore] = useState(0);
  const canvasRef = useRef(null);
  const objectsRef = useRef([]);
  const catchSound = useRef(new Audio('/sounds/catch.mp3'));

  useEffect(() => {
    fetch('/user', { headers: { 'Authorization': `Bearer ${initData}` } })
      .then(res => res.json())
      .then(data => setTickets(data.tickets));
  }, []);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    let animationFrameId;

    const render = () => {
      if (!playing) return;
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      objectsRef.current.forEach(obj => {
        obj.y += obj.speed;
        if (obj.y > canvas.height) {
          objectsRef.current = objectsRef.current.filter(o => o !== obj);
        } else {
          ctx.beginPath();
          ctx.arc(obj.x, obj.y, 10, 0, Math.PI * 2);
          ctx.fillStyle = 'green';
          ctx.fill();
        }
      });
      if (objectsRef.current.length < 20 && Math.random() < 0.1) {
        objectsRef.current.push({ x: Math.random() * canvas.width, y: 0, speed: 2 + Math.random() * 2 });
      }
      animationFrameId = requestAnimationFrame(render);
    };

    if (playing) {
      render();
    }

    return () => cancelAnimationFrame(animationFrameId);
  }, [playing]);

  const startGame = async () => {
    const response = await fetch('/play_game', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${initData}` }
    });
    if (response.ok) {
      setPlaying(true);
      setScore(0);
      objectsRef.current = [];
      setTickets(prev => prev - 1);
      setTimeout(() => {
        setPlaying(false);
        submitScore();
      }, 25000);
    }
  };

  const submitScore = async () => {
    await fetch('/submit_score', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${initData}`
      },
      body: JSON.stringify({ score })
    });
  };

  const handleCanvasClick = (e) => {
    if (!playing) return;
    const canvas = canvasRef.current;
    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    objectsRef.current = objectsRef.current.filter(obj => {
      if (Math.hypot(obj.x - x, obj.y - y) < 10) {
        setScore(prev => prev + 10);
        catchSound.current.play();
        return false;
      }
      return true;
    });
  };

  return (
    <div>
      {playing ? (
        <div>
          <canvas ref={canvasRef} width="300" height="400" onClick={handleCanvasClick} />
          <p>Score: {score}</p>
        </div>
      ) : (
        <button onClick={startGame} disabled={tickets <= 0}>
          Play (Tickets: {tickets})
        </button>
      )}
    </div>
  );
}

export default Game;