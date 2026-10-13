import React, { useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';

export default function AuthCallback({ setAuth }) {
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const token = params.get('token');

    if (token) {
      localStorage.setItem('token', token);
      setAuth(true);
      navigate('/', { replace: true });
    } else {
      navigate('/login?error=sso_failed', { replace: true });
    }
  }, [location, navigate, setAuth]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#F5F7FA]">
      <div className="text-center p-8 bg-white rounded-2xl shadow-lg border border-gray-100 max-w-sm w-full">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-[#12355B] mx-auto mb-4"></div>
        <h3 className="text-lg font-bold text-gray-800">Authenticating Citizen SSO</h3>
        <p className="text-xs text-gray-500 mt-2">Securing session credentials...</p>
      </div>
    </div>
  );
}
