#!/usr/bin/env python3

######
# TODO: DETECT DUPLICATE DATA
#####

import os
import pymisp
import tempfile
import logging
from pyaml import yaml
from yaml import Loader
from io import StringIO

log = logging.getLogger("__main__")

from opentaxii.signals import (
    CONTENT_BLOCK_CREATED, INBOX_MESSAGE_CREATED
)

def env_config_helper(env_name):
    if env_name in os.environ:
        if env_name == "MISP_COLLECTIONS":
            name = os.environ[env_name]
            return name.split(',')
        return os.environ[env_name]
    else:
        print("Missing env setting {0}. Set OPENTAXII_CONFIG or {0}.".format(env_name))
        return "UNKNOWN"

def yaml_config_helper(config_name, CONFIG):
    if config_name in CONFIG["misp"]:
        if not CONFIG["misp"][config_name]:
            CONFIG["misp"][config_name] = "UNKNOWN"
    else:
        CONFIG["misp"][config_name] = "UNKNOWN"
    return CONFIG

## CONFIG
if "OPENTAXII_CONFIG" in os.environ:
    print("Using config from {}".format(os.environ["OPENTAXII_CONFIG"]))
    CONFIG =  yaml.load(open(os.environ["OPENTAXII_CONFIG"], "r"), Loader=Loader)
    # validate dedup and collections and publish
    CONFIG = yaml_config_helper("dedup", CONFIG)
    CONFIG = yaml_config_helper("collections", CONFIG)
    CONFIG = yaml_config_helper("publish", CONFIG)

else:
    print("Trying to use env variables...")
    misp_url = env_config_helper("MISP_URL")
    misp_api = env_config_helper("MISP_API")
    misp_dedup = env_config_helper("MISP_DEDUP")
    misp_collections = env_config_helper("MISP_COLLECTIONS")
    misp_publish = env_config_helper("MISP_PUBLISH")

    CONFIG = {
                "misp" : {
                            "url" : misp_url,
                            "api" : misp_api,
                            "dedup" : misp_dedup,
                            "collections": misp_collections
                        }
            }

MISP = pymisp.PyMISP( 
                        CONFIG["misp"]["url"],
                        CONFIG["misp"]["api"],
                        ssl = CONFIG["misp"].get("verifySSL", True)
                )

def post_stix(manager, content_block, collection_ids, service_id):
    '''
        Callback function for when our taxii server gets new data
        Will convert it to a MISPEvent and push to the server
    '''

    # make sure collections, if specified are supposed to be sent to 
    if CONFIG["misp"]["collections"] != "UNKNOWN" or CONFIG["misp"]["collections"] == False:
        should_send_to_misp = False
        collection_names = [collection.name for collection in manager.get_collections(service_id)]
        for collection in CONFIG["misp"]["collections"]:
            if collection in collection_names or collection in collection_ids:
                should_send_to_misp = True
        if should_send_to_misp == False:
            log.info('''No collections match misp.collections; aborting MISP extraction.
    Collection ids whitelisted: {}
    Collection ids sent to: {}
    Collection names sent to: {}'''.format(
                CONFIG["misp"]["collections"],
                collection_ids,
                collection_names
            ))
            return None

    # Load the package
    log.info("Posting STIX...")
    block = content_block.content
    if isinstance(block, bytes):
        block = block.decode()
 
    package = pymisp.tools.stix.load_stix(StringIO(block))
    log.info("STIX loaded succesfully.")
    values = [x.value for x in package.attributes]
    log.info("Extracted %s", values)

    # if deduping is enabled, start deduping
    if (
        CONFIG["misp"]["dedup"] or 
        CONFIG["misp"]["dedup"] == "True" or 
        CONFIG["misp"]["dedup"] == "UNKNOWN"
    ):
        for attrib in values:
            log.info("Checking for existence of %s", attrib)
            search = MISP.search("attributes", values=str(attrib))
            if 'response' in search:
                if search["response"]["Attribute"] != []:
                    # This means we have it!
                    log.info("%s is a duplicate, we'll ignore it.", attrib)
                    package.attributes.pop([x.value for x in package.attributes].index(attrib))
                else:
                    log.info("%s is unique, we'll keep it", attrib)
            elif 'Attribute' in search:
                if search["Attribute"] != []:
                    # This means we have it!
                    log.info("%s is a duplicate, we'll ignore it.", attrib)
                    package.attributes.pop([x.value for x in package.attributes].index(attrib))
                else:
                    log.info("%s is unique, we'll keep it", attrib)
            else:
                log.error("Something went wrong with search, and it doesn't have an 'attribute' or a 'response' key: {}".format(search.keys()))

    # Push the event to MISP
    # TODO: There's probably a proper method to do this rather than json_full
    # But I don't wanna read docs
    if (len(package.attributes) > 0):
        log.info("Uploading event to MISP with attributes %s", [x.value for x in package.attributes])
        event = MISP.add_event(package)
        if (
            CONFIG["misp"]["publish"] or
            CONFIG["misp"]["publish"] == "True"
        ):
            log.info("Publishing event to MISP with ID {}".format(event['id']))
            MISP.publish(event)
    else:
        log.info("No attributes, not bothering.")

# Make TAXII call our push function whenever it gets new data
CONTENT_BLOCK_CREATED.connect(post_stix)
