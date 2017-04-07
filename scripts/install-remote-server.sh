HOMEDIR=~
CONFIGDIR=$HOMEDIR/.misptaxii

echo "[MISP-TAXII-SERVER]"
echo "POLLING SERVER INSTALLATION"

if [ ! -d $CONFIGDIR ]; then
    echo "Creating config directory at $CONFIGDIR"
    mkdir -p $CONFIGDIR;
fi

if [ ! -f $CONFIGDIR/local-server.yml ]; then
    echo "Creating local server configuration at $CONFIGDIR"
    cat >> $CONFIGDIR/local-server.yml << EOF
host: localhost
port: 9000
discovery_path: /services/discovery
inbox_path: /services/inbox
use_https: False
taxii_version: '1.1'
headers:
auth:
  username: test
  password: test
collections:
  - collection
EOF
fi

echo "FRIENDLY SERVER NAME:"
read SNAME

cat >> $CONFIGDIR/remote-servers.yml << EOF
- name: '$SNAME'
  host: localhost
  port: 9000
  discovery_path: 
  use_https: False
  taxii_version: '1.1'
  headers: 
  auth:
    username:
    password:
    cacert_path:
    cert_file:
    key_file:
    key_password:
    jwt_auth_url:
    verify_ssl: True
  collections:
    - collection
EOF

echo "New server added to $CONFIGDIR/remote-servers.yml - please go change the settings"
