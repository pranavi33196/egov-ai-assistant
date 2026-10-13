import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import Login from './components/Login';
import Dashboard from './components/Dashboard';
import AuthCallback from './components/AuthCallback';
import { auth } from './services/api';

function DirectDashboardWrapper({ setAuth }) {
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    const init = async () => {
      const existingToken = localStorage.getItem('token');
      if (existingToken) {
        setAuth(true);
        setLoading(false);
        return;
      }
      try {
        const data = await auth.demoLogin();
        if (data.access_token) {
          localStorage.setItem('token', data.access_token);
          setAuth(true);
        }
      } catch (err) {
        console.error("Direct demo login failed", err);
      } finally {
        setLoading(false);
      }
    };
    init();
  }, [navigate, setAuth]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#F5F7FA]">
        <div className="text-center">
          <div className="animate-spin rounded-full h-9 w-9 border-b-2 border-[#12355B] mx-auto mb-3"></div>
          <p className="text-xs text-gray-500 font-medium">Opening Citizen Dashboard...</p>
        </div>
      </div>
    );
  }

  return <Dashboard setAuth={setAuth} />;
}

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isCheckingAuth, setIsCheckingAuth] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token) {
      setIsAuthenticated(true);
    }
    setIsCheckingAuth(false);
  }, []);

  if (isCheckingAuth) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[#F5F7FA]">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-[#12355B]"></div>
      </div>
    );
  }

  return (
    <Router>
      <div className="min-h-screen bg-[#F5F7FA] font-sans text-[#17202A]">
        <Routes>
          <Route 
            path="/login" 
            element={!isAuthenticated ? <Login setAuth={setIsAuthenticated} /> : <Navigate to="/" replace />} 
          />
          <Route 
            path="/auth/callback" 
            element={<AuthCallback setAuth={setIsAuthenticated} />} 
          />
          <Route 
            path="/dashboard" 
            element={<DirectDashboardWrapper setAuth={setIsAuthenticated} />} 
          />
          <Route 
            path="/" 
            element={isAuthenticated ? <Dashboard setAuth={setIsAuthenticated} /> : <Navigate to="/login" replace />} 
          />
          <Route 
            path="*" 
            element={<Navigate to="/" replace />} 
          />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
