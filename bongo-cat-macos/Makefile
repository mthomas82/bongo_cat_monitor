# Bongo Cat Native macOS App - Build System
#
# Usage:
#   make          - Build everything (Rust daemon + Swift app + bundle)
#   make clean    - Clean all build artifacts
#   make run      - Build and run the app
#
# Code Signing (set these for proper signing):
#   SIGNING_IDENTITY - Your certificate name (e.g., "Developer ID Application: Your Name (TEAMID)")
#   TEAM_ID          - Your Apple Developer Team ID (e.g., "ABCD123456")
#
# Example:
#   make SIGNING_IDENTITY="Developer ID Application: John Doe (ABC123)" TEAM_ID="ABC123"

RUST_SRC = bongocat-daemon
SWIFT_SRC = BongoCatApp
BUILD_DIR = build
RUST_BINARY = $(RUST_SRC)/target/release/bongocat-daemon
SWIFT_APP = $(BUILD_DIR)/BongoCat.app
SWIFT_BINARY = $(SWIFT_APP)/Contents/MacOS/BongoCat
BUNDLE_RESOURCES = $(SWIFT_APP)/Contents/Resources
ENTITLEMENTS = BongoCat.entitlements

# Code signing identity (use "-" for ad-hoc, or your certificate name for proper signing)
SIGNING_IDENTITY ?= -
TEAM_ID ?=
# Native arch so Intel Macs are not forced onto arm64
ARCH := $(shell uname -m)
SWIFT_TARGET ?= $(ARCH)-apple-macosx12.0

