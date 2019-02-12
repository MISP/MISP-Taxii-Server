from setuptools import setup

setup(
    name="misp_taxii_hooks",
    description="A little package just to install hooks to PYTHONPATH",
    version="0.2",
    author="Hannah Ward",
    author_email="hannah.ward2@baesystems.com",
    packages=['misp_taxii_hooks'],
    scripts=["scripts/start-misp-taxii.sh",
             "scripts/push_published_to_taxii.py",
             "scripts/install-remote-server.sh",
             "scripts/run-taxii-poll.py"]
)
