import React from 'react';
import Tag from './Tag';

const RequirementCard = ({ requirement }) => {
  const { req_id, title, description, status, priority, source_document_filename, tags } = requirement;

  return (
    // Card background is white, border changed to warm orange
    <div className="bg-white rounded-xl shadow-md p-6 border-l-4 border-orange-400 hover:shadow-orange-400/30 transition-shadow duration-300">
      <div className="flex justify-between items-start mb-3">
        <h3 className="text-xl font-semibold text-gray-900">{title}</h3>
        <span className="text-orange-500 font-mono text-sm">{req_id}</span>
      </div>

      <div className="flex flex-wrap gap-2 mb-4">
        {/* Tags will manage their own colors */}
        <Tag name={status} type="status" />
        <Tag name={`${priority} Priority`} type="priority" />

        {tags.map(tag => (
          <Tag key={tag.name} name={tag.name} /> 
        ))}
      </div>

      <p className="text-gray-700 mb-4 whitespace-pre-line">{description}</p>

      <div className="text-sm text-gray-500">
        <span className="font-semibold">Source:</span> {source_document_filename || 'N/A'}
      </div>
    </div>
  );
};

export default RequirementCard;