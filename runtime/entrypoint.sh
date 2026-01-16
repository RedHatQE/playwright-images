#!/bin/bash
# ==============================================================================
# Entrypoint script for Playwright VNC Container
# Manages VNC server and Playwright server processes
# ==============================================================================

set -e

log_info() {
    echo "[INFO] $1"
}

log_warn() {
    echo "[WARN] $1"
}

log_error() {
    echo "[ERROR] $1"
}

# Cleanup function for graceful shutdown
cleanup() {
    log_info "Received shutdown signal, cleaning up..."
    
    # Kill child processes
    if [ ! -z "$PLAYWRIGHT_PID" ] && kill -0 $PLAYWRIGHT_PID 2>/dev/null; then
        log_info "Stopping Playwright server (PID: $PLAYWRIGHT_PID)..."
        kill -TERM $PLAYWRIGHT_PID 2>/dev/null || true
    fi
    
    if [ ! -z "$VNC_PID" ] && kill -0 $VNC_PID 2>/dev/null; then
        log_info "Stopping VNC server (PID: $VNC_PID)..."
        kill -TERM $VNC_PID 2>/dev/null || true
    fi
    
    # Wait for processes to terminate gracefully
    wait $PLAYWRIGHT_PID 2>/dev/null || true
    wait $VNC_PID 2>/dev/null || true
    
    log_info "Cleanup complete. Exiting."
    exit 0
}

# Set up signal handlers
trap cleanup SIGTERM SIGINT SIGQUIT

log_info "Starting Playwright VNC Container..."
log_info "Display: ${DISPLAY}"
log_info "VNC Port: ${VNC_PORT}"
log_info "Playwright Port: ${PW_PORT}"
log_info "Browser: ${PW_BROWSER}"
log_info "Headless Mode: ${PW_HEADLESS}"

# Start VNC server
log_info "Starting VNC server on ${DISPLAY}..."
Xvnc ${DISPLAY} \
    -geometry 1280x1024 \
    -depth 24 \
    -rfbport ${VNC_PORT} \
    -SecurityTypes None \
    -AlwaysShared \
    -verbose \
    -Log *:stdout:100 \
    -fp catalogue:/etc/X11/fontpath.d,/usr/share/fonts/X11/misc/,/usr/share/fonts/X11/Type1/ \
    -pn &

VNC_PID=$!

# Check if VNC started successfully
sleep 2
if ! kill -0 $VNC_PID 2>/dev/null; then
    log_error "VNC server failed to start!"
    exit 1
fi

log_info "VNC server started successfully (PID: $VNC_PID)"
log_info "Note: Running without window manager (browsers work fine)"

# Start Playwright server
log_info "Starting Playwright server..."
DISPLAY=${DISPLAY} node ${APP_HOME}/start-playwright-server.js &
PLAYWRIGHT_PID=$!

# Check if Playwright started successfully
sleep 2
if ! kill -0 $PLAYWRIGHT_PID 2>/dev/null; then
    log_error "Playwright server failed to start!"
    log_info "Stopping VNC server..."
    kill -TERM $VNC_PID 2>/dev/null || true
    exit 1
fi

log_info "Playwright server started successfully (PID: $PLAYWRIGHT_PID)"
log_info "All services running. Container ready!"
log_info "Connect to VNC: localhost:${VNC_PORT}"
log_info "Playwright endpoint: ws://localhost:${PW_PORT}/playwright"

# Monitor processes
while true; do
    # Check if VNC is still running
    if ! kill -0 $VNC_PID 2>/dev/null; then
        log_error "VNC server died unexpectedly!"
        kill -TERM $PLAYWRIGHT_PID 2>/dev/null || true
        exit 1
    fi
    
    # Check if Playwright is still running
    if ! kill -0 $PLAYWRIGHT_PID 2>/dev/null; then
        log_error "Playwright server died unexpectedly!"
        kill -TERM $VNC_PID 2>/dev/null || true
        exit 1
    fi
    
    sleep 5
done
