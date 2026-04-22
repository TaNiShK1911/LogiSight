import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
import { Zap, AlertCircle, Eye, EyeOff, ChevronDown, Shield, Building2, Truck, User } from 'lucide-react';
import { useAuth } from '../hooks/useAuth';

const schema = z.object({
  email: z.string().email('Enter a valid email address'),
  password: z.string().min(6, 'Password must be at least 6 characters'),
});

type FormData = z.infer<typeof schema>;

const TEST_ACCOUNTS = [
  {
    label: 'Super Admin',
    email: 'super_admin@logisight.dev',
    password: 'TestPass123!',
    description: 'Platform-wide access, manages all companies',
    icon: Shield,
    color: 'text-amber-400',
    bg: 'bg-amber-950/40 border-amber-800/50 hover:bg-amber-950/70',
  },
  {
    label: 'Client Admin',
    email: 'client.admin@acmeco.dev',
    password: 'TestPass123!',
    description: 'AcmeCo Logistics — admin access',
    icon: Building2,
    color: 'text-sky-400',
    bg: 'bg-sky-950/40 border-sky-800/50 hover:bg-sky-950/70',
  },
  {
    label: 'Client User',
    email: 'client.user@acmeco.dev',
    password: 'TestPass123!',
    description: 'AcmeCo Logistics — standard access',
    icon: User,
    color: 'text-sky-300',
    bg: 'bg-sky-950/30 border-sky-800/40 hover:bg-sky-950/60',
  },
  {
    label: 'Forwarder Admin',
    email: 'fwd.admin@fastfreight.dev',
    password: 'TestPass123!',
    description: 'FastFreight Co — admin access',
    icon: Truck,
    color: 'text-emerald-400',
    bg: 'bg-emerald-950/40 border-emerald-800/50 hover:bg-emerald-950/70',
  },
  {
    label: 'Forwarder User',
    email: 'fwd.user@fastfreight.dev',
    password: 'TestPass123!',
    description: 'FastFreight Co — standard access',
    icon: User,
    color: 'text-emerald-300',
    bg: 'bg-emerald-950/30 border-emerald-800/40 hover:bg-emerald-950/60',
  },
];

