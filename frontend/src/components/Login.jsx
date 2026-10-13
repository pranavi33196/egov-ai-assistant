import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { auth, API_URL } from '../services/api';
import { Lock, ShieldCheck, Mail, User, KeyRound, ArrowRight, CheckCircle, AlertCircle, ArrowLeft, ShieldAlert } from 'lucide-react';

export default function Login({ setAuth }) {
  // Modes: 'login', '2fa', 'register', 'register_verify', 'forgot', 'reset'
  const [mode, setMode] = useState('login');
  
  // Login / Register Form Fields
  const [fullName, setFullName] = useState('');
  const [identifier, setIdentifier] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [otp, setOtp] = useState('');
  const [newPassword, setNewPassword] = useState('');
  
  // Status & Feedback
  const [devOtpNotification, setDevOtpNotification] = useState('');
  const [infoMessage, setInfoMessage] = useState('');
  const [errorMessage, setErrorMessage] = useState('');
  const [loading, setLoading] = useState(false);
  const [resendCooldown, setResendCooldown] = useState(0);

  const navigate = useNavigate();
  const location = useLocation();

  // Check URL params for OAuth callbacks or errors
  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const errorParam = params.get('error');
    if (errorParam) {
      if (errorParam === 'google_not_configured') {
        setErrorMessage('Google OAuth is not configured yet. Please add GOOGLE_CLIENT_ID in .env');
      } else if (errorParam === 'session_expired') {
        setErrorMessage('Your session expired. Please sign in again.');
      } else {
        setErrorMessage(`SSO Error: ${errorParam.replace(/_/g, ' ')}`);
      }
    }
  }, [location]);

  // Resend cooldown timer
  useEffect(() => {
    if (resendCooldown > 0) {
      const timer = setTimeout(() => setResendCooldown(resendCooldown - 1), 1000);
      return () => clearTimeout(timer);
    }
  }, [resendCooldown]);

  const clearMessages = () => {
    setErrorMessage('');
    setInfoMessage('');
    setDevOtpNotification('');
  };

  // ── Step 1 Login ─────────────────────────────────────────
  const handleLoginSubmit = async (e) => {
    e.preventDefault();
    clearMessages();
    setLoading(true);
    try {
      const data = await auth.login(identifier.trim(), password);
      if (data.requires_2fa) {
        setMode('2fa');
        setInfoMessage(data.message || 'Verification code sent to your email.');
        if (data.dev_otp) {
          setDevOtpNotification(`[Dev 2FA Code]: ${data.dev_otp}`);
          setOtp(data.dev_otp); // autofill for testing convenience
        }
      } else if (data.access_token) {
        localStorage.setItem('token', data.access_token);
        setAuth(true);
        navigate('/');
      }
    } catch (err) {
      const msg = err.response?.data?.detail || 'Invalid username/email or password.';
      setErrorMessage(msg);
    } finally {
      setLoading(false);
    }
  };

  // ── Step 2 2FA Verification ─────────────────────────────
  const handle2FASubmit = async (e) => {
    e.preventDefault();
    clearMessages();
    setLoading(true);
    try {
      const data = await auth.verify2FA(identifier.trim(), otp.trim());
      if (data.access_token) {
        localStorage.setItem('token', data.access_token);
        setAuth(true);
        navigate('/');
      }
    } catch (err) {
      const msg = err.response?.data?.detail || 'Invalid verification code.';
      setErrorMessage(msg);
    } finally {
      setLoading(false);
    }
  };

  // ── Registration ────────────────────────────────────────
  const handleRegisterSubmit = async (e) => {
    e.preventDefault();
    clearMessages();
    if (password !== confirmPassword) {
      setErrorMessage('Passwords do not match.');
      return;
    }
    if (password.length < 8) {
      setErrorMessage('Password must be at least 8 characters.');
      return;
    }

    setLoading(true);
    try {
      const data = await auth.register({
        full_name: fullName.trim(),
        email: identifier.trim(),
        password,
        confirm_password: confirmPassword
      });
      setMode('register_verify');
      setInfoMessage(data.message || 'Account created! Enter the verification code sent to your email.');
      if (data.dev_otp) {
        setDevOtpNotification(`[Dev OTP Code]: ${data.dev_otp}`);
        setOtp(data.dev_otp);
      }
    } catch (err) {
      const msg = err.response?.data?.detail || 'Registration failed. Please check your details.';
      setErrorMessage(msg);
    } finally {
      setLoading(false);
    }
  };

  // ── Registration OTP Verify ─────────────────────────────
  const handleRegisterVerifySubmit = async (e) => {
    e.preventDefault();
    clearMessages();
    setLoading(true);
    try {
      const data = await auth.verifyOTP({
        email: identifier.trim(),
        otp: otp.trim(),
        purpose: 'register'
      });
      setInfoMessage(data.message + ' You can now log in.');
      setMode('login');
      setPassword('');
      setOtp('');
    } catch (err) {
      const msg = err.response?.data?.detail || 'Invalid verification code.';
      setErrorMessage(msg);
    } finally {
      setLoading(false);
    }
  };

  // ── Forgot Password Request ─────────────────────────────
  const handleForgotPasswordSubmit = async (e) => {
    e.preventDefault();
    clearMessages();
    setLoading(true);
    try {
      const data = await auth.forgotPassword(identifier.trim());
      setInfoMessage(data.message || 'Reset code sent to your email.');
      setMode('reset');
    } catch (err) {
      setErrorMessage(err.response?.data?.detail || 'Unable to process request.');
    } finally {
      setLoading(false);
    }
  };

  // ── Reset Password Submit ───────────────────────────────
  const handleResetPasswordSubmit = async (e) => {
    e.preventDefault();
    clearMessages();
    if (newPassword.length < 8) {
      setErrorMessage('Password must be at least 8 characters.');
      return;
    }
    setLoading(true);
    try {
      const data = await auth.resetPassword(identifier.trim(), otp.trim(), newPassword);
      setInfoMessage(data.message || 'Password successfully reset! Please log in.');
      setMode('login');
      setPassword('');
      setOtp('');
    } catch (err) {
      setErrorMessage(err.response?.data?.detail || 'Reset failed. Verify your code and try again.');
    } finally {
      setLoading(false);
    }
  };

  // ── Instant Demo Login ─────────────────────────────────────
  const handleInstantDemoLogin = async () => {
    clearMessages();
    setLoading(true);
    try {
      const data = await auth.demoLogin();
      if (data.access_token) {
        localStorage.setItem('token', data.access_token);
        setAuth(true);
        navigate('/');
      }
    } catch (err) {
      setErrorMessage('Instant access failed. Please try normal login.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-[#F5F7FA] px-4 py-8">
      <div className="max-w-md w-full bg-white rounded-3xl shadow-xl overflow-hidden border border-gray-100 transition-all">
        
        {/* Header Banner with Clean Tricolor Emblem */}
        <div className="bg-[#12355B] p-7 text-center text-white relative">
          <div className="flex justify-center mb-3">
            <div className="w-14 h-14 rounded-2xl bg-white/10 flex items-center justify-center border border-white/20 shadow-inner">
              <svg className="w-10 h-7 rounded shadow-xs" viewBox="0 0 900 600">
                <rect width="900" height="200" fill="#FF9933"/>
                <rect y="200" width="900" height="200" fill="#FFFFFF"/>
                <rect y="400" width="900" height="200" fill="#138808"/>
                <circle cx="450" cy="300" r="80" fill="none" stroke="#000080" strokeWidth="12"/>
                <circle cx="450" cy="300" r="16" fill="#000080"/>
              </svg>
            </div>
          </div>
          <h1 className="text-2xl font-extrabold tracking-tight">e-Gov AI Assistant</h1>
          <p className="text-xs mt-1.5 opacity-85 font-medium tracking-wide">
            Multilingual AI Gateway for Citizen Services
          </p>
          <div className="mt-3.5 inline-flex items-center space-x-1.5 bg-white/10 px-3 py-1 rounded-full text-xs font-semibold backdrop-blur-sm border border-white/15">
            <ShieldCheck size={14} className="text-emerald-400" />
            <span>Secure Government SSO Gateway</span>
          </div>
        </div>

        <div className="p-7">
          
          {/* Notifications */}
          {errorMessage && (
            <div className="mb-5 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-xl text-sm flex items-start shadow-2xs">
              <AlertCircle size={18} className="mr-2.5 mt-0.5 flex-shrink-0 text-red-500" />
              <span>{errorMessage}</span>
            </div>
          )}

          {infoMessage && (
            <div className="mb-5 bg-emerald-50 border border-emerald-200 text-emerald-800 px-4 py-3 rounded-xl text-sm flex items-start shadow-2xs">
              <CheckCircle size={18} className="mr-2.5 mt-0.5 flex-shrink-0 text-emerald-600" />
              <span>{infoMessage}</span>
            </div>
          )}

          {devOtpNotification && (
            <div className="mb-5 bg-amber-50 border border-amber-200 text-amber-900 px-4 py-3 rounded-xl text-sm flex items-start shadow-2xs">
              <KeyRound size={18} className="mr-2.5 mt-0.5 flex-shrink-0 text-amber-600" />
              <div>
                <strong className="font-semibold">{devOtpNotification}</strong>
                <p className="text-xs text-amber-700 mt-0.5">Development Mode: OTP auto-filled for instant testing.</p>
              </div>
            </div>
          )}

          {/* ════════════════════ MODE: LOGIN ════════════════════ */}
          {mode === 'login' && (
            <div>
              {/* Tab Selector */}
              <div className="flex bg-gray-100 p-1 rounded-xl mb-6 text-sm font-semibold">
                <button
                  type="button"
                  onClick={() => { clearMessages(); setMode('login'); }}
                  className="flex-1 py-2 rounded-lg bg-white text-[#12355B] shadow-sm transition-all text-center"
                >
                  Citizen Login
                </button>
                <button
                  type="button"
                  onClick={() => { clearMessages(); setMode('register'); }}
                  className="flex-1 py-2 rounded-lg text-gray-500 hover:text-gray-900 transition-all text-center"
                >
                  Register
                </button>
              </div>

              <form onSubmit={handleLoginSubmit} className="space-y-4">
                <div>
                  <label className="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-1.5">
                    Email Address or Username
                  </label>
                  <div className="relative">
                    <Mail size={18} className="absolute left-3.5 top-3 text-gray-400" />
                    <input
                      type="text"
                      value={identifier}
                      onChange={(e) => setIdentifier(e.target.value)}
                      placeholder="citizen@gov.in or username"
                      className="w-full pl-10 pr-4 py-2.5 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-[#1D7874] focus:border-transparent outline-none text-sm transition-all shadow-inner"
                      required
                    />
                  </div>
                </div>

                <div>
                  <div className="flex justify-between items-center mb-1.5">
                    <label className="block text-xs font-bold text-gray-700 uppercase tracking-wider">
                      Password
                    </label>
                    <button
                      type="button"
                      onClick={() => { clearMessages(); setMode('forgot'); }}
                      className="text-xs text-[#1D7874] hover:underline font-semibold"
                    >
                      Forgot password?
                    </button>
                  </div>
                  <div className="relative">
                    <Lock size={18} className="absolute left-3.5 top-3 text-gray-400" />
                    <input
                      type="password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="••••••••"
                      className="w-full pl-10 pr-4 py-2.5 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-[#1D7874] focus:border-transparent outline-none text-sm transition-all shadow-inner"
                      required
                    />
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full mt-2 bg-[#12355B] hover:bg-[#0e2a48] text-white font-bold py-3 rounded-xl flex items-center justify-center transition-all shadow-md hover:shadow-lg disabled:opacity-60"
                >
                  {loading ? (
                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                  ) : (
                    <>
                      <span>Continue to 2FA Verification</span>
                      <ArrowRight size={18} className="ml-2" />
                    </>
                  )}
                </button>

                {/* 1-Click Instant Demo Button */}
                <button
                  type="button"
                  onClick={handleInstantDemoLogin}
                  disabled={loading}
                  className="w-full mt-2 bg-gradient-to-r from-[#1D7874] to-teal-700 hover:from-teal-700 hover:to-teal-800 text-white font-bold py-2.5 rounded-xl flex items-center justify-center transition-all shadow-sm text-xs tracking-wide"
                >
                  <span>⚡ 1-Click Instant Citizen Access (Pranavi)</span>
                </button>
              </form>

              {/* SSO Divider */}
              <div className="relative my-6 text-center">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-gray-200"></div>
                </div>
                <span className="relative bg-white px-3 text-xs uppercase tracking-wider font-semibold text-gray-400">
                  Or Sign In With
                </span>
              </div>

              {/* Google SSO Button */}
              <a
                href={`${API_URL}/oauth/google`}
                className="w-full border border-gray-300 hover:bg-gray-50 text-gray-700 font-semibold py-2.5 px-4 rounded-xl flex items-center justify-center space-x-3 transition-colors text-sm shadow-2xs"
              >
                <svg className="w-4 h-4" viewBox="0 0 24 24">
                  <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                  <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                  <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"/>
                  <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"/>
                </svg>
                <span>Government SSO via Google OIDC</span>
              </a>
            </div>
          )}

          {/* ════════════════════ MODE: 2FA VERIFY ════════════════════ */}
          {mode === '2fa' && (
            <div>
              <button
                type="button"
                onClick={() => { clearMessages(); setMode('login'); }}
                className="flex items-center text-xs font-semibold text-gray-500 hover:text-gray-800 mb-4 transition-colors"
              >
                <ArrowLeft size={14} className="mr-1" />
                Back to Login
              </button>

              <div className="text-center mb-6">
                <div className="w-12 h-12 bg-teal-50 text-[#1D7874] rounded-full flex items-center justify-center mx-auto mb-3 shadow-inner">
                  <KeyRound size={24} />
                </div>
                <h2 className="text-lg font-bold text-gray-800">Two-Factor Authentication</h2>
                <p className="text-xs text-gray-500 mt-1">
                  Enter the 6-digit verification code for <strong className="text-gray-700">{identifier}</strong>
                </p>
              </div>

              <form onSubmit={handle2FASubmit} className="space-y-5">
                <div>
                  <input
                    type="text"
                    maxLength={6}
                    value={otp}
                    onChange={(e) => setOtp(e.target.value.replace(/\D/g, ''))}
                    placeholder="• • • • • •"
                    className="w-full text-center text-2xl tracking-[12px] font-mono py-3 bg-gray-50 border-2 border-gray-200 rounded-xl focus:ring-2 focus:ring-[#1D7874] focus:border-[#1D7874] outline-none transition-all shadow-inner"
                    required
                  />
                </div>

                <button
                  type="submit"
                  disabled={loading || otp.length < 6}
                  className="w-full bg-[#1D7874] hover:bg-teal-700 text-white font-bold py-3 rounded-xl flex items-center justify-center transition-all shadow-md disabled:opacity-50"
                >
                  {loading ? (
                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                  ) : (
                    <>
                      <span>Verify & Access Dashboard</span>
                      <ShieldCheck size={18} className="ml-2" />
                    </>
                  )}
                </button>
              </form>

              <div className="mt-5 text-center">
                <button
                  type="button"
                  onClick={() => handleResendOTP('login_2fa')}
                  disabled={resendCooldown > 0}
                  className="text-xs font-semibold text-[#1D7874] hover:underline disabled:text-gray-400"
                >
                  {resendCooldown > 0 ? `Resend code in ${resendCooldown}s` : 'Resend verification code'}
                </button>
              </div>
            </div>
          )}

          {/* ════════════════════ MODE: REGISTER ════════════════════ */}
          {mode === 'register' && (
            <div>
              {/* Tab Selector */}
              <div className="flex bg-gray-100 p-1 rounded-xl mb-6 text-sm font-semibold">
                <button
                  type="button"
                  onClick={() => { clearMessages(); setMode('login'); }}
                  className="flex-1 py-2 rounded-lg text-gray-500 hover:text-gray-900 transition-all text-center"
                >
                  Citizen Login
                </button>
                <button
                  type="button"
                  onClick={() => { clearMessages(); setMode('register'); }}
                  className="flex-1 py-2 rounded-lg bg-white text-[#12355B] shadow-sm transition-all text-center"
                >
                  Register
                </button>
              </div>

              <form onSubmit={handleRegisterSubmit} className="space-y-3.5">
                <div>
                  <label className="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-1">
                    Full Name
                  </label>
                  <div className="relative">
                    <User size={18} className="absolute left-3.5 top-3 text-gray-400" />
                    <input
                      type="text"
                      value={fullName}
                      onChange={(e) => setFullName(e.target.value)}
                      placeholder="e.g. Pranavi"
                      className="w-full pl-10 pr-4 py-2.5 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-[#1D7874] focus:border-transparent outline-none text-sm transition-all shadow-inner"
                      required
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-1">
                    Email Address or Username
                  </label>
                  <div className="relative">
                    <Mail size={18} className="absolute left-3.5 top-3 text-gray-400" />
                    <input
                      type="text"
                      value={identifier}
                      onChange={(e) => setIdentifier(e.target.value)}
                      placeholder="citizen@gov.in or username"
                      className="w-full pl-10 pr-4 py-2.5 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-[#1D7874] focus:border-transparent outline-none text-sm transition-all shadow-inner"
                      required
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-1">
                    Password (min. 8 characters)
                  </label>
                  <div className="relative">
                    <Lock size={18} className="absolute left-3.5 top-3 text-gray-400" />
                    <input
                      type="password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="••••••••"
                      className="w-full pl-10 pr-4 py-2.5 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-[#1D7874] focus:border-transparent outline-none text-sm transition-all shadow-inner"
                      required
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-1">
                    Confirm Password
                  </label>
                  <div className="relative">
                    <Lock size={18} className="absolute left-3.5 top-3 text-gray-400" />
                    <input
                      type="password"
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      placeholder="••••••••"
                      className="w-full pl-10 pr-4 py-2.5 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-[#1D7874] focus:border-transparent outline-none text-sm transition-all shadow-inner"
                      required
                    />
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full mt-3 bg-[#1D7874] hover:bg-teal-700 text-white font-bold py-3 rounded-xl flex items-center justify-center transition-all shadow-md disabled:opacity-60"
                >
                  {loading ? (
                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                  ) : (
                    <>
                      <span>Create Account & Send OTP</span>
                      <ArrowRight size={18} className="ml-2" />
                    </>
                  )}
                </button>
              </form>
            </div>
          )}

          {/* ════════════════════ MODE: REGISTER VERIFY ════════════════════ */}
          {mode === 'register_verify' && (
            <div>
              <div className="text-center mb-6">
                <div className="w-12 h-12 bg-blue-50 text-[#12355B] rounded-full flex items-center justify-center mx-auto mb-3 shadow-inner">
                  <ShieldCheck size={24} />
                </div>
                <h2 className="text-lg font-bold text-gray-800">Verify Your Account</h2>
                <p className="text-xs text-gray-500 mt-1">
                  Enter the 6-digit registration code for <strong className="text-gray-700">{identifier}</strong>
                </p>
              </div>

              <form onSubmit={handleRegisterVerifySubmit} className="space-y-5">
                <div>
                  <input
                    type="text"
                    maxLength={6}
                    value={otp}
                    onChange={(e) => setOtp(e.target.value.replace(/\D/g, ''))}
                    placeholder="• • • • • •"
                    className="w-full text-center text-2xl tracking-[12px] font-mono py-3 bg-gray-50 border-2 border-gray-200 rounded-xl focus:ring-2 focus:ring-[#12355B] focus:border-[#12355B] outline-none transition-all shadow-inner"
                    required
                  />
                </div>

                <button
                  type="submit"
                  disabled={loading || otp.length < 6}
                  className="w-full bg-[#12355B] hover:bg-[#0e2a48] text-white font-bold py-3 rounded-xl flex items-center justify-center transition-all shadow-md disabled:opacity-50"
                >
                  {loading ? (
                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                  ) : (
                    <>
                      <span>Activate Account</span>
                      <CheckCircle size={18} className="ml-2" />
                    </>
                  )}
                </button>
              </form>

              <div className="mt-5 text-center">
                <button
                  type="button"
                  onClick={() => handleResendOTP('register')}
                  disabled={resendCooldown > 0}
                  className="text-xs font-semibold text-[#1D7874] hover:underline disabled:text-gray-400"
                >
                  {resendCooldown > 0 ? `Resend code in ${resendCooldown}s` : 'Resend verification code'}
                </button>
              </div>
            </div>
          )}

          {/* ════════════════════ MODE: FORGOT PASSWORD ════════════════════ */}
          {mode === 'forgot' && (
            <div>
              <button
                type="button"
                onClick={() => { clearMessages(); setMode('login'); }}
                className="flex items-center text-xs font-semibold text-gray-500 hover:text-gray-800 mb-4 transition-colors"
              >
                <ArrowLeft size={14} className="mr-1" />
                Back to Login
              </button>

              <div className="text-center mb-6">
                <div className="w-12 h-12 bg-amber-50 text-amber-600 rounded-full flex items-center justify-center mx-auto mb-3 shadow-inner">
                  <ShieldAlert size={24} />
                </div>
                <h2 className="text-lg font-bold text-gray-800">Reset Password</h2>
                <p className="text-xs text-gray-500 mt-1">
                  Enter your registered username or email to receive a recovery code.
                </p>
              </div>

              <form onSubmit={handleForgotPasswordSubmit} className="space-y-4">
                <div>
                  <label className="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-1.5">
                    Email Address or Username
                  </label>
                  <div className="relative">
                    <Mail size={18} className="absolute left-3.5 top-3 text-gray-400" />
                    <input
                      type="text"
                      value={identifier}
                      onChange={(e) => setIdentifier(e.target.value)}
                      placeholder="citizen@gov.in or username"
                      className="w-full pl-10 pr-4 py-2.5 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-[#12355B] focus:border-transparent outline-none text-sm transition-all shadow-inner"
                      required
                    />
                  </div>
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full bg-[#12355B] hover:bg-[#0e2a48] text-white font-bold py-3 rounded-xl flex items-center justify-center transition-all shadow-md disabled:opacity-60"
                >
                  {loading ? (
                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                  ) : (
                    <>
                      <span>Send Recovery Code</span>
                      <ArrowRight size={18} className="ml-2" />
                    </>
                  )}
                </button>
              </form>
            </div>
          )}

          {/* ════════════════════ MODE: RESET PASSWORD ════════════════════ */}
          {mode === 'reset' && (
            <div>
              <div className="text-center mb-6">
                <h2 className="text-lg font-bold text-gray-800">Set New Password</h2>
                <p className="text-xs text-gray-500 mt-1">
                  Enter the recovery OTP and your new password.
                </p>
              </div>

              <form onSubmit={handleResetPasswordSubmit} className="space-y-4">
                <div>
                  <label className="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-1">
                    6-Digit OTP Code
                  </label>
                  <input
                    type="text"
                    maxLength={6}
                    value={otp}
                    onChange={(e) => setOtp(e.target.value.replace(/\D/g, ''))}
                    placeholder="• • • • • •"
                    className="w-full text-center text-xl tracking-widest font-mono py-2 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-[#12355B] outline-none shadow-inner"
                    required
                  />
                </div>

                <div>
                  <label className="block text-xs font-bold text-gray-700 uppercase tracking-wider mb-1">
                    New Password
                  </label>
                  <input
                    type="password"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    placeholder="••••••••"
                    className="w-full px-4 py-2.5 bg-gray-50 border border-gray-200 rounded-xl focus:ring-2 focus:ring-[#12355B] outline-none text-sm shadow-inner"
                    required
                  />
                </div>

                <button
                  type="submit"
                  disabled={loading}
                  className="w-full bg-[#12355B] hover:bg-[#0e2a48] text-white font-bold py-3 rounded-xl flex items-center justify-center transition-all shadow-md disabled:opacity-60"
                >
                  {loading ? (
                    <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                  ) : (
                    <span>Update Password & Login</span>
                  )}
                </button>
              </form>
            </div>
          )}

        </div>

        {/* Footer info */}
        <div className="bg-gray-50 p-4 text-center border-t border-gray-100">
          <p className="text-[11px] text-gray-400">
            Protected by Cloudflare Turnstile & 256-bit AES SSO Encryption
          </p>
        </div>

      </div>
    </div>
  );
}
