#!/usr/bin/env python3

######
# TODO: DETECT DUPLICATE DATA
#####

import os
import pymisp
import tempfile
import logging
from pyaml import yaml
from io import StringIO

log = logging.getLogger("__main__")

from opentaxii.signals import (
    CONTENT_BLOCK_CREATED, INBOX_MESSAGE_CREATED
)

## CONFIG
if "OPENTAXII_CONFIG" in os.environ:
    print("Using config from {}".format(os.environ["OPENTAXII_CONFIG"]))
    CONFIG =  yaml.load(open(os.environ["OPENTAXII_CONFIG"], "r"))
else:
    print("Trying to use env variables...")
    if "MISP_URL" in os.environ:
        misp_url = os.environ["MISP_URL"]
    else:
        print("Unkown misp URL. Set OPENTAXII_CONFIG or MISP_URL.")
        misp_url = "UNKNOWN"
    if "MISP_API" in os.environ:
        misp_api = os.environ["MISP_API"]
    else:
        print("Unknown misp API key. Set OPENTAXII_CONFIG or MISP_API.")
        misp_api = "UNKNOWN"

    CONFIG = {
                "misp" : {
                            "url" : misp_url,
                            "api" : misp_api
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

    # Load the package
    log.info("Posting STIX...")
    block = content_block.content
    if isinstance(block, bytes):
        block = block.decode()
 
    package = pymisp.tools.stix.load_stix(StringIO(block))
    log.info("STIX loaded succesfully.")
    values = [x.value for x in package.attributes]
    log.info("Extracted %s", values)
    for attrib in values:
        log.info("Checking for existence of %s", attrib)
        search = MISP.search("attributes", values=str(attrib))
        if search["response"]["Attribute"] != []:
            # This means we have it!
            log.info("%s is a duplicate, we'll ignore it.", attrib)
            package.attributes.pop([x.value for x in package.attributes].index(attrib))
        else:
            log.info("%s is unique, we'll keep it", attrib)

    # Push the event to MISP
    # TODO: There's probably a proper method to do this rather than json_full
    # But I don't wanna read docs
    if (len(package.attributes) > 0):
        log.info("Uploading event to MISP with attributes %s", [x.value for x in package.attributes])
        MISP.add_event(package)
    else:
        log.info("No attributes, not bothering.")

# Make TAXII call our push function whenever it gets new data
CONTENT_BLOCK_CREATED.connect(post_stix)
