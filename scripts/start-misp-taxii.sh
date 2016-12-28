#!/bin/bash

if [ -z $OPENTAXII_CONFIG ]
    then
        echo "Warning : Variable OPENTAXII_CONFIG not set!";
fi

if [ -z $MISP_TAXII_CONFIG] 
    then
        echo "Warning: Variable MISP_TAXII_CONFIG not set!";
fi


echo "Running taxii..."
opentaxii-run-dev 
