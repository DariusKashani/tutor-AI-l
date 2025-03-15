#!/bin/bash
# Script to install dependencies for the Math Tutorial Generator

echo "Installing dependencies for Math Tutorial Generator..."

# Detect OS
if [[ "$OSTYPE" == "darwin"* ]]; then
    # macOS
    echo "Detected macOS..."
    
    # Check if Homebrew is installed
    if ! command -v brew &> /dev/null; then
        echo "Homebrew is not installed. Installing Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
    fi
    
    # Check if MacTeX is installed
    if ! command -v latex &> /dev/null; then
        echo "Installing MacTeX (this may take some time)..."
        brew install --cask mactex
    fi
    
    # Install standalone package
    echo "Installing LaTeX standalone package..."
    sudo tlmgr update --self
    sudo tlmgr install standalone
    
    # Install FFmpeg if not present
    if ! command -v ffmpeg &> /dev/null; then
        echo "Installing FFmpeg..."
        brew install ffmpeg
    fi
    
elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
    # Linux
    echo "Detected Linux..."
    
    # Check distribution
    if [ -f /etc/debian_version ]; then
        # Debian/Ubuntu
        echo "Detected Debian/Ubuntu..."
        
        # Install texlive with necessary packages
        echo "Installing LaTeX dependencies..."
        sudo apt-get update
        sudo apt-get install -y texlive texlive-latex-extra texlive-fonts-extra
        
        # Install FFmpeg
        echo "Installing FFmpeg..."
        sudo apt-get install -y ffmpeg
    
    elif [ -f /etc/fedora-release ]; then
        # Fedora
        echo "Detected Fedora..."
        
        # Install texlive with necessary packages
        echo "Installing LaTeX dependencies..."
        sudo dnf install -y texlive texlive-standalone texlive-latex
        
        # Install FFmpeg
        echo "Installing FFmpeg..."
        sudo dnf install -y ffmpeg
    
    elif [ -f /etc/arch-release ]; then
        # Arch
        echo "Detected Arch Linux..."
        
        # Install texlive with necessary packages
        echo "Installing LaTeX dependencies..."
        sudo pacman -Sy texlive-most
        
        # Install FFmpeg
        echo "Installing FFmpeg..."
        sudo pacman -Sy ffmpeg
    
    else
        echo "Unsupported Linux distribution. Please install texlive-latex-extra and ffmpeg manually."
    fi
else
    echo "Unsupported operating system. Please install LaTeX with the standalone package and FFmpeg manually."
fi

# Check Python dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

echo "Dependencies installation completed."
echo "If you still experience LaTeX errors, you may need to install the standalone package manually:"
echo "For macOS: sudo tlmgr install standalone"
echo "For Debian/Ubuntu: sudo apt-get install texlive-latex-extra"

echo "Installation completed." 