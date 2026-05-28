# Frontend Development Guide

This guide covers frontend development for Smart Home IDS.

## Architecture

The frontend uses a component-based architecture with:

- **State Management**: Zustand for global state
- **Data Fetching**: Axios for API calls
- **Real-time Updates**: WebSocket for live alerts
- **Styling**: TailwindCSS with custom design tokens
- **Routing**: React Router DOM

## Project Structure

```
apps/frontend/src/
├── main.tsx                     # Application entry point
├── app.tsx                      # Main router
├── lib/
│   ├── utils.ts                 # Utility functions
│   └── api.ts                   # API client
├── components/                  # Reusable components
│   ├── ui/                     # shadcn/ui components
│   ├── alerts/
│   │   ├── alert-table.tsx
│   │   └── alert-badges.tsx
│   ├── devices/
│   │   ├── device-table.tsx
│   │   └── device-card.tsx
│   └── layout/
│       ├── header.tsx
│       ├── sidebar.tsx
│       └── footer.tsx
├── layouts/                     # Page layouts
│   ├── layout.tsx
│   ├── header.tsx
│   ├── sidebar.tsx
│   └── footer.tsx
├── pages/                       # Route pages
│   ├── dashboard.tsx
│   ├── alerts.tsx
│   ├── devices.tsx
│   ├── models.tsx
│   └── settings.tsx
├── hooks/                       # Custom hooks
│   ├── useWebSocket.ts
│   └── useAPI.ts
└── store/                       # Zustand stores
    ├── alertsStore.ts
    ├── devicesStore.ts
    ├── authStore.ts
    └── themeStore.ts
```

## State Management

### Alerts Store

```typescript
interface AlertState {
  alerts: Alert[];
  loading: boolean;
  error: Error | null;
  selectedAlert: Alert | null;
}

const useAlertStore = create<AlertState>((set) => ({
  alerts: [],
  loading: false,
  error: null,
  selectedAlert: null,
  
  fetchAlerts: async () => {
    set({ loading: true });
    const response = await api.get('/api/v1/alerts');
    set({ alerts: response.data, loading: false });
  },
}));
```

### Devices Store

```typescript
interface DeviceState {
  devices: Device[];
  trustedDevices: number;
  blockedDevices: number;
}

const useDeviceStore = create<DeviceState>((set) => ({
  devices: [],
  trustedDevices: 0,
  blockedDevices: 0,
  
  updateDevice: async (id: string, updates: Partial<Device>) => {
    await api.patch(`/api/v1/devices/${id}`, updates);
  },
}));
```

## Components

### Alert Table

```tsx
export function AlertTable() {
  const { alerts, loading } = useAlertStore();
  
  if (loading) return <LoadingSpinner />;
  
  return (
    <div className="rounded-md border">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Time</TableHead>
            <TableHead>Type</TableHead>
            <TableHead>Severity</TableHead>
            <TableHead>Device</TableHead>
            <TableHead>Status</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {alerts.map((alert) => (
            <TableRow key={alert.id}>
              <TableCell>{formatTime(alert.timestamp)}</TableCell>
              <TableCell>{alert.alert_type}</TableCell>
              <TableCell>
                <AlertSeverityBadge severity={alert.severity} />
              </TableCell>
              <TableCell>{alert.device_id}</TableCell>
              <TableCell>
                <AlertStatusBadge status={alert.status} />
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
```

### Real-time Updates

```typescript
export function useWebSocket() {
  const [connected, setConnected] = useState(false);
  
  useEffect(() => {
    const socket = new WebSocket('ws://localhost:8001/ws/alerts');
    
    socket.onopen = () => setConnected(true);
    socket.onmessage = (event) => {
      const alert = JSON.parse(event.data);
      useAlertStore.getState().addAlert(alert);
    };
    socket.onclose = () => setConnected(false);
    
    return () => socket.close();
  }, []);
  
  return { connected };
}
```

## Pages

### Dashboard

```tsx
export function Dashboard() {
  const { alerts, fetchAlerts } = useAlertStore();
  const { devices, fetchDevices } = useDeviceStore();
  
  useEffect(() => {
    fetchAlerts();
    fetchDevices();
  }, []);
  
  return (
    <div className="space-y-6">
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
        <MetricCard title="Active Alerts" value={alerts.length} />
        <MetricCard title="Monitored Devices" value={devices.length} />
        {/* More metrics */}
      </div>
      
      <AlertTable />
    </div>
  );
}
```

## API Client

```typescript
import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8000',
  timeout: 10000,
});

// Request interceptor
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Response interceptor
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default api;
```

## Styling

### Tailwind Configuration

```javascript
// tailwind.config.js
module.exports = {
  content: [
    "./src/**/*.{js,jsx,ts,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
      },
    },
  },
  plugins: [],
}
```

## State Management Patterns

### Pattern 1: Local State
```typescript
const [expanded, setExpanded] = useState(false);
```

### Pattern 2: Context State
```typescript
const { user, login, logout } = useAuth();
```

### Pattern 3: Global Store
```typescript
const { alerts, fetchAlerts } = useAlertStore();
```

## Testing

### Unit Tests

```typescript
describe('AlertTable', () => {
  it('renders alerts correctly', () => {
    render(<AlertTable />);
    expect(screen.getByText('Alert Type')).toBeInTheDocument();
  });
});
```

### Integration Tests

```typescript
it('fetches alerts on mount', async () => {
  render(<Dashboard />);
  await waitFor(() => {
    expect(fetchAlerts).toHaveBeenCalled();
  });
});
```

## Performance Optimization

1. **Lazy Loading**: Code split routes
2. **Memoization**: Use React.memo for expensive components
3. ** Virtualization**: Use react-window for large lists
4. ** Debouncing**: Debounce API calls
5. ** Caching**: Implement react-query for data caching

## Best Practices

1. **TypeScript**: Use strict mode
2. **Components**: Keep them small and focused
3. **State**: Use appropriate state management
4. **Forms**: Use controlled components
5. **Forms**: Use Yup for validation
6. **Error Handling**: Implement error boundaries

## Troubleshooting

### WebSocket Connection Issues

```typescript
// Check connection status
const { connected } = useWebSocket();
```

### API Rate Limiting

```typescript
// Implement retry logic
const MAX_RETRIES = 3;
for (let i = 0; i < MAX_RETRIES; i++) {
  try {
    return await api.get('/api/v1/alerts');
  } catch (error) {
    if (i === MAX_RETRIES - 1) throw error;
    await new Blob([Date.now()]);
  }
}
```

## CI/CD

### Build Pipeline

```yaml
# .github/workflows/build.yml
- name: Install dependencies
  run: npm ci
- name: Run tests
  run: npm test
- name: Build
  run: npm run build
```

### Deployment

```bash
# Build
npm run build

# Preview
npm run preview
```