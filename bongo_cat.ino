#include <lvgl.h>
#include <TFT_eSPI.h>
#include <WiFi.h>
#include <EEPROM.h>
#include "Free_Fonts.h"
#include "animations_sprites.h"
#include "display_layout.h"
#ifndef STAT_KEYS_X
#define STAT_KEYS_X -5
#endif
#ifndef STAT_KEYS_Y
#define STAT_KEYS_Y 25
#endif

// Display settings
#define SCREEN_WIDTH 240
#define SCREEN_HEIGHT 320

// Configuration settings structure
struct BongoCatSettings {
    bool show_cpu = true;
    bool show_ram = true;
    bool show_wpm = true;
    bool show_time = true;
    bool time_format_24h = true;
    int sleep_timeout_minutes = 5;
    float animation_sensitivity = 1.0;
    uint32_t checksum = 0;  // For validation
};

// EEPROM settings
#define SETTINGS_ADDRESS 0
#define SETTINGS_SIZE sizeof(BongoCatSettings)
#define EEPROM_SIZE 512  // ESP32 EEPROM size

// Global settings instance
BongoCatSettings settings;

TFT_eSPI tft = TFT_eSPI();

// LVGL display buffer
static lv_disp_draw_buf_t draw_buf;
static lv_color_t buf[SCREEN_WIDTH * 10];

// Animation system with sprites
sprite_manager_t sprite_manager;
lv_obj_t * cat_canvas = NULL;
uint32_t last_frame_time = 0;
bool animation_paused = false;

// Enhanced animation control
bool python_control_mode = true;  // Python controls idle progression
uint32_t last_command_time = 0;   // Track when last command received
#define TYPING_TIMEOUT_MS 2000    // Stop typing animation after 2 seconds of no commands
#define PYTHON_TIMEOUT_MS 5000    // Fall back to auto mode after 5 seconds
#define EXCITEMENT_IDLE_MS (10UL * 60UL * 1000UL)  // Extreme excitement after 10 min idle
#define SCREENSAVER_IDLE_MS (20UL * 60UL * 1000UL)
#define SCREENSAVER_ZOOM 512
#define SCREENSAVER_MARGIN_TOP 40
#define SCREENSAVER_STEP_MS 40
#define MIMIC_PAW_HOLD_MS 70
#define REACT_TYPO_MS 800
#define REACT_SAVE_MS 400
#define REACT_GROOM_MS 700
#define REACT_NONE 0
#define REACT_TYPO 1
#define REACT_SAVE 2
#define REACT_GROOM 3

// Simplified animation performance (removed aggressive frame limiting)
uint32_t frame_skip_counter = 0;

// Cat positioning (restored to original working method)
#define CAT_SIZE 64   // Base sprite size

bool screensaver_active = false;
int screensaver_x = 0;
int screensaver_y = SCREENSAVER_MARGIN_TOP;
int screensaver_vx = 1;
int screensaver_vy = 1;
uint32_t screensaver_last_move = 0;

void screensaver_enter();
void screensaver_exit();
void screensaver_update(uint32_t current_time);
void updateKeysDisplay();

// System stats display
lv_obj_t * screen = NULL;
lv_obj_t * cpu_label = NULL;
lv_obj_t * ram_label = NULL;
lv_obj_t * wpm_label = NULL;
lv_obj_t * time_label = NULL;
lv_obj_t * keys_label = NULL;

// Stats data
int cpu_usage = 0;
int ram_usage = 0;
int wpm_speed = 0;
uint32_t keys_typed = 0;
String current_time_str = "00:00";
bool time_initialized = false;  // Track if we've received time from Python

// Function to flush the display buffer
void my_disp_flush(lv_disp_drv_t *disp, const lv_area_t *area, lv_color_t *color_p) {
    uint32_t w = (area->x2 - area->x1 + 1);
    uint32_t h = (area->y2 - area->y1 + 1);

    tft.startWrite();
    tft.setAddrWindow(area->x1, area->y1, w, h);
    tft.pushColors((uint16_t*)&color_p->full, w * h, true);
    tft.endWrite();

    lv_disp_flush_ready(disp);
}

// Update system stats display
void updateSystemStats(int cpu, int ram, int wpm) {
    cpu_usage = cpu;
    ram_usage = ram;
    wpm_speed = wpm;
    
    if (cpu_label) {
        lv_label_set_text_fmt(cpu_label, "CPU: %d%%", cpu);
    }
    if (ram_label) {
        lv_label_set_text_fmt(ram_label, "RAM: %d%%", ram);
    }
    if (wpm_label) {
        lv_label_set_text_fmt(wpm_label, "WPM: %d", wpm);
    }
    updateKeysDisplay();
}

void updateKeysDisplay() {
    if (!keys_label) {
        return;
    }
    if (keys_typed >= 1000000UL) {
        lv_label_set_text_fmt(keys_label, "KEYS:%lu.%luM",
                              (unsigned long)(keys_typed / 1000000UL),
                              (unsigned long)((keys_typed / 100000UL) % 10UL));
    } else if (keys_typed >= 10000UL) {
        lv_label_set_text_fmt(keys_label, "KEYS:%luk",
                              (unsigned long)(keys_typed / 1000UL));
    } else {
        lv_label_set_text_fmt(keys_label, "KEYS:%lu", (unsigned long)keys_typed);
    }
}

// Update time display  
void updateTimeDisplay() {
    if (time_label && current_time_str.length() > 0) {
        String display_time = current_time_str;
        
        // Convert to 12-hour format if needed
        if (!settings.time_format_24h && current_time_str.length() == 5) {
            int hour = current_time_str.substring(0, 2).toInt();
            String minute = current_time_str.substring(3, 5);
            String ampm = (hour >= 12) ? "PM" : "AM";
            
            if (hour == 0) hour = 12;      // 00:xx -> 12:xx AM
            else if (hour > 12) hour -= 12; // 13:xx -> 1:xx PM
            
            display_time = String(hour) + ":" + minute + " " + ampm;
        }
        
        lv_label_set_text(time_label, display_time.c_str());
        
        // Debug output for time updates
        if (!time_initialized) {
            Serial.print("🕐 Time initialized: ");
            Serial.println(display_time);
            time_initialized = true;
        }
    }
}

// Settings management functions
uint32_t calculateChecksum(const BongoCatSettings* s) {
    // Simple checksum calculation (excluding checksum field itself)
    uint32_t sum = 0;
    const uint8_t* data = (const uint8_t*)s;
    size_t size = sizeof(BongoCatSettings) - sizeof(uint32_t); // Exclude checksum field
    
    for (size_t i = 0; i < size; i++) {
        sum += data[i];
    }
    return sum;
}

bool validateSettings(const BongoCatSettings* s) {
    // Check if settings are within valid ranges
    if (s->sleep_timeout_minutes < 1 || s->sleep_timeout_minutes > 60) return false;
    if (s->animation_sensitivity < 0.1 || s->animation_sensitivity > 5.0) return false;
    
    // Check if checksum matches
    uint32_t expected_checksum = calculateChecksum(s);
    return (s->checksum == expected_checksum);
}

void saveSettings() {
    settings.checksum = calculateChecksum(&settings);
    EEPROM.put(SETTINGS_ADDRESS, settings);
    EEPROM.commit();
    Serial.println("💾 Settings saved to EEPROM");
}

