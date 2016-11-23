#!/usr/bin/env python3

######
# TODO: DETECT DUPLICATE DATA
#####

import os
import pymisp
import tempfile
from pyaml import yaml

from opentaxii.signals import (
    CONTENT_BLOCK_CREATED, INBOX_MESSAGE_CREATED
)

## CONFIG
if "MISP_TAXII_CONFIG" in os.environ:
    print("Using config from {}".format(os.environ["MISP_TAXII_CONFIG"]))
    CONFIG =  yaml.parse(open(os.environ["MISP_TAXII_CONFIG"], "r"))
else:
    print("Trying to use env variables...")
    if "MISP_URL" in os.environ:
        misp_url = os.environ["MISP_URL"]
    else:
        print("Unkown misp URL. Set MISP_TAXII_CONFIG or MISP_URL.")
        misp_url = "UNKNOWN"
    if "MISP_API" in os.environ:
        misp_api = os.environ["MISP_API"]
    else:
        print("Unknown misp API key. Set MISP_TAXII_CONFIG or MISP_API.")
        misp_api = "UNKNOWN"

    CONFIG = {
            "MISP_URL" : misp_url,
            "MISP_API" : misp_api,
            }

MISP = pymisp.PyMISP( 
                        CONFIG["MISP_URL"],
                        CONFIG["MISP_API"],
                )

def post_stix(manager, content_block, collection_ids, service_id):
    '''
        Callback function for when our taxii server gets new data
        Will convert it to a MISPEvent and push to the server
    '''

    # Create a temporary file to load STIX data from
    f = tempfile.SpooledTemporaryFile(max_size=10*1024, mode="w")
    f.write(content_block.content)
    f.seek(0)

    # Load the package
    package = pymisp.tools.stix.load_stix(f)

    # Check for duplicates
    for attrib in package.attributes:
        try:
            if (0 != len(MISP.search_index(attrib.value)["response"])):
                # It's a dupe! 
                package.attributes.remove(attrib)        
        except:
            # idk, this is just in case pymisp does a weird
            pass

    # Push the event to MISP
    # TODO: There's probably a proper method to do this rather than json_full
    # But I don't wanna read docs
    if (len(package.attributes) > 0):
        MISP.add_event(package._json_full())

# Make TAXII call our push function whenever it gets new data
CONTENT_BLOCK_CREATED.connect(post_stix)
