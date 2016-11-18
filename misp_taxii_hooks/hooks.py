#!/usr/bin/env python3

######
# TODO: DETECT DUPLICATE DATA
#####

import pymisp
import tempfile
import os

from opentaxii.signals import (
    CONTENT_BLOCK_CREATED, INBOX_MESSAGE_CREATED
)

## CONFIG

CONFIG = {
            "MISP_URL" : "[URL]",
            "MISP_API" : "[APIKEY]",
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
    f = tempfile.NamedTemporaryFile(delete=False, mode="w")
    f.write(content_block.content)
    f.close()

    # Load the package
    package = pymisp.tools.stix.load_stix(f.name)

    # Check for duplicates
    for attrib in package.attributes:
        try:
            if (0 != len(MISP.search_index(attrib.value)["response"])):
                # It's a dupe! 
                package.attributes.remove(attrib)        
        except:
            # idk, this is just in case pymisp does a weird
            pass

    # Delete that old temporary file
    os.unlink(f.name)

    # Push the event to MISP
    # TODO: There's probably a proper method to do this rather than json_full
    # But I don't wanna read docs
    if (len(package.attributes) > 0):
        MISP.add_event(package._json_full())

# Make TAXII call our push function whenever it gets new data
CONTENT_BLOCK_CREATED.connect(post_stix)
