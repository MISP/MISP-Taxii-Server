#!/usr/bin/env python3

from cabby import create_client
from pyaml import yaml
import argparse
import os
import logging
import sys

parser = argparse.ArgumentParser(description='Run MISP taxii pull.')

parser.add_argument('-c', "--configdir", default="~/.misptaxii", help='Config directory')
parser.add_argument("-v", "--verbose", action="store_true", help="More verbose logging")
parser.add_argument("-s", "--stdout", action="store_true", help="Log to STDOUT")

args = parser.parse_args()
log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG if args.verbose else logging.INFO)

if args.stdout:
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    ch = logging.StreamHandler(sys.stdout)    
    ch.setFormatter(formatter)
    log.addHandler(ch)

configFile = "{}/servers.yml".format(os.path.expanduser(args.configdir))
log.debug("Opening config file %s", configFile)
with open(configFile, "r") as f:
    config = yaml.load(f.read())

log.debug("Config read %s", config)

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

    log.info(list(cli.poll("collection")))
