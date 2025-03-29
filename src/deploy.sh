#!/bin/bash

set -e

echo "🚀 Starting deployment to fly.io..."

curl -L https://fly.io/install.sh | sh

export FLYCTL_INSTALL="$HOME/.fly"
export PATH="$FLYCTL_INSTALL/bin:$PATH"

flyctl auth login

flyctl deploy