SWIFT_FILES = $(wildcard $(SWIFT_SRC)/BongoCat/*.swift)

.PHONY: all clean build-rust build-swift bundle codesign run

# Default target: build everything
all: bundle codesign
	@echo "Build complete: $(SWIFT_APP)"

# Build Rust daemon
build-rust:
	@echo "Building Rust daemon..."
	cd $(RUST_SRC) && cargo build --release

# Build Swift app using swiftc directly
build-swift: $(SWIFT_BINARY)

$(SWIFT_BINARY): $(SWIFT_FILES)
	@echo "Building Swift app..."
	@mkdir -p $(SWIFT_APP)/Contents/MacOS
	@mkdir -p $(SWIFT_APP)/Contents/Resources
	swiftc -O \
		-sdk $(shell xcrun --show-sdk-path) \
		-target $(SWIFT_TARGET) \
		-framework AppKit \
		-framework SwiftUI \
		-framework ApplicationServices \
		$(SWIFT_FILES) \
		-o $(SWIFT_BINARY)
	@cp $(SWIFT_SRC)/BongoCat/Info.plist $(SWIFT_APP)/Contents/

# Bundle: copy Rust binary and assets into app bundle
bundle: build-rust build-swift
	@echo "Creating app bundle..."
	@mkdir -p "$(BUNDLE_RESOURCES)"
	cp "$(RUST_BINARY)" "$(BUNDLE_RESOURCES)/bongocat-daemon"
	chmod +x "$(BUNDLE_RESOURCES)/bongocat-daemon"
	@echo "Copying icons..."
	cp "$(SWIFT_SRC)/BongoCat/Assets.xcassets/MenuBarIcon.imageset/tray.png" "$(BUNDLE_RESOURCES)/tray.png"
	cp "$(SWIFT_SRC)/BongoCat/AppIcon.icns" "$(BUNDLE_RESOURCES)/AppIcon.icns"

# Code sign the app
codesign:
	@echo "Code signing..."
ifeq ($(SIGNING_IDENTITY),-)
	@echo "  Using ad-hoc signing (for local development only)"
	codesign --force --deep --sign - "$(SWIFT_APP)"
else
	@echo "  Signing with: $(SIGNING_IDENTITY)"
	# Sign embedded daemon first (inside-out signing)
	codesign --force --options runtime --timestamp \
		--entitlements "$(ENTITLEMENTS)" \
		--sign "$(SIGNING_IDENTITY)" \
		"$(BUNDLE_RESOURCES)/bongocat-daemon"
	# Sign the main app bundle
	codesign --force --options runtime --timestamp \
		--entitlements "$(ENTITLEMENTS)" \
		--sign "$(SIGNING_IDENTITY)" \
		"$(SWIFT_APP)"
	@echo "Verifying signature..."
	codesign --verify --deep --strict --verbose=2 "$(SWIFT_APP)"
endif

# Clean all build artifacts
clean:
	@echo "Cleaning..."
	cd $(RUST_SRC) && cargo clean
	rm -rf $(BUILD_DIR)

# Build and run
run: all
	@echo "Launching Bongo Cat..."
	open "$(SWIFT_APP)"

# Run Rust tests
test-rust:
	cd $(RUST_SRC) && cargo test

# Check Rust code
check:
	cd $(RUST_SRC) && cargo check

# Format Rust code
fmt:
	cd $(RUST_SRC) && cargo fmt

# Create a signed DMG for distribution
DMG_ICON = $(SWIFT_SRC)/BongoCat/AppIcon.icns
dmg: all
	@echo "Creating DMG..."
	@mkdir -p "$(BUILD_DIR)/dmg"
	@cp -r "$(SWIFT_APP)" "$(BUILD_DIR)/dmg/"
	@ln -sf /Applications "$(BUILD_DIR)/dmg/Applications"
	@# Check for background image
	@if [ -f "dmg-background.png" ]; then \
		mkdir -p "$(BUILD_DIR)/dmg/.background"; \
		cp "dmg-background.png" "$(BUILD_DIR)/dmg/.background/background.png"; \
	fi
	@# Create temporary read-write DMG
	hdiutil create -volname "BongoCat" -srcfolder "$(BUILD_DIR)/dmg" \
		-ov -format UDRW "$(BUILD_DIR)/BongoCat-temp.dmg"
	@rm -rf "$(BUILD_DIR)/dmg"
	@# Mount and configure window
	@echo "Setting DMG layout..."
	@hdiutil detach /Volumes/BongoCat 2>/dev/null || true
	hdiutil attach "$(BUILD_DIR)/BongoCat-temp.dmg"
	@# Configure Finder window appearance
	@if [ -f "dmg-background.png" ]; then \
		mkdir -p "/Volumes/BongoCat/.background"; \
		cp "dmg-background.png" "/Volumes/BongoCat/.background/background.png"; \
		osascript -e 'tell application "Finder"' \
			-e 'tell disk "BongoCat"' \
			-e 'open' \
			-e 'set current view of container window to icon view' \
			-e 'set toolbar visible of container window to false' \
			-e 'set statusbar visible of container window to false' \
			-e 'set bounds of container window to {100, 100, 640, 440}' \
			-e 'set theViewOptions to icon view options of container window' \
			-e 'set arrangement of theViewOptions to not arranged' \
			-e 'set icon size of theViewOptions to 80' \
			-e 'set background picture of theViewOptions to file ".background:background.png"' \
			-e 'set position of item "BongoCat.app" of container window to {135, 170}' \
			-e 'set position of item "Applications" of container window to {405, 170}' \
			-e 'close' \
			-e 'open' \
			-e 'update without registering applications' \
			-e 'delay 3' \
			-e 'close' \
			-e 'end tell' \
			-e 'end tell'; \
	fi
	@# Set volume icon (after Finder operations)
	@echo "Setting volume icon..."
	cp "$(DMG_ICON)" "/Volumes/BongoCat/.VolumeIcon.icns"
	SetFile -c icnC "/Volumes/BongoCat/.VolumeIcon.icns"
	SetFile -a C "/Volumes/BongoCat"
	@sync && sleep 1
	hdiutil detach /Volumes/BongoCat
	@# Convert to compressed read-only DMG
	hdiutil convert "$(BUILD_DIR)/BongoCat-temp.dmg" -format UDZO -o "$(BUILD_DIR)/BongoCat.dmg" -ov
	@rm "$(BUILD_DIR)/BongoCat-temp.dmg"
ifneq ($(SIGNING_IDENTITY),-)
	codesign --force --sign "$(SIGNING_IDENTITY)" "$(BUILD_DIR)/BongoCat.dmg"
endif
	@echo "DMG created: $(BUILD_DIR)/BongoCat.dmg"

# Notarize the app (requires Apple ID credentials in keychain)
# Usage: make notarize APPLE_ID="your@email.com" KEYCHAIN_PROFILE="notary-profile"
APPLE_ID ?=
KEYCHAIN_PROFILE ?=
notarize: dmg
ifeq ($(SIGNING_IDENTITY),-)
	$(error Cannot notarize with ad-hoc signing. Set SIGNING_IDENTITY to your Developer ID certificate)
endif
ifeq ($(KEYCHAIN_PROFILE),)
	$(error Set KEYCHAIN_PROFILE to your notarytool keychain profile name)
endif
	@echo "Submitting for notarization..."
	xcrun notarytool submit "$(BUILD_DIR)/BongoCat.dmg" \
		--keychain-profile "$(KEYCHAIN_PROFILE)" \
		--wait
	@echo "Stapling notarization ticket..."
	xcrun stapler staple "$(BUILD_DIR)/BongoCat.dmg"
	@echo "Notarization complete!"

# List available signing identities
list-identities:
	@echo "Available signing identities:"
	@security find-identity -v -p codesigning

# Verify code signing and notarization
verify:
	@echo "=== App Signature ==="
	@codesign --verify --deep --strict --verbose=2 "$(SWIFT_APP)" && echo "✓ Signature valid" || echo "✗ Signature invalid"
	@echo ""
	@echo "=== Notarization Status ==="
	@spctl --assess --type execute --verbose=2 "$(SWIFT_APP)" 2>&1 || true
	@echo ""
	@echo "=== DMG Status ==="
	@if [ -f "$(BUILD_DIR)/BongoCat.dmg" ]; then \
		spctl --assess --type open --context context:primary-signature --verbose=2 "$(BUILD_DIR)/BongoCat.dmg" 2>&1 || true; \
	else \
		echo "DMG not found. Run 'make dmg' first."; \
	fi
	@echo ""
	@echo "(Note: 'Unnotarized Developer ID' means signed but not yet notarized)"
