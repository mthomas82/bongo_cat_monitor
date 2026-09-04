#!/usr/bin/env python3
"""
Bongo Cat Application - Main Entry Point
Fixed threading model - Engine ALWAYS runs on main thread for proper keyboard timing
"""

import sys
import signal
import argparse
import threading
import time
from config import ConfigManager
from engine import BongoCatEngine
try:
    from tray import BongoCatSystemTray
except Exception as e:
    BongoCatSystemTray = None
    print(f"System tray not available ({e}); continuing without it")

class BongoCatApplication:
    """Main Bongo Cat application with FIXED thread-safe GUI"""
    
    def __init__(self, start_minimized=False, port=None, no_tray=False):
        """Initialize the application"""
        self.start_minimized = start_minimized
        self.port_override = port
        self.no_tray = no_tray
        self.config = None
        self.engine = None
        self.studio = None
        self.tray = None
        self.tk_root = None
        self.running = False
        
        # Setup signal handlers
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
    
    def signal_handler(self, sig, frame):
        """Handle shutdown signals gracefully"""
        print('\n🛑 Shutting down gracefully...')
        self.shutdown()
    
    def initialize_components(self):
        """Initialize all application components"""
        try:
            # Initialize configuration manager
            print("📂 Loading configuration...")
            self.config = ConfigManager()
            
            # Initialize engine with configuration
            print("Initializing Bongo Cat Engine...")
            from sprite_studio_ctl import SpriteStudioController
            self.studio = SpriteStudioController()
            self.engine = BongoCatEngine(config_manager=self.config)
            if self.port_override:
                self.engine.port = self.port_override
                print(f"Using serial port {self.port_override}")
            
            if self.no_tray:
                print("Skipping system tray")
            elif BongoCatSystemTray is None:
                print("pystray not installed; continuing without tray (pip install pystray)")
                self.no_tray = True
            else:
                print("Setting up system tray...")
                self.tray = BongoCatSystemTray(
                    config_manager=self.config,
                    engine=self.engine,
                    on_exit_callback=self.shutdown,
                    studio=self.studio,
                )
                self.engine.set_tray_reference(self.tray)
                self.config.add_change_callback(self.tray.on_config_change)
            
            return True
            
        except Exception as e:
            print(f"❌ Initialization error: {e}")
            return False
    
    def run(self):
        """Run the main application with FIXED threading model"""
        print("🐱 Bongo Cat Application v2.1 - FIXED THREADING")
        print("=" * 60)
        
        # Initialize components
        if not self.initialize_components():
            return 1
        
        self.running = True
        
        try:
            if self.no_tray:
                print("Tray disabled (--no-tray). Keyboard + serial only.")
            else:
                print("Starting system tray...")
                try:
                    self.tray.start_detached()
                except Exception as exc:
                    print(f"Tray failed ({exc}); continuing without it.")
                    self.no_tray = True
            
            # Update initial connection status
            print("🔄 Checking initial connection status...")
            
            if self.start_minimized:
                print("🔕 Running in background mode...")
                print("📱 Look for the cat icon in your system tray")
                print("🖱️ Right-click the tray icon for options")
                print("⌨️ Keyboard monitoring active on main thread")
            else:
                print("🖥️ Running in normal mode...")
                print("📝 Start typing to see your cat react!")
                print("🔄 System tray available in background")
                print("🛑 Press Ctrl+C to stop")
            
            print("✅ System tray started with run_detached()")
            print("💡 Settings window available from tray menu")
            print("🎯 Starting animation engine on MAIN THREAD for optimal responsiveness...")
            
            # CRITICAL FIX: Engine ALWAYS runs on main thread (like original script)  
            # This ensures proper keyboard listener timing regardless of start mode
            self.engine.start_monitoring()
                
        except KeyboardInterrupt:
            print("\n🛑 Interrupted by user")
        except Exception as e:
            print(f"❌ Runtime error: {e}")
            return 1
        finally:
            self.shutdown()
        
        return 0
    

    
    def shutdown(self):
        """Shutdown the application gracefully"""
        print("🛑 Shutting down components...")
        
        self.running = False
        
        # Stop engine first
        if self.engine:
            self.engine.stop_monitoring()
        
        # Stop system tray
        if self.tray:
            self.tray.stop()
        
        # Clean up tkinter root if it exists
        if hasattr(self, 'tk_root') and self.tk_root:
            try:
                self.tk_root.destroy()
            except:
                pass
        
        print("👋 Goodbye!")
        sys.exit(0)

def main():
    """Main application entry point"""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Bongo Cat Typing Monitor")
    parser.add_argument("--minimized", action="store_true",
                       help="Start minimized to system tray")
    parser.add_argument("--startup", action="store_true",
                       help="Started automatically with Windows")
    parser.add_argument("--port", default=None,
                       help="Serial device (e.g. /dev/cu.usbserial-0001). Default: auto")
    parser.add_argument("--no-tray", action="store_true",
                       help="Skip system tray (recommended for first Mac/Linux test)")
    
    args = parser.parse_args()
    
    start_minimized = args.minimized or args.startup
    app = BongoCatApplication(
        start_minimized=start_minimized,
        port=args.port,
        no_tray=args.no_tray,
    )
    return app.run()

if __name__ == "__main__":
    sys.exit(main())
