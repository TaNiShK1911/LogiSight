import { useState } from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import {
  LayoutDashboard,
  FileText,
  Upload,
  BookOpen,
  MapPin,
  MessageSquare,
  Building2,
  LogOut,
  ChevronLeft,
  ChevronRight,
  Zap,
  Menu,
  X,
} from 'lucide-react';
import { useAuth } from '../hooks/useAuth';

interface NavItem {
  to: string;
  label: string;
  Icon: React.ElementType;
}

const SUPER_ADMIN_NAV: NavItem[] = [
  { to: '/app', label: 'Dashboard', Icon: LayoutDashboard },
  { to: '/app/companies', label: 'Companies', Icon: Building2 },
];

const CLIENT_NAV: NavItem[] = [
  { to: '/app', label: 'Dashboard', Icon: LayoutDashboard },
  { to: '/app/quotes', label: 'Quotes', Icon: FileText },
  { to: '/app/invoices', label: 'Invoices', Icon: Upload },
  { to: '/app/charge-master', label: 'Charge Master', Icon: BookOpen },
  { to: '/app/tracking', label: 'Tracking', Icon: MapPin },
  { to: '/app/copilot', label: 'Copilot', Icon: MessageSquare },
];

const FORWARDER_NAV: NavItem[] = [
  { to: '/app', label: 'Dashboard', Icon: LayoutDashboard },
  { to: '/app/quotes', label: 'Quotes', Icon: FileText },
  { to: '/app/invoices', label: 'Invoices', Icon: Upload },
  { to: '/app/tracking', label: 'Tracking', Icon: MapPin },
];

export function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [collapsed, setCollapsed] = useState(false);
  const [mobileOpen, setMobileOpen] = useState(false);

  const nav =
    user?.role === 'super_admin'
      ? SUPER_ADMIN_NAV
      : user?.role === 'forwarder'
      ? FORWARDER_NAV
      : CLIENT_NAV;

  const rolePill =
    user?.role === 'super_admin'
      ? { label: 'Super Admin', cls: 'bg-violet-900/60 text-violet-300 border-violet-800' }
      : user?.role === 'forwarder'
      ? { label: 'Forwarder', cls: 'bg-sky-900/60 text-sky-300 border-sky-800' }
      : { label: 'Client', cls: 'bg-emerald-900/60 text-emerald-300 border-emerald-800' };

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const Sidebar = ({ mobile = false }: { mobile?: boolean }) => (
    <div
      className={`flex flex-col h-full bg-slate-950 border-r border-slate-800 transition-all duration-200 ${
        mobile ? 'w-64' : collapsed ? 'w-16' : 'w-60'
      }`}
    >
      <div className={`flex items-center gap-3 px-4 py-5 border-b border-slate-800 ${collapsed && !mobile ? 'justify-center' : ''}`}>
        <div className="w-8 h-8 rounded-lg bg-sky-500 flex items-center justify-center flex-shrink-0">
          <Zap className="w-4 h-4 text-white" />
        </div>
        {(!collapsed || mobile) && (
          <span className="text-slate-100 font-bold text-base tracking-tight">LogiSight</span>
        )}
        {!mobile && (
          <button
            onClick={() => setCollapsed((v) => !v)}
            className="ml-auto text-slate-500 hover:text-slate-300 transition-colors"
          >
            {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
          </button>
        )}
      </div>

      <nav className="flex-1 py-4 overflow-y-auto">
        <ul className="space-y-0.5 px-2">
          {nav.map(({ to, label, Icon }) => (
            <li key={to}>
              <NavLink
                to={to}
                end={to === '/app'}
                onClick={() => mobile && setMobileOpen(false)}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm transition-colors ${
                    collapsed && !mobile ? 'justify-center' : ''
                  } ${
                    isActive
                      ? 'bg-sky-900/50 text-sky-300 border border-sky-800/50'
                      : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                  }`
                }
                title={collapsed && !mobile ? label : undefined}
              >
                <Icon className="w-4 h-4 flex-shrink-0" />
                {(!collapsed || mobile) && <span>{label}</span>}
              </NavLink>
            </li>
          ))}
        </ul>
      </nav>

      <div className={`px-2 py-3 border-t border-slate-800 ${collapsed && !mobile ? 'items-center flex flex-col' : ''}`}>
        {(!collapsed || mobile) && (
          <div className="px-3 py-2 mb-2">
            <p className="text-sm font-medium text-slate-200 truncate">{user?.name}</p>
            <p className="text-xs text-slate-500 truncate">{user?.company_name}</p>
            <span className={`mt-1.5 inline-block px-2 py-0.5 rounded-full border text-xs font-medium ${rolePill.cls}`}>
              {rolePill.label}
            </span>
          </div>
        )}
        <button
          onClick={handleLogout}
          className={`flex items-center gap-2 px-3 py-2 w-full rounded-lg text-sm text-slate-400 hover:text-red-400 hover:bg-red-950/30 transition-colors ${
            collapsed && !mobile ? 'justify-center' : ''
          }`}
          title={collapsed && !mobile ? 'Sign out' : undefined}
        >
          <LogOut className="w-4 h-4 flex-shrink-0" />
          {(!collapsed || mobile) && <span>Sign out</span>}
        </button>
      </div>
    </div>
  );

  return (
    <div className="flex h-screen bg-slate-950 overflow-hidden">
      <div className="hidden md:flex h-full flex-shrink-0">
        <Sidebar />
      </div>

      {mobileOpen && (
        <div className="fixed inset-0 z-50 md:hidden">
          <div className="absolute inset-0 bg-black/60" onClick={() => setMobileOpen(false)} />
          <div className="relative h-full">
            <Sidebar mobile />
          </div>
        </div>
      )}

      <div className="flex-1 flex flex-col overflow-hidden">
        <header className="h-14 border-b border-slate-800 bg-slate-950/90 backdrop-blur flex items-center px-4 gap-3 flex-shrink-0">
          <button
            onClick={() => setMobileOpen(true)}
            className="md:hidden text-slate-400 hover:text-slate-200"
          >
            <Menu className="w-5 h-5" />
          </button>
          {mobileOpen && (
            <button onClick={() => setMobileOpen(false)} className="md:hidden text-slate-400">
              <X className="w-5 h-5" />
            </button>
          )}
        </header>
        <main className="flex-1 overflow-y-auto bg-slate-950">
          <div className="max-w-7xl mx-auto px-4 md:px-6 py-6">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
