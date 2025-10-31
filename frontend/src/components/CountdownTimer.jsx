import React, { useState, useEffect } from 'react';

const CountdownTimer = ({ 
  initialTime, 
  onComplete, 
  format = 'seconds',
  className = '',
  prefix = '',
  suffix = ''
}) => {
  const [timeLeft, setTimeLeft] = useState(initialTime);

  useEffect(() => {
    setTimeLeft(initialTime);
  }, [initialTime]);

  useEffect(() => {
    if (timeLeft <= 0) {
      if (onComplete) {
        onComplete();
      }
      return;
    }

    const timer = setTimeout(() => {
      setTimeLeft(timeLeft - 1);
    }, 1000);

    return () => clearTimeout(timer);
  }, [timeLeft, onComplete]);

  const formatTime = (seconds) => {
    if (format === 'mm:ss') {
      const minutes = Math.floor(seconds / 60);
      const remainingSeconds = seconds % 60;
      return `${minutes.toString().padStart(2, '0')}:${remainingSeconds.toString().padStart(2, '0')}`;
    }
    return seconds.toString();
  };

  if (timeLeft <= 0) {
    return null;
  }

  return (
    <span className={className}>
      {prefix}{formatTime(timeLeft)}{suffix}
    </span>
  );
};

export default CountdownTimer;