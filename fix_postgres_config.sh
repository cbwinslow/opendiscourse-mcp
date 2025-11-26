#!/bin/bash
set -e

echo "--- PostgreSQL Auto-Configuration Script ---"
echo "This script will attempt to configure PostgreSQL to accept network connections."
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
    echo "Please configure PostgreSQL manually."
    exit 1
fi

echo "Found PostgreSQL configuration directory: $PG_CONF_DIR"

PG_CONF_FILE="$PG_CONF_DIR/postgresql.conf"
PG_HBA_FILE="$PG_CONF_DIR/pg_hba.conf"

# --- 1. Backup configuration files ---
echo "Backing up configuration files..."
sudo cp "$PG_CONF_FILE" "$PG_CONF_FILE.bak"
sudo cp "$PG_HBA_FILE" "$PG_HBA_FILE.bak"
echo "Backup complete: $PG_CONF_FILE.bak, $PG_HBA_FILE.bak"

# --- 2. Modify postgresql.conf to listen on all addresses ---
echo "Modifying postgresql.conf to set listen_addresses = '*'..."
# This command will uncomment the line if it's commented, and set the value to '*'
sudo sed -i "s/#listen_addresses = 'localhost'/listen_addresses = '*'/" "$PG_CONF_FILE"
# If the line was already uncommented but different, this will set it to '*'
sudo sed -i "s/listen_addresses = .*/listen_addresses = '*'/" "$PG_CONF_FILE"
echo "postgresql.conf modified."

# --- 3. Modify pg_hba.conf to allow connections ---
echo "Modifying pg_hba.conf to allow connections for 'opendiscourse' user..."
# Check if the rule already exists to avoid duplicates
if ! sudo grep -q "host    opendiscourse    opendiscourse    0.0.0.0/0   md5" "$PG_HBA_FILE"; then
    echo "Adding new host rule to pg_hba.conf."
    echo "host    opendiscourse    opendiscourse    0.0.0.0/0   md5" | sudo tee -a "$PG_HBA_FILE" > /dev/null
else
    echo "Host rule already exists in pg_hba.conf. Skipping."
fi
echo "pg_hba.conf modified."

# --- 4. Open firewall port ---
echo "Opening port 5432 in firewall (ufw)..."
if command -v ufw &> /dev/null; then
    sudo ufw allow 5432/tcp
    echo "Firewall rule added for port 5432."
else
    echo "ufw not found. Skipping firewall configuration. Please configure your firewall manually if needed."
fi

# --- 5. Restart PostgreSQL service ---
echo "Restarting PostgreSQL service to apply changes..."
sudo systemctl restart postgresql
echo "PostgreSQL service restarted."

echo "--- Configuration Complete ---"
echo "PostgreSQL has been configured. Please try connecting to the database again."
