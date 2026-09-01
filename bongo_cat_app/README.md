# 🖥️ Bongo Cat Desktop Application

The companion Windows application that monitors your typing and system stats, then sends this data to your ESP32 Bongo Cat display.

## 📁 Application Structure

- **`main.py`** - Application entry point and startup logic
- **`engine.py`** - Core functionality (keyboard monitoring, system stats, serial communication)
- **`gui.py`** - Settings interface using Tkinter (includes Sprite editor tab)
- **`tray.py`** - System tray integration and menu (includes Sprite editor)
- **`sprite_studio_ctl.py`** - Start/stop the browser sprite editor (port 8765)
- **`config.py`** - Configuration management and persistence
- **`default_config.json`** - Default application settings

## ⚙️ Features

### 🎯 Real-time Monitoring
- **Keyboard Input Detection** - Tracks typing activity and calculates WPM
- **System Statistics** - Monitors CPU and RAM usage
- **Time Display** - Sends current time to ESP32

### 🔗 Communication
- **Automatic ESP32 Detection** - Finds and connects to your Bongo Cat device
- **Serial Protocol** - Sends formatted commands over USB serial
- **Connection Management** - Handles reconnection and error recovery

### 🎛️ User Interface
- **System Tray Operation** - Runs quietly in background
- **Settings GUI** - Easy configuration of display options
- **Sprite editor** - Tray and Settings can start, stop, and open the pixel editor (does not auto-start)
- **Visual Feedback** - Shows connection status and activity

## 🚀 Setup Instructions

### Prerequisites
```bash
pip install -r requirements_app.txt
```

Required packages:
- `psutil` - System monitoring
- `pynput` - Keyboard input detection  
- `pyserial` - Serial communication
- `tkinter` - GUI (usually included with Python)

### Running from Source
```bash
cd bongo_cat_app
python main.py
```

Omit `--no-tray` if you want the Sprite editor menu. `--no-tray` is keyboard + serial only.

### Sprite editor (start / stop)

The pixel editor is a separate process (`tools/sprite_studio.py`). Cloning or
launching this app does **not** start it.

From the tray: **Sprite editor → Start / Stop / Open in browser**.
From Settings: **Sprite editor** tab, same buttons.

Start listens on port 8765. Stop kills the listener on that port. Closing this
app does not stop the editor.

Full guide: `../tools/sprite_studio/README.md`

### Building Executable
The project includes PyInstaller configuration for creating a standalone executable:
```bash
pyinstaller --onefile --windowed --icon=icon.ico main.py
```

## ⚙️ Configuration

Settings are stored in `config.json` and include:

### Display Settings
```json
{
  "display": {
    "show_cpu": true,
    "show_ram": true, 
    "show_wpm": true,
    "show_time": true
  }
}
```

### Behavior Settings
```json
{
  "behavior": {
    "sleep_timeout": 300,
    "animation_speed": 1.0,
    "wpm_calculation_window": 10
  }
}
```

### Connection Settings
```json
{
  "connection": {
    "auto_connect": true,
    "baud_rate": 115200,
    "reconnect_delay": 5
  }
}
```

## 📡 Communication Protocol

The app sends commands to ESP32 via serial at 115200 baud:

| Command | Format | Description |
|---------|--------|-------------|
| CPU | `CPU:XX` | CPU usage percentage (0-100) |
| RAM | `RAM:XX` | RAM usage percentage (0-100) |
| WPM | `WPM:XX` | Words per minute (0-999) |
| TIME | `TIME:HH:MM` | Current time in 24h format |
| ANIM | `ANIM:X` | Animation state (0-9) |

## 🔧 Development

### Code Structure
- **Object-oriented design** with clear separation of concerns
- **Threading** for non-blocking operation
- **Error handling** for robust operation
- **Logging** for debugging and troubleshooting

### Key Classes
- `BongoCatEngine` - Main application logic
- `ConfigManager` - Settings management
- `SystemTray` - Tray icon and menu
- `SettingsGUI` - Configuration interface
- `SpriteStudioController` - Start/stop the sprite editor process

### Adding Features
1. **Extend the engine** - Add new monitoring capabilities
2. **Update the protocol** - Define new command formats
3. **Modify the GUI** - Add configuration options
4. **Test thoroughly** - Ensure stability and performance

## 🐛 Troubleshooting

### Common Issues
- **ESP32 not detected**: Check USB drivers and COM port
- **High CPU usage**: Adjust monitoring intervals in config
- **Connection drops**: Verify cable connection and power

### Debug Mode
Run with debug logging:
```bash
python main.py --debug
```

## 🤝 Contributing

Contributions welcome! Areas for improvement:
- **Cross-platform support** (macOS, Linux)
- **Additional system metrics** (network, disk usage)
- **Plugin system** for custom monitoring
- **UI improvements** and themes

---

*Keep your Bongo Cat happy with real-time data!* 🐱💻 