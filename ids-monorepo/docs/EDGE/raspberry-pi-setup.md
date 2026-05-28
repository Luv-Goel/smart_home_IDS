# Raspberry Pi Edge Deployment Guide

This guide covers deploying Smart Home IDS on Raspberry Pi devices.

## Hardware Requirements

### Minimum
- Raspberry Pi 3B+ (1GB RAM)
- microSD card (16GB minimum)
- Network interface

### Recommended
- Raspberry Pi 4B/5 (4GB+ RAM)
- microSD card (32GB+)
- External USB network adapter for better packet capture
- Power supply with adequate current

## Software Installation

### 1. Install Raspberry Pi OS

Download and install Raspberry Pi OS Lite (64-bit):

```bash
# Using Raspberry Pi Imager
# Select: Raspberry Pi OS Lite (64-bit)
```

### 2. Update System

```bash
sudo apt update && sudo apt upgrade -y
sudo reboot
```

### 3. Install Docker

```bash
curl -sSL https://get.docker.com | sh
sudo usermod -aG docker pi
sudo reboot
```

### 4. Enable Network Interface

For packet capture, you may need to enable promiscuous mode:

```bash
# Check available interfaces
ip link show

# Enable promiscuous mode (if needed)
sudo ip link set eth0 promisc on
```

## Deployment

### Using Docker Compose

1. Clone the repository:
```bash
git clone https://github.com/your-org/smart_home_IDS.git
cd smart_home_IDS/ids-monorepo
```

2. Create configuration:
```bash
cp .env.example .env
nano .env  # Edit with your settings
```

3. Start services:
```bash
docker compose -f infra/docker/docker-compose.edge.yml up -d
```

### Using Docker Commands

```bash
# Start MQTT broker
docker run -d \
  --name mosquitto \
  -p 1883:1883 \
  -v ./mosquitto/config:/mosquitto/config \
  eclipse-mosquitto:2-alpine

# Start edge service
docker run -d \
  --name edge-service \
  --network host \
  --cap-add NET_RAW \
  --cap-add NET_ADMIN \
  -v /path/to/config:/app/config \
  ids-edge:latest
```

## Configuration

### Environment Variables

```bash
# Node identification
NODE_ID=pi-gateway-01

# Network interface
NETWORK_INTERFACE=eth0

# MQTT broker
MQTT_BROKER_URL=mqtt://broker.local:1883

# Model path
ML_MODEL_PATH=/app/models/rf_lightweight_v1.onnx

# Inference batch size
ML_BATCH_SIZE=32
```

### Configuration File

Create `config.yaml`:

```yaml
edge:
  node_id: ${NODE_ID}
  interface: ${NETWORK_INTERFACE}
ml:
  active_model: "models/rf_lightweight_v1.onnx"
  inference_batch_size: 32
fusion:
  alert_threshold: 0.85
  anomaly_cost_weight: 1.2
mqtt:
  broker_url: "mqtt://broker.local:8883"
  ca_certs: "/etc/ssl/certs/ca-certificates.crt"
```

## Performance Optimization

### CPU Optimization

```bash
# Set CPU governor to performance
echo performance | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor

# Or use powersave for longer battery life
echo powersave | sudo tee /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor
```

### Memory Optimization

```bash
# Reduce swap usage
sudo sysctl vm.swappiness=10

# Configure zram for compressed RAM
sudo apt install zram-tools
```

### Network Optimization

```bash
# Increase network buffer
echo 'net.core.rmem_max = 16777216' | sudo tee -a /etc/sysctl.conf
echo 'net.core.wmem_max = 16777216' | sudo tee -a /etc/sysctl.conf
sudo sysctl -p
```

## Monitoring

### System Health

```bash
# Check Docker containers
docker ps

# Check logs
docker logs -f edge-service

# System resources
htop
```

### Service Health

```bash
# Check MQTT broker
mosquitto_sub -t "ids/status" -h localhost

# Check packet capture
docker logs edge-service | grep "packets processed"
```

## Troubleshooting

### Common Issues

1. **No packet capture**
   ```bash
   # Check interface permissions
   sudo tcpdump -i eth0
   
   # Enable promiscuous mode
   sudo ip link set eth0 promisc on
   ```

2. **MQTT connection failure**
   ```bash
   # Check broker status
   docker logs mosquitto
   
   # Test connection
   mosquitto_pub -t test -h localhost -m "test"
   ```

3. **High CPU usage**
   ```bash
   # Reduce batch size
   export ML_BATCH_SIZE=16
   
   # Lower inference frequency
   ```

### Logs

```bash
# All container logs
docker logs --tail 100 -f $(docker ps -q)

# Specific service
docker logs -f edge-service
```

### Reset

```bash
# Stop all services
docker compose -f docker-compose.edge.yml down

# Remove containers
docker compose -f docker-compose.edge.yml down -v

# Rebuild and start
docker compose -f docker-compose.edge.yml up --build
```

## Maintenance

### Updates

```bash
# Pull latest changes
git pull origin main

# Rebuild and restart
docker compose down
docker compose build
docker compose up -d
```

### Backups

```bash
# Backup configuration
tar -czvf backup-$(date +%Y%m%d).tar.gz config/ .env models/

# Restore
tar -xzvf backup-YYYYMMDD.tar.gz
```

### Model Updates

1. Place new model in `models/` directory
2. Update configuration:
   ```yaml
   ml:
     active_model: "models/new_model.onnx"
   ```
3. Restart service

## Security

### Hardening

```bash
# Remove default user password
sudo passwd -d pi

# Change default password
sudo passwd pi

# Disable SSH password authentication
sudo nano /etc/ssh/sshd_config
# Set PasswordAuthentication no
```

### Network Security

```bash
# Enable firewall
sudo ufw enable
sudo ufw allow 1883
sudo ufw allow 8883

# Limit Docker network
docker network create --driver bridge --subnet=172.20.0.0/16 ids-network
```

## Battery Considerations

For battery-powered deployments:

```bash
# Reduce USB power
echo 'max_current=500' | sudo tee /sys/kernel/debug/usb/power

# Disable HDMI
sudo tvservice -o

# Disable Bluetooth
sudo dtoverlay=disable-bt
```