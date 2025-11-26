#!/bin/bash
set -e

echo "--- PostgreSQL Targeted listen_addresses Fix Script ---"
echo "You may be prompted for your password for 'sudo' commands."

# Find PostgreSQL config directory
PG_CONF_DIR=""
if [ -d "/etc/postgresql" ]; then
    # Debian/Ubuntu style
    PG_VERSION=$(ls /etc/postgresql/ | head -n 1)
    PG_CONF_DIR="/etc/postgresql/$PG_VERSION/main"
elif [ -d "/var/lib/pgsql" ]; then
    # RHEL/CentOS style
    PG_VERSION=$(ls /var/lib/pgsql/ | head -n 1)
    PG_CONF_DIR="/var/lib/pgsql/$PG_VERSION/data"
else
    echo "Error: Could not automatically determine PostgreSQL configuration directory."
    exit 1
fi

echo "Found PostgreSQL configuration directory: $PG_CONF_DIR"

PG_CONF_FILE="$PG_CONF_DIR/postgresql.conf"

# --- 1. Backup configuration file ---
echo "Backing up $PG_CONF_FILE..."
sudo cp "$PG_CONF_FILE" "$PG_CONF_FILE.bak.$(date +%s)"
echo "Backup complete."

# --- 2. Modify postgresql.conf ---
echo "Commenting out any existing 'listen_addresses' line..."
# Add a '#' to the beginning of any line starting with 'listen_addresses'
sudo sed -i -E "s/^[[:space:]]*listen_addresses[[:space:]]*=/#&/" "$PG_CONF_FILE"

echo "Appending 'listen_addresses = \"*\"' to the end of the file..."
echo "listen_addresses = '*'". | sudo tee -a "$PG_CONF_FILE" > /dev/null

echo "postgresql.conf modification complete."

# --- 3. Restart PostgreSQL service ---
echo "Restarting PostgreSQL service to apply changes..."
sudo systemctl restart postgresql
echo "PostgreSQL service restarted."

echo "--- Targeted Fix Complete ---"
