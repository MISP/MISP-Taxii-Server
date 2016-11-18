# MISP Taxii Server

A set of configuration files to use with EclecticIQ's OpenTAXII implementation,
along with a callback for when data is sent to the TAXII Server's inbox.

## Installation

Download the repository with
```bash
git clone --recursive https://github.com/FloatingGhost/MISP-Taxii-Server
```

This will also download the OpenTAXII Server, which you should install with
```bash
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

If you wish, you can edit the taxii service definitions in `services.yaml`, 
or the collections to be created in `collections.yaml`; full documentation on how this is set up is available at [OpenTaxii's docs](https://opentaxii.readthedocs.io/en/stable/configuration.html).

Now it's time to create all your SQL tables. Luckily OpenTaxii comes with commands for this.

You're going to want to export your configuration file to a variable as well.
```bash
export OPENTAXII_CONFIG=/path/to/config.yaml

opentaxii-create-services -c services.yaml
opentaxii-create-collections -c collections.yaml

# Create a user account
# Set the username and password to whatever you want
opentaxii-create-account -u root -p root
```

OpenTaxii is now ready to roll, we've just gotta do one or two more things.

Edit `misp_taxii_hooks/hooks.py` and add your MISP server's URL and API key.

Then, in the repository root directory, run 
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

The client should say "Content Block Pushed Succesfully" if all went well.

Now you have a TAXII server hooked up to MISP, you're able to send STIX files to the inbox and have them uploaded directly to MISP. So that's nice <3

## Planned features

- Duplicate Detection
- Possible sync misp -> Taxii 
