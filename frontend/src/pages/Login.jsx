import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useUser } from '../context/UserContext';
import { setRememberMe } from '../lib/api';
import { GraduationCap, Check, Eye, EyeOff, Sparkles, ShieldCheck, Zap } from 'lucide-react';

function Login() {
  const [identifier, setIdentifier] = useState('');
  const [password, setPassword] = useState('');
  const [remember, setRemember] = useState(true);
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();
  const { login } = useUser();

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (busy) return;
    setError('');

    const value = identifier.trim();
    if (!value) {
      setError('Please enter your username or email.');
      return;
    }
    if (!value.includes('@')) {
      setError('Please enter the email you signed up with.');
      return;
    }

    setBusy(true);
    try {
      setRememberMe(remember);
      await login(value, password);
      navigate('/dashboard');
    } catch (err) {
      setError(err.message || 'Unable to log in. Please try again.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen w-full bg-white text-slate-800 lg:flex">
      {/* ---------- Left: blue gradient welcome panel ---------- */}
      <div className="relative flex w-full flex-col justify-between overflow-hidden bg-gradient-to-br from-blue-700 via-blue-600 to-indigo-800 px-8 py-10 text-white lg:w-1/2 lg:px-14 lg:py-14">
        {/* Decorative shapes */}
        <div className="pointer-events-none absolute -left-24 -top-24 h-72 w-72 rounded-full bg-white/10 blur-3xl" />
        <div className="pointer-events-none absolute -right-20 top-1/4 h-64 w-64 rounded-full bg-blue-300/20 blur-3xl" />
        <div className="pointer-events-none absolute bottom-16 left-10 h-36 w-36 rotate-12 rounded-3xl border border-white/20" />
        <div className="pointer-events-none absolute -bottom-24 right-1/4 h-64 w-64 rounded-full border border-white/10" />
        <div className="pointer-events-none absolute right-16 top-16 h-16 w-16 rounded-2xl bg-white/10 rotate-6" />

        {/* Brand */}
        <div className="relative flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center rounded-xl bg-white/15 backdrop-blur">
            <GraduationCap className="h-6 w-6" />
          </div>
          <span className="text-lg font-bold tracking-wide">CampusLearn AI</span>
        </div>

        {/* Welcome copy */}
        <div className="relative max-w-lg py-10">
          <p className="text-sm font-semibold uppercase tracking-[0.25em] text-white/70">
            Welcome back
          </p>
          <h1 className="mt-4 text-4xl font-bold leading-tight lg:text-5xl">
            Turn your study material into answers.
          </h1>
          <p className="mt-5 text-base leading-7 text-white/80">
            Upload notes, PDFs, slides and handwritten pages, then ask the AI
            tutor anything. Get grounded answers with citations from your own
            material — plus general help whenever you need it.
          </p>
        </div>

        {/* Feature ticks */}
        <ul className="relative space-y-3 text-sm text-white/85">
          <li className="flex items-center gap-3">
            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-white/15">
              <Check className="h-3.5 w-3.5" />
            </span>
            RAG answers cited from your uploaded material
          </li>
          <li className="flex items-center gap-3">
            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-white/15">
              <Sparkles className="h-3.5 w-3.5" />
            </span>
            Summaries, flashcards, quizzes and study plans
          </li>
          <li className="flex items-center gap-3">
            <span className="flex h-6 w-6 items-center justify-center rounded-full bg-white/15">
              <ShieldCheck className="h-3.5 w-3.5" />
            </span>
            Your files stay private to your account
          </li>
        </ul>
      </div>

      {/* ---------- Right: white sign-in form ---------- */}
      <div className="flex w-full items-center justify-center bg-white px-6 py-14 lg:w-1/2 lg:px-16">
        <div className="w-full max-w-md">
          <div className="flex items-center gap-2 text-blue-600 lg:hidden">
            <GraduationCap className="h-6 w-6" />
            <span className="font-bold">CampusLearn AI</span>
          </div>

          <h2 className="mt-6 text-3xl font-bold text-slate-900 lg:mt-0">
            Sign in
          </h2>
          <p className="mt-2 text-sm text-slate-500">
            Welcome back! Please enter your details.
          </p>

          <form className="mt-8 space-y-5" onSubmit={handleSubmit}>
            <div>
              <label
                htmlFor="identifier"
                className="mb-2 block text-sm font-medium text-slate-700"
              >
                Username or Email
              </label>
              <input
                id="identifier"
                type="text"
                autoComplete="username"
                placeholder="you@example.com"
                value={identifier}
                onChange={(e) => setIdentifier(e.target.value)}
                required
                className="w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-900 placeholder-slate-400 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20"
              />
            </div>

            <div>
              <label
                htmlFor="password"
                className="mb-2 block text-sm font-medium text-slate-700"
              >
                Password
              </label>
              <div className="relative">
                <input
                  id="password"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="current-password"
                  placeholder="Enter your password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  className="w-full rounded-xl border border-slate-200 bg-white px-4 py-3 pr-12 text-sm text-slate-900 placeholder-slate-400 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                >
                  {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                </button>
              </div>
            </div>

            <div className="flex items-center justify-between">
              <label className="flex cursor-pointer items-center gap-2 text-sm text-slate-600">
                <input
                  type="checkbox"
                  checked={remember}
                  onChange={(e) => setRemember(e.target.checked)}
                  className="h-4 w-4 rounded border-slate-300 text-blue-600 focus:ring-blue-500"
                />
                Remember me
              </label>
              <button
                type="button"
                className="text-sm font-medium text-blue-600 hover:underline"
              >
                Forgot password?
              </button>
            </div>

            {error ? (
              <p className="rounded-xl border border-red-100 bg-red-50 px-4 py-3 text-sm text-red-600">
                {error}
              </p>
            ) : null}

            <button
              type="submit"
              disabled={busy}
              className="flex w-full items-center justify-center gap-2 rounded-xl bg-blue-600 px-4 py-3 text-sm font-semibold text-white shadow-lg shadow-blue-600/25 transition hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500/40 disabled:opacity-60"
            >
              <Zap className="h-4 w-4" />
              {busy ? 'Signing in…' : 'Sign in'}
            </button>
          </form>

          <p className="mt-6 text-center text-sm text-slate-500">
            Don&apos;t have an account?{' '}
            <Link to="/register" className="font-semibold text-blue-600 hover:underline">
              Sign up
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}

export default Login;
