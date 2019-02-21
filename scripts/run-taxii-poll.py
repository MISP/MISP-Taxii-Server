#!/usr/bin/env python3

from cabby import create_client
from pyaml import yaml
import pytz
import argparse
import os
import logging
import sys
from datetime import datetime

# Create an argument parser for our program
# Will just take in a config file and logging options
parser = argparse.ArgumentParser(description='Run MISP taxii pull.')
parser.add_argument('-c', "--configdir", default="~/.misptaxii",
                    help='Config directory')
parser.add_argument("-v", "--verbose", action="store_true",
                    help="More verbose logging")
parser.add_argument("-s", "--stdout", action="store_true",
                    help="Log to STDOUT")
parser.add_argument("--start",
                    help="Date to poll from (YYYY-MM-DDTHH:MM:SS), Exclusive")
parser.add_argument("--end",
                    help="Date to poll to (YYYY-MM-DDTHH:MM:SS), Inclusive")
parser.add_argument("--subscription_id", help="The ID of the subscription",
                    default=None)
parser.add_argument("--tz",
                    help="Your timezone, e.g Europe/London. Default utc",
                    default="utc")

args = parser.parse_args()

# Set up a logger for logging's sake
log = logging.getLogger(__name__)
logging.basicConfig(
    filename="poll.log",
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
log.setLevel(logging.DEBUG if args.verbose else logging.INFO)

# If we want, print the output to stdout
if args.stdout:
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(formatter)
    log.addHandler(ch)

# Read in the remote server configurations
config_file = "{}/remote-servers.yml".format(
    os.path.expanduser(args.configdir))

log.debug("Opening config file %s", config_file)
with open(config_file, "r") as f:
    config = yaml.load(f.read())
log.debug("Config read %s", config)

# Read in the local server configuration
local_config = "{}/local-server.yml".format(os.path.expanduser(args.configdir))
log.debug("Reading local server config")
with open(local_config, "r") as f:
    local_config = yaml.load(f.read())

# Attempt to make contact with the local server
log.info("Connecting to local server...")
local_client = create_client(host=local_config["host"],
                             port=local_config["port"],
                             discovery_path=local_config["discovery_path"],
                             use_https=local_config["use_https"],
                             version=local_config["taxii_version"],
                             headers=local_config["headers"])

local_client.username = local_config["auth"]["username"]
local_client.password = local_config["auth"]["password"]


local_inbox = "{}://{}:{}{}".format(
    "https" if local_config["use_https"] else "http",
    local_config["host"], local_config["port"],
    local_config["inbox_path"])

# Check that we're all good and authenticated
try:
    list(local_client.discover_services())
except Exception as ex:
    log.fatal("Could not connect to local server")
    log.fatal(ex)
    sys.exit(1)

log.info("Connected")

subscription_id = args.subscription_id
poll_from = datetime.strptime(args.start, "%Y-%m-%dT%H:%M:%S") if args.start else None
poll_to = datetime.strptime(args.end, "%Y-%m-%dT%H:%M:%S") if args.end else datetime.now()

timezone = args.tz
# Try to cast to pytz
try:
    timezone = pytz.timezone(timezone)
except pytz.exceptions.UnknownTimeZoneError:
    log.fatal("Timezone %s unknown", timezone)
    log.fatal("Please select one of %s", ", ".join(pytz.all_timezones))
    log.fatal("That's case sensitive!")
    sys.exit(1)

# Add timezone info
if poll_from:
    # (may not exist)
    poll_from = poll_from.replace(tzinfo=pytz.timezone(args.tz))

poll_to = poll_to.replace(tzinfo=pytz.timezone(args.tz))

log.info("Set poll time to %s - %s", poll_from, poll_to)

for server in config:
    log.info("== %s ==", server["name"])

    log.debug("Creating client")
    log.debug("HOST:PORT : %s:%s", server["host"], server["port"])
    log.debug("DISCPATH: %s", server["discovery_path"])

    # Standard autodiscovery
    client_args = {
        "host": server["host"],
        "port": server["port"],
        "discovery_path": server["discovery_path"],
        "use_https": server["use_https"],
        "version": server["taxii_version"],
        "headers": server["headers"]
    }

    cli = create_client(**client_args)

    log.debug("Setting client log level")
    cli.log.setLevel(logging.DEBUG if args.verbose else logging.INFO)

    log.debug("Setting authentication...")
    cli.set_auth(username=server["auth"]["username"],
                 password=server["auth"]["password"],
                 ca_cert=server["auth"].get("ca_cert"),
                 cert_file=server["auth"].get("cert_file"),
                 key_file=server["auth"].get("key_file"),
                 key_password=server["auth"].get("key_password"),
                 jwt_auth_url=server["auth"].get("jwt_auth_url"),
                 verify_ssl=server["auth"].get("verify_ssl"))

    log.debug("Discovering services...")
    services = cli.discover_services()
    log.debug(services)

    log.debug("Auth set.")
    for collection in server["collections"]:
        log.debug("Polling %s", collection)
        server_uri_override = server.get("uri", None)
        if not server_uri_override.startswith("http"):
            server_uri_override = None
        if server_uri_override:
            log.debug("Poll URL override set to %s", server_uri_override)

        log.debug("Within date range %s - %s",
                  poll_from or "Beginning of time", poll_to)
        try:
            for content_block in cli.poll(collection_name=collection,
                                          subscription_id=subscription_id,
                                          begin_date=poll_from,
                                          end_date=poll_to,
                                          uri=server.get("uri", None)):
                try:
                    log.debug("Pushing block %s", content_block)
                    local_client.push(
                        content_block.content.decode("utf-8"),
                        collection_names=local_config["collections"],
                        content_binding=content_block.binding,
                        uri=local_inbox)
                except Exception as ex:
                    log.error("FAILED TO PUSH BLOCK!")
                    log.error("%s", content_block)
                    log.exception(ex, exc_info=True)
        except Exception as ex:
            log.error("FAILED TO POLL %s", collection)
            log.exception(ex, exc_info=True)

log.info("Finished!")