export function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [devOpen, setDevOpen] = useState(false);
  const [quickLoading, setQuickLoading] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors, isSubmitting },
  } = useForm<FormData>({ resolver: zodResolver(schema) });

  const onSubmit = async (data: FormData) => {
    setError(null);
    try {
      await login(data.email, data.password);
      navigate('/app');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Invalid credentials. Please try again.';
      setError(msg);
    }
  };

  const quickLogin = async (email: string, password: string) => {
    setError(null);
    setQuickLoading(email);
    try {
      await login(email, password);
      navigate('/app');
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Login failed.';
      setError(msg);
    } finally {
      setQuickLoading(null);
    }
  };

  const fillCredentials = (email: string, password: string) => {
    setValue('email', email);
    setValue('password', password);
  };

  return (
    <div className="min-h-screen bg-slate-950 flex">
      {/* Left panel */}
      <div className="hidden lg:flex flex-1 flex-col justify-between p-12 bg-slate-900/50 border-r border-slate-800">
        <Link to="/" className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-sky-500 flex items-center justify-center">
            <Zap className="w-4 h-4 text-white" />
          </div>
          <span className="font-bold text-lg text-slate-100">LogiSight</span>
        </Link>
        <div className="max-w-sm">
          <h2 className="text-2xl font-bold text-slate-100 mb-3">
            AI-Powered Freight Audit Intelligence
          </h2>
          <p className="text-slate-400 leading-relaxed">
            Automatically map forwarder charge names to your internal standards, detect invoice anomalies, and query your freight data in plain English.
          </p>
        </div>
        <p className="text-xs text-slate-600">&copy; {new Date().getFullYear()} LogiSight</p>
      </div>

      {/* Right panel */}
      <div className="flex-1 flex flex-col items-center justify-center px-6 py-12 overflow-y-auto">
        <div className="w-full max-w-sm">
          <div className="lg:hidden flex items-center gap-2 mb-10">
            <div className="w-7 h-7 rounded-lg bg-sky-500 flex items-center justify-center">
              <Zap className="w-3.5 h-3.5 text-white" />
            </div>
            <span className="font-bold text-slate-100">LogiSight</span>
          </div>

          <h1 className="text-2xl font-bold text-slate-100 mb-2">Welcome back</h1>
          <p className="text-sm text-slate-400 mb-8">Sign in to your account to continue</p>

          {error && (
            <div className="flex items-start gap-2.5 p-3 rounded-lg bg-red-950/60 border border-red-800 mb-6">
              <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0 mt-0.5" />
              <p className="text-sm text-red-300">{error}</p>
            </div>
          )}

          <form onSubmit={handleSubmit(onSubmit)} className="space-y-5" noValidate>
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1.5">
                Email address
              </label>
              <input
                {...register('email')}
                type="email"
                autoComplete="email"
                placeholder="you@company.com"
                className="w-full px-3 py-2.5 rounded-lg border border-slate-700 bg-slate-900 text-slate-100 placeholder-slate-500 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-transparent transition-shadow"
              />
              {errors.email && (
                <p className="mt-1.5 text-xs text-red-400">{errors.email.message}</p>
              )}
            </div>

            <div>
              <label className="block text-sm font-medium text-slate-300 mb-1.5">
                Password
              </label>
              <div className="relative">
                <input
                  {...register('password')}
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="current-password"
                  placeholder="••••••••"
                  className="w-full px-3 py-2.5 pr-10 rounded-lg border border-slate-700 bg-slate-900 text-slate-100 placeholder-slate-500 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-transparent transition-shadow"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((v) => !v)}
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 transition-colors"
                >
                  {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              {errors.password && (
                <p className="mt-1.5 text-xs text-red-400">{errors.password.message}</p>
              )}
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full py-2.5 rounded-lg bg-sky-500 hover:bg-sky-400 disabled:opacity-60 disabled:cursor-not-allowed text-white font-semibold text-sm transition-colors flex items-center justify-center gap-2"
            >
              {isSubmitting ? (
                <>
                  <span className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Signing in…
                </>
              ) : (
                'Sign in'
              )}
            </button>
          </form>

          {/* Dev Quick Login */}
          <div className="mt-8">
            <button
              type="button"
              onClick={() => setDevOpen((v) => !v)}
              className="w-full flex items-center justify-between px-3 py-2 rounded-lg border border-dashed border-slate-700 text-slate-500 hover:border-slate-500 hover:text-slate-400 transition-colors text-xs font-medium"
            >
              <span>Dev — Quick Login</span>
              <ChevronDown
                className={`w-3.5 h-3.5 transition-transform duration-200 ${devOpen ? 'rotate-180' : ''}`}
              />
            </button>

            {devOpen && (
              <div className="mt-3 space-y-2">
                <p className="text-xs text-slate-600 mb-3">
                  All accounts use password: <span className="font-mono text-slate-500">TestPass123!</span>
                </p>
                {TEST_ACCOUNTS.map((acc) => {
                  const Icon = acc.icon;
                  const isLoading = quickLoading === acc.email;
                  return (
                    <div
                      key={acc.email}
                      className={`flex items-center gap-3 p-2.5 rounded-lg border cursor-pointer transition-colors ${acc.bg}`}
                      onClick={() => !quickLoading && quickLogin(acc.email, acc.password)}
                    >
                      <div className="flex-shrink-0">
                        <Icon className={`w-4 h-4 ${acc.color}`} />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className={`text-xs font-semibold ${acc.color}`}>{acc.label}</p>
                        <p className="text-xs text-slate-500 truncate">{acc.description}</p>
                      </div>
                      <div className="flex-shrink-0 flex items-center gap-2">
                        {isLoading ? (
                          <span className="w-3.5 h-3.5 border-2 border-slate-600 border-t-slate-400 rounded-full animate-spin" />
                        ) : (
                          <>
                            <button
                              type="button"
                              onClick={(e) => {
                                e.stopPropagation();
                                fillCredentials(acc.email, acc.password);
                              }}
                              className="text-slate-600 hover:text-slate-400 text-xs transition-colors px-1"
                              title="Fill credentials"
                            >
                              Fill
                            </button>
                            <span className="text-slate-600 text-xs">|</span>
                            <span className="text-slate-600 text-xs">Login</span>
                          </>
                        )}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          <p className="mt-6 text-center text-xs text-slate-500">
            Platform access is by invitation only.{' '}
            <Link to="/" className="text-sky-400 hover:text-sky-300 transition-colors">
              Learn more
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
