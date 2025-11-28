/**
 * Layout - Main application layout with bottom navigation for mobile.
 */

import { Outlet, NavLink } from 'react-router-dom';
import {
  Search,
  Database,
  Server,
  Settings,
  LogOut,
} from 'lucide-react';

const navItems = [
  { to: '/diagnosis', icon: Search, label: 'Diagnose' },
  { to: '/documents', icon: Database, label: 'Library' },
  { to: '/settings', icon: Settings, label: 'Admin' },
];

export default function Layout() {


  return (
    <div className="min-h-screen bg-gray-900 text-white pb-20 lg:pb-0">
      {/* Desktop Sidebar */}
      <aside className="hidden lg:flex fixed inset-y-0 left-0 z-50 w-64 bg-gray-800 border-r border-gray-700 flex-col">
        <div className="h-16 flex items-center px-6 border-b border-gray-700 gap-3">
          <div className="p-1.5 bg-gray-800 rounded-lg border border-gray-700">
            <Server className="text-orange-500 h-6 w-6" />
          </div>
          <span className="text-xl font-bold text-orange-500">
            LIFTLOGIC
          </span>
        </div>

        <nav className="flex-1 p-4 space-y-2">
          {navItems.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex items-center gap-3 px-4 py-3 rounded-lg transition-colors ${
                  isActive
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-400 hover:bg-gray-700 hover:text-white'
                }`
              }
            >
              <Icon size={20} />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>
      </aside>

      {/* Mobile Header */}
      <header className="lg:hidden h-14 bg-gray-900 border-b border-gray-800 flex items-center justify-between px-4 sticky top-0 z-40">
        <div className="flex items-center gap-3">
          <div className="p-1.5 bg-gray-800 rounded-lg border border-gray-700">
            <Server className="text-orange-500 h-5 w-5" />
          </div>
          <span className="text-lg font-bold tracking-wide">
            <span className="text-orange-500">LIFT</span>
            <span className="text-white">LOGIC</span>
          </span>
        </div>
        <button className="p-2 text-gray-400 hover:text-white">
          <LogOut size={18} />
        </button>
      </header>

      {/* Main content */}
      <main className="lg:ml-64 p-4 lg:p-8">
        <Outlet />
      </main>

      {/* Mobile Bottom Navigation */}
      <nav className="lg:hidden fixed bottom-0 left-0 right-0 bg-gray-900 border-t border-gray-800 z-50 pb-safe">
        <div className="flex justify-around items-center h-16">
          {navItems.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              className={({ isActive }) =>
                `flex flex-col items-center justify-center w-full h-full space-y-1 ${
                  isActive ? 'text-blue-500' : 'text-gray-500'
                }`
              }
            >
              <Icon size={24} />
              <span className="text-xs font-medium">{label}</span>
            </NavLink>
          ))}
        </div>
      </nav>
    </div>
  );
}
