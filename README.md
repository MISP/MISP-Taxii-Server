# MISP Taxii Server

![Build Status ](https://travis-ci.org/MISP/MISP-Taxii-Server.svg?branch=master)
[![Code Health](https://landscape.io/github/MISP/MISP-Taxii-Server/master/landscape.svg?style=flat)](https://landscape.io/github/MISP/MISP-Taxii-Server/master)

A set of configuration files to use with EclecticIQ's OpenTAXII implementation,
along with a callback for when data is sent to the TAXII Server's inbox.

## Installation

Download the repository with
```bash
git clone --recursive https://github.com/MISP/MISP-Taxii-Server
```

This will also download the OpenTAXII Server, which you should install with
```bash
# There's some weird bug wherein pip can't parge >=1.1.111
sudo pip3 install libtaxii==1.1.111
cd OpenTAXII
sudo python3 setup.py install
```

You'll then need to set up your TAXII database. As you're using MISP, you'll likely
already have a MySQL environment running. 

Run the following commands to create your databases
```bash
mysql -u [database user] -p
# Enter Database password

mysql> create database taxiiauth;

mysql> create database taxiipersist;

mysql> grant all on taxiiauth.* to 'taxii'@'%' identified by 'some_password';

mysql> grant all on taxiipersist.* to 'taxii'@'%' identified by 'some_password';

mysql> exit;
```

Now, with that data edit `config.yaml`, and edit the `db_connection` parameters to match
your environment. Change `auth_api -> parameters -> secret` whilst you're here as well.
Do not forget to set your MISP server's URL and API key at the bottom.

If you wish, you can edit the taxii service definitions in `services.yaml`, 
or the collections to be created in `collections.yaml`; full documentation on how this is set up is available at [OpenTaxii's docs](https://opentaxii.readthedocs.io/en/stable/configuration.html).

Now it's time to create all your SQL tables. Luckily OpenTaxii comes with commands for this.

You're going to want to export your configuration file to a variable as well.
```bash
# Install mysqlclient for python3 if you haven't already done so
apt-get install libmysqlclient-dev # for mysql_config
pip3 install mysqlclient

# An example of this config is in the config directory
export OPENTAXII_CONFIG=/path/to/config.yaml
export PYTHONPATH=.

opentaxii-create-services -c config/services.yaml
opentaxii-create-collections -c config/collections.yaml

# Create a user account
# Set the username and password to whatever you want
opentaxii-create-account -u root -p root
```

OpenTaxii is now ready to roll, we've just gotta do one more thing.

In the repository root directory, run 
```bash
sudo python3 setup.py install
```

This will install the TAXII hooks to run when we have new data.

Now we should be ready to go!

```bash
opentaxii-run-dev
```

This should tell you that there is now a server running on `localhost:9000` (maybe a different port if you changed it). If there are no errors, you're good!

If you want to test everything is working, run
```bash
taxii-push --path http://localhost:9000/services/inbox -f stix_sample.xml \
           --dest collection --username root --password root
```

Obviously replace anything that differs in your system. 

The client should say "Content Block Pushed Successfully" if all went well.

Now you have a TAXII server hooked up to MISP, you're able to send STIX files to the inbox and have them uploaded directly to MISP. So that's nice <3

There is also an experimental feature to push MISP events to the TAXII server when they're published - that's in `scripts/push_published_to_taxii.py`. It seems to work, but may occasionally re-upload duplicate events to MISP.

## Automated TAXII -> MISP Sync

If you want, there is the ability to synchronise between a remote TAXII server and the local MISP server.

```bash
$ install-remote-server.sh

[MISP-TAXII-SERVER]
POLLING SERVER INSTALLATION
FRIENDLY SERVER NAME:
< Add a unique server name here, can be anything >
```

This will then install 2 files to `~/.misptaxii`, one for a local server and one for the remote servers.
Edit these files as needed. Run `install-remote-server.sh` once for each remote server you want to add.

You'll probably want to put the sync script on a crontab,

First, run

```bash
echo `which python3` `which run-taxii-poll.py`
```

to get the path of your script, copy it. Then 

```bash
crontab -e
```

This will open your crontab. Paste in

```cron
0 */6 * * * <the output of that echo command you just ran>
```

This will run the polling script every 6 hours to keep things all synced up.

## Planned features

- Duplicate Detection
