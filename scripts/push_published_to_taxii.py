import os
import zmq
import sys
import json
import pymisp
from pyaml import yaml

if "MISP_TAXII_CONFIG" in os.environ:
    config = yaml.parse(open(os.environ["MISP_TAXII_CONFIG"], "r"))
else:
    config = { "taxii" : { "host" : "127.0.0.1", "port" : 9000, "inbox" : "inbox" },
               "zmq"   : { "host" : "127.0.0.1", "port" : 50000 }
             }

context = zmq.Context()
socket = context.socket(zmq.SUB)

print("Subscribing to tcp://{}:{}".format(
                                    config["zmq"]["host"],
                                    config["zmq"]["port"]
                                    ))

socket.connect("tcp://{}:{}".format(
                                    config["zmq"]["host"],
                                    config["zmq"]["port"]
                                    ))

socket.setsockopt_string(zmq.SUBSCRIBE, '')

while True:
    message = socket.recv().decode("utf-8")[10:]
    msg = json.loads(message)
    ev = pymisp.mispevent.MISPEvent()
    ev.load(msg)
    print(ev.attributes)
