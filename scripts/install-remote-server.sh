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
'$SNAME':
  host: localhost
  port: 9000
  discovery_path: None
  use_https: False
  taxii_version: 1.1
  headers: None
