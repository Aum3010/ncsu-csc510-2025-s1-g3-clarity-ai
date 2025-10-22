import React from 'react';

const Tag = ({ name, type = 'default' }) => {
  let colorClass = 'bg-gray-200 text-gray-700'; // Default light mode tag

  // Determine color based on common categories or explicit types
  if (name.toLowerCase().includes('high priority')) {
    colorClass = 'bg-red-500 text-white';
  } else if (name.toLowerCase().includes('medium priority')) {
    colorClass = 'bg-yellow-400 text-gray-900';
  } else if (name.toLowerCase().includes('low priority')) {
    colorClass = 'bg-green-200 text-green-800';
  } else if (name.toLowerCase().includes('security')) {
    colorClass = 'bg-purple-400 text-white';
  } else if (name.toLowerCase().includes('ux') || name.toLowerCase().includes('ui')) {
    colorClass = 'bg-blue-400 text-white';
  } else if (name.toLowerCase().includes('authentication')) {
    colorClass = 'bg-indigo-400 text-white';
  } else if (type === 'status') {
    // Status tags are more muted/official
    colorClass = name === 'Draft' ? 'bg-gray-300 text-gray-800' : 'bg-orange-200 text-orange-800';
  } else if (name.toLowerCase().includes('performance')) {
    colorClass = 'bg-fuchsia-300 text-fuchsia-800';
  }

  return (
    <span className={`inline-flex items-center px-3 py-0.5 rounded-full text-xs font-medium ${colorClass}`}>
      {name}
    </span>
  );
};

export default Tag;