void loadSettings() {
    BongoCatSettings temp_settings;
    EEPROM.get(SETTINGS_ADDRESS, temp_settings);
    
    if (validateSettings(&temp_settings)) {
        settings = temp_settings;
        Serial.println("📂 Settings loaded from EEPROM");
        // Note: updateDisplayVisibility() will be called after UI creation
    } else {
        Serial.println("⚠️ Invalid settings in EEPROM, using defaults");
        resetSettings();
    }
}

void resetSettings() {
    // Reset to default values
    settings.show_cpu = true;
    settings.show_ram = true;
    settings.show_wpm = true;
    settings.show_time = true;
    settings.time_format_24h = true;
    settings.sleep_timeout_minutes = 5;
    settings.animation_sensitivity = 1.0;
    settings.checksum = calculateChecksum(&settings);
    
    Serial.println("🔄 Settings reset to factory defaults");
    // Note: updateDisplayVisibility() will be called after UI creation if needed
}

void updateDisplayVisibility() {
    // Show/hide labels based on settings (only if UI is created)
    if (cpu_label) {
        if (settings.show_cpu) {
            lv_obj_clear_flag(cpu_label, LV_OBJ_FLAG_HIDDEN);
        } else {
            lv_obj_add_flag(cpu_label, LV_OBJ_FLAG_HIDDEN);
        }
        Serial.println("🖥️ CPU visibility updated: " + String(settings.show_cpu ? "ON" : "OFF"));
    }
    
    if (ram_label) {
        if (settings.show_ram) {
            lv_obj_clear_flag(ram_label, LV_OBJ_FLAG_HIDDEN);
        } else {
            lv_obj_add_flag(ram_label, LV_OBJ_FLAG_HIDDEN);
        }
        Serial.println("💾 RAM visibility updated: " + String(settings.show_ram ? "ON" : "OFF"));
    }
    
    if (wpm_label) {
        if (settings.show_wpm) {
            lv_obj_clear_flag(wpm_label, LV_OBJ_FLAG_HIDDEN);
        } else {
            lv_obj_add_flag(wpm_label, LV_OBJ_FLAG_HIDDEN);
        }
        Serial.println("⌨️ WPM visibility updated: " + String(settings.show_wpm ? "ON" : "OFF"));
    }
    
    if (time_label) {
        if (settings.show_time) {
            lv_obj_clear_flag(time_label, LV_OBJ_FLAG_HIDDEN);
        } else {
            lv_obj_add_flag(time_label, LV_OBJ_FLAG_HIDDEN);
        }
        Serial.println("🕐 Time visibility updated: " + String(settings.show_time ? "ON" : "OFF"));
    }
}

void start_reaction(sprite_manager_t* manager, uint8_t kind, uint32_t current_time, uint32_t duration_ms);
void apply_mimic_tap(sprite_manager_t* manager, uint8_t paw, uint32_t current_time);
void apply_reaction_overlay(sprite_manager_t* manager, uint32_t current_time);

