#!/usr/bin/env bash
set -euo pipefail

# Update and install dependencies
sudo apt update
sudo apt install -y make build-essential libssl-dev zlib1g-dev libbz2-dev \
    libreadline-dev libsqlite3-dev wget curl llvm libncurses5-dev \
    libncursesw5-dev xz-utils tk-dev libffi-dev liblzma-dev python-openssl git

# Install pyenv (only if not installed already)
if [ ! -d "$HOME/.pyenv" ]; then
    curl https://pyenv.run | bash
fi

# Configure shell for pyenv (if not already configured)
if ! grep -q 'pyenv init' "$HOME/.bashrc"; then
    cat << 'EOF' >> "$HOME/.bashrc"

# >>> pyenv setup >>>
export PATH="$HOME/.pyenv/bin:$PATH"
eval "$(pyenv init --path)"
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"
# <<< pyenv setup <<<
EOF
fi

# Add ~/.local/bin to PATH (for user-installed pip packages)
if ! grep -q '$HOME/.local/bin' "$HOME/.bashrc"; then
    echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$HOME/.bashrc"
fi

# Load pyenv into this script's environment
export PATH="$HOME/.pyenv/bin:$PATH"
eval "$(pyenv init --path)"
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"

# Install Python 3.10 if missing
if ! pyenv versions | grep -q "3.10.0"; then
    pyenv install 3.10.0
fi

# Set Python 3.10 as global default
pyenv global 3.10.0

# Upgrade pip inside Python 3.10
pyenv exec python -m ensurepip --upgrade
pyenv exec python -m pip install --upgrade pip

# Check
echo "Python version set to: $(python --version)"
echo "Pip version set to: $(pip --version)"

echo ""
echo ">>> IMPORTANT: Close this terminal and open a new one, OR run 'source ~/.bashrc' <<<"
