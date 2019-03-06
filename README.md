# MISP Taxii Server

![Build Status ](https://travis-ci.org/MISP/MISP-Taxii-Server.svg?branch=master)
[![Code Health](https://landscape.io/github/MISP/MISP-Taxii-Server/master/landscape.svg?style=flat)](https://landscape.io/github/MISP/MISP-Taxii-Server/master)

A set of configuration files to use with EclecticIQ's OpenTAXII implementation,
along with a callback for when data is sent to the TAXII Server's inbox.

## Installation


### Manual install

```bash
git clone https://github.com/MISP/MISP-Taxii-Server
cd MISP-Taxii-Server

apt-get install libmysqlclient-dev # for mysql_config
pip3 install -r REQUIREMENTS.txt
```

You'll then need to set up your TAXII database. As you're using MISP, you'll likely
already have a MySQL environment running. 

```bash
mysql -u [database user] -p
# Enter Database password
mysql> create database taxiiauth;
mysql> create database taxiipersist;
mysql> grant all on taxiiauth.* to 'taxii'@'%' identified by 'some_password';
mysql> grant all on taxiipersist.* to 'taxii'@'%' identified by 'some_password';
mysql> exit;
```

Now configure your TAXII server

```bash
cp config/config.default.yaml config/config.yaml
```

Now, with that data, copy `config/config.default.yaml` over to `config/config.yaml` and open it. Edit the `db_connection` parameters to match your environment. Change `auth_api -> parameters -> secret` whilst you're here as well.

Do not forget to set your MISP server's URL and API key at the bottom.

If you wish, you can edit the taxii service definitions and collections in 
`config/data-configuration.yaml`; full documentation on how this is set up is available at [OpenTaxii's docs](https://opentaxii.readthedocs.io/en/stable/configuration.html).

Now it's time to create all your SQL tables. Luckily OpenTaxii comes with commands for this.

You're going to want to export your configuration file to a variable as well.
```bash
# An example of this config is in the config directory
export OPENTAXII_CONFIG=/path/to/config.yaml
export PYTHONPATH=.

opentaxii-sync-data config/data-configuration.yaml
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
taxii-push --path http://localhost:9000/services/inbox -f tests/test.xml \
           --dest my_collection --username admin --password admin
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

## Troubleshooting

### Data truncated for column...

```python 
Warning: (1265, "Data truncated for column 'original_message' at row 1")

Warning: (1265, "Data truncated for column 'content' at row 1")
```

If you encounter the error above, this means you tried to push a STIX file bigger than 65,535 bytes. To fix it run the following commands.
```bash
mysql -u [database user] -p
# Enter Database password

mysql> use taxiipersist;
mysql> alter table `inbox_messages` modify `original_message` LONGTEXT;
mysql> alter table `content_blocks` modify `content` LONGTEXT;
mysql> exit;
```

### Specified key was too long

```python 
Warning: (1071, 'Specified key was too long; max key length is 767 bytes')
```

If you encounter the error above, try the following after creating the databases as per [this issue](https://github.com/MISP/MISP-Taxii-Server/issues/3#issuecomment-291875813):

```SQL
ALTER DATABASE taxiipersist CHARACTER SET latin1 COLLATE latin1_general_ci;
ALTER DATABASE taxiiauth CHARACTER SET latin1 COLLATE latin1_general_ci;
```

### Nothing appears in MISP

Take note of the user you did `export OPENTAXII_CONFIG=/path/to/config.yaml` with. If you `sudo`, this env will be lost. Use `sudo -E` to preserve env instead.

### InsecureRequestWarning

PyMISP complains about missing certificate verification. Under the misp-options in  `config.yaml` do not simply set `verifySSL = False`. You can provide the CA bundle, a concatenation of all certificates in the chain, as `verifySSL = /path/to/ca_bundle`. Alternatively, you can `export REQUESTS_CA_BUNDLE=/path/to/ca_bundle`.

## Verifying the database

To verify that the `opentaxii-sync-data` worked, check the tables of database `taxiipersist`:

```
MariaDB [taxiipersist]> show tables;
+-----------------------------+
| Tables_in_taxiipersist      |
+-----------------------------+
| collection_to_content_block |
| content_blocks              |
| data_collections            |
| inbox_messages              |
| result_sets                 |
| service_to_collection       |
| services                    |
| subscriptions               |
+-----------------------------+
```

To verify whether the account-creation worked, check database `taxiiauth`:
```
MariaDB [taxiiauth]> select * from accounts;
+----+----------+-----------------------------------------------------------------------------------------------+
| id | username | password_hash                                                                                 |
+----+----------+-----------------------------------------------------------------------------------------------+
|  1 | ltaxii   | pbkdf2:sha256:50000$99999999$1111111111111111111111111111111111111111111111111111111111111111 |
+----+----------+-----------------------------------------------------------------------------------------------+
```

### Ambigious Polling Service

In the case that the server you want to poll has multiple `POLL` services,
run

```bash
taxii-discovery \
  --host <HOST TO POLL>
  --port <POLLING PORT>
  --discovery <DISCOVERY PATH, sometimes /taxii-discovery-service, may vary>
```

It'll show you the services available on the server. You'll *probably*
see two POLL services, for different version of TAXII (message binding)

Find the one relevent to you, copy its `Service Address`,
and modify `~/.misptaxii/remote-servers.yml` to resemble

```yaml
- name: "my server"
  taxii_version: "1.1"
  ...
  uri: <SERVICE ADDRESS>
```

now try polling again
