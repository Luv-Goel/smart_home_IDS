# Raspberry Pi Optimization Configs

To optimize the IDS for a Raspberry Pi 4 (or similar ARM64 edge device), you can use the configs here.

## OS Level optimizations

1. Edit `/boot/config.txt` to allocate less memory to GPU if running headless:
   `gpu_mem=16`
2. Enable 64-bit kernel if not already running on standard 64-bit OS:
   `arm_64bit=1`
3. Consider mounting `/var/log` as `tmpfs` in `/etc/fstab` to reduce SD card wear:
   `tmpfs /var/log tmpfs defaults,noatime,nosuid,mode=0755,size=100m 0 0`

## Docker Daemon

It's recommended to configure the Docker daemon for log rotation to prevent filling up the disk.

File: `/etc/docker/daemon.json`

```json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
```

## Swap Configuration

Increase swap space to handle memory spikes (e.g. 2GB):

Edit `/etc/dphys-swapfile`
`CONF_SWAPSIZE=2048`

Then restart the service:
`sudo systemctl restart dphys-swapfile`
