#!/usr/bin/env python3

import pymisp

from opentaxii.signals import (
    CONTENT_BLOCK_CREATED, INBOX_MESSAGE_CREATED
)

## CONFIG

def post_stix(manager, content_block, collection_ids, service_id):
    CONFIG = {
                "MISP_URL" : "localhost",
                "MISP_API" : "DEADBEEF",
            }

    MISP = pymisp.PyMISP( 
                            CONFIG["MISP_URL"],
                            CONFIG["MISP_API"],
                    )

    with open("/tmp/test.txt", "w") as f:
        f.write("connect!")
    print("Content: {}".format(content_block.content))

CONTENT_BLOCK_CREATED.connect(post_stix)
