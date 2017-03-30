HOMEDIR=~
CONFIGDIR=$HOMEDIR/.misptaxii

echo "[MISP-TAXII-SERVER]"
echo "POLLING SERVER INSTALLATION"

if [ ! -d $CONFIGDIR ]; then
    echo "Creating config directory at $CONFIGDIR"
    mkdir -p $CONFIGDIR;
fi

echo "FRIENDLY SERVER NAME:"
read SNAME

cat >> $CONFIGDIR/servers.yml << EOF
- name: '$SNAME':
  host: localhost
  port: 9000
  discovery_path: 
  use_https: False
  taxii_version: 1.1
  headers: 
EOF

echo "New server added to $CONFIGDIR/servers.yml - please go change the settings"
