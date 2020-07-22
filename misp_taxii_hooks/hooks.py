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
from lxml.etree import XMLSyntaxError
import time
import json
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

if "auto_publish" in CONFIG:
    AUTO_PUBLISH = CONFIG["auto_publish"]

def post_stix(manager, content_block, collection_ids, service_id):
    '''
        Callback function for when our taxii server gets new data
        Will convert it to a MISPEvent and push to the server
    '''
    # Handle exceptions
    try:
        # Load the package
        log.info("Posting STIX...")
        block = content_block.content
        if isinstance(block, bytes):
            block = block.decode()

        package = pymisp.tools.stix.load_stix(StringIO(block),distribution=0)
        log.info("STIX loaded succesfully.")

        # Auto-publish the event,if configured to do so.
        if AUTO_PUBLISH:
            package.publish()
    
        values = [x.value for x in package.attributes]
        log.info("Extracted %s", values)
        for attrib in values:
            try:
                log.debug("Checking for existence of %s", attrib)
                search = MISP.search(controller="attributes", value=str(attrib))
                if   search["Attribute"] != []:
                    # This means we have it!
                    log.debug("%s is a duplicate, we'll ignore it.", attrib)
                    package.attributes.pop([x.value for x in package.attributes].index(attrib))
                else:
                    log.info("%s is unique, we'll keep it", attrib)
            except Exception:
                log.exception("Attribute lookup error:%s",attrib)
                continue
        # Push the event to MISP
        # TODO: There's probably a proper method to do this rather than json_full
        # But I don't wanna read docs
        if (len(package.attributes) > 0):
            log.info("Uploading event to MISP with attributes %s", [x.value for x in package.attributes])
            MISP.add_event(package)
        else:
            log.debug("No attributes %s, not bothering.",str(package.attributes))
    except json.decoder.JSONDecodeError as e:
        log.exception("Json Decoder Error")
        log.info("Content: %s",str(block))
    except XMLSyntaxError as e:
        log.exception("lxml.etree.XMLSyntaxError")
        log.info("Content: %s",str(block))
    except Exception as e:
        log.exception("Exception: %s",str(e))
# Make TAXII call our push function whenever it gets new data
CONTENT_BLOCK_CREATED.connect(post_stix)

