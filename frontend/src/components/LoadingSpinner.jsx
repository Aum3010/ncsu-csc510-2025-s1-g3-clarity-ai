import React from 'react';

const LoadingSpinner = ({ 
  size = 'md', 
  color = 'blue', 
  text = '', 
  fullScreen = false,
  className = '' 
}) => {
  const getSizeClasses = () => {
    switch (size) {
      case 'sm':
        return 'h-4 w-4';
      case 'lg':
        return 'h-8 w-8';
      case 'xl':
        return 'h-12 w-12';
      default:
        return 'h-6 w-6';
    }
  };

  const getColorClasses = () => {
    switch (color) {
      case 'white':
        return 'border-white';
      case 'gray':
        return 'border-gray-600';
      case 'green':
        return 'border-green-600';
      case 'red':
        return 'border-red-600';
      default:
        return 'border-blue-600';
    }
  };

  const spinner = (
    <div className={`animate-spin rounded-full border-b-2 ${getSizeClasses()} ${getColorClasses()} ${className}`}></div>
  );

  if (fullScreen) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="text-center">
          {spinner}
          {text && <p className="mt-4 text-gray-600">{text}</p>}
        </div>
      </div>
    );
  }

  if (text) {
    return (
      <div className="flex items-center justify-center space-x-2">
        {spinner}
        <span className="text-gray-600">{text}</span>
      </div>
    );
  }

  return spinner;
};

export default LoadingSpinner;