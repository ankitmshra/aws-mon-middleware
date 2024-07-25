import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { Line } from 'react-chartjs-2';
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend } from 'chart.js';
import { startOfDay, endOfDay, format, addDays, subDays } from 'date-fns';
import './CostExplorer.css';

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend);

const API_BASE_URL = process.env.REACT_APP_API_BASE_URL;

const costColors = {
  ec2_cost: '#FF6384',
  rds_cost: '#36A2EB',
  ebs_cost: '#FFCE56',
  rds_snapshots_cost: '#4BC0C0',
  ebs_snapshots_cost: '#9966FF',
  elastic_ips_cost: '#FF9F40'
};

function CostExplorer() {
  const [costData, setCostData] = useState(null);
  const [historicalData, setHistoricalData] = useState(null);
  const [error, setError] = useState('');
  const [dateRange, setDateRange] = useState({
    startDate: format(startOfDay(subDays(new Date(), 1)), 'yyyy-MM-dd'),
    endDate: format(endOfDay(addDays(new Date(), 1)), 'yyyy-MM-dd'),
  });

  const fetchCostData = useCallback(async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/rmon/latest-cumulative-cost/`, {
        headers: {
          Authorization: `Bearer ${localStorage.getItem('accessToken')}`,
        },
      });
      setCostData(response.data);
    } catch (error) {
      console.error('Failed to fetch cost data:', error);
      setError('Failed to load cost data. Please try again later.');
    }
  }, []);

  const fetchHistoricalData = useCallback(async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/api/rmon/cumulative-cost-range/`, {
        params: {
          start_date: dateRange.startDate,
          end_date: dateRange.endDate,
        },
        headers: {
          Authorization: `Bearer ${localStorage.getItem('accessToken')}`,
        },
      });
      setHistoricalData(response.data);
      setError('');
    } catch (error) {
      if (error.response && error.response.status === 404) {
        setHistoricalData({ message: error.response.data.message });
        setError('');
      } else {
        console.error('Failed to fetch historical data:', error);
        setError('Failed to load historical data. Please try again later.');
      }
    }
  }, [dateRange]);

  useEffect(() => {
    fetchCostData();
    fetchHistoricalData();
  }, [fetchCostData, fetchHistoricalData]);

  const handleDateChange = (e) => {
    setDateRange({ ...dateRange, [e.target.name]: e.target.value });
  };

  if (error) {
    return <div className="error-message">{error}</div>;
  }

  if (!costData || !historicalData) {
    return <div>Loading cost data...</div>;
  }

  const renderChart = () => {
    if (historicalData.message) {
      return (
        <div className="no-data-message">
          <p>{historicalData.message}</p>
        </div>
      );
    }

    const chartData = {
      labels: Array.from({ length: historicalData.ec2_cost.length }, (_, i) => 
        format(new Date(dateRange.startDate).setDate(new Date(dateRange.startDate).getDate() + i), 'MMM dd')
      ),
      datasets: Object.entries(historicalData).map(([key, data]) => ({
        label: key.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' '),
        data: data,
        borderColor: costColors[key],
        backgroundColor: `${costColors[key]}50`,
        tension: 0.1
      })).filter(dataset => Array.isArray(dataset.data))
    };

    const chartOptions = {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: false,
        },
        title: {
          display: false,
        },
      },
    };

    return <Line options={chartOptions} data={chartData} />;
  };

  return (
    <div className="cost-explorer">
      <div className="cost-explorer-header">
        <h3>Cost Explorer</h3>
        <div className="date-range-selector">
          <input
            type="date"
            name="startDate"
            value={dateRange.startDate}
            onChange={handleDateChange}
          />
          <input
            type="date"
            name="endDate"
            value={dateRange.endDate}
            onChange={handleDateChange}
          />
        </div>
      </div>
      <div className="cost-explorer-content">
        <div className="cost-cards">
          {Object.entries(costData).map(([key, value]) => {
            if (key !== 'last_updated' && typeof value === 'number') {
              return (
                <div key={key} className="cost-card" style={{borderLeft: `4px solid ${costColors[key]}`}}>
                  <h4>{key.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ')}</h4>
                  <p>${value.toFixed(2)}</p>
                </div>
              );
            }
            return null;
          })}
        </div>
        <div className="cost-graph">
          {renderChart()}
        </div>
      </div>
      <div className="last-updated-container">
        <span className="last-updated">Last updated: {new Date(costData.last_updated).toLocaleString()}</span>
      </div>
    </div>
  );
}

export default CostExplorer;