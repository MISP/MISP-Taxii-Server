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
from requests.exceptions import ConnectionError
from pymisp.exceptions import PyMISPError
import warnings
warnings.filterwarnings("ignore")

TOTAL_ATTRIBUTES_SENT = 0
TOTAL_ATTRIBUTES_ANALYZED = 0

logging_level = logging.INFO

log = logging.getLogger("misp_taxii_server")
log.setLevel(logging_level)
handler = logging.StreamHandler()
handler.setLevel(logging_level)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
if log.handlers:
    log.handlers = []
log.addHandler(handler)

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
        log.error("Missing env setting {0}. Set OPENTAXII_CONFIG or {0}.".format(env_name))
        return "UNKNOWN"

def yaml_config_helper(config_name, CONFIG):
    if config_name in CONFIG["misp"]:
        if not CONFIG["misp"][config_name] and CONFIG["misp"][config_name] != False:
            CONFIG["misp"][config_name] = "UNKNOWN"
    else:
        CONFIG["misp"][config_name] = "UNKNOWN"
    return CONFIG

## CONFIG
if "OPENTAXII_CONFIG" in os.environ:
    log.debug("Using config from {}".format(os.environ["OPENTAXII_CONFIG"]))
    CONFIG =  yaml.load(open(os.environ["OPENTAXII_CONFIG"], "r"), Loader=Loader)
    # validate dedup and collections and publish
    CONFIG = yaml_config_helper("dedup", CONFIG)
    CONFIG = yaml_config_helper("collections", CONFIG)
    CONFIG = yaml_config_helper("publish", CONFIG)

else:
    log.debug("Trying to use env variables...")
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
MISP = ''
try:
    MISP = pymisp.PyMISP( 
                        CONFIG["misp"]["url"],
                        CONFIG["misp"]["api"],
                        ssl = CONFIG["misp"].get("verifySSL", True)
                )
except PyMISPError:
    log.error("Cannot connect to MISP; please ensure that MISP is up and running at {}. Skipping MISP upload.".format(CONFIG['misp']['url']))

def post_stix(manager, content_block, collection_ids, service_id):
    '''
        Callback function for when our taxii server gets new data
        Will convert it to a MISPEvent and push to the server
    '''

    # make sure collections, if specified are supposed to be sent to 
    if CONFIG["misp"]["collections"] != "UNKNOWN" or CONFIG["misp"]["collections"] == False:
        log.debug("Using collections")
        should_send_to_misp = False
        collection_names = [collection.name for collection in manager.get_collections(service_id) if collection.id in collection_ids]
        for collection in CONFIG["misp"]["collections"]:
            if collection in collection_names or collection in collection_ids:
                log.debug("Collection specified matches push collection: {}".format(collection))
                should_send_to_misp = True
                break
        if should_send_to_misp == False:
            log.debug('''No collections match misp.collections; aborting MISP extraction.''')
            log.debug("Collection ids whitelisted: {}".format(CONFIG["misp"]["collections"]))
            log.debug("Collection ids sent to: {}".format(collection_ids))
            log.debug('''Collection names sent to: {}'''.format(collection_names))
            return None

    # Load the package
    log.debug("Posting STIX...")
    block = content_block.content
    if isinstance(block, bytes):
        block = block.decode()

    try:
        package = pymisp.tools.stix.load_stix(StringIO(block))
    except Exception:
        log.error('Could not load stix into MISP format; exiting.')
        return 0
    log.debug("STIX loaded succesfully.")
    values = [x.value for x in package.attributes]
    log.debug("Extracted %s", values)
    TOTAL_ATTRIBUTES_ANALYZED = len(values)

    # if deduping is enabled, start deduping
    if (
        CONFIG["misp"]["dedup"] or 
        CONFIG["misp"]["dedup"] == "True" or 
        CONFIG["misp"]["dedup"] == "UNKNOWN"
    ):
        for attrib in values:
            log.debug("Checking for existence of %s", attrib)
            search = ''
            if MISP:
                search = MISP.search("attributes", values=str(attrib))
            else:
                return 0
            if 'response' in search:
                if search["response"]["Attribute"] != []:
                    # This means we have it!
                    log.debug("%s is a duplicate, we'll ignore it.", attrib)
                    package.attributes.pop([x.value for x in package.attributes].index(attrib))
                else:
                    log.debug("%s is unique, we'll keep it", attrib)
            elif 'Attribute' in search:
                if search["Attribute"] != []:
                    # This means we have it!
                    log.debug("%s is a duplicate, we'll ignore it.", attrib)
                    package.attributes.pop([x.value for x in package.attributes].index(attrib))
                else:
                    log.debug("%s is unique, we'll keep it", attrib)
            else:
                log.error("Something went wrong with search, and it doesn't have an 'attribute' or a 'response' key: {}".format(search.keys()))
    else:
        log.debug("Skipping deduplication")

    # Push the event to MISP
    # TODO: There's probably a proper method to do this rather than json_full
    # But I don't wanna read docs
    if (len(package.attributes) > 0):
        log.debug("Uploading event to MISP with attributes %s", [x.value for x in package.attributes])
        event = ''
        try:
            if MISP:
                event = MISP.add_event(package)
                TOTAL_ATTRIBUTES_SENT = len(package.attributes)
        except ConnectionError:
            log.error("Cannot push to MISP; please ensure that MISP is up and running at {}. Skipping MISP upload.".format(CONFIG['misp']['url']))
        if (
            CONFIG["misp"]["publish"] == True or
            CONFIG["misp"]["publish"] == "True"
        ):
            log.info("Publishing event to MISP with ID {}".format(event.get('uuid')))
            if MISP:
                MISP.publish(event)
        else:
            log.debug("Skipping MISP event publishing")
    else:
        log.info("No attributes, not bothering.")

log.debug("total_attributes_analyzed={}, total_attributes_sent={}".format(TOTAL_ATTRIBUTES_ANALYZED, TOTAL_ATTRIBUTES_SENT))
# Make TAXII call our push function whenever it gets new data
CONTENT_BLOCK_CREATED.connect(post_stix)
