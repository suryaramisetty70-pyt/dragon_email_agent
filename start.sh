#!/bin/bash
# =============================================================================
# PROJECT DRAGON - QUICK START SCRIPT
# =============================================================================

echo "
╔══════════════════════════════════════════════════════════════════════╗
║                                                                      ║
║         🐉 PROJECT DRAGON - EMAIL AI AGENT                           ║
║                                                                      ║
╚══════════════════════════════════════════════════════════════════════╝
"

# Check Python version
python_version=$(python3 --version 2>&1 | grep -oP '\d+\.\d+')
if [[ $(echo "$python_version < 3.10" | bc) -eq 1 ]]; then
    echo "❌ Python 3.10+ required. Current: $(python3 --version)"
    exit 1
fi

echo "✓ Python version OK: $(python3 --version)"

# Install dependencies
echo ""
echo "📦 Installing dependencies..."
pip install loguru pydantic pydantic-settings sqlalchemy fastapi uvicorn python-dateutil beautifulsoup4 apscheduler pyyaml --quiet 2>/dev/null
echo "✓ Core dependencies installed"

# Check for email config
if [ ! -f "config/email_accounts.json" ]; then
    echo ""
    echo "⚠️  No email accounts configured yet!"
    echo ""
    read -p "Do you want to set up your email accounts now? (y/n): " setup
    if [ "$setup" = "y" ]; then
        python3 setup_emails.py
    fi
fi

echo ""
echo "🚀 Starting Dragon Email Agent..."
echo ""

# Run the agent
python3 main.py "$@"