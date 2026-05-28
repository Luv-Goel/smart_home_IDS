import React from 'react'
import { AlertCircle, Devices, Activity, Clock } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

interface MetricCardProps {
  title: string
  value: string | number
  icon: React.ElementType
  trend?: 'up' | 'down' | 'neutral'
}

function MetricCard({ title, value, icon: Icon, trend = 'neutral' }: MetricCardProps) {
  const trendColors = {
    up: 'text-green-500',
    down: 'text-red-500',
    neutral: 'text-muted-foreground',
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium">{title}</CardTitle>
        <Icon className="h-4 w-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-bold">{value}</div>
        <p className={`text-xs ${trendColors[trend]}`}>
          {trend === 'up' && '↑ Increasing'}
          {trend === 'down' && '↓ Decreasing'}
          {trend === 'neutral' && '→ Stable'}
        </p>
      </CardContent>
    </Card>
  )
}

export function Dashboard() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">Dashboard</h2>
        <p className="text-muted-foreground">
          Real-time monitoring of your IoT network
        </p>
      </div>

      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          title="Active Alerts"
          value={24}
          icon={AlertCircle}
          trend="up"
        />
        <MetricCard
          title="Monitored Devices"
          value={128}
          icon={Devices}
        />
        <MetricCard
          title="Network Flows"
          value={15234}
          icon={Activity}
          trend="down"
        />
        <MetricCard
          title="Critical Alerts"
          value={3}
          icon={AlertCircle}
          trend="up"
        />
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Recent Alerts</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {[1, 2, 3, 4, 5].map((i) => (
                <div key={i} className="flex items-center gap-3">
                  <div className="h-2 w-2 rounded-full bg-red-500" />
                  <div className="flex-1">
                    <p className="text-sm font-medium">Potential DDoS Attempt</p>
                    <p className="text-xs text-muted-foreground">
                      192.168.1.{i * 10} → 10.0.0.1
                    </p>
                  </div>
                  <Badge variant="destructive">Critical</Badge>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Device Health</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span>Trusted Devices</span>
                  <span className="font-medium">110</span>
                </div>
                <div className="h-2 rounded-full bg-muted">
                  <div className="h-full rounded-full bg-green-500" style={{ width: '86%' }} />
                </div>
              </div>
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span>Suspicious Devices</span>
                  <span className="font-medium">12</span>
                </div>
                <div className="h-2 rounded-full bg-muted">
                  <div className="h-full rounded-full bg-yellow-500" style={{ width: '9%' }} />
                </div>
              </div>
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span>Blocked Devices</span>
                  <span className="font-medium">6</span>
                </div>
                <div className="h-2 rounded-full bg-muted">
                  <div className="h-full rounded-full bg-red-500" style={{ width: '5%' }} />
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}