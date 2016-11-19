#!/usr/bin/env python

import subprocess
import glob

def test_push():
    for fname in glob.glob("*.xml"):
        proc = subprocess.Popen([
                        "taxii-push", 
                        "--path", "http://127.0.0.1:9000/services/inbox", 
                        "-f", fname, 
                        "--dest", "collection", 
                        "--username", "travis", 
                        "--password", "travis"
                    ],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )

        out,err = proc.communicate()
        assert("Content block successfully pushed" in err.decode("utf-8"))
