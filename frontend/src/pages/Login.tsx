import { useState } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { z } from 'zod';
import { zodResolver } from '@hookform/resolvers/zod';
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
    description: 'Platform-wide access',
    icon: 'shield',
    color: 'text-error',
    bg: 'bg-error-container/30 border-error-container',
  },
  {
    label: 'Client Admin',
    email: 'client.admin@acmeco.dev',
    password: 'TestPass123!',
    description: 'AcmeCo Logistics — admin',
    icon: 'domain',
    color: 'text-secondary',
    bg: 'bg-secondary-fixed border-secondary-fixed-dim',
  },
  {
    label: 'Client User',
    email: 'client.user@acmeco.dev',
    password: 'TestPass123!',
    description: 'AcmeCo Logistics — standard',
    icon: 'person',
    color: 'text-secondary',
    bg: 'bg-surface-container border-surface-container-high',
  },
  {
    label: 'Forwarder Admin',
    email: 'fwd.admin@fastfreight.dev',
    password: 'TestPass123!',
    description: 'FastFreight Co — admin',
    icon: 'local_shipping',
    color: 'text-primary',
    bg: 'bg-surface-container border-surface-container-highest',
  },
  {
    label: 'Forwarder User',
    email: 'fwd.user@fastfreight.dev',
    password: 'TestPass123!',
    description: 'FastFreight Co — standard',
    icon: 'person',
    color: 'text-primary',
    bg: 'bg-surface-container-low border-surface-container',
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
    <main className="w-full flex items-center justify-center min-h-screen bg-background font-body-md text-on-surface">
      <div className="flex flex-col w-full h-full min-h-[calc(100vh-80px)] justify-center items-center relative overflow-hidden bg-background py-10">
        
        {/* Ambient Background Decorations */}
        <div className="absolute inset-0 z-0 pointer-events-none opacity-40">
          <div className="absolute top-[-10%] left-[-5%] w-1/2 h-1/2 bg-secondary-fixed rounded-full blur-[100px] opacity-30 mix-blend-multiply"></div>
          <div className="absolute bottom-[-10%] right-[-5%] w-1/2 h-1/2 bg-primary-fixed rounded-full blur-[100px] opacity-30 mix-blend-multiply"></div>
        </div>

        {/* Login Card */}
        <div className="relative z-10 w-full max-w-[440px] px-gutter mx-auto">
          <div className="bg-surface-container-lowest rounded-[1.5rem] shadow-[0_20px_60px_-15px_rgba(0,0,0,0.08)] overflow-hidden">
            
            {/* Branding Header */}
            <div className="px-8 pt-10 pb-6 text-center">
              <div className="flex justify-center items-center mb-6">
                <img src="/logo.png" alt="LogiSight" className="h-12 w-auto object-contain" onError={(e) => { e.currentTarget.style.display = 'none'; }} />
              </div>
              <h1 className="font-headline-md-mobile text-headline-md-mobile text-on-surface mb-2 tracking-tight">LogiSight</h1>
              <p className="font-body-md text-body-md text-on-surface-variant">Secure Global Operations Portal</p>
            </div>

            {/* Error Message */}
            {error && (
              <div className="mx-8 mb-4 p-3 rounded-lg bg-error-container text-on-error-container flex items-start gap-2 text-sm">
                <span className="material-symbols-outlined text-[18px]">error</span>
                {error}
              </div>
            )}

            {/* Form Container */}
            <div className="px-8 pb-10">
              <form onSubmit={handleSubmit(onSubmit)} className="flex flex-col gap-6" noValidate>
                {/* Input Group: Email */}
                <div className="relative group">
                  <input
                    {...register('email')}
                    id="email"
                    type="email"
                    placeholder=" "
                    className={`peer w-full bg-transparent px-0 py-3 font-body-md text-body-md text-on-surface border-b-2 ${errors.email ? 'border-error focus:border-error' : 'border-outline-variant focus:border-primary'} outline-none transition-colors duration-300 placeholder-transparent`}
                  />
                  <label
                    htmlFor="email"
                    className={`absolute left-0 top-3 font-body-md text-body-md ${errors.email ? 'text-error' : 'text-on-surface-variant'} transition-all duration-300 peer-focus:-top-4 peer-focus:font-label-sm peer-focus:text-label-sm ${errors.email ? 'peer-focus:text-error' : 'peer-focus:text-primary'} peer-[&:not(:placeholder-shown)]:-top-4 peer-[&:not(:placeholder-shown)]:font-label-sm peer-[&:not(:placeholder-shown)]:text-label-sm cursor-text pointer-events-none`}
                  >
                    Work Email
                  </label>
                  {errors.email && (
                    <p className="absolute -bottom-5 left-0 text-[11px] text-error">{errors.email.message}</p>
                  )}
                </div>

                {/* Input Group: Password */}
                <div className="relative group mt-2">
                  <input
                    {...register('password')}
                    id="password"
                    type={showPassword ? 'text' : 'password'}
                    placeholder=" "
                    className={`peer w-full bg-transparent px-0 py-3 font-body-md text-body-md text-on-surface border-b-2 ${errors.password ? 'border-error focus:border-error' : 'border-outline-variant focus:border-primary'} outline-none transition-colors duration-300 placeholder-transparent`}
                  />
                  <label
                    htmlFor="password"
                    className={`absolute left-0 top-3 font-body-md text-body-md ${errors.password ? 'text-error' : 'text-on-surface-variant'} transition-all duration-300 peer-focus:-top-4 peer-focus:font-label-sm peer-focus:text-label-sm ${errors.password ? 'peer-focus:text-error' : 'peer-focus:text-primary'} peer-[&:not(:placeholder-shown)]:-top-4 peer-[&:not(:placeholder-shown)]:font-label-sm peer-[&:not(:placeholder-shown)]:text-label-sm cursor-text pointer-events-none`}
                  >
                    Password
                  </label>
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-0 top-3 text-on-surface-variant hover:text-primary transition-colors cursor-pointer outline-none"
                  >
                    <span className="material-symbols-outlined text-[20px]">
                      {showPassword ? 'visibility' : 'visibility_off'}
                    </span>
                  </button>
                  {errors.password && (
                    <p className="absolute -bottom-5 left-0 text-[11px] text-error">{errors.password.message}</p>
                  )}
                </div>

                {/* Utilities */}
                <div className="flex justify-between items-center mt-2">
                  <label className="flex items-center gap-2 cursor-pointer group">
                    <input type="checkbox" className="peer sr-only" />
                    <div className="w-4 h-4 rounded-[4px] bg-surface-container-low border border-outline-variant peer-checked:bg-primary peer-checked:border-primary flex items-center justify-center transition-colors">
                      <span className="material-symbols-outlined text-on-primary text-[12px] opacity-0 peer-checked:opacity-100 transition-opacity" style={{ fontVariationSettings: "'wght' 600" }}>check</span>
                    </div>
                    <span className="font-label-sm text-label-sm text-on-surface-variant group-hover:text-on-surface transition-colors">Remember me</span>
                  </label>
                  <a href="#" className="font-label-sm text-label-sm text-on-surface-variant hover:text-primary underline decoration-transparent hover:decoration-primary transition-all duration-300 ease-out">Forgot password?</a>
                </div>

                {/* Submit Button */}
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="mt-6 w-full py-4 bg-primary text-on-primary font-body-md text-body-md rounded-full hover:shadow-lg hover:-translate-y-[1px] transition-all duration-300 relative overflow-hidden group disabled:opacity-70 disabled:cursor-not-allowed"
                >
                  <span className="relative z-10 flex items-center justify-center gap-2">
                    {isSubmitting ? 'Authenticating...' : 'Secure Access'}
                    {!isSubmitting && <span className="material-symbols-outlined text-[18px] group-hover:translate-x-1 transition-transform duration-300">arrow_forward</span>}
                  </span>
                  <div className="absolute inset-0 bg-white/20 translate-y-full group-hover:translate-y-0 transition-transform duration-300 ease-out"></div>
                </button>
              </form>

              {/* Dev Quick Login */}
              <div className="mt-8 border-t border-surface-container pt-6">
                <button
                  type="button"
                  onClick={() => setDevOpen((v) => !v)}
                  className="w-full flex items-center justify-between px-3 py-2 rounded-lg border border-dashed border-outline-variant text-on-surface-variant hover:border-outline hover:text-on-surface transition-colors font-label-sm text-label-sm"
                >
                  <span>Dev — Quick Login</span>
                  <span className={`material-symbols-outlined text-[18px] transition-transform duration-200 ${devOpen ? 'rotate-180' : ''}`}>
                    expand_more
                  </span>
                </button>

                {devOpen && (
                  <div className="mt-3 space-y-2">
                    <p className="text-[11px] text-on-surface-variant mb-3 text-center">
                      All accounts use password: <span className="font-mono text-on-surface">TestPass123!</span>
                    </p>
                    {TEST_ACCOUNTS.map((acc) => {
                      const isLoading = quickLoading === acc.email;
                      return (
                        <div
                          key={acc.email}
                          className={`flex items-center gap-3 p-2.5 rounded-lg border cursor-pointer transition-colors ${acc.bg} hover:shadow-sm`}
                          onClick={() => !quickLoading && quickLogin(acc.email, acc.password)}
                        >
                          <div className="flex-shrink-0">
                            <span className={`material-symbols-outlined text-[18px] ${acc.color}`}>{acc.icon}</span>
                          </div>
                          <div className="flex-1 min-w-0">
                            <p className={`text-xs font-semibold ${acc.color}`}>{acc.label}</p>
                            <p className="text-[10px] text-on-surface-variant truncate">{acc.description}</p>
                          </div>
                          <div className="flex-shrink-0 flex items-center gap-2">
                            {isLoading ? (
                              <span className="w-3.5 h-3.5 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                            ) : (
                              <>
                                <button
                                  type="button"
                                  onClick={(e) => {
                                    e.stopPropagation();
                                    fillCredentials(acc.email, acc.password);
                                  }}
                                  className="text-on-surface-variant hover:text-primary text-[10px] transition-colors px-1 uppercase font-medium"
                                  title="Fill credentials"
                                >
                                  Fill
                                </button>
                                <span className="text-outline-variant text-xs">|</span>
                                <span className="text-on-surface-variant hover:text-primary text-[10px] transition-colors uppercase font-medium">Login</span>
                              </>
                            )}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>

            {/* Footer Area */}
            <div className="bg-surface-container py-4 px-8 border-t border-outline-variant/30">
              <p className="text-center font-label-sm text-label-sm text-on-surface-variant">
                Authorized personnel only. <a href="#" className="text-primary hover:underline">Compliance Policy</a>
              </p>
            </div>
            
          </div>
        </div>
      </div>
    </main>
  );
}
