#!/bin/bash

# Setup script for SPADE agent environment

echo "Step 1: Verifying Python and SPADE installation..."
python3 --version
pip list | grep spade

echo ""
echo "Step 2: Installing Ejabberd XMPP server..."
apt-get update -qq
apt-get install -y -qq ejabberd

echo ""
echo "Step 3: Starting Ejabberd service..."
service ejabberd start
sleep 5

echo ""
echo "Step 4: Checking Ejabberd status..."
service ejabberd status

echo ""
echo "Step 5: Creating agent credentials..."
# Register default admin user
ejabberdctl register testadmin localhost password123
ejabberdctl register testagent localhost password123

echo ""
echo "Setup complete! Ready to run SPADE agents."
