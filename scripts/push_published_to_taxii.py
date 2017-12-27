import os
import zmq
import sys
import json
import pymisp
import warnings
from pyaml import yaml
from cabby import create_client
from misp_stix_converter.converters import lint_roller
import logging

# Set up logger
logging.basicConfig(level=logging.INFO, format="'%(asctime)s - %(name)s - %(levelname)s - %(message)s')")
log = logging.getLogger(__name__)

# Try to load in config
if "OPENTAXII_CONFIG" in os.environ:
    config = yaml.load(open(os.environ["OPENTAXII_CONFIG"], "r"))
else:
    config = { "domain" : "127.0.0.1:9000" ,
               "zmq"   : { "host" : "127.0.0.1", "port" : 50000 }
             }

# Set up our ZMQ socket to recieve MISP JSON on publish
context = zmq.Context()
socket = context.socket(zmq.SUB)

log.info("Subscribing to tcp://{}:{}".format(
                                    config["zmq"]["host"],
                                    config["zmq"]["port"]
                                    ))

# Connect to the socket
socket.connect("tcp://{}:{}".format(
                                    config["zmq"]["host"],
                                    config["zmq"]["port"]
                                    ))
# Set the option to subscribe
socket.setsockopt_string(zmq.SUBSCRIBE, '')

# Connct to TAXII as well
cli = create_client(discovery_path="{}://{}/services/discovery".format(config.get("protocol", "http"), config["domain"]))
cli.set_auth(username = config["taxii"]["auth"]["username"], 
             password = config["taxii"]["auth"]["password"]
            )
if not config.get("verify_ssl", True):
    cli.verify_ssl = False

while True:
    # Wait for something to come in on the ZMQ socket
    message = socket.recv().decode("utf-8")
    log.info("Recieved a message!")
    topic = message.split(' ', 1)[0]

    if topic != 'misp_json':
      log.info("Ignoring " + topic + "...")
      continue

    # Process the JSON payload
    log.debug("Processing...")
    payload = message[len(topic)+1:]

    # Load the message JSON
    msg = json.loads(payload)

    log.debug(msg)

    # Load it as a misp object for easy conversion to STIX
    ev = pymisp.mispevent.MISPEvent()
    ev.load(msg)

    # Convert to STIX
    pkg = pymisp.tools.stix.make_stix_package(ev)
    
    log.debug("Loaded successfully!")
    
    # Push the package to TAXII
    for version in config.get("stix_versions", ["1.1.1"]):
        # Convert to that version 
        objs = lint_roller.lintRoll(pkg)
        for i in objs:
            # Set the object's version
            if hasattr(i, "version"):
                i.version = version

        # Set the top-level
        pkg.version = version

        try:
            log.info("Using binding %s", "urn:stix.mitre.org:xml:{}".format(version))
            cli.push(content=pkg.to_xml().decode("utf-8"), 
                     content_binding="urn:stix.mitre.org:xml:{}".format(version), 
                     uri="{}://{}/services/inbox".format(config.get("protocol", "http"), 
                                                         config["domain"]),
                     collection_names=config["taxii"].get("collections", ["collection"]))

            log.info("Pushed! (%s)", version)     
            
        except Exception as ex:
            log.fatal("COULD NOT PUSH")
            log.exception(ex)
