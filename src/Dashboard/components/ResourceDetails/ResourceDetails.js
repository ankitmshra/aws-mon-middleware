import React, { useState, useEffect, useMemo } from 'react';
import axios from 'axios';
import './ResourceDetails.css';

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL;

const ResourceCard = ({ resource }) => {
  const [isPopupOpen, setIsPopupOpen] = useState(false);

  const togglePopup = () => setIsPopupOpen(!isPopupOpen);

  const renderValue = (key, value) => {
    if (key === 'recommendations') {
      const parts = value.split(/(https?:\/\/[^\s]+)/);
      return parts.map((part, index) => 
        part.startsWith('http') ? <a key={index} href={part} target="_blank" rel="noopener noreferrer">{part}</a> : part
      );
    }
    if (key === 'tags' && Array.isArray(value)) {
      return value.map(tag => `${tag.Key}: ${tag.Value}`).join(', ');
    }
    if (typeof value === 'object') {
      return JSON.stringify(value, null, 2);
    }
    return value;
  };

  return (
    <div className="resource-card">
      <button className="expand-button" onClick={togglePopup}>⤢</button>
      <h4>{resource.id || resource.instance_id || resource.db_instance_identifier || resource.volume_id}</h4>
      <p>Type: {resource.instance_type || resource.db_instance_class || `EBS ${resource.size}GB`}</p>
      <p>Region: {resource.region}</p>
      <p>Potential Cost Savings: <span className="cost-savings">${resource.potential_cost_savings.toFixed(2)}</span></p>

      {isPopupOpen && (
        <div className="popup-overlay">
          <div className="popup-content">
            <button className="close-button" onClick={togglePopup}>×</button>
            <h3>Resource Details</h3>
            <table className="resource-details-table">
              <tbody>
                {Object.entries(resource).map(([key, value]) => (
                  <tr key={key}>
                    <td><strong>{key}</strong></td>
                    <td>{renderValue(key, value)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

const FilterSection = ({ title, filters, selectedFilters, onChange, initialDisplayCount = 3 }) => {
  const [showAll, setShowAll] = useState(false);

  const displayedFilters = showAll ? filters : filters.slice(0, initialDisplayCount);

  return (
    <div className="filter-section">
      <h4>{title}</h4>
      {displayedFilters.map(filter => (
        <label key={filter}>
          <input
            type="checkbox"
            checked={selectedFilters.includes(filter)}
            onChange={() => onChange(filter)}
          />
          {filter}
        </label>
      ))}
      {filters.length > initialDisplayCount && (
        <button className="load-more-btn" onClick={() => setShowAll(!showAll)}>
          {showAll ? 'Show Less' : 'Load More'}
        </button>
      )}
    </div>
  );
};

const Pagination = ({ totalItems, itemsPerPage, currentPage, onPageChange }) => {
  const totalPages = Math.ceil(totalItems / itemsPerPage);

  return (
    <div className="pagination">
      <button 
        onClick={() => onPageChange(currentPage - 1)} 
        disabled={currentPage === 1}
      >
        Previous
      </button>
      <span>{`Page ${currentPage} of ${totalPages}`}</span>
      <button 
        onClick={() => onPageChange(currentPage + 1)} 
        disabled={currentPage === totalPages}
      >
        Next
      </button>
    </div>
  );
};

const ResourceDetails = ({ selectedRegions }) => {
  const [allData, setAllData] = useState(null);
  const [activeTab, setActiveTab] = useState('all_resources');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [filters, setFilters] = useState({
    instanceTypes: [],
    tags: [],
    statuses: [],
    costSavings: { min: '', max: '' }
  });
  const [currentPage, setCurrentPage] = useState(1);
  const cardsPerPage = 4;

  useEffect(() => {
    const fetchAllData = async () => {
      setLoading(true);
      setError('');
      try {
        const response = await axios.get(`${API_BASE_URL}/api/rmon/all-resources/`, {
          headers: {
            Authorization: `Bearer ${localStorage.getItem('accessToken')}`,
          },
        });
        setAllData(response.data);
      } catch (error) {
        console.error('Failed to fetch resource data:', error);
        setError('Failed to load resource data. Please try again later.');
      } finally {
        setLoading(false);
      }
    };

    fetchAllData();
  }, []);

  const filteredData = useMemo(() => {
    if (!allData) return null;

    const isGlobalSelected = selectedRegions.includes('Global');

    return Object.keys(allData).reduce((acc, key) => {
      const filteredResources = allData[key].filter(resource => 
        (isGlobalSelected || selectedRegions.includes(resource.region)) &&
        (filters.instanceTypes.length === 0 || filters.instanceTypes.includes(resource.instance_type)) &&
        (filters.statuses.length === 0 || filters.statuses.includes(resource.status)) &&
        (filters.tags.length === 0 || filters.tags.some(tag => 
          resource.tags && resource.tags.some(resourceTag => 
            resourceTag.Key === tag.split(':')[0] && resourceTag.Value === tag.split(':')[1]
          )
        )) &&
        (filters.costSavings.min === '' || resource.potential_cost_savings >= parseFloat(filters.costSavings.min)) &&
        (filters.costSavings.max === '' || resource.potential_cost_savings <= parseFloat(filters.costSavings.max))
      );
      
      acc[key] = filteredResources;
      
      if (key !== 'all_resources') {
        if (!acc.all_resources) acc.all_resources = [];
        acc.all_resources = [...acc.all_resources, ...filteredResources];
      }
      
      return acc;
    }, {});
  }, [allData, selectedRegions, filters]);

  const availableFilters = useMemo(() => {
    if (!allData) return {};

    const isGlobalSelected = selectedRegions.includes('Global');
    
    const filters = {
      instanceTypes: new Set(),
      tags: new Set(),
      statuses: new Set()
    };

    const resourcesToConsider = activeTab === 'all_resources' 
      ? Object.values(allData).flat() 
      : allData[activeTab] || [];

    resourcesToConsider.forEach(resource => {
      if (isGlobalSelected || selectedRegions.includes(resource.region)) {
        if (resource.instance_type) filters.instanceTypes.add(resource.instance_type);
        if (resource.status) filters.statuses.add(resource.status);
        if (resource.tags) {
          resource.tags.forEach(tag => filters.tags.add(`${tag.Key}:${tag.Value}`));
        }
      }
    });

    return {
      instanceTypes: Array.from(filters.instanceTypes),
      tags: Array.from(filters.tags),
      statuses: Array.from(filters.statuses)
    };
  }, [allData, activeTab, selectedRegions]);

  const handleFilterChange = (filterType, value) => {
    setFilters(prevFilters => ({
      ...prevFilters,
      [filterType]: prevFilters[filterType].includes(value)
        ? prevFilters[filterType].filter(item => item !== value)
        : [...prevFilters[filterType], value]
    }));
    setCurrentPage(1);
  };

  const handleCostSavingsChange = (type, value) => {
    setFilters(prevFilters => ({
      ...prevFilters,
      costSavings: {
        ...prevFilters.costSavings,
        [type]: value
      }
    }));
    setCurrentPage(1);
  };

  useEffect(() => {
    // Reset filters when changing tabs or regions
    setFilters({
      instanceTypes: [],
      tags: [],
      statuses: [],
      costSavings: { min: '', max: '' }
    });
    setCurrentPage(1);
  }, [activeTab, selectedRegions]);

  const paginateData = (data, page, perPage) => {
    const startIndex = (page - 1) * perPage;
    return data.slice(startIndex, startIndex + perPage);
  };

  const renderResourceCards = () => {
    if (!filteredData || !filteredData[activeTab]) {
      return <p>No resources found.</p>;
    }

    const resources = filteredData[activeTab];
    const paginatedResources = paginateData(resources, currentPage, cardsPerPage);

    return paginatedResources.map((resource, index) => (
      <ResourceCard key={index} resource={resource} />
    ));
  };

  if (loading) {
    return <div>Loading...</div>;
  }

  if (error) {
    return <div className="error-message">{error}</div>;
  }

  const tabs = [
    { key: 'all_resources', label: 'All Resources' },
    { key: 'ec2_instances', label: 'EC2 Instances' },
    { key: 'rds_instances', label: 'RDS Instances' },
    { key: 'ebs_volumes', label: 'EBS Volumes' },
    { key: 'rds_snapshots', label: 'RDS Snapshots' },
    { key: 'ec2_snapshots', label: 'EC2 Snapshots' },
    { key: 'elastic_ips', label: 'Elastic IPs' },
  ];

  return (
    <div className="resource-details-container">
      <div className="resource-details">
        <div className="tabs">
          {tabs.map(tab => (
            <button
              key={tab.key}
              className={`tab ${activeTab === tab.key ? 'active' : ''}`}
              onClick={() => {
                setActiveTab(tab.key);
                setCurrentPage(1);
              }}
            >
              {tab.label}
            </button>
          ))}
        </div>
        <div className="scrollable-content">
          <div className="tab-content">
            {renderResourceCards()}
          </div>
        </div>
        <div className="pagination-container">
          {filteredData && filteredData[activeTab] && (
            <Pagination
              totalItems={filteredData[activeTab].length}
              itemsPerPage={cardsPerPage}
              currentPage={currentPage}
              onPageChange={setCurrentPage}
            />
          )}
        </div>
    </div>
      <div className="filter-module">
        <h3>Filters</h3>
        <div className="filter-section">
          <h4>Potential Cost Savings ($)</h4>
          <div className="cost-savings-filter">
            <input
              type="number"
              placeholder="Min"
              value={filters.costSavings.min}
              onChange={(e) => handleCostSavingsChange('min', e.target.value)}
            />
            <input
              type="number"
              placeholder="Max"
              value={filters.costSavings.max}
              onChange={(e) => handleCostSavingsChange('max', e.target.value)}
            />
          </div>
        </div>
        {availableFilters.instanceTypes && availableFilters.instanceTypes.length > 0 && (
          <FilterSection
            title="Instance Types"
            filters={availableFilters.instanceTypes}
            selectedFilters={filters.instanceTypes}
            onChange={(value) => handleFilterChange('instanceTypes', value)}
          />
        )}
        {availableFilters.tags && availableFilters.tags.length > 0 && (
          <FilterSection
            title="Tags"
            filters={availableFilters.tags}
            selectedFilters={filters.tags}
            onChange={(value) => handleFilterChange('tags', value)}
          />
        )}
        {availableFilters.statuses && availableFilters.statuses.length > 0 && (
          <FilterSection
            title="Status"
            filters={availableFilters.statuses}
            selectedFilters={filters.statuses}
            onChange={(value) => handleFilterChange('statuses', value)}
          />
        )}
      </div>
    </div>
  );
};

export default ResourceDetails;