// Handle serial commands from Python script
void handleSerialCommands() {
    if (Serial.available()) {
        String command = Serial.readStringUntil('\n');
        command.trim();
        
        uint32_t current_time = millis();
        last_command_time = current_time;  // Update command timestamp
        python_control_mode = true;        // Ensure Python control is active
        
        if (command.startsWith("SPEED:")) {
            if (sprite_manager.mimic_mode) {
                last_command_time = current_time;
                python_control_mode = true;
                sprite_manager.idle_progression_enabled = false;
                Serial.println("SPEED ignored in MIMIC");
            } else {
            // Handle speed commands with enhanced logic  
            String speed_str = command.substring(6);
            uint16_t speed = speed_str.toInt();
            
            // Updated thresholds to match Python script (2024 industry standards)
            // Research shows: Average 40-45 WPM, Slow <20, Good 50-60, Professional 70+
            animation_state_t new_state = sprite_manager.current_state;
            
            if (speed == 0) {
                // Explicit stop command
                sprite_manager_set_state(&sprite_manager, ANIM_STATE_IDLE_STAGE1, current_time);
            } else if (speed < 80) {        // Slow threshold: <20 WPM -> speed 80+
                new_state = ANIM_STATE_TYPING_SLOW;
            } else if (speed < 150) {       // Normal threshold: 20-40 WPM -> speed 80-150
                new_state = ANIM_STATE_TYPING_NORMAL;
            } else {                        // Fast threshold: 40+ WPM -> speed 150+
                new_state = ANIM_STATE_TYPING_FAST;
            }
            
            // Always refresh state to prevent stuck animations (even if same state)
            sprite_manager_set_state(&sprite_manager, new_state, current_time);
            Serial.println("🔄 Animation state refreshed");
            
            // Check for significant speed changes that might cause stuck paws
            uint16_t old_speed = sprite_manager.animation_speed_ms;
            sprite_manager.animation_speed_ms = speed;
            
            // If speed changed significantly, reset paw timing to prevent stuck paws
            if (sprite_manager.paw_animation_active && abs((int)speed - (int)old_speed) > 50) {
                sprite_manager.paw_timer = current_time;  // Reset timing
                Serial.println("🔄 Speed change - resetting paw timing");
            }
            
            // Reset Python control timeout
            last_command_time = current_time;
            python_control_mode = true;
            sprite_manager.idle_progression_enabled = false;
            }
        } else if (command == "STOP") {
            // Explicit stop command - better than IDLE
            sprite_manager_set_state(&sprite_manager, ANIM_STATE_IDLE_STAGE1, current_time);
            sprite_manager.idle_progression_enabled = false; // Keep disabled until IDLE_START
            sprite_manager.mimic_paw_until = 0;
            python_control_mode = true;
            last_command_time = current_time;
            Serial.println("🛑 Received STOP command");
            
        } else if (command == "IDLE_START") {
            // Enable idle progression when Python detects no typing
            python_control_mode = false;  // Let Arduino handle idle progression
            if (sprite_manager.current_state == ANIM_STATE_EXCITED ||
                sprite_manager.current_state == ANIM_STATE_SCREENSAVER) {
                Serial.println("😴 IDLE_START ignored — already in long-idle state");
            } else {
                sprite_manager_set_state(&sprite_manager, ANIM_STATE_IDLE_STAGE1, current_time);
                sprite_manager.idle_progression_enabled = true;  // Enable automatic progression
                Serial.println("😴 Idle progression enabled");
            }
        } else if (command == "EXCITED") {
            sprite_manager_set_state(&sprite_manager, ANIM_STATE_EXCITED, current_time);
            python_control_mode = true;
            last_command_time = current_time;
            Serial.println("Excited after long idle");
            
        } else if (command == "SCREENSAVER") {
            sprite_manager_set_state(&sprite_manager, ANIM_STATE_SCREENSAVER, current_time);
            python_control_mode = true;
            last_command_time = current_time;
            Serial.println("Screensaver after 20 min idle");
            
        } else if (command == "IDLE") {
            // Compatibility with old command
            sprite_manager_set_state(&sprite_manager, ANIM_STATE_IDLE_STAGE1, current_time);
            Serial.println("PONG");
            
        } else if (command == "HEARTBEAT") {
            // Connection keepalive - just reset timeout
            last_command_time = current_time;
            python_control_mode = true;
        } else if (command == "STREAK_ON") {
            // Enable streak mode (happy face)
            sprite_manager.is_streak_mode = true;
            Serial.println("😊 Streak mode enabled - happy face!");
        } else if (command == "STREAK_OFF") {
            // Disable streak mode
            sprite_manager.is_streak_mode = false;
            Serial.println("😐 Streak mode disabled - normal face");
        } else if (command == "MODE:MIMIC") {
            sprite_manager.mimic_mode = true;
            sprite_manager.paw_animation_active = false;
            sprite_manager.mimic_paw_until = 0;
            Serial.println("Mimic mode — per-key TAP");
        } else if (command == "MODE:GROOVE") {
            sprite_manager.mimic_mode = false;
            sprite_manager.mimic_paw_until = 0;
            Serial.println("Groove mode — WPM SPEED loop");
        } else if (command.startsWith("TAP:")) {
            if (sprite_manager.mimic_mode) {
                uint8_t paw = (command.length() >= 5 && command.charAt(4) == 'R') ? 2 : 1;
                apply_mimic_tap(&sprite_manager, paw, current_time);
            }
        } else if (command == "REACT:TYPO") {
            start_reaction(&sprite_manager, REACT_TYPO, current_time, REACT_TYPO_MS);
            Serial.println("Typo tantrum");
        } else if (command == "REACT:SAVE") {
            start_reaction(&sprite_manager, REACT_SAVE, current_time, REACT_SAVE_MS);
            Serial.println("Save sparkle");
        } else if (command == "REACT:GROOM") {
            start_reaction(&sprite_manager, REACT_GROOM, current_time, REACT_GROOM_MS);
            Serial.println("Groom fidget");
        } else if (command.startsWith("STATS:")) {
            // Parse stats: STATS:CPU:45,RAM:67,WPM:23
            String stats = command.substring(6);
            
            int cpuStart = stats.indexOf("CPU:") + 4;
            int cpuEnd = stats.indexOf(",", cpuStart);
            int cpu = stats.substring(cpuStart, cpuEnd).toInt();
            
            int ramStart = stats.indexOf("RAM:") + 4;
            int ramEnd = stats.indexOf(",", ramStart);
            int ram = stats.substring(ramStart, ramEnd).toInt();
            
            int wpmStart = stats.indexOf("WPM:") + 4;
            int keysMark = stats.indexOf("KEYS:");
            int wpm = 0;
            if (keysMark >= 0 && keysMark > wpmStart) {
                wpm = stats.substring(wpmStart, keysMark).toInt();
                keys_typed = (uint32_t) stats.substring(keysMark + 5).toInt();
            } else {
                wpm = stats.substring(wpmStart).toInt();
            }
            
            updateSystemStats(cpu, ram, wpm);
            
        } else if (command.startsWith("KEYS:")) {
            keys_typed = (uint32_t) command.substring(5).toInt();
            updateKeysDisplay();

        } else if (command.startsWith("TIME:")) {
            // Handle time updates from Python script
            String time_str = command.substring(5);
            if (time_str.length() == 5 && time_str.charAt(2) == ':') {
                current_time_str = time_str;
            }
            
        } else if (command.startsWith("CPU:")) {
            // Handle CPU usage updates
            cpu_usage = command.substring(4).toInt();
            
        } else if (command.startsWith("RAM:")) {
            // Handle RAM usage updates  
            ram_usage = command.substring(4).toInt();
            
        } else if (command.startsWith("WPM:")) {
            // Handle WPM display updates
            wpm_speed = command.substring(4).toInt();
            
        } else if (command == "PING") {
            Serial.println("PONG");
            
        } else if (command.startsWith("ANIM:")) {
            // Handle specific animation commands from tester
            String anim = command.substring(5);
            if (anim == "IDLE_1") {
                sprite_manager_set_state(&sprite_manager, ANIM_STATE_IDLE_STAGE1, current_time);
            } else if (anim == "IDLE_2") {
                sprite_manager_set_state(&sprite_manager, ANIM_STATE_IDLE_STAGE2, current_time);
            } else if (anim == "IDLE_3") {
                sprite_manager_set_state(&sprite_manager, ANIM_STATE_IDLE_STAGE3, current_time);
            } else if (anim == "IDLE_4") {
                sprite_manager_set_state(&sprite_manager, ANIM_STATE_IDLE_STAGE4, current_time);
            } else if (anim == "BLINK") {
                sprite_manager_set_state(&sprite_manager, ANIM_STATE_BLINKING, current_time);
            } else if (anim == "EAR_TWITCH") {
                sprite_manager_set_state(&sprite_manager, ANIM_STATE_EAR_TWITCH, current_time);
            } else if (anim == "EXCITED") {
                sprite_manager_set_state(&sprite_manager, ANIM_STATE_EXCITED, current_time);
            } else if (anim == "SCREENSAVER") {
                sprite_manager_set_state(&sprite_manager, ANIM_STATE_SCREENSAVER, current_time);
            }
            Serial.println("PONG");
            
        // NEW CONFIGURATION COMMANDS
        } else if (command.startsWith("DISPLAY_CPU:")) {
            String value = command.substring(12);
            settings.show_cpu = (value == "ON");
            updateDisplayVisibility();
            Serial.println("🖥️ CPU display: " + value);
            
        } else if (command.startsWith("DISPLAY_RAM:")) {
            String value = command.substring(12);
            settings.show_ram = (value == "ON");
            updateDisplayVisibility();
            Serial.println("💾 RAM display: " + value);
            
        } else if (command.startsWith("DISPLAY_WPM:")) {
            String value = command.substring(12);
            settings.show_wpm = (value == "ON");
            updateDisplayVisibility();
            Serial.println("⌨️ WPM display: " + value);
            
        } else if (command.startsWith("DISPLAY_TIME:")) {
            String value = command.substring(13);
            settings.show_time = (value == "ON");
            updateDisplayVisibility();
            Serial.println("🕐 Time display: " + value);
            
        } else if (command.startsWith("TIME_FORMAT:")) {
            String format = command.substring(12);
            settings.time_format_24h = (format == "24");
            Serial.println("🕐 Time format: " + format + " hour");
            
        } else if (command.startsWith("SLEEP_TIMEOUT:")) {
            int timeout = command.substring(14).toInt();
            if (timeout >= 1 && timeout <= 60) {
                settings.sleep_timeout_minutes = timeout;
                Serial.println("😴 Sleep timeout: " + String(timeout) + " minutes");
            } else {
                Serial.println("❌ Invalid sleep timeout (1-60 minutes)");
            }
            
        } else if (command.startsWith("SENSITIVITY:")) {
            float sensitivity = command.substring(12).toFloat();
            if (sensitivity >= 0.1 && sensitivity <= 5.0) {
                settings.animation_sensitivity = sensitivity;
                Serial.println("🎚️ Animation sensitivity: " + String(sensitivity));
            } else {
                Serial.println("❌ Invalid sensitivity (0.1-5.0)");
            }
            
        } else if (command == "SAVE_SETTINGS") {
            saveSettings();
            
        } else if (command == "LOAD_SETTINGS") {
            loadSettings();
            updateDisplayVisibility();  // Apply the loaded settings immediately
            
        } else if (command == "RESET_SETTINGS") {
            resetSettings();
            updateDisplayVisibility();  // Apply the reset settings immediately
            saveSettings();  // Save defaults to EEPROM
            Serial.println("🔄 Settings reset and saved");
        }
    }
}

