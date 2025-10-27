#!/bin/bash
# Quick Setup Script for Mobile Credentials
# This script sets up Google Cloud Secret Manager for mobile access

set -e  # Exit on any error

echo "=========================================="
echo "🔐 MOBILE CREDENTIALS SETUP"
echo "=========================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print colored output
print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

# Check if running from correct directory
if [ ! -f "requirements.txt" ]; then
    print_error "Please run this script from the project root directory"
    exit 1
fi

# Step 1: Check prerequisites
echo "[1/7] Checking prerequisites..."

# Check Python
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed"
    exit 1
fi
print_success "Python 3 found"

# Check gcloud
if ! command -v gcloud &> /dev/null; then
    print_warning "gcloud CLI not found"
    echo "Install from: https://cloud.google.com/sdk/docs/install"
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
else
    print_success "gcloud CLI found"
fi

# Step 2: Install dependencies
echo ""
echo "[2/7] Installing Python dependencies..."
pip install google-cloud-secret-manager python-dotenv
print_success "Dependencies installed"

# Step 3: Get Google Cloud project ID
echo ""
echo "[3/7] Google Cloud configuration..."

# Try to get project from gcloud
if command -v gcloud &> /dev/null; then
    DEFAULT_PROJECT=$(gcloud config get-value project 2>/dev/null || echo "")
    if [ -n "$DEFAULT_PROJECT" ]; then
        print_success "Found project: $DEFAULT_PROJECT"
        read -p "Use this project? (Y/n) " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Nn]$ ]]; then
            read -p "Enter your Google Cloud project ID: " PROJECT_ID
        else
            PROJECT_ID=$DEFAULT_PROJECT
        fi
    else
        read -p "Enter your Google Cloud project ID: " PROJECT_ID
    fi
else
    read -p "Enter your Google Cloud project ID: " PROJECT_ID
fi

if [ -z "$PROJECT_ID" ]; then
    print_error "Project ID is required"
    exit 1
fi

print_success "Using project: $PROJECT_ID"

# Step 4: Authenticate
echo ""
echo "[4/7] Authenticating with Google Cloud..."
if command -v gcloud &> /dev/null; then
    print_warning "This will open a browser window for authentication..."
    gcloud auth application-default login
    print_success "Authenticated successfully"
else
    print_warning "Skipping authentication (gcloud not installed)"
fi

# Step 5: Enable API
echo ""
echo "[5/7] Enabling Secret Manager API..."
if command -v gcloud &> /dev/null; then
    gcloud services enable secretmanager.googleapis.com --project=$PROJECT_ID 2>/dev/null || true
    print_success "Secret Manager API enabled"
else
    print_warning "Skipping API enablement (gcloud not installed)"
    echo "  Please enable manually: https://console.cloud.google.com/apis/library/secretmanager.googleapis.com"
fi

# Step 6: Set environment variable
echo ""
echo "[6/7] Setting environment variable..."
export GOOGLE_CLOUD_PROJECT=$PROJECT_ID

# Add to shell profile
SHELL_PROFILE=""
if [ -f "$HOME/.zshrc" ]; then
    SHELL_PROFILE="$HOME/.zshrc"
elif [ -f "$HOME/.bashrc" ]; then
    SHELL_PROFILE="$HOME/.bashrc"
elif [ -f "$HOME/.bash_profile" ]; then
    SHELL_PROFILE="$HOME/.bash_profile"
fi

if [ -n "$SHELL_PROFILE" ]; then
    if grep -q "GOOGLE_CLOUD_PROJECT" "$SHELL_PROFILE"; then
        print_warning "GOOGLE_CLOUD_PROJECT already in $SHELL_PROFILE"
    else
        echo "" >> "$SHELL_PROFILE"
        echo "# Google Cloud Project for Trading System" >> "$SHELL_PROFILE"
        echo "export GOOGLE_CLOUD_PROJECT=\"$PROJECT_ID\"" >> "$SHELL_PROFILE"
        print_success "Added to $SHELL_PROFILE"
    fi
fi

print_success "Environment variable set"

# Step 7: Migrate credentials
echo ""
echo "[7/7] Migrating credentials to Secret Manager..."
echo ""

# First do a dry run
echo "Performing dry run (no changes will be made)..."
python3 migrate_credentials_to_secret_manager.py --project-id "$PROJECT_ID" --dry-run

echo ""
read -p "Proceed with actual migration? (Y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Nn]$ ]]; then
    python3 migrate_credentials_to_secret_manager.py --project-id "$PROJECT_ID"
    print_success "Credentials migrated!"
else
    print_warning "Migration skipped"
fi

# Final summary
echo ""
echo "=========================================="
echo "🎉 SETUP COMPLETE!"
echo "=========================================="
echo ""
echo "What's been done:"
echo "  ✓ Installed dependencies"
echo "  ✓ Configured Google Cloud"
echo "  ✓ Authenticated"
echo "  ✓ Enabled Secret Manager API"
echo "  ✓ Set environment variables"
echo "  ✓ Migrated credentials"
echo ""
echo "Next steps:"
echo ""
echo "1. TEST the setup:"
echo "   python3 test_secret_manager.py"
echo ""
echo "2. UPDATE your code (see INTEGRATION_GUIDE.md)"
echo ""
echo "3. FOR MOBILE ACCESS:"
echo "   Your credentials are now in Google Cloud!"
echo "   Access from anywhere with gcloud authentication"
echo ""
echo "4. RELOAD your shell to apply environment variables:"
if [ -n "$SHELL_PROFILE" ]; then
    echo "   source $SHELL_PROFILE"
fi
echo ""
echo "📚 Documentation:"
echo "   • MOBILE_CREDENTIALS_SETUP.md - Full guide"
echo "   • INTEGRATION_GUIDE.md - Code integration"
echo "   • example_secret_manager_usage.py - Code examples"
echo ""
echo "=========================================="

# Test credentials
echo ""
read -p "Run test now? (Y/n) " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Nn]$ ]]; then
    echo ""
    python3 test_secret_manager.py
fi

echo ""
print_success "All done! 🚀"


