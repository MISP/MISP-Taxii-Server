#!/usr/bin/env python3

######
# TODO: DETECT DUPLICATE DATA
#####

import os
import pymisp
import tempfile
import logging
import datetime
import time
import base64
import json
from pymisp.abstract import MISPEncode
from misp_stix_converter.converters import convert
from misp_stix_converter.converters import buildMISPAttribute
from pyaml import yaml
from io import StringIO

log = logging.getLogger("__main__")

from opentaxii.signals import (
    CONTENT_BLOCK_CREATED, INBOX_MESSAGE_CREATED
)

## CONFIG
if "OPENTAXII_CONFIG" in os.environ:
    log.info("Using config from {}".format(os.environ["OPENTAXII_CONFIG"]))
    CONFIG =  yaml.load(open(os.environ["OPENTAXII_CONFIG"], "r"))
else:
    log.info("Trying to use env variables...")
    if "MISP_URL" in os.environ:
        misp_url = os.environ["MISP_URL"]
    else:
        log.info("Unkown misp URL. Set OPENTAXII_CONFIG or MISP_URL.")
        misp_url = "UNKNOWN"
    if "MISP_API" in os.environ:
        misp_api = os.environ["MISP_API"]
    else:
        log.info("Unknown misp API key. Set OPENTAXII_CONFIG or MISP_API.")
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
                        ssl = CONFIG["misp"].get("verifySSL", False)
                )

def mytimestamp():
    return datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d_%H:%M:%S')

def sanitizer(s):
    return s.strip(' \t\n\r')


def detect_tlp(package):
    
    handling = {}
    
    if hasattr(package, "stix_header"):
        if hasattr(package.stix_header, "handling"):
             
            for markingitem in package.stix_header.handling:

                if hasattr(markingitem, "controlled_structure"):
                    
                    handling["marking"] = markingitem.controlled_structure
                    
                    for itemcolor in markingitem.marking_structures:
                        if hasattr(itemcolor, "color"):
                            handling["color"] = itemcolor.color
        else:
            log.info("NO Handling found in this package")
    else:
        log.info("No Header found in this package")

    return handling
    
    
def detect_source(package):
    
    source = False
    
    if hasattr(package, "stix_header"):
        if hasattr(package.stix_header, "information_source"):
            if hasattr(package.stix_header.information_source.identity, "name"):
                source = package.stix_header.information_source.identity.name
    
    return source


def detect_title(package):
    '''
    Return a list 
    - event tile + attachment filename
    - 1 for detectable event (and possible event update), 0 for undetectable event 
    '''
    timestamp = mytimestamp()

    if hasattr(package, "stix_header"):
        if hasattr(package.stix_header, "title"):
            return package.stix_header.title, 1

        elif hasattr(package.stix_header, "description"):
            return package.stix_header.description, 1
        else:
            return "STIX_FILE_NO_TITLE_" + timestamp, 0
    else:
        return "STIX_FILE_NO_TITLE_" + timestamp, 0

def searchEvent(search):
    result = MISP.search("events", values=str(sanitizer(search)))
    
    if result["response"] == []:
        # New event
        return 0
    else:
        # Maybe an update
        # Check if a stix file named with `title`.xml exists
        event = result["response"][0]["Event"]["Attribute"][0]["event_id"]
        filename = search + ".xml"
        attachment = MISP.search("events", values=str(filename), type_attribute="attachment", eventid=event)
        
        if attachment["response"] == []:
            # New event
            return 0
        else:
            # Event to update
            return event

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

    package = convert.load_stix(StringIO(block))
    # Building event obj
    distribution=3
    threat_level_id=2
    analysis=0
    
    misp_event = buildMISPAttribute.buildEvent(package, distribution=distribution, threat_level_id=threat_level_id, analysis=analysis)
    log.info("STIX loaded succesfully. Let's go!")

    evaluatePackage = detect_title(package)
    tlp = detect_tlp(package)
    source = detect_source(package)
    
    title = evaluatePackage[0]
    detectable = evaluatePackage[1]
    
    if detectable == 1:
    
        search = searchEvent(title)

        if search == 0 :
            # New Event!
            b64Pkg = base64.b64encode(package.to_xml()).decode("utf-8")

            if misp_event.attributes:
                filename = title + ".xml"
                misp_event.add_attribute(type="attachment", value=filename, data=b64Pkg)
                
                if tlp:
                    misp_event.add_tag("tlp:"+tlp['color'])
                    misp_event.add_tag("Marking_Controlled_Structure:"+tlp['marking'])
                    
                if source:
                    misp_event.add_tag("source:"+source)
                
                response = MISP.add_event(json.dumps(misp_event, cls=MISPEncode))

                if response.get('errors'):
                    raise Exception("PACKAGE: {}\nERROR: {}".format(json.dumps(misp_event, cls=MISPEncode),response.get('errors')))
                
                else:
                    MISP.fast_publish(response["Event"]["id"])
            else:
                log.info("No attributes detected")
        else:
            myeventid = search
            
            # Just the library default!
            # Edit if you need
            distribution=3
            threat_level_id=2
            analysis=0
            buildattribute = buildMISPAttribute.buildEvent(package, distribution=distribution, threat_level_id=threat_level_id, analysis=analysis)
            
            items = [x for x in buildattribute.attributes]
            
            for attrib in items:

                searchatt = MISP.search("attributes", values=str(sanitizer(attrib.value)), type_attribute=str(attrib.type), eventid=myeventid)

                if searchatt["response"] != []:
                    log.info("%s is a duplicate, we'll ignore it.", attrib.value)
                    buildattribute.attributes.pop([x.value for x in buildattribute.attributes].index(attrib.value))
                else:
                    log.info("%s is unique, we'll keep it", attrib.value)
            
            if (len(buildattribute.attributes) > 0 ):
                b64Pkg = base64.b64encode(package.to_xml()).decode("utf-8")
                updatetimestamp = mytimestamp()
                filename = title + "_" + updatetimestamp + ".xml"
                misp_event.add_attribute(type="attachment", value=filename, data=b64Pkg)
                
                if tlp:
                    misp_event.add_tag("tlp:"+tlp['color'])
                    misp_event.add_tag("Marking_Controlled_Structure:"+tlp['marking'])
                    
                if source:
                    misp_event.add_tag("source:"+source)
                
                MISP.update_event(myeventid,json.dumps(misp_event, cls=MISPEncode))
                MISP.fast_publish(myeventid)
                log.info("Updating event: " +myeventid)
            else:
                log.info("Nothing to update for event: "+ myeventid)
    else:
        log.info("Event undetectable. Will be used old style import!")
        values = [x.value for x in misp_event.attributes]
        log.info("Extracted %s", values)
        
        for attrib in values:
            log.info("Checking for existence of %s", attrib)
            search = MISP.search("attributes", values=str(sanitizer(attrib)))
            
            if search["response"] != []:
                # This means we have it!
                log.info("%s is a duplicate, we'll ignore it.", attrib)
                misp_event.attributes.pop([x.value for x in misp_event.attributes].index(attrib))
            else:
                log.info("%s is unique, we'll keep it", attrib)

                # Push the event to MISP
                # TODO: There's probably a proper method to do this rather than json_full
                # But I don't wanna read docs
                if (len(misp_event.attributes) > 0):
                    log.info("Uploading event to MISP with attributes %s", [x.value for x in misp_event.attributes])
                    MISP.add_event(misp_event)
                else:
                    log.info("No attributes, not bothering.")

# Make TAXII call our push function whenever it gets new data
CONTENT_BLOCK_CREATED.connect(post_stix)