// Sprite management functions
void sprite_manager_init(sprite_manager_t* manager) {
    // Initialize all layers to basic state
    manager->current_sprites[LAYER_BODY] = &standardbody1;
    manager->current_sprites[LAYER_FACE] = &stock_face;
    manager->current_sprites[LAYER_TABLE] = &table1;
    manager->current_sprites[LAYER_PAWS] = &twopawsup;  // Default paws up
    manager->current_sprites[LAYER_EFFECTS] = NULL;
    
    manager->current_state = ANIM_STATE_IDLE_STAGE1;
    manager->state_start_time = millis();
    manager->blink_timer = millis() + random(3000, 8000);
    manager->ear_twitch_timer = millis() + random(10000, 30000);
    manager->effect_timer = 0;
    manager->effect_frame = 0;
    manager->paw_animation_active = false;
    manager->paw_frame = 0;
    manager->paw_timer = 0;
    manager->animation_speed_ms = 200;  // Default speed
    manager->click_effect_left = false;
    
    // Enhanced animation control
    manager->idle_progression_enabled = false;  // Start with Python control
    manager->last_typing_time = 0;
    manager->is_streak_mode = false;             // Start without streak mode
    
    // Initialize animation state variables
    manager->blink_start_time = 0;
    manager->blinking = false;
    manager->ear_twitch_start_time = 0;
    manager->ear_twitching = false;
    manager->mimic_mode = false;
    manager->mimic_paw_until = 0;
    manager->mimic_paw = 0;
    manager->reaction_until = 0;
    manager->reaction_kind = REACT_NONE;
    
    Serial.println("🐱 Sprite manager initialized");
}

// Calculate adaptive sleep stage timing based on user's timeout setting
void calculateSleepStageTiming(int timeout_minutes, unsigned long* stage1_ms, unsigned long* stage2_ms, unsigned long* stage3_ms) {
    unsigned long total_ms = (unsigned long)timeout_minutes * 60 * 1000;
    
    // Define minimums and maximums for each stage
    unsigned long min_stage2 = 5000;   // 5 seconds minimum
    unsigned long max_stage2 = 60000;  // 1 minute maximum
    unsigned long min_stage3 = 3000;   // 3 seconds minimum  
    unsigned long max_stage3 = 30000;  // 30 seconds maximum
    
    // Calculate based on timeout range for optimal user experience
    if (timeout_minutes <= 3) {
        // Short timeouts: quick but visible progression
        *stage2_ms = max(min_stage2, min(max_stage2, (unsigned long)(total_ms * 0.25)));
        *stage3_ms = max(min_stage3, min(max_stage3, (unsigned long)(total_ms * 0.15)));
    } else if (timeout_minutes <= 10) {
        // Medium timeouts: balanced progression
        *stage2_ms = max(min_stage2, min(max_stage2, (unsigned long)(total_ms * 0.20)));
        *stage3_ms = max(min_stage3, min(max_stage3, (unsigned long)(total_ms * 0.10)));
    } else {
        // Long timeouts: mostly normal, quick sleep transition
        *stage2_ms = max(min_stage2, min(max_stage2, (unsigned long)(total_ms * 0.15)));
        *stage3_ms = max(min_stage3, min(max_stage3, (unsigned long)(total_ms * 0.05)));
    }
    
    // Stage 1 gets the remainder to ensure total equals user setting
    *stage1_ms = total_ms - *stage2_ms - *stage3_ms;
}

