FROM debian:buster-slim
EXPOSE 9000

RUN apt-get update && \
    apt-get -y install python3 python3-pip git build-essential default-libmysqlclient-dev

RUN git clone --recursive https://github.com/MISP/MISP-Taxii-Server

RUN pip3 install libtaxii==1.1.111  mysqlclient gunicorn

WORKDIR /MISP-Taxii-Server/OpenTAXII
RUN python3 setup.py install

WORKDIR /MISP-Taxii-Server
RUN python3 setup.py install

RUN export OPENTAXII_CONFIG=/MISP-Taxii-Server/config.yaml && export PYTHONPATH=.
RUN opentaxii-create-services -c config/services.yaml && opentaxii-create-collections -c config/collections.yaml

ADD ./docker-run.sh /run.sh

CMD /bin/sh /run.sh
