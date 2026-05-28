import React from 'react'
import { useNavigate } from 'react-router-dom'
import { Bell, Settings, LogOut, Menu } from 'lucide-react'

export function Header() {
  const navigate = useNavigate()

  return (
    <header className="flex h-16 items-center justify-between border-b bg-card px-6">
      <div className="flex items-center gap-4">
        <button className="md:hidden" onClick={() => {}}>
          <Menu className="h-6 w-6" />
        </button>
        <div>
          <h1 className="text-xl font-bold">Smart Home IDS</h1>
          <p className="text-sm text-muted-foreground">IoT Intrusion Detection System</p>
        </div>
      </div>

      <div className="flex items-center gap-4">
        <button className="relative p-2 rounded-full hover:bg-accent">
          <Bell className="h-5 w-5" />
          <span className="absolute top-1 right-1 h-2 w-2 rounded-full bg-red-500" />
        </button>
        <button className="p-2 rounded-full hover:bg-accent">
          <Settings className="h-5 w-5" />
        </button>
        <button
          className="p-2 rounded-full hover:bg-accent text-muted-foreground"
          onClick={() => navigate('/')}
        >
          <LogOut className="h-5 w-5" />
        </button>
        <div className="h-8 w-8 rounded-full bg-primary flex items-center justify-center text-primary-foreground">
          <span className="text-sm font-medium">A</span>
        </div>
      </div>
    </header>
  )
}