void sprite_manager_update(sprite_manager_t* manager, uint32_t current_time) {
    // Check for typing timeout (Arduino-side safety)
    if (manager->paw_animation_active && manager->last_typing_time > 0) {
        if (current_time - manager->last_typing_time > TYPING_TIMEOUT_MS) {
            // Stop typing animation due to timeout
            manager->paw_animation_active = false;
            manager->current_sprites[LAYER_EFFECTS] = NULL;
            Serial.println("🛑 Typing timeout - stopping animation");
        }
    }
    
    // Check if Python control has timed out
    if (python_control_mode && current_time - last_command_time > PYTHON_TIMEOUT_MS) {
        python_control_mode = false;
        manager->idle_progression_enabled = true;
        Serial.println("⚠️ Python timeout - enabling auto mode");
    }
    
    // Long-idle milestones (host also sends EXCITED / SCREENSAVER)
    if (manager->current_state != ANIM_STATE_TYPING_SLOW &&
        manager->current_state != ANIM_STATE_TYPING_NORMAL &&
        manager->current_state != ANIM_STATE_TYPING_FAST &&
        manager->current_state != ANIM_STATE_TYPING_STREAK &&
        manager->last_typing_time > 0) {
        uint32_t idle_ms = current_time - manager->last_typing_time;
        if (idle_ms >= SCREENSAVER_IDLE_MS &&
            manager->current_state != ANIM_STATE_SCREENSAVER) {
            sprite_manager_set_state(manager, ANIM_STATE_SCREENSAVER, current_time);
        } else if (idle_ms >= EXCITEMENT_IDLE_MS &&
                   manager->current_state != ANIM_STATE_EXCITED &&
                   manager->current_state != ANIM_STATE_SCREENSAVER) {
            sprite_manager_set_state(manager, ANIM_STATE_EXCITED, current_time);
        }
    }

    // Handle automatic idle progression only if enabled
    if ((manager->idle_progression_enabled || !python_control_mode) &&
        manager->current_state != ANIM_STATE_EXCITED &&
        manager->current_state != ANIM_STATE_SCREENSAVER) {
        // Calculate adaptive timing based on current sleep timeout setting
        unsigned long stage1_duration, stage2_duration, stage3_duration;
        calculateSleepStageTiming(settings.sleep_timeout_minutes, &stage1_duration, &stage2_duration, &stage3_duration);
        
        if (manager->current_state == ANIM_STATE_IDLE_STAGE1) {
            if (current_time - manager->state_start_time > stage1_duration) {
                sprite_manager_set_state(manager, ANIM_STATE_IDLE_STAGE2, current_time);
            }
        } else if (manager->current_state == ANIM_STATE_IDLE_STAGE2) {
            if (current_time - manager->state_start_time > stage2_duration) {
                sprite_manager_set_state(manager, ANIM_STATE_IDLE_STAGE3, current_time);
            }
        } else if (manager->current_state == ANIM_STATE_IDLE_STAGE3) {
            if (current_time - manager->state_start_time > stage3_duration) {
                sprite_manager_set_state(manager, ANIM_STATE_IDLE_STAGE4, current_time);
            }
        }
    }
    
    // Handle paw animations - 4-step pattern: left_down → both_up → right_down → both_up
    if (manager->mimic_mode) {
        if (manager->mimic_paw_until != 0 && current_time < manager->mimic_paw_until) {
            if (manager->mimic_paw == 2) {
                manager->current_sprites[LAYER_PAWS] = &rightpawdown;
                manager->current_sprites[LAYER_EFFECTS] = manager->is_streak_mode ? &right_click_effect : NULL;
            } else {
                manager->current_sprites[LAYER_PAWS] = &leftpawdown;
                manager->current_sprites[LAYER_EFFECTS] = manager->is_streak_mode ? &left_click_effect : NULL;
            }
        } else if (manager->mimic_paw_until != 0 && current_time >= manager->mimic_paw_until) {
            manager->mimic_paw_until = 0;
            manager->current_sprites[LAYER_PAWS] = &twopawsup;
            if (manager->current_state != ANIM_STATE_EXCITED) {
                manager->current_sprites[LAYER_EFFECTS] = NULL;
            }
        }
    } else if (manager->paw_animation_active) {
        // Trust Python's speed calculations - no additional rate limiting
        if (current_time - manager->paw_timer >= manager->animation_speed_ms) {
            manager->paw_frame = (manager->paw_frame + 1) % 4;  // 4-step pattern
            
            // 4-step typing pattern with effects synchronized to paw strikes
            switch (manager->paw_frame) {
                case 0:  // Left paw down
                    manager->current_sprites[LAYER_PAWS] = &leftpawdown;
                    // Show left click effect for fast typing
                    if (manager->current_state == ANIM_STATE_EXCITED) {
                        // Sparkle layer is driven separately
                    } else if (manager->current_state == ANIM_STATE_TYPING_FAST || 
                        manager->current_state == ANIM_STATE_TYPING_STREAK) {
                        manager->current_sprites[LAYER_EFFECTS] = &left_click_effect;
                    } else {
                        manager->current_sprites[LAYER_EFFECTS] = NULL;
                    }
                    break;
                    
                case 1:  // Both paws up (rest position)
                    manager->current_sprites[LAYER_PAWS] = &twopawsup;
                    if (manager->current_state != ANIM_STATE_EXCITED) {
                        manager->current_sprites[LAYER_EFFECTS] = NULL;  // No effects during rest
                    }
                    break;
                    
                case 2:  // Right paw down  
                    manager->current_sprites[LAYER_PAWS] = &rightpawdown;
                    // Show right click effect for fast typing
                    if (manager->current_state == ANIM_STATE_EXCITED) {
                        // Sparkle layer is driven separately
                    } else if (manager->current_state == ANIM_STATE_TYPING_FAST || 
                        manager->current_state == ANIM_STATE_TYPING_STREAK) {
                        manager->current_sprites[LAYER_EFFECTS] = &right_click_effect;
                    } else {
                        manager->current_sprites[LAYER_EFFECTS] = NULL;
                    }
                    break;
                    
                case 3:  // Both paws up (rest position)
                    manager->current_sprites[LAYER_PAWS] = &twopawsup;
                    if (manager->current_state != ANIM_STATE_EXCITED) {
                        manager->current_sprites[LAYER_EFFECTS] = NULL;  // No effects during rest
                    }
                    break;
            }
            manager->paw_timer = current_time;
        }
    } else {
        // When not typing, ensure paws are in the correct idle position based on state
        if (manager->current_state == ANIM_STATE_IDLE_STAGE1) {
            manager->current_sprites[LAYER_PAWS] = &twopawsup;  // Visible paws for stage 1
        } else if (manager->current_state >= ANIM_STATE_IDLE_STAGE2 && 
                   manager->current_state <= ANIM_STATE_IDLE_STAGE4) {
            manager->current_sprites[LAYER_PAWS] = NULL;  // Hidden paws for stages 2-4
        } else if (manager->current_state == ANIM_STATE_SCREENSAVER) {
            manager->current_sprites[LAYER_PAWS] = NULL;
        }
        
        // Only clear effects if NOT in IDLE_STAGE4 / screensaver (sleepy Zzz)
        if (manager->current_state != ANIM_STATE_IDLE_STAGE4 &&
            manager->current_state != ANIM_STATE_SCREENSAVER) {
            manager->current_sprites[LAYER_EFFECTS] = NULL;  // Clear typing effects
        }
    }
    
    // Handle sleepy effects animation (for IDLE_STAGE4)
    if (manager->current_state == ANIM_STATE_EXCITED) {
        if (current_time - manager->effect_timer > 180) {
            manager->effect_frame = (manager->effect_frame + 1) % 2;
            manager->current_sprites[LAYER_EFFECTS] = (manager->effect_frame == 0) ? &excited1 : &excited2;
            manager->effect_timer = current_time;
        }
    } else if (manager->current_state == ANIM_STATE_IDLE_STAGE4 ||
               manager->current_state == ANIM_STATE_SCREENSAVER) {
        uint32_t zzz_ms = (manager->current_state == ANIM_STATE_SCREENSAVER) ? 1600 : 1000;
        if (current_time - manager->effect_timer > zzz_ms) {
            manager->effect_frame = (manager->effect_frame + 1) % 3;
            switch (manager->effect_frame) {
                case 0: manager->current_sprites[LAYER_EFFECTS] = &sleepy1; break;
                case 1: manager->current_sprites[LAYER_EFFECTS] = &sleepy2; break;
                case 2: manager->current_sprites[LAYER_EFFECTS] = &sleepy3; break;
            }
            manager->effect_timer = current_time;
        }
    }
    
    // Handle automatic blinking (only when awake, not during sleep)
    // Only blink when not sleeping (stages 3 and 4 have sleepy face, no blinking)
    bool in_reaction = (manager->reaction_kind != REACT_NONE && current_time < manager->reaction_until);
    bool can_blink = (!in_reaction &&
                      manager->current_state != ANIM_STATE_IDLE_STAGE3 && 
                      manager->current_state != ANIM_STATE_IDLE_STAGE4 &&
                      manager->current_state != ANIM_STATE_EXCITED &&
                      manager->current_state != ANIM_STATE_SCREENSAVER);
    
    if (!manager->blinking && current_time >= manager->blink_timer && can_blink) {
        // Start blink
        manager->blinking = true;
        manager->blink_start_time = current_time;
        manager->current_sprites[LAYER_FACE] = &blink_face;
    } else if (manager->blinking && current_time - manager->blink_start_time > 200) {
        // End blink after 200ms
        manager->blinking = false;
        // Restore normal face after blink based on current state and streak mode
        if (manager->current_state == ANIM_STATE_IDLE_STAGE3 || 
            manager->current_state == ANIM_STATE_IDLE_STAGE4 ||
            manager->current_state == ANIM_STATE_SCREENSAVER) {
            manager->current_sprites[LAYER_FACE] = &sleepy_face;
        } else if (manager->current_state == ANIM_STATE_EXCITED) {
            manager->current_sprites[LAYER_FACE] = &excited_face;
        } else if (manager->is_streak_mode && manager->paw_animation_active) {
            manager->current_sprites[LAYER_FACE] = &happy_face;  // Happy face during any typing streak
        } else {
            manager->current_sprites[LAYER_FACE] = &stock_face;  // Default face
        }
        // Set next blink time (only if can still blink)
        if (can_blink) {
            manager->blink_timer = current_time + random(3000, 8000);
        } else {
            // When entering sleep, set longer blink timer for when waking up
            manager->blink_timer = current_time + random(5000, 10000);
        }
    }
    
    // Handle ear twitch
    if (!in_reaction && !manager->ear_twitching && current_time >= manager->ear_twitch_timer) {
        // Start ear twitch
        manager->ear_twitching = true;
        manager->ear_twitch_start_time = current_time;
        manager->current_sprites[LAYER_BODY] = &bodyeartwitch;
    } else if (manager->ear_twitching && current_time - manager->ear_twitch_start_time > 500) {
        // End ear twitch after 500ms
        manager->ear_twitching = false;
        manager->current_sprites[LAYER_BODY] = &standardbody1;
        // Set next ear twitch time
        manager->ear_twitch_timer = current_time + random(10000, 30000);
    }

    apply_reaction_overlay(manager, current_time);
}

