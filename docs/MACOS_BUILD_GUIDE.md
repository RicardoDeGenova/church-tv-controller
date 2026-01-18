# macOS Build and Test Guide

A complete step-by-step guide to build and test the Waves Church TV Controller on macOS.

---

## Table of Contents

1. [Prerequisites](#1-prerequisites)
2. [Install Homebrew](#2-install-homebrew)
3. [Install Python 3](#3-install-python-3)
4. [Clone/Download the Project](#4-clonedownload-the-project)
5. [Set Up Python Virtual Environment](#5-set-up-python-virtual-environment)
6. [Install Dependencies](#6-install-dependencies)
7. [Configure ADB (Android Debug Bridge)](#7-configure-adb-android-debug-bridge)
8. [Configure Your TVs](#8-configure-your-tvs)
9. [Run the Application](#9-run-the-application)
10. [Testing the Application](#10-testing-the-application)
11. [Troubleshooting](#11-troubleshooting)
12. [Building for Distribution](#12-building-for-distribution)

---

## 1. Prerequisites

Before you begin, ensure you have:

- **macOS 10.14 (Mojave) or later** (recommended: macOS 12+)
- **Admin access** to your Mac (for installing software)
- **Network access** to your TVs (same WiFi/LAN network)
- **Terminal app** (built into macOS, found in Applications > Utilities)

---

## 2. Install Homebrew

Homebrew is a package manager for macOS that makes installing software easy.

### Step 2.1: Open Terminal

Press `Cmd + Space`, type "Terminal", and press Enter.

### Step 2.2: Install Homebrew

Copy and paste this command into Terminal:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Follow the prompts. You may need to enter your Mac password.

### Step 2.3: Verify Installation

```bash
brew --version
```

You should see something like: `Homebrew 4.x.x`

---

## 3. Install Python 3

### Step 3.1: Install Python via Homebrew

```bash
brew install python3
```

### Step 3.2: Verify Python Installation

```bash
python3 --version
```

You should see: `Python 3.11.x` or similar (3.8+ required)

### Step 3.3: Verify pip (Python package manager)

```bash
pip3 --version
```

You should see: `pip 23.x.x from ...`

---

## 4. Clone/Download the Project

### Option A: Using Git (Recommended)

```bash
# Install git if not already installed
brew install git

# Clone the repository
git clone https://github.com/RicardoDeGenova/church-tv-controller.git

# Navigate to the project directory
cd church-tv-controller
```

### Option B: Download ZIP

1. Download the project ZIP from GitHub
2. Extract to your desired location
3. Open Terminal and navigate to the folder:

```bash
cd /path/to/church-tv-controller
```

---

## 5. Set Up Python Virtual Environment

A virtual environment keeps project dependencies isolated from your system Python.

### Step 5.1: Create Virtual Environment

```bash
python3 -m venv venv
```

### Step 5.2: Activate Virtual Environment

```bash
source venv/bin/activate
```

You should see `(venv)` appear at the beginning of your terminal prompt.

> **Note:** You'll need to activate the virtual environment every time you open a new Terminal window to run the application.

---

## 6. Install Dependencies

### Step 6.1: Upgrade pip

```bash
pip install --upgrade pip
```

### Step 6.2: Install Project Dependencies

```bash
pip install -r requirements.txt
```

This installs:
- `pywebostv>=0.8.9` - Library for LG WebOS TV control

### Step 6.3: Verify Installation

```bash
pip list
```

You should see `pywebostv` in the list.

---

## 7. Configure ADB (Android Debug Bridge)

ADB is used to communicate with Android-based TVs. The project includes a pre-built ADB binary for macOS.

### Step 7.1: Make ADB Executable

```bash
chmod +x adb/mac/adb
```

### Step 7.2: Verify ADB Works

```bash
./adb/mac/adb version
```

You should see: `Android Debug Bridge version 1.0.xx`

### Step 7.3: Handle macOS Security (if needed)

If you see a security warning:

1. Go to **System Preferences** > **Security & Privacy** > **General**
2. Click **"Allow Anyway"** next to the message about `adb`
3. Run the command again and click **"Open"** when prompted

Alternatively, you can remove the quarantine flag:

```bash
xattr -d com.apple.quarantine adb/mac/adb
```

### Step 7.4: (Optional) Install System ADB

If the bundled ADB doesn't work, install via Homebrew:

```bash
brew install android-platform-tools
```

Then modify `adb_controller.py` to use system ADB, or symlink:

```bash
ln -sf $(which adb) adb/mac/adb
```

---

## 8. Configure Your TVs

### Step 8.1: Edit Configuration File

Open `config.json` in a text editor:

```bash
open -e config.json
```

Or use any text editor (VS Code, Sublime Text, etc.)

### Step 8.2: Configure Android TVs (ADB Protocol)

For each Android TV, add an entry:

```json
{
  "name": "Living Room TV",
  "ip": "192.168.1.100",
  "protocol": "adb"
}
```

**Requirements for Android TVs:**
- Enable **Developer Options** on the TV
- Enable **USB Debugging** (sometimes called "ADB Debugging")
- Enable **ADB over Network** or **Wireless Debugging**
- Note the TV's IP address (usually found in Settings > Network)

### Step 8.3: Configure LG WebOS TVs

For each LG TV, add an entry:

```json
{
  "name": "Conference Room LG",
  "ip": "192.168.1.101",
  "protocol": "webos",
  "mac": "AA:BB:CC:DD:EE:FF"
}
```

**Finding MAC Address on LG TV:**
1. Go to **Settings** > **Network** > **Wi-Fi Connection**
2. Select your network and view details
3. Note the MAC address

### Step 8.4: Example Complete Configuration

```json
{
  "adb_port": 5555,
  "inside_tvs": [
    {"name": "TV 1", "ip": "192.168.1.10", "protocol": "adb"},
    {"name": "TV 2", "ip": "192.168.1.11", "protocol": "adb"},
    {"name": "LG TV", "ip": "192.168.1.12", "protocol": "webos", "mac": "A1:B2:C3:D4:E5:F6"}
  ],
  "outside_tvs": [
    {"name": "Lobby TV", "ip": "192.168.1.20", "protocol": "adb"},
    {"name": "Entrance TV", "ip": "192.168.1.21", "protocol": "adb"}
  ]
}
```

---

## 9. Run the Application

### Option A: Direct Python Execution (Recommended for Testing)

```bash
# Make sure virtual environment is activated
source venv/bin/activate

# Run the application
python3 tv_controller.py
```

### Option B: Use the Launch Script

```bash
# Make the script executable (one-time)
chmod +x "Start TV Controller.command"

# Run the application
./Start\ TV\ Controller.command
```

### Option C: Double-Click to Launch

1. In Finder, navigate to the project folder
2. Double-click `Start TV Controller.command`
3. If prompted about security, right-click and select "Open"

---

## 10. Testing the Application

### Step 10.1: Initial Launch Test

When you first run the application:

1. **GUI Window** should appear with a dark theme
2. **Two columns** should display: "Inside TVs" and "Outside TVs"
3. **All indicators** should be gray (unknown state)
4. **Buttons** should be clickable

### Step 10.2: Test TV Connectivity

#### For Android TVs:

1. Ensure the TV is powered on and connected to the network
2. Click the **"Check"** button next to a TV
3. Watch the indicator:
   - **Yellow** → Connecting...
   - **Green** → Connected successfully
   - **Red** → Connection failed

#### For LG WebOS TVs:

1. First connection requires TV approval
2. Click **"Check"** on an LG TV
3. **Accept the connection prompt** on the TV screen
4. The token is saved for future connections

### Step 10.3: Test Power Controls

1. Click **"On"** to turn on a TV
2. Click **"Off"** to turn off a TV
3. Use **"All On"** / **"All Off"** for group control

### Step 10.4: Test from Terminal (ADB Direct)

Test ADB connectivity directly:

```bash
# Connect to a TV
./adb/mac/adb connect 192.168.1.100:5555

# Check if connected
./adb/mac/adb devices

# Check power state
./adb/mac/adb -s 192.168.1.100:5555 shell dumpsys power | grep mWakefulness

# Send power toggle
./adb/mac/adb -s 192.168.1.100:5555 shell input keyevent 26

# Disconnect
./adb/mac/adb disconnect 192.168.1.100:5555
```

---

## 11. Troubleshooting

### Issue: "Python not found"

**Solution:**
```bash
# Check if python3 is installed
which python3

# If not found, reinstall
brew install python3
```

### Issue: "No module named 'tkinter'"

**Solution:**
```bash
# Install Python with tkinter support
brew install python-tk@3.11
```

### Issue: "ADB: Permission denied"

**Solution:**
```bash
chmod +x adb/mac/adb
xattr -d com.apple.quarantine adb/mac/adb
```

### Issue: "Cannot connect to TV"

**Checklist:**
1. Is the TV powered on?
2. Is the TV on the same network as your Mac?
3. Can you ping the TV? `ping 192.168.1.100`
4. Is ADB debugging enabled on the TV?
5. Is the firewall blocking port 5555?

### Issue: "LG TV: Connection refused"

**Solution:**
1. Ensure **LG Connect Apps** is enabled on the TV
2. Go to TV Settings > Network > LG Connect Apps
3. Enable the setting and try again
4. You may need to accept a pairing prompt on the TV

### Issue: "GUI looks wrong or doesn't display"

**Solution:**
```bash
# Install XQuartz for better display support
brew install --cask xquartz

# Restart your Mac after installation
```

### Issue: "Virtual environment issues"

**Solution:**
```bash
# Remove and recreate virtual environment
rm -rf venv
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## 12. Building for Distribution

### Create a Standalone App Bundle (Optional)

If you want to distribute the app to other Macs:

#### Step 12.1: Install PyInstaller

```bash
pip install pyinstaller
```

#### Step 12.2: Create App Bundle

```bash
pyinstaller --onefile --windowed \
  --name "TV Controller" \
  --add-data "adb/mac/adb:adb/mac" \
  --add-data "config.json:." \
  tv_controller.py
```

#### Step 12.3: Find Your App

The app will be in: `dist/TV Controller.app`

### Alternative: Simple Distribution

For simple sharing within your organization:

1. Zip the entire project folder
2. Share the ZIP file
3. Recipients follow this guide to set up

---

## Quick Reference Commands

```bash
# Activate virtual environment
source venv/bin/activate

# Run the application
python3 tv_controller.py

# Check ADB connectivity
./adb/mac/adb devices

# Install dependencies
pip install -r requirements.txt

# Deactivate virtual environment
deactivate
```

---

## Support

If you encounter issues:

1. Check the [Troubleshooting](#11-troubleshooting) section above
2. Ensure your TV supports ADB over network (Android TVs) or LG Connect Apps (WebOS TVs)
3. Verify network connectivity between your Mac and TVs
4. Report issues at the project repository

---

*Last updated: January 2026*
