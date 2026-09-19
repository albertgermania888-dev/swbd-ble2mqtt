# SWBD Home Assistant Integration

This repository contains a native Home Assistant custom component for the SWBD (Smart Baby Rocker) devices, replacing the previous ESP32-based BLE-to-MQTT bridge. It natively uses Home Assistant's Bluetooth integration to connect directly to the rockers.

## Installation

1. Install the `swbd` integration via HACS or copy the `custom_components/swbd` directory into your `config/custom_components/` directory in Home Assistant.
2. Restart Home Assistant.
3. Go to **Settings** > **Devices & Services** > **Add Integration** and search for "SWBD".
4. The integration will automatically discover nearby SWBD baby rockers.

## Features
- Direct BLE control of speed, sensitivity, rocking toggle, and timers.
- Two Connection Modes: Continuous (instant updates) or Polling (saves BLE proxy resources).

