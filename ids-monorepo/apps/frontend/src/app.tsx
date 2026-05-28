import React from 'react'
import { Routes, Route } from 'react-router-dom'
import { Layout } from './layouts/layout'
import { Dashboard } from './pages/dashboard'
import { AlertsPage } from './pages/alerts'
import { DevicesPage } from './pages/devices'
import { ModelsPage } from './pages/models'
import { SettingsPage } from './pages/settings'

export function App() {
  return (
    <Layout>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/alerts" element={<AlertsPage />} />
        <Route path="/devices" element={<DevicesPage />} />
        <Route path="/models" element={<ModelsPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Routes>
    </Layout>
  )
}