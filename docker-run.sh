export OPENTAXII_CONFIG=/MISP-Taxii-Server/config.yaml && export PYTHONPATH=.

cat > /MISP-Taxii-Server/config.yaml <<EOF
domain: "localhost:9000"
support_basic_auth: yes

persistence_api:
  class: opentaxii.persistence.sqldb.SQLDatabaseAPI
  parameters:
    db_connection: $PERSIST_CONNECTION_STRING
    create_tables: yes

auth_api:
  class: opentaxii.auth.sqldb.SQLDatabaseAPI
  parameters:
    db_connection: $AUTH_CONNECTION_STRING
    create_tables: yes
    secret: ILoveTheSecretStringIsIsGreatButNeedsToBeChangedFrienderino

logging:
  opentaxii: info
  root: info

hooks: misp_taxii_hooks.hooks
# Sample configuration for misp_taxii_server

zmq:
    host: "$ZMQ_HOST"
    port: "$ZMQ_PORT"

misp:
    url: "$MISP_URL"
    api: "$MISP_KEY"

taxii:
    auth:
        username: "$TAXII_USER"
        password: "$TAXII_PASS"
    collections:
        - collection
EOF
opentaxii-create-services -c config/services.yaml && opentaxii-create-collections -c config/collections.yaml

opentaxii-create-account -u $TAXII_USER -p $TAXII_PASS
gunicorn opentaxii.http:app --bind 0.0.0.0:9000