void screensaver_enter() {
    if (cat_canvas == NULL || screensaver_active) {
        return;
    }
    screensaver_active = true;
    lv_img_set_zoom(cat_canvas, SCREENSAVER_ZOOM);
    screensaver_x = 40;
    screensaver_y = SCREENSAVER_MARGIN_TOP + 20;
    screensaver_vx = 1;
    screensaver_vy = 1;
    screensaver_last_move = millis();
    lv_obj_align(cat_canvas, LV_ALIGN_TOP_LEFT, screensaver_x, screensaver_y);
}

void screensaver_exit() {
    if (!screensaver_active) {
        return;
    }
    screensaver_active = false;
    if (cat_canvas == NULL) {
        return;
    }
    lv_img_set_zoom(cat_canvas, CAT_ZOOM);
    lv_obj_align(cat_canvas, LV_ALIGN_CENTER, CAT_OFFSET_X, CAT_OFFSET_Y);
}

void screensaver_update(uint32_t current_time) {
    if (!screensaver_active || cat_canvas == NULL) {
        return;
    }
    if (current_time - screensaver_last_move < SCREENSAVER_STEP_MS) {
        return;
    }
    screensaver_last_move = current_time;
    int size = (CAT_SIZE * SCREENSAVER_ZOOM) / 256;
    screensaver_x += screensaver_vx;
    screensaver_y += screensaver_vy;
    if (screensaver_x <= 0) {
        screensaver_x = 0;
        screensaver_vx = 1;
    }
    if (screensaver_y <= SCREENSAVER_MARGIN_TOP) {
        screensaver_y = SCREENSAVER_MARGIN_TOP;
        screensaver_vy = 1;
    }
    if (screensaver_x + size >= SCREEN_WIDTH) {
        screensaver_x = SCREEN_WIDTH - size;
        screensaver_vx = -1;
    }
    if (screensaver_y + size >= SCREEN_HEIGHT) {
        screensaver_y = SCREEN_HEIGHT - size;
        screensaver_vy = -1;
    }
    lv_obj_set_pos(cat_canvas, screensaver_x, screensaver_y);
}

void start_reaction(sprite_manager_t* manager, uint8_t kind, uint32_t current_time, uint32_t duration_ms) {
    manager->reaction_kind = kind;
    manager->reaction_until = current_time + duration_ms;
    manager->effect_timer = current_time;
    manager->effect_frame = 0;
}

void apply_mimic_tap(sprite_manager_t* manager, uint8_t paw, uint32_t current_time) {
    manager->last_typing_time = current_time;
    manager->idle_progression_enabled = false;
    manager->paw_animation_active = false;
    manager->mimic_paw = paw;
    manager->mimic_paw_until = current_time + MIMIC_PAW_HOLD_MS;
    if (paw == 2) {
        manager->current_sprites[LAYER_PAWS] = &rightpawdown;
    } else {
        manager->current_sprites[LAYER_PAWS] = &leftpawdown;
    }
    if (manager->current_state == ANIM_STATE_IDLE_STAGE2 ||
        manager->current_state == ANIM_STATE_IDLE_STAGE3 ||
        manager->current_state == ANIM_STATE_IDLE_STAGE4 ||
        manager->current_state == ANIM_STATE_EXCITED ||
        manager->current_state == ANIM_STATE_SCREENSAVER) {
        if (manager->current_state == ANIM_STATE_SCREENSAVER) {
            screensaver_exit();
        }
        manager->current_state = ANIM_STATE_IDLE_STAGE1;
        manager->state_start_time = current_time;
        manager->current_sprites[LAYER_BODY] = &standardbody1;
        manager->current_sprites[LAYER_TABLE] = &table1;
        manager->current_sprites[LAYER_EFFECTS] = NULL;
    }
    manager->current_sprites[LAYER_FACE] = manager->is_streak_mode ? &happy_face : &stock_face;
}

void apply_reaction_overlay(sprite_manager_t* manager, uint32_t current_time) {
    if (manager->reaction_kind == REACT_NONE) {
        return;
    }
    if (current_time >= manager->reaction_until) {
        manager->reaction_kind = REACT_NONE;
        manager->current_sprites[LAYER_BODY] = &standardbody1;
        if (manager->current_state == ANIM_STATE_IDLE_STAGE3 ||
            manager->current_state == ANIM_STATE_IDLE_STAGE4 ||
            manager->current_state == ANIM_STATE_SCREENSAVER) {
            manager->current_sprites[LAYER_FACE] = &sleepy_face;
        } else if (manager->current_state == ANIM_STATE_EXCITED) {
            manager->current_sprites[LAYER_FACE] = &excited_face;
        } else if (manager->is_streak_mode) {
            manager->current_sprites[LAYER_FACE] = &happy_face;
        } else {
            manager->current_sprites[LAYER_FACE] = &stock_face;
        }
        if (!manager->mimic_mode && !manager->paw_animation_active) {
            if (manager->current_state == ANIM_STATE_IDLE_STAGE1) {
                manager->current_sprites[LAYER_PAWS] = &twopawsup;
            } else if (manager->current_state >= ANIM_STATE_IDLE_STAGE2 &&
                       manager->current_state <= ANIM_STATE_IDLE_STAGE4) {
                manager->current_sprites[LAYER_PAWS] = NULL;
            }
            if (manager->current_state != ANIM_STATE_IDLE_STAGE4 &&
                manager->current_state != ANIM_STATE_EXCITED) {
                manager->current_sprites[LAYER_EFFECTS] = NULL;
            }
        }
        return;
    }
    if (manager->reaction_kind == REACT_TYPO) {
        manager->current_sprites[LAYER_FACE] = &blink_face;
        manager->current_sprites[LAYER_PAWS] = &twopawsup;
        manager->current_sprites[LAYER_EFFECTS] = NULL;
    } else if (manager->reaction_kind == REACT_SAVE) {
        manager->current_sprites[LAYER_FACE] = &happy_face;
        if (current_time - manager->effect_timer > 120) {
            manager->effect_frame = (manager->effect_frame + 1) % 2;
            manager->effect_timer = current_time;
        }
        manager->current_sprites[LAYER_EFFECTS] = (manager->effect_frame == 0) ? &excited1 : &excited2;
    } else if (manager->reaction_kind == REACT_GROOM) {
        manager->current_sprites[LAYER_BODY] = &bodyeartwitch;
        manager->current_sprites[LAYER_PAWS] = &leftpawdown;
    }
}

