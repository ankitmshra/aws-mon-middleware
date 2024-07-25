import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';

function AuthWrapper({ children }) {
  const isAuthenticated = localStorage.getItem('accessToken') !== null;
  const location = useLocation();

  if (isAuthenticated && location.pathname === '/login') {
    return <Navigate to="/dashboard" replace />;
  }

  if (!isAuthenticated && location.pathname !== '/login') {
    return <Navigate to="/login" replace />;
  }

  return children;
}

export default AuthWrapper;