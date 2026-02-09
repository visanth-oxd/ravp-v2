#!/usr/bin/env bash
#
# Download and install Docker Desktop for macOS.
# Usage: ./scripts/install_docker_mac.sh
# Or:    bash scripts/install_docker_mac.sh
#

set -e

echo "=========================================="
echo "  Docker Desktop for Mac - Installer"
echo "=========================================="

# Check we're on macOS
if [[ "$(uname)" != "Darwin" ]]; then
  echo "Error: This script is for macOS only."
  exit 1
fi

# Detect architecture
ARCH=$(uname -m)
if [[ "$ARCH" == "arm64" ]]; then
  echo "Detected: Apple Silicon (M1/M2/M3)"
  DOCKER_URL="https://desktop.docker.com/mac/main/arm64/Docker.dmg"
elif [[ "$ARCH" == "x86_64" ]]; then
  echo "Detected: Intel"
  DOCKER_URL="https://desktop.docker.com/mac/main/amd64/Docker.dmg"
else
  echo "Error: Unsupported architecture: $ARCH"
  exit 1
fi

# Download directory
DOWNLOAD_DIR="${HOME}/Downloads"
DMG_PATH="${DOWNLOAD_DIR}/Docker.dmg"
APP_PATH="/Applications/Docker.app"

# Check if Docker is already installed and running
if [[ -d "$APP_PATH" ]]; then
  if docker info &>/dev/null; then
    echo "Docker Desktop is already installed and running."
    docker --version
    exit 0
  fi
  echo "Docker Desktop is installed but not running."
  echo "Opening Docker Desktop..."
  open "$APP_PATH"
  echo "Wait for Docker to start (whale icon in menu bar), then run: docker run hello-world"
  exit 0
fi

echo ""
echo "Step 1/4: Downloading Docker Desktop..."
echo "  URL: $DOCKER_URL"
echo "  To:  $DMG_PATH"
echo ""

if command -v curl &>/dev/null; then
  curl -L -o "$DMG_PATH" "$DOCKER_URL"
elif command -v wget &>/dev/null; then
  wget -O "$DMG_PATH" "$DOCKER_URL"
else
  echo "Error: Need curl or wget to download. Install one of them and try again."
  exit 1
fi

if [[ ! -f "$DMG_PATH" ]]; then
  echo "Error: Download failed."
  exit 1
fi

echo "  Download complete."
echo ""

echo "Step 2/4: Mounting DMG..."
MOUNT_POINT=$(hdiutil attach -nobrowse -quiet "$DMG_PATH" | tail -1 | awk '{print $3}')
if [[ -z "$MOUNT_POINT" ]]; then
  echo "Error: Failed to mount DMG."
  exit 1
fi

echo "  Mounted at: $MOUNT_POINT"
echo ""

echo "Step 3/4: Installing Docker to Applications..."
# Copy Docker.app to /Applications (may prompt for password)
if [[ -d "${MOUNT_POINT}/Docker.app" ]]; then
  cp -R "${MOUNT_POINT}/Docker.app" /Applications/
else
  echo "Error: Docker.app not found in DMG."
  hdiutil detach "$MOUNT_POINT" 2>/dev/null || true
  exit 1
fi

echo "  Unmounting DMG..."
hdiutil detach "$MOUNT_POINT" -quiet 2>/dev/null || true

echo "  Removing downloaded DMG..."
rm -f "$DMG_PATH"

echo "  Done."
echo ""

echo "Step 4/4: Starting Docker Desktop..."
open "/Applications/Docker.app"

echo ""
echo "=========================================="
echo "  Installation complete"
echo "=========================================="
echo ""
echo "Docker Desktop has been installed and launched."
echo ""
echo "Next steps:"
echo "  1. Wait for Docker to finish starting (whale icon in menu bar)."
echo "  2. Accept the Docker subscription agreement if prompted."
echo "  3. Verify:  docker run hello-world"
echo ""
echo "Then you can use Build & Push in RAVP v2 (REgulated Agent Vending Platform)."
echo ""