void sprite_manager_set_state(sprite_manager_t* manager, animation_state_t new_state, uint32_t current_time) {
    Serial.print("🔄 Animation state: ");
    Serial.print(get_state_name(manager->current_state));
    Serial.print(" → ");
    Serial.println(get_state_name(new_state));

    if (manager->current_state == ANIM_STATE_SCREENSAVER && new_state != ANIM_STATE_SCREENSAVER) {
        screensaver_exit();
    }
    
    manager->current_state = new_state;
    manager->state_start_time = current_time;
    
    // Update typing timing for timeout tracking
    if (new_state == ANIM_STATE_TYPING_SLOW || 
        new_state == ANIM_STATE_TYPING_NORMAL || 
        new_state == ANIM_STATE_TYPING_FAST) {
        manager->last_typing_time = current_time;
    }
    
    // Set appropriate sprites based on state - always ensure base layers are set
    // Base layers that should always be present
    manager->current_sprites[LAYER_BODY] = &standardbody1;
    manager->current_sprites[LAYER_TABLE] = &table1;
    
    switch (new_state) {
        case ANIM_STATE_IDLE_STAGE1:
            // Stage 1: Stock face with paws up (hands visible above table)
            manager->current_sprites[LAYER_PAWS] = &twopawsup;  // Both paws visible above table
            manager->current_sprites[LAYER_EFFECTS] = NULL;
            manager->current_sprites[LAYER_FACE] = &stock_face;
            manager->paw_animation_active = false;
            Serial.println("😐 Stage 1: Stock face, paws up");
            break;
            
        case ANIM_STATE_IDLE_STAGE2:
            // Stage 2: Stock face + hands gone (underneath table)
            manager->current_sprites[LAYER_PAWS] = NULL;  // No paws visible (hands underneath table)
            manager->current_sprites[LAYER_EFFECTS] = NULL;
            manager->current_sprites[LAYER_FACE] = &stock_face;  // Still stock face
            manager->paw_animation_active = false;
            Serial.println("😐 Stage 2: Stock face, hands hidden");
            break;
            
        case ANIM_STATE_IDLE_STAGE3:
            // Stage 3: Hands gone + sleepy face (prepare for effects)
            manager->current_sprites[LAYER_PAWS] = NULL;  // No paws visible
            manager->current_sprites[LAYER_EFFECTS] = NULL;
            manager->current_sprites[LAYER_FACE] = &sleepy_face;
            manager->paw_animation_active = false;
            Serial.println("😴 Stage 3: Deep sleep preparation, hands hidden");
            break;
            
        case ANIM_STATE_IDLE_STAGE4:
            // Stage 4: Hands gone + sleepy face + cycling sleepy effects
            manager->current_sprites[LAYER_PAWS] = NULL;  // No paws visible
            manager->current_sprites[LAYER_FACE] = &sleepy_face;
            manager->paw_animation_active = false;
            manager->effect_timer = current_time;  // Initialize effect timer for cycling
            // Effects will cycle in main update loop
            Serial.println("😴 Stage 4: Deep sleep with cycling effects, hands hidden");
            break;
            
        case ANIM_STATE_TYPING_SLOW:
            // Slow typing: 4-step paw pattern, no effects
            manager->current_sprites[LAYER_FACE] = manager->is_streak_mode ? &happy_face : &stock_face;
            manager->current_sprites[LAYER_EFFECTS] = NULL;
            manager->current_sprites[LAYER_PAWS] = &leftpawdown;  // Start with left paw (frame 0)
            manager->paw_animation_active = true;
            manager->paw_frame = 0;  // Reset paw frame to prevent stuck paws
            manager->paw_timer = current_time;
            Serial.println(manager->is_streak_mode ? "👐😊 Slow typing with happy face" : "👐 Slow typing");
            break;
            
        case ANIM_STATE_TYPING_NORMAL:
            // Normal typing: 4-step paw pattern, no effects
            manager->current_sprites[LAYER_FACE] = manager->is_streak_mode ? &happy_face : &stock_face;
            manager->current_sprites[LAYER_EFFECTS] = NULL;
            manager->current_sprites[LAYER_PAWS] = &leftpawdown;  // Start with left paw (frame 0)
            manager->paw_animation_active = true;
            manager->paw_frame = 0;  // Reset paw frame to prevent stuck paws
            manager->paw_timer = current_time;
            Serial.println(manager->is_streak_mode ? "👐😊 Normal typing with happy face" : "👐 Normal typing");
            break;
            
        case ANIM_STATE_TYPING_FAST:
            // Fast typing: 4-step paw pattern + click effects
            manager->current_sprites[LAYER_FACE] = manager->is_streak_mode ? &happy_face : &stock_face;
            manager->current_sprites[LAYER_PAWS] = &leftpawdown;  // Start with left paw (frame 0)
            manager->paw_animation_active = true;
            manager->paw_frame = 0;  // Reset paw frame to prevent stuck paws
            manager->paw_timer = current_time;
            Serial.println(manager->is_streak_mode ? "👐⚡😊 Fast typing with happy face and effects" : "👐⚡ Fast typing with click effects");
            break;
            
        case ANIM_STATE_TYPING_STREAK:
            // Legacy streak state - treat as fast typing with happy face
            manager->current_sprites[LAYER_FACE] = &happy_face;
            manager->current_sprites[LAYER_PAWS] = &leftpawdown;  // Start with left paw (frame 0)
            manager->paw_animation_active = true;
            manager->paw_frame = 0;  // Reset paw frame to prevent stuck paws
            manager->paw_timer = current_time;
            Serial.println("👐⚡😊 Legacy streak mode - fast typing with happy face");
            break;

        case ANIM_STATE_EXCITED:
            manager->current_sprites[LAYER_FACE] = &excited_face;
            manager->current_sprites[LAYER_PAWS] = &leftpawdown;
            manager->current_sprites[LAYER_EFFECTS] = &excited1;
            manager->paw_animation_active = true;
            manager->paw_frame = 0;
            manager->paw_timer = current_time;
            manager->effect_timer = current_time;
            manager->effect_frame = 0;
            manager->animation_speed_ms = 40;
            manager->idle_progression_enabled = false;
            Serial.println("Extreme excitement — 10 min idle");
            break;

        case ANIM_STATE_SCREENSAVER:
            manager->current_sprites[LAYER_FACE] = &sleepy_face;
            manager->current_sprites[LAYER_PAWS] = NULL;
            manager->current_sprites[LAYER_EFFECTS] = &sleepy1;
            manager->paw_animation_active = false;
            manager->effect_timer = current_time;
            manager->effect_frame = 0;
            manager->idle_progression_enabled = false;
            screensaver_enter();
            Serial.println("Screensaver — drifting asleep cat");
            break;
    }
    
    // Reset idle progression when entering any typing state
    if (new_state == ANIM_STATE_TYPING_SLOW || 
        new_state == ANIM_STATE_TYPING_NORMAL || 
        new_state == ANIM_STATE_TYPING_FAST) {
        manager->idle_progression_enabled = false;  // Stop auto idle progression
        Serial.println("🚫 Auto idle progression disabled");
    }
}

void sprite_render_layers(sprite_manager_t* manager, lv_obj_t* canvas, uint32_t current_time) {
    // Clear canvas with minimal operations
    lv_canvas_fill_bg(canvas, lv_color_white(), LV_OPA_TRANSP);
    
    // Render layers in order (back to front) with optimized drawing
    lv_draw_img_dsc_t img_dsc;
    lv_draw_img_dsc_init(&img_dsc);  // Initialize once outside loop
    
    for (int layer = 0; layer < NUM_LAYERS; layer++) {
        const lv_img_dsc_t* sprite = manager->current_sprites[layer];
        if (sprite) {
            // Draw sprite at origin (0,0) - canvas will be zoomed to 4x size
            // Using single draw call per sprite to minimize operations
            lv_canvas_draw_img(canvas, 0, 0, sprite, &img_dsc);
        }
    }
}

