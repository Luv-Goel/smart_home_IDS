import React from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { AlertSeverityBadge, AlertCategoryBadge } from '@/components/alerts/alert-badges'
import { AlertTable } from '@/components/alerts/alert-table'

export function AlertsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">Alerts</h2>
        <p className="text-muted-foreground">Monitor and manage detected threats</p>
      </div>

      <AlertTable />
    </div>
  )
}