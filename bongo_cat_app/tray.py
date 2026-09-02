#!/usr/bin/env python3
"""
Bongo Cat System Tray Integration
Provides system tray icon, menu, and background operation
"""

import pystray
from pystray import MenuItem as item
from PIL import Image, ImageDraw
import threading
import sys
import os
from typing import Optional, Callable

class BongoCatSystemTray:
    """System tray integration for Bongo Cat application"""
    
    def __init__(self, config_manager=None, engine=None, on_exit_callback: Optional[Callable] = None, studio=None):
        """Initialize system tray"""
        self.config = config_manager
        self.engine = engine
        self.studio = studio
        self.on_exit_callback = on_exit_callback
        
        self.icon = None
        self.settings_gui = None
        self.running = False
        self.tk_root = None  # Will be set by main app
        
        # Status tracking
        self.connection_status = "disconnected"
        self.last_wpm = 0
        self.typing_active = False
        

        
        # Create tray icon
        self.create_icon()
    
    def set_tkinter_root(self, root):
        """Set the tkinter root window for GUI operations"""
        self.tk_root = root
    
    def start_detached(self):
        """Start system tray using run_detached for proper GUI coexistence"""
        if self.icon:
            print("🚀 Starting pystray with run_detached()...")
            self.running = True
            self.icon.run_detached()
        else:
            print("❌ No tray icon created")
    
    def create_icon(self):
        """Create the system tray icon"""
        try:
            # Try to load icon from file first - check multiple formats
            # Support both development and exe paths
            import sys
            if getattr(sys, 'frozen', False):
                # Running as exe - assets are in the same directory
                base_path = sys._MEIPASS if hasattr(sys, '_MEIPASS') else os.path.dirname(sys.executable)
            else:
                # Running as script - look in bongo_cat_app/assets
                base_path = os.path.dirname(__file__)
            
            possible_paths = [
                os.path.join(base_path, "assets", "tray_icon.ico"),
                os.path.join(base_path, "assets", "tray_icon.png"),
                os.path.join(base_path, "assets", "tray_icon.jpg"),
                os.path.join(base_path, "assets", "tray_icon.jpeg"),
                # Fallback paths for development
                "assets/tray_icon.png",
                "bongo_cat_app/assets/tray_icon.png"
            ]
            
            icon_image = None
            for icon_path in possible_paths:
                if os.path.exists(icon_path):
                    print(f"🎨 Loading custom icon: {icon_path}")
                    icon_image = Image.open(icon_path)
                    # Resize to 64x64 for system tray
                    icon_image = icon_image.resize((64, 64), Image.Resampling.LANCZOS)
                    break
            
            if icon_image is None:
                # Create a simple cat icon if no file found
                print("🎨 Using generated cat icon")
                icon_image = self.create_cat_icon()
                
        except Exception as e:
            print(f"⚠️ Icon loading error: {e}")
            # Fallback to generated icon
            icon_image = self.create_cat_icon()
        
        # Create pystray icon
        self.icon = pystray.Icon(
            "BongoCat",
            icon_image,
            "Bongo Cat - Typing Monitor",
            menu=self.create_menu()
        )
    
    def create_cat_icon(self, size=64):
        """Create a simple cat icon programmatically"""
        # Create image with transparent background
        image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        
        # Draw simple cat face
        # Face (circle)
        face_margin = size // 8
        draw.ellipse([face_margin, face_margin, size-face_margin, size-face_margin], 
                    fill=(100, 100, 100, 255), outline=(50, 50, 50, 255), width=2)
        
        # Ears (triangles)
        ear_size = size // 6
        # Left ear
        draw.polygon([(face_margin, face_margin + ear_size), 
                     (face_margin + ear_size, face_margin), 
                     (face_margin + ear_size*2, face_margin + ear_size)], 
                    fill=(100, 100, 100, 255))
        # Right ear  
        draw.polygon([(size - face_margin - ear_size*2, face_margin + ear_size),
                     (size - face_margin - ear_size, face_margin),
                     (size - face_margin, face_margin + ear_size)],
                    fill=(100, 100, 100, 255))
        
        # Eyes
        eye_y = face_margin + size // 4
        eye_size = size // 12
        # Left eye
        draw.ellipse([face_margin + size//4 - eye_size, eye_y - eye_size,
                     face_margin + size//4 + eye_size, eye_y + eye_size],
                    fill=(0, 0, 0, 255))
        # Right eye
        draw.ellipse([size - face_margin - size//4 - eye_size, eye_y - eye_size,
                     size - face_margin - size//4 + eye_size, eye_y + eye_size],
                    fill=(0, 0, 0, 255))
        
        # Nose (small triangle)
        nose_y = eye_y + size // 8
        nose_size = size // 20
        draw.polygon([(size//2, nose_y - nose_size),
                     (size//2 - nose_size, nose_y + nose_size),
                     (size//2 + nose_size, nose_y + nose_size)],
                    fill=(255, 100, 100, 255))
        
        return image
    
    def create_menu(self):
        """Create the system tray context menu"""
        return pystray.Menu(
            item(
                "Bongo Cat Monitor",
                self.show_about,
                default=True
            ),
            pystray.Menu.SEPARATOR,
            item(
                "Settings...",
                self.show_settings
            ),
            item(
                "Connection",
                pystray.Menu(
                    item(
                        self.get_connection_status,
                        None,
                        enabled=False
                    ),
                    pystray.Menu.SEPARATOR,
                    item(
                        "Reconnect",
                        self.reconnect_device,
                        enabled=lambda item: self.connection_status != "connected"
                    ),
                    item(
                        "Disconnect", 
                        self.disconnect_device,
                        enabled=lambda item: self.connection_status == "connected"
                    )
                )
            ),

            item(
                "Animation",
                pystray.Menu(
                    item(
                        "Groove (WPM loop)",
                        self.set_paw_mode_groove,
                        checked=lambda item: self.get_paw_mode() == "groove",
                    ),
                    item(
                        "Mimic (per-key)",
                        self.set_paw_mode_mimic,
                        checked=lambda item: self.get_paw_mode() == "mimic",
                    ),
                ),
            ),
            item(
                "Sprite editor",
                pystray.Menu(
                    item(
                        self.get_sprite_studio_status,
                        None,
                        enabled=False,
                    ),
                    pystray.Menu.SEPARATOR,
                    item(
                        "Start",
                        self.start_sprite_studio,
                        enabled=lambda item: not self.sprite_studio_running(),
                    ),
                    item(
                        "Stop",
                        self.stop_sprite_studio,
                        enabled=lambda item: self.sprite_studio_running(),
                    ),
                    item(
                        "Open in browser",
                        self.open_sprite_studio,
                        enabled=lambda item: self.sprite_studio_running(),
                    ),
                ),
            ),
            pystray.Menu.SEPARATOR,
            item(
                "Start with Windows",
                self.toggle_startup,
                checked=lambda item: self.get_startup_setting()
            ),
            item(
                "Show Notifications",
                self.toggle_notifications,
                checked=lambda item: self.get_notifications_setting()
            ),
            pystray.Menu.SEPARATOR,
            item(
                "Exit",
                self.exit_application
            )
        )
    
    def get_connection_status(self, item=None):
        """Get current connection status text"""
        status_map = {
            "connected": "[✓] Connected to ESP32",
            "connecting": "[~] Connecting...",
            "disconnected": "[✗] Disconnected", 
            "error": "[!] Connection Error"
        }
        return status_map.get(self.connection_status, "[?] Unknown")
    

    
    def get_paw_mode(self):
        if self.config:
            return self.config.get_behavior_settings().get("paw_mode", "groove")
        if self.engine:
            return getattr(self.engine, "paw_mode", "groove")
        return "groove"

    def set_paw_mode_groove(self, item=None):
        self._set_paw_mode("groove")

    def set_paw_mode_mimic(self, item=None):
        self._set_paw_mode("mimic")

    def _set_paw_mode(self, mode):
        if self.config:
            self.config.set_setting("behavior", "paw_mode", mode)
            self.config.save_config()
        if self.engine:
            for cmd in self.engine.mimic.set_mode(mode):
                self.engine.send_command(cmd)
            self.engine.paw_mode = mode
        self.show_notification("Animation", f"Paw mode: {mode}")

    def get_startup_setting(self):
        """Get startup setting from config"""
        if self.config:
            startup = self.config.get_startup_settings()
            return startup.get('start_with_windows', True)
        return False
    
    def get_notifications_setting(self):
        """Get notifications setting from config"""
        if self.config:
            startup = self.config.get_startup_settings()
            return startup.get('show_notifications', True)
        return False
    
    def show_about(self, item=None):
        """Show about dialog"""
        self.show_notification(
            "About Bongo Cat",
            "Bongo Cat Typing Monitor v2.0\n\nMonitors your typing and shows cute cat animations!\n\nRight-click for more options."
        )
    
    def show_settings(self, item=None):
        """Show the settings GUI window"""
        try:
            print("⚙️ Opening settings window...")
            
            # Import here to avoid circular imports
            from gui import BongoCatSettingsGUI
            
            # Create and show settings GUI in separate thread (simpler approach)
            def create_and_show_gui():
                try:
                    import tkinter as tk
                    
                    if not self.settings_gui:
                        print("🔧 Creating settings GUI...")
                        
                        # Create a new root window for the settings
                        settings_root = tk.Tk()
                        settings_root.withdraw()  # Hide the root
                        
                        self.settings_gui = BongoCatSettingsGUI(
                            config_manager=self.config,
                            engine=self.engine,
                            on_close_callback=self.on_settings_closed,
                            parent_root=settings_root,
                            studio=self._studio(),
                        )
                    
                    print("📱 Showing settings window...")
                    self.settings_gui.show()
                    
                    # Start the GUI event loop for this window
                    if hasattr(self.settings_gui, 'window') and self.settings_gui.window:
                        self.settings_gui.window.mainloop()
                        
                except Exception as e:
                    print(f"❌ Error creating settings GUI: {e}")
                    self.show_notification("Error", f"Failed to open settings: {e}")
            
            # Run GUI in separate thread
            import threading
            gui_thread = threading.Thread(target=create_and_show_gui, daemon=True)
            gui_thread.start()
            print("🚀 Settings GUI started in separate thread")
            
        except Exception as e:
            print(f"❌ Error starting settings GUI: {e}")
            self.show_notification("Error", f"Failed to open settings: {e}")
    
    def on_settings_closed(self):
        """Handle settings window being closed"""
        self.settings_gui = None
    
    def reconnect_device(self, item=None):
        """Reconnect to ESP32"""
        if self.engine:
            def reconnect_thread():
                self.update_connection_status("connecting")
                self.show_notification("Bongo Cat", "Attempting to reconnect...")
                
                # Disconnect first if connected
                if self.engine.serial_conn and self.engine.serial_conn.is_open:
                    self.engine.disconnect_serial()
                
                # Try to reconnect
                if self.engine.connect_serial():
                    self.update_connection_status("connected")
                    self.show_notification("Bongo Cat", "Successfully reconnected to ESP32!")
                else:
                    self.update_connection_status("error")
                    self.show_notification("Bongo Cat", "Failed to reconnect. Check USB connection.")
            
            threading.Thread(target=reconnect_thread, daemon=True).start()
    
    def disconnect_device(self, item=None):
        """Disconnect from ESP32"""
        if self.engine:
            self.engine.disconnect_serial()
            self.update_connection_status("disconnected")
            self.show_notification("Bongo Cat", "Disconnected from ESP32")

    def _studio(self):
        if self.studio is None:
            from sprite_studio_ctl import SpriteStudioController
            self.studio = SpriteStudioController()
        return self.studio

    def sprite_studio_running(self, item=None):
        return self._studio().is_running()

    def get_sprite_studio_status(self, item=None):
        studio = self._studio()
        if studio.is_running():
            return f"[✓] Running (port {studio.port})"
        return "[✗] Stopped"

    def start_sprite_studio(self, item=None):
        result = self._studio().start()
        self.refresh_menu()
        if result.get("ok"):
            self.open_sprite_studio()
            self.show_notification("Sprite editor", "Started")
        else:
            self.show_notification("Sprite editor", result.get("error") or "Failed to start")

    def stop_sprite_studio(self, item=None):
        result = self._studio().stop()
        self.refresh_menu()
        if result.get("ok"):
            self.show_notification("Sprite editor", "Stopped")
        else:
            self.show_notification("Sprite editor", result.get("error") or "Failed to stop")

    def open_sprite_studio(self, item=None):
        import webbrowser
        studio = self._studio()
        if not studio.is_running():
            self.show_notification("Sprite editor", "Start the editor first")
            return
        webbrowser.open(studio.local_url())
    
    def toggle_startup(self, item=None):
        """Toggle startup with Windows setting"""
        if self.config:
            current = self.get_startup_setting()
            self.config.set_setting('startup', 'start_with_windows', not current)
            self.config.save_config()
            
            status = "enabled" if not current else "disabled"
            self.show_notification("Startup Setting", f"Start with Windows {status}")
    
    def toggle_notifications(self, item=None):
        """Toggle notifications setting"""
        if self.config:
            current = self.get_notifications_setting()
            self.config.set_setting('startup', 'show_notifications', not current)
            self.config.save_config()
            
            status = "enabled" if not current else "disabled"
            self.show_notification("Notifications", f"Notifications {status}")
    
    def exit_application(self, item=None):
        """Exit the application"""
        self.show_notification("Bongo Cat", "Goodbye! 👋")
        self.stop()
        
        if self.on_exit_callback:
            self.on_exit_callback()
        else:
            sys.exit(0)
    
    def update_connection_status(self, status: str):
        """Update connection status"""
        old_status = self.connection_status
        self.connection_status = status

        
        # Update icon tooltip
        status_text = self.get_connection_status().replace('🟢 ', '').replace('🟡 ', '').replace('🔴 ', '').replace('❌ ', '')
        if self.icon:
            self.icon.title = f"Bongo Cat - {status_text}"
            # Refresh menu to update connection status display
            self.refresh_menu()
    
    def update_typing_status(self, active: bool, wpm: float = 0):
        """Update typing status"""
        self.typing_active = active
        self.last_wpm = wpm
        
        # Update tooltip with current status
        if self.icon:
            if active:
                self.icon.title = f"Bongo Cat - Typing ({wpm:.0f} WPM)"
            else:
                self.icon.title = "Bongo Cat - Idle"
    
    def refresh_menu(self):
        """Refresh the tray menu to reflect current settings"""
        try:
            if self.icon:
                # Update the menu with current settings
                self.icon.menu = self.create_menu()

        except Exception as e:
            print(f"⚠️ Menu refresh error: {e}")
    
    def on_config_change(self, key: str, value):
        """Handle configuration changes from settings GUI"""
        # Refresh menu when startup settings change (affects checkboxes)
        if key.startswith('startup.'):

            self.refresh_menu()
    
    def show_notification(self, title: str, message: str):
        """Show system notification"""
        try:
            if self.icon and self.get_notifications_setting():
                self.icon.notify(message, title)
        except Exception as e:
            print(f"⚠️ Notification error: {e}")
    
    def start(self):
        """Start the system tray"""
        if self.icon and not self.running:
            self.running = True
            print("🔄 Starting system tray...")
            
            # Show startup notification
            self.show_notification("Bongo Cat", "Started successfully! Right-click the tray icon for options.")
            
            # Run the icon (this blocks)
            self.icon.run()
    
    def stop(self):
        """Stop the system tray"""
        if self.icon and self.running:
            self.running = False
            print("🛑 Stopping system tray...")
            self.icon.stop()
    
    def run_in_background(self):
        """Run system tray in background thread"""
        if not self.running:
            tray_thread = threading.Thread(target=self.start, daemon=True)
            tray_thread.start()
            return tray_thread
        return None

def main():
    """Test system tray independently"""
    print("🧪 Testing System Tray...")
    
    # Create basic tray (without engine/config for testing)
    tray = BongoCatSystemTray()
    
    print("📱 System tray started. Check your system tray area!")
    print("🖱️ Right-click the cat icon to see the menu")
    print("🛑 Use 'Exit' from the tray menu to close")
    
    try:
        # Start tray (this will block)
        tray.start()
    except KeyboardInterrupt:
        print("\n🛑 Stopping...")
        tray.stop()
    
    print("✅ System tray test completed")

if __name__ == "__main__":
    main() 