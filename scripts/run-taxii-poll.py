#!/usr/bin/env python3

from cabby import create_client
from pyaml import yaml
import argparse
import os
import logging
import sys

# Create an argument parser for our program
# Will just take in a config file and logging options
parser = argparse.ArgumentParser(description='Run MISP taxii pull.')
parser.add_argument('-c', "--configdir", default="~/.misptaxii", help='Config directory')
parser.add_argument("-v", "--verbose", action="store_true", help="More verbose logging")
parser.add_argument("-s", "--stdout", action="store_true", help="Log to STDOUT")
args = parser.parse_args()

# Set up a logger for logging's sake
log = logging.getLogger(__name__)
logging.basicConfig(filename="poll.log")
log.setLevel(logging.DEBUG if args.verbose else logging.INFO)

# If we want, print the output to stdout
if args.stdout:
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    ch = logging.StreamHandler(sys.stdout)    
    ch.setFormatter(formatter)
    log.addHandler(ch)

# Read in the remote server configurations
configFile = "{}/remote-servers.yml".format(os.path.expanduser(args.configdir))
log.debug("Opening config file %s", configFile)
with open(configFile, "r") as f:
    config = yaml.load(f.read())
log.debug("Config read %s", config)

# Read in the local server configuration
localConfig = "{}/local-server.yml".format(os.path.expanduser(args.configdir))
log.debug("Reading local server config")
with open(localConfig, "r") as f:
    localConfig = yaml.load(f.read())

# Attempt to make contact with the local server
log.info("Connecting to local server...")
localClient = create_client(host = localConfig["host"],
                            port = localConfig["port"],
                            discovery_path = localConfig["discovery_path"],
                            use_https = localConfig["use_https"],
                            version = localConfig["taxii_version"],
                            headers = localConfig["headers"])
localClient.username = localConfig["auth"]["username"]
localClient.password = localConfig["auth"]["password"]

localInbox = "{}://{}:{}{}".format("https" if localConfig["use_https"] else "http",
                                   localConfig["host"], localConfig["port"],
                                   localConfig["inbox_path"])

# Check that we're all good and authenticated
try:
    list(localClient.discover_services())
except Exception as ex:
    log.fatal("Could not connect to local server")
    log.fatal(ex)
    sys.exit(1)

log.info("Connected")

for server in config:
    log.info("== %s ==", server["name"])

    log.debug("Creating client")
    log.debug("HOST:PORT : %s:%s", server["host"], server["port"])
    log.debug("DISCPATH: %s", server["discovery_path"])
    cli = create_client(host = server["host"],
                        port = server["port"],
                        discovery_path = server["discovery_path"],
                        use_https = server["use_https"],
                        version = server["taxii_version"],
                        headers = server["headers"])

    log.debug("Setting client log level")
    cli.log.setLevel(logging.DEBUG if args.verbose else logging.INFO)
        

    log.debug("Setting authentication...")
    cli.set_auth(username = server["auth"]["username"],
                 password = server["auth"]["password"],
                 ca_cert  = server["auth"].get("ca_cert"),
                 cert_file= server["auth"].get("cert_file"),
                 key_file = server["auth"].get("key_file"),
                 key_password = server["auth"].get("key_password"),
                 jwt_auth_url = server["auth"].get("jwt_auth_url"),
                 verify_ssl = server["auth"].get("verify_ssl"))

    log.debug("Discovering services...")
    services = cli.discover_services()
    log.debug(services)

    log.debug("Auth set.")
    for collection in server["collections"]:
        log.debug("Polling %s", collection)
        for content_block in cli.poll(collection_name=collection):
            log.debug("Pushing block %s", content_block)
            localClient.push(content_block.content.decode("utf-8"), 
                             collection_names=localConfig["collections"],
                             content_binding=content_block.binding,
                             uri=localInbox)

log.info("Finished!")
