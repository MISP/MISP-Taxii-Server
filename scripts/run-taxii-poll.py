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
    cli = create_client(host = server["host"],
                        port = server["port"],
                        discovery_path = server["discovery_path"],
                        use_https = server["use_https"],
                        version = server["taxii_version"],
                        headers = server["headers"])

    cli.username = server["auth"]["username"]
    cli.password = server["auth"]["password"]

    for collection in server["collections"]:
        for content_block in cli.poll(collection):
            pass            
