#!/usr/bin/env python3

import pymisp

from opentaxii.signals import (
    CONTENT_BLOCK_CREATED, INBOX_MESSAGE_CREATED
)

## CONFIG

CONFIG = {
            "MISP_URL" : "localhost",
            "MISP_API" : "DEADBEEF",
        }

MISP = pymisp.PyMISP( 
                        config["MISP_URL"],
                        config["MISP_API"],
                )

def post_stix(manager, content_block, collection_ids, service_id):
    print("Content: {}".format(content_block.content))

CONTENT_BLOCK_CREATED.connect(post_stix)
