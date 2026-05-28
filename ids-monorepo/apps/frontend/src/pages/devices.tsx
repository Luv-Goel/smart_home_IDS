import React from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { DeviceTable } from '@/components/devices/device-table'

export function DevicesPage() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">Devices</h2>
        <p className="text-muted-foreground">Manage and monitor IoT devices</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Monitored Devices</CardTitle>
        </CardHeader>
        <CardContent>
          <DeviceTable />
        </CardContent>
      </Card>
    </div>
  )
}