#!/bin/bash

set -e

# Enhanced build script with multi-base support
DEFAULT_BASE="${DEFAULT_BASE:-bookworm}"
IMAGE_REPO="${IMAGE_REPO:-digitronik/playwright-vnc}"
CONTAINER_ENGINE="${CONTAINER_ENGINE:-podman}"

# Version handling
PLAYWRIGHT_VERSION=""
USE_LATEST_TAG=false
BASE_IMAGE=""

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --playwright-version)
            PLAYWRIGHT_VERSION="$2"
            shift 2
            ;;
        --latest)
            USE_LATEST_TAG=true
            shift
            ;;
        --repo)
            IMAGE_REPO="$2"
            shift 2
            ;;
        --base)
            BASE_IMAGE="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [options] [browser-targets...]"
            echo ""
            echo "Options:"
            echo "  --playwright-version VERSION  Use specific Playwright version"
            echo "  --latest                      Also tag as latest"
            echo "  --repo REPO                   Image repository (default: digitronik/playwright-vnc)"
            echo "  --base BASE                   Base image: bookworm or ubi9 (default: bookworm)"
            echo "  --help                        Show this help"
            echo ""
            echo "Environment Variables:"
            echo "  CONTAINER_ENGINE              podman or docker (default: podman)"
            echo ""
            echo "Browser targets: firefox, chromium, chrome, all (default: all if none specified)"
            echo ""
            echo "Examples:"
            echo "  $0                                    # Build all browsers for bookworm"
            echo "  $0 firefox chrome                     # Build Firefox and Chrome for bookworm"
            echo "  $0 --base ubi9 firefox                # Build Firefox for UBI9"
            echo "  $0 --playwright-version 1.57.0 all    # Build all with specific version"
            echo "  $0 --latest firefox                   # Build Firefox and tag as latest"
            echo "  CONTAINER_ENGINE=docker $0 all        # Use Docker instead of Podman"
            exit 0
            ;;
        -*)
            echo "Unknown option: $1"
            exit 1
            ;;
        *)
            break
            ;;
    esac
done

# Set base image
if [ -z "$BASE_IMAGE" ]; then
    BASE_IMAGE="$DEFAULT_BASE"
fi

# Validate base
if [[ ! "$BASE_IMAGE" =~ ^(bookworm|ubi9)$ ]]; then
    echo "Error: Invalid base '$BASE_IMAGE'. Must be 'bookworm' or 'ubi9'"
    exit 1
fi

# Set Dockerfile
DOCKERFILE="docker/Dockerfile.${BASE_IMAGE}"

if [ ! -f "$DOCKERFILE" ]; then
    echo "Error: Dockerfile not found: $DOCKERFILE"
    exit 1
fi

# Auto-detect Playwright version if not specified
if [ -z "$PLAYWRIGHT_VERSION" ]; then
    echo "Auto-detecting latest Playwright version..."
    if [ -f "scripts/get-playwright-version.sh" ]; then
        PLAYWRIGHT_VERSION=$(scripts/get-playwright-version.sh latest)
        echo "Detected Playwright version: $PLAYWRIGHT_VERSION"
    else
        echo "Warning: Version detection script not found, using default"
        PLAYWRIGHT_VERSION="1.57.0"
    fi
fi

# Normalize version (remove 'v' prefix for consistency)
PLAYWRIGHT_VERSION=$(echo "$PLAYWRIGHT_VERSION" | sed 's/^v//')

# Define all build targets
declare -A targets
targets["firefox"]="firefox"
targets["chromium"]="chromium"
targets["chrome"]="chrome"
targets["all"]="all"

# Build metadata
BUILD_DATE=$(date -u +%Y-%m-%dT%H:%M:%SZ)
VERSION="pw-${PLAYWRIGHT_VERSION}"

echo "Starting image build process..."
echo "Build Configuration:"
echo "   Base Image:         ${BASE_IMAGE}"
echo "   Playwright Version: ${PLAYWRIGHT_VERSION}"
echo "   Repository:         ${IMAGE_REPO}"
echo "   Container Engine:   ${CONTAINER_ENGINE}"
echo "   Build Date:         ${BUILD_DATE}"
echo "   Version Tag:        ${VERSION}"

