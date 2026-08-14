import { useState } from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';

interface NavItem {
  to: string;
  label: string;
  icon: string;
}

const SUPER_ADMIN_NAV: NavItem[] = [
  { to: '/app', label: 'Dashboard', icon: 'grid_view' },
  { to: '/app/companies', label: 'Companies', icon: 'group' },
];

const CLIENT_NAV: NavItem[] = [
  { to: '/app', label: 'Dashboard', icon: 'grid_view' },
  { to: '/app/quotes', label: 'Quotes', icon: 'request_quote' },
  { to: '/app/invoices', label: 'Invoices', icon: 'receipt_long' },
  { to: '/app/charge-master', label: 'Charge Master', icon: 'lists' },
  { to: '/app/tracking', label: 'Tracking', icon: 'local_shipping' },
  { to: '/app/copilot', label: 'Copilot', icon: 'smart_toy' },
];

const FORWARDER_NAV: NavItem[] = [
  { to: '/app', label: 'Dashboard', icon: 'grid_view' },
  { to: '/app/quotes', label: 'Quotes', icon: 'request_quote' },
  { to: '/app/invoices', label: 'Invoices', icon: 'receipt_long' },
  { to: '/app/tracking', label: 'Tracking', icon: 'local_shipping' },
];

export function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const nav =
    user?.role === 'super_admin'
      ? SUPER_ADMIN_NAV
      : user?.role === 'forwarder'
      ? FORWARDER_NAV
      : CLIENT_NAV;

  const roleLabel =
    user?.role === 'super_admin' ? 'Super Admin' : user?.role === 'forwarder' ? 'Forwarder' : 'Client';

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  return (
    <div className="bg-surface-container-low font-body-md text-on-surface min-h-screen flex">
      {/* Sidebar */}
      <aside className={`fixed left-0 top-0 h-full bg-surface-container-low z-50 flex flex-col py-6 transition-all duration-300 ${sidebarOpen ? 'w-60' : 'w-14'}`}>
         {/* Hamburger & Logo */}
         <div className={`mb-8 flex items-center ${sidebarOpen ? 'px-4 gap-3' : 'justify-center'}`}>
           <button 
             onClick={() => setSidebarOpen(!sidebarOpen)} 
             className="w-10 h-10 rounded-full hover:bg-surface-container flex items-center justify-center flex-shrink-0 text-on-surface-variant transition-colors"
           >
              <span className="material-symbols-outlined">menu</span>
           </button>
           
           <div className={`flex items-center gap-3 overflow-hidden transition-all duration-300 ${sidebarOpen ? 'w-auto opacity-100' : 'w-0 opacity-0'}`}>
             <img src="/logo.png" alt="LogiSight" className="h-8 w-auto object-contain" onError={(e) => { e.currentTarget.style.display = 'none'; }} />
             <span className="font-headline-md-mobile text-[22px] font-bold tracking-tighter text-on-surface whitespace-nowrap">
               LogiSight
             </span>
           </div>
         </div>

         <nav className={`flex-1 space-y-1 ${sidebarOpen ? 'px-2' : 'px-2'}`}>
           {nav.map(({ to, label, icon }) => (
             <NavLink
               key={to}
               to={to}
               end={to === '/app'}
               className={({ isActive }) =>
                 `flex items-center px-3 py-3 rounded-xl transition-all font-label-sm tracking-tight ${
                   isActive
                     ? 'bg-primary text-on-primary'
                     : 'text-on-surface-variant hover:bg-surface-container hover:text-on-surface'
                 } ${!sidebarOpen ? 'justify-center px-0' : ''}`
               }
               title={!sidebarOpen ? label : undefined}
             >
               <span className={`material-symbols-outlined text-[22px] ${sidebarOpen ? 'mr-3' : ''}`}>{icon}</span>
               {sidebarOpen && <span className="whitespace-nowrap">{label}</span>}
             </NavLink>
           ))}
         </nav>

         <div className={`mt-auto pb-4 ${sidebarOpen ? 'px-2' : 'px-2'}`}>
           <button
             onClick={handleLogout}
             className={`w-full flex items-center py-3 rounded-xl text-on-surface-variant hover:bg-error-container hover:text-on-error-container transition-all font-label-sm text-label-sm tracking-tight ${!sidebarOpen ? 'justify-center px-0' : 'px-3'}`}
             title={!sidebarOpen ? 'Sign Out' : undefined}
           >
             <span className={`material-symbols-outlined text-[22px] ${sidebarOpen ? 'mr-3' : ''}`}>logout</span>
             {sidebarOpen && <span className="whitespace-nowrap">Sign Out</span>}
           </button>
         </div>
      </aside>

      {/* Main Content Area */}
      <div className={`flex-1 flex flex-col min-h-screen transition-all duration-300 ${sidebarOpen ? 'pl-60' : 'pl-14'}`}>
        <header className="sticky top-0 h-20 flex items-center justify-end px-10 z-40 bg-surface-container-low/90 backdrop-blur-md">
           <div className="flex items-center gap-4">
             <div className="flex items-center gap-3 bg-surface px-4 py-2 rounded-full border border-surface-container shadow-sm">
               <div className="text-right">
                 <p className="text-xs font-bold leading-none text-on-surface">{user?.name}</p>
                 <p className="text-[10px] text-on-surface-variant mt-1">{roleLabel}</p>
               </div>
               <div className="w-8 h-8 rounded-full bg-primary flex items-center justify-center">
                 <span className="material-symbols-outlined text-on-primary text-[18px]">person</span>
               </div>
             </div>
           </div>
        </header>

        <div className="px-10 pb-10 pt-2 flex-1 flex flex-col">
          <main className="flex-1 bg-surface rounded-[32px] shadow-sm border border-surface-container relative overflow-hidden">
            <div className="absolute inset-0 overflow-y-auto custom-scrollbar flex flex-col">
              <div className="px-12 md:px-16 pt-8 pb-8 flex-1 flex flex-col">
                <Outlet />
              </div>
            </div>
          </main>
        </div>
      </div>
    </div>
  );
}
