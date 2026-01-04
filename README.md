# Waves Church TV Controller

A simple GUI application to remotely control Android-based TVs via ADB (Android Debug Bridge).

## Features

- Turn on/off all TVs at once
- Control Inside and Outside TV groups separately
- Check status of all TVs without changing their state
- Visual indicators showing connection status (gray/yellow/green/red)
- Threaded operations for fast parallel execution

## Setup
gotta rememeber to brew install python3 in case the Mac at church doesnt have it.

### Mac
Remember to make the `Start TV Controller.command` executable:
```bash
chmod +x "Start TV Controller.command"
```

## Status Indicator Colors

- **Gray (●)** - Unknown/Idle state
- **Yellow (●)** - Currently connecting...
- **Green (●)** - Successfully connected/command sent
- **Red (●)** - Failed to connect or command failed

Indicators automatically reset to gray after 1 minute.

## ADB Commands Reference

```bash
# Connect to TV
adb connect <ip>:5555

# Check power state
adb -s <ip>:5555 shell "dumpsys power | grep 'mWakefulness='"
# Returns: mWakefulness=Awake or mWakefulness=Asleep

# Toggle power (like pressing power button)
adb -s <ip>:5555 shell "input keyevent 26"

# Disconnect
adb disconnect <ip>:5555
```