# Determine which targets to build
targets_to_build=("$@")
if [ ${#targets_to_build[@]} -eq 0 ]; then
    # If no targets specified, build all in specific order
    targets_to_build=("firefox" "chromium" "chrome" "all")
    echo "No specific targets provided. Building all variants: ${targets_to_build[*]}"
fi

# Function to build and tag images
build_and_tag() {
    local target="$1"
    local tag_suffix="$2"
    
    echo ""
    echo "============================================================"
    echo "Building target: '$target' for base: '${BASE_IMAGE}'"
    echo "============================================================"
    
    # Tagging strategy with base prefix
    # Primary tag: <base>-<browser>-<version> or <base>-<version> for 'all'
    local version_tag
    local latest_tag
    
    if [ "$target" = "all" ]; then
        version_tag="${IMAGE_REPO}:${BASE_IMAGE}-${PLAYWRIGHT_VERSION}"
        latest_tag="${IMAGE_REPO}:${BASE_IMAGE}-latest"
    else
        version_tag="${IMAGE_REPO}:${BASE_IMAGE}-${tag_suffix}-${PLAYWRIGHT_VERSION}"
        latest_tag="${IMAGE_REPO}:${BASE_IMAGE}-${tag_suffix}-latest"
    fi
    
    echo "Tags to create:"
    echo "   ${version_tag}"
    echo "   ${latest_tag}"
    
    # Build the image
    ${CONTAINER_ENGINE} build \
        --file ${DOCKERFILE} \
        --target ${target} \
        --build-arg PLAYWRIGHT_VERSION="${PLAYWRIGHT_VERSION}" \
        --build-arg BUILD_DATE="${BUILD_DATE}" \
        --build-arg VERSION="${VERSION}" \
        --tag "${version_tag}" \
        --tag "${latest_tag}" \
        .
    
    local build_status=$?
    
    if [ $build_status -eq 0 ]; then
        echo "Successfully built ${version_tag}"
        echo "Successfully tagged ${latest_tag}"
        
        # If --latest flag is used and this is bookworm (default base)
        # create additional simple tags for backward compatibility
        if [ "$USE_LATEST_TAG" = true ] && [ "$BASE_IMAGE" = "bookworm" ]; then
            if [ "$target" = "all" ]; then
                local simple_tag="${IMAGE_REPO}:latest"
                ${CONTAINER_ENGINE} tag "${version_tag}" "${simple_tag}"
                echo "Additionally tagged as: ${simple_tag}"
            else
                local simple_tag="${IMAGE_REPO}:${tag_suffix}-latest"
                ${CONTAINER_ENGINE} tag "${version_tag}" "${simple_tag}"
                echo "Additionally tagged as: ${simple_tag}"
            fi
        fi
        
        return 0
    else
        echo "Build failed for target: $target"
        return 1
    fi
}

# Loop through targets and build
echo ""
echo "Starting build process for ${#targets_to_build[@]} target(s)..."

SUCCESS_COUNT=0
FAILED_COUNT=0

for target in "${targets_to_build[@]}"; do
    # Validate target exists
    tag_suffix="${targets[$target]}"
    if [ -z "$tag_suffix" ]; then
        echo "Warning: Unknown build target '$target'. Skipping."
        continue
    fi
    
    echo ""
    echo "Building target: ${BASE_IMAGE}/${target}..."
    
    # Call build function
    if build_and_tag "$target" "$tag_suffix"; then
        SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
        echo "✓ Success: ${target}"
    else
        FAILED_COUNT=$((FAILED_COUNT + 1))
        echo "✗ Failed: ${target}"
    fi
done

echo ""
echo "============================================================"
echo "Build Summary"
echo "============================================================"
echo "Base Image:      ${BASE_IMAGE}"
echo "Playwright:      ${PLAYWRIGHT_VERSION}"
echo "Total Targets:   ${#targets_to_build[@]}"
echo "Successful:      ${SUCCESS_COUNT}"
echo "Failed:          ${FAILED_COUNT}"
echo ""

if [ $FAILED_COUNT -eq 0 ]; then
    echo "All images built successfully!"
    echo ""
    echo "Built images:"
    ${CONTAINER_ENGINE} images | grep "${IMAGE_REPO}" | grep "${BASE_IMAGE}"
    echo ""
    echo "Next steps:"
    echo "  • Test: ${CONTAINER_ENGINE} run -p 5900:5900 -p 3000:3000 ${IMAGE_REPO}:${BASE_IMAGE}-latest"
    echo "  • Push: ${CONTAINER_ENGINE} push ${IMAGE_REPO} --all-tags"
    exit 0
else
    echo "Some builds failed. Please check the logs above."
    exit 1
fi
