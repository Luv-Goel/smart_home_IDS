import React from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

export function SettingsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">Settings</h2>
        <p className="text-muted-foreground">System and user configuration</p>
      </div>

      <div className="grid gap-6">
        <Card>
          <CardHeader>
            <CardTitle>General Settings</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium">Dark Mode</p>
                <p className="text-sm text-muted-foreground">Toggle dark mode theme</p>
              </div>
              <div className="h-6 w-11 rounded-full bg-primary relative cursor-pointer">
                <div className="absolute right-0.5 top-0.5 h-5 w-5 rounded-full bg-white" />
              </div>
            </div>
            <div className="flex items-center justify-between">
              <div>
                <p className="font-medium">Auto Refresh</p>
                <p className="text-sm text-muted-foreground">Auto-refresh dashboard data</p>
              </div>
              <div className="h-6 w-11 rounded-full bg-primary relative cursor-pointer">
                <div className="absolute right-0.5 top-0.5 h-5 w-5 rounded-full bg-white" />
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Network Configuration</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="text-sm font-medium">Network Interface</label>
              <select className="mt-1 w-full rounded-md border bg-background px-3 py-2">
                <option>eth0</option>
                <option>wlan0</option>
                <option>docker0</option>
              </select>
            </div>
            <div>
              <label className="text-sm font-medium">Monitoring Mode</label>
              <select className="mt-1 w-full rounded-md border bg-background px-3 py-2">
                <option>Active</option>
                <option>Passive</option>
                <option>Hybrid</option>
              </select>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Alert Thresholds</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="text-sm font-medium">Confidence Threshold</label>
              <input
                type="range"
                min="0"
                max="1"
                step="0.05"
                defaultValue="0.75"
                className="mt-2 h-2 w-full appearance-none rounded-lg bg-muted accent-primary"
              />
              <div className="flex justify-between text-xs text-muted-foreground">
                <span>0.5</span>
                <span>Current: 0.75</span>
                <span>0.95</span>
              </div>
            </div>
            <div>
              <label className="text-sm font-medium">Alert Cooldown (minutes)</label>
              <input
                type="number"
                defaultValue="5"
                className="mt-1 w-full rounded-md border bg-background px-3 py-2"
              />
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}