// Helper function to get state name for debugging
const char* get_state_name(animation_state_t state) {
    switch (state) {
        case ANIM_STATE_IDLE_STAGE1: return "IDLE_STAGE1";
        case ANIM_STATE_IDLE_STAGE2: return "IDLE_STAGE2"; 
        case ANIM_STATE_IDLE_STAGE3: return "IDLE_STAGE3";
        case ANIM_STATE_IDLE_STAGE4: return "IDLE_STAGE4";
        case ANIM_STATE_TYPING_SLOW: return "TYPING_SLOW";
        case ANIM_STATE_TYPING_NORMAL: return "TYPING_NORMAL";
        case ANIM_STATE_TYPING_FAST: return "TYPING_FAST";
        case ANIM_STATE_TYPING_STREAK: return "TYPING_STREAK";  // Keep for compatibility but unused
        case ANIM_STATE_EXCITED: return "EXCITED";
        case ANIM_STATE_SCREENSAVER: return "SCREENSAVER";
        default: return "UNKNOWN";
    }
}

void setup() {
    Serial.begin(115200);
    Serial.println("🐱 Bongo Cat with Sprites Starting...");
    
    // Initialize EEPROM for settings persistence
    EEPROM.begin(EEPROM_SIZE);
    
    // Load settings from EEPROM (will use defaults if invalid)
    loadSettings();
    
    // Initialize random seed for animations
    randomSeed(analogRead(0));
    
    tft.init();
    tft.setRotation(0);
    tft.fillScreen(tft.color565(SCREEN_BG_R, SCREEN_BG_G, SCREEN_BG_B));
    
    lv_init();
    
    lv_disp_draw_buf_init(&draw_buf, buf, NULL, SCREEN_WIDTH * 10);
    
    static lv_disp_drv_t disp_drv;
    lv_disp_drv_init(&disp_drv);
    disp_drv.hor_res = SCREEN_WIDTH;
    disp_drv.ver_res = SCREEN_HEIGHT;
    disp_drv.flush_cb = my_disp_flush;
    disp_drv.draw_buf = &draw_buf;
    lv_disp_drv_register(&disp_drv);
    
    // Initialize sprite manager
    sprite_manager_init(&sprite_manager);
    
    createBongoCat();
    
    // Apply loaded settings to display visibility now that UI is created
    updateDisplayVisibility();
    
    Serial.println("✅ Bongo Cat Ready!");
}

void createBongoCat() {
    screen = lv_scr_act();
    
    // Set white background
    lv_obj_set_style_bg_color(screen, lv_color_make(SCREEN_BG_R, SCREEN_BG_G, SCREEN_BG_B), 0);
    
    // Create cat canvas with proper sizing
    cat_canvas = lv_canvas_create(screen);
    
    // Use 64x64 base sprite size for the canvas buffer
    static lv_color_t canvas_buf[CAT_SIZE * CAT_SIZE];  // 64x64 buffer
    lv_canvas_set_buffer(cat_canvas, canvas_buf, CAT_SIZE, CAT_SIZE, LV_IMG_CF_TRUE_COLOR);
    
    // Zoom is 256 = 1x. Default CAT_ZOOM 1024 = 4x (64x64 -> 256x256).
    lv_img_set_zoom(cat_canvas, CAT_ZOOM);
    lv_img_set_antialias(cat_canvas, false);  // Keep pixels crisp and blocky
    
    // Position cat relative to screen center. Edited by sprite studio.
    lv_obj_align(cat_canvas, LV_ALIGN_CENTER, CAT_OFFSET_X, CAT_OFFSET_Y);
    
    // Create system stats labels (top left) with pixelated font
    cpu_label = lv_label_create(screen);
    lv_label_set_text(cpu_label, "CPU: 0%");
    lv_obj_set_style_text_font(cpu_label, &lv_font_unscii_16, 0);
    lv_obj_set_style_text_color(cpu_label, lv_color_black(), 0);
    lv_obj_align(cpu_label, LV_ALIGN_TOP_LEFT, STAT_CPU_X, STAT_CPU_Y);
    
    ram_label = lv_label_create(screen);
    lv_label_set_text(ram_label, "RAM: 0%");
    lv_obj_set_style_text_font(ram_label, &lv_font_unscii_16, 0);
    lv_obj_set_style_text_color(ram_label, lv_color_black(), 0);
    lv_obj_align(ram_label, LV_ALIGN_TOP_LEFT, STAT_RAM_X, STAT_RAM_Y);
    
    wpm_label = lv_label_create(screen);
    lv_label_set_text(wpm_label, "WPM: 0");
    lv_obj_set_style_text_font(wpm_label, &lv_font_unscii_16, 0);
    lv_obj_set_style_text_color(wpm_label, lv_color_black(), 0);
    lv_obj_align(wpm_label, LV_ALIGN_TOP_LEFT, STAT_WPM_X, STAT_WPM_Y);
    
    // Create time label (top right) - bigger pixelated font
    time_label = lv_label_create(screen);
    lv_label_set_text(time_label, "00:00");
    lv_obj_set_style_text_font(time_label, &lv_font_unscii_16, 0);
    lv_obj_set_style_text_color(time_label, lv_color_black(), 0);
    lv_obj_align(time_label, LV_ALIGN_TOP_RIGHT, STAT_TIME_X, STAT_TIME_Y);

    keys_label = lv_label_create(screen);
    lv_label_set_text(keys_label, "KEYS:0");
    lv_obj_set_style_text_font(keys_label, &lv_font_unscii_16, 0);
    lv_obj_set_style_text_color(keys_label, lv_color_black(), 0);
    lv_obj_align(keys_label, LV_ALIGN_TOP_RIGHT, STAT_KEYS_X, STAT_KEYS_Y);
    
    // Initial render
    sprite_render_layers(&sprite_manager, cat_canvas, millis());
}

void loop() {
    handleSerialCommands();
    
    uint32_t current_time = millis();
    
    // Update animations - removed fixed frame rate to prevent conflicts
    static uint32_t last_animation_update = 0;
    if (current_time - last_animation_update >= 25) {  // 40 FPS max (more responsive)
        sprite_manager_update(&sprite_manager, current_time);
        
        // Only render if sprites actually changed to reduce canvas operations
        static uint32_t last_sprite_hash = 0;
        uint32_t current_sprite_hash = 0;
        
        // Calculate simple hash of current sprites to detect changes (optimized)
        for (int i = 0; i < NUM_LAYERS; i++) {
            current_sprite_hash += (uint32_t)sprite_manager.current_sprites[i];
        }
        
        // Only re-render if sprites changed or it's been too long (forced refresh)
        if (current_sprite_hash != last_sprite_hash || (current_time - last_animation_update) > 200) {
            sprite_render_layers(&sprite_manager, cat_canvas, current_time);
            last_sprite_hash = current_sprite_hash;
        }
        
        last_animation_update = current_time;
    }

    screensaver_update(current_time);
    
    // Update time display every second
    static uint32_t last_time_update = 0;
    if (current_time - last_time_update >= 1000) {
        updateTimeDisplay();
        last_time_update = current_time;
    }
    
    // Reduce LVGL timer handler frequency to prevent system overload
    static uint32_t last_lvgl_update = 0;
    if (current_time - last_lvgl_update >= 20) {  // 50 FPS max for LVGL (was every 5ms)
        lv_timer_handler();
        last_lvgl_update = current_time;
    }
    
    delay(2);  // Reduced from 5ms for better responsiveness
} 