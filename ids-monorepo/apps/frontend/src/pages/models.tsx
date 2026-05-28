import React from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'

export function ModelsPage() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">ML Models</h2>
        <p className="text-muted-foreground">Manage detection models</p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Active Model</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              <div>
                <p className="text-sm font-medium">Model Name</p>
                <p className="text-lg">Random Forest v2.1</p>
              </div>
              <div>
                <p className="text-sm font-medium">Version</p>
                <p className="text-lg">2.1.0</p>
              </div>
              <div>
                <p className="text-sm font-medium">Accuracy</p>
                <div className="flex items-center gap-2">
                  <div className="h-2 w-24 rounded-full bg-muted">
                    <div className="h-full rounded-full bg-green-500" style={{ width: '94%' }} />
                  </div>
                  <span className="text-lg">94%</span>
                </div>
              </div>
              <div>
                <p className="text-sm font-medium">Last Updated</p>
                <p className="text-lg">2024-02-15 14:30:00</p>
              </div>
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Model Information</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3 text-sm">
              <div className="flex justify-between">
                <span>Type:</span>
                <span>Random Forest</span>
              </div>
              <div className="flex justify-between">
                <span>Input Features:</span>
                <span>27</span>
              </div>
              <div className="flex justify-between">
                <span>Threshold:</span>
                <span>0.75</span>
              </div>
              <div className="flex justify-between">
                <span>File Size:</span>
                <span>2.4 MB</span>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}