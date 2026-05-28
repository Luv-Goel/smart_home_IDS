import React from 'react'
import { Link, useLocation } from 'react-router-dom'
import {
  LayoutDashboard,
  AlertTriangle,
  Devices,
  Cpu,
  Settings,
  ShieldCheck,
} from 'lucide-react'

const navItems = [
  {
    title: 'Dashboard',
    icon: LayoutDashboard,
    path: '/',
  },
  {
    title: 'Alerts',
    icon: AlertTriangle,
    path: '/alerts',
  },
  {
    title: 'Devices',
    icon: Devices,
    path: '/devices',
  },
  {
    title: 'Models',
    icon: Cpu,
    path: '/models',
  },
  {
    title: 'Settings',
    icon: Settings,
    path: '/settings',
  },
]

export function Sidebar() {
  const location = useLocation()

  return (
    <aside className="hidden md:flex w-64 flex-col border-r bg-card">
      <div className="flex h-16 items-center justify-center border-b">
        <span className="font-bold text-xl">IDS</span>
      </div>

      <nav className="flex-1 space-y-1 px-2 py-4">
        {navItems.map((item) => {
          const isActive = location.pathname === item.path

          return (
            <Link
              key={item.path}
              to={item.path}
              className={`flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-primary text-primary-foreground'
                  : 'text-muted-foreground hover:bg-accent hover:text-foreground'
              }`}
            >
              <item.icon className="h-5 w-5" />
              {item.title}
            </Link>
          )
        })}
      </nav>

      <div className="border-t p-4">
        <div className="flex items-center gap-3 rounded-lg bg-muted p-3">
          <div className="h-10 w-10 rounded-full bg-primary flex items-center justify-center text-primary-foreground">
            <ShieldCheck className="h-5 w-5" />
          </div>
          <div>
            <p className="text-sm font-medium">Admin User</p>
            <p className="text-xs text-muted-foreground">admin@smarthome.ids</p>
          </div>
        </div>
      </div>
    </aside>
  )
}