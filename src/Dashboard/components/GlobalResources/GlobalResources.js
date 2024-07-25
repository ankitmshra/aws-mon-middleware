import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './GlobalResources.css';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL;

const ResourceCard = ({ resource, type }) => (
  <div className="global-resource-card">
    {type === 'IAM User' && (
      <>
        <h4>{resource.user_name}</h4>
        <p>ID: {resource.user_id}</p>
        <p>Last Login: {resource.last_login}</p>
      </>
    )}
    {type === 'S3 Bucket' && (
      <>
        <h4>{resource.bucket_name}</h4>
        <p>Created: {new Date(resource.creation_date).toLocaleDateString()}</p>
        <p>Status: {resource.status}</p>
      </>
    )}
  </div>
);

const GlobalResources = ({ isGlobalSelected }) => {
  const [resources, setResources] = useState({ iamUsers: [], s3Buckets: [] });
  const [activeTab, setActiveTab] = useState('iamUsers');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchGlobalResources = async () => {
      if (!isGlobalSelected) return;

      setLoading(true);
      setError('');
      try {
        const [iamResponse, s3Response] = await Promise.all([
          axios.get(`${API_BASE_URL}/api/rmon/iam-users/`, {
            headers: { Authorization: `Bearer ${localStorage.getItem('accessToken')}` },
          }),
          axios.get(`${API_BASE_URL}/api/rmon/s3-buckets/`, {
            headers: { Authorization: `Bearer ${localStorage.getItem('accessToken')}` },
          })
        ]);

        setResources({
          iamUsers: iamResponse.data,
          s3Buckets: s3Response.data
        });
      } catch (error) {
        console.error('Failed to fetch global resources:', error);
        setError('Failed to load global resources. Please try again later.');
      } finally {
        setLoading(false);
      }
    };

    fetchGlobalResources();
  }, [isGlobalSelected]);

  if (!isGlobalSelected) {
    return <div className="global-resources-module">Global resources are only supported for Global region selection.</div>;
  }

  if (loading) {
    return <div className="global-resources-module">Loading global resources...</div>;
  }

  if (error) {
    return <div className="global-resources-module error-message">{error}</div>;
  }

  const tabs = [
    { key: 'iamUsers', label: 'Inactive IAM Users' },
    { key: 's3Buckets', label: 'Empty S3 Buckets' },
  ];

  return (
    <div className="global-resources-module">
      <h3>Global Resources</h3>
      <div className="tabs">
        {tabs.map(tab => (
          <button
            key={tab.key}
            className={`tab ${activeTab === tab.key ? 'active' : ''}`}
            onClick={() => setActiveTab(tab.key)}
          >
            {tab.label}
          </button>
        ))}
      </div>
      <div className="global-resources-content">
        {resources[activeTab].length > 0 ? (
          resources[activeTab].map((resource, index) => (
            <ResourceCard 
              key={index} 
              resource={resource} 
              type={activeTab === 'iamUsers' ? 'IAM User' : 'S3 Bucket'} 
            />
          ))
        ) : (
          <p>No {activeTab === 'iamUsers' ? 'IAM users' : 'S3 buckets'} found.</p>
        )}
      </div>
    </div>
  );
};

export default GlobalResources;