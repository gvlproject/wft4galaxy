# wft4galaxy: <br> Workflow Tester for Galaxy

Version: 0.1.0

## Description
**wft4galaxy** is a Python module which allows to automate the running of Galaxy workflow tests. It can be used either as local Python library or a Docker image running inside a Docker container.

## Installation

Basically, to install **wft4galaxy** as a local Python library, you need to follow the two speps below:

  1. clone the github repository:
      ```bash
      git clone https://github.com/phnmnl/wft4galaxy
      ```
  2. install the module using the usual setup script:
     ```bash
     cd wft4galaxy
     python setup.py install
     ```
> **Notice**. If you are using a Linux based system, like *Ubuntu*, you probably need to install the two libraries **`python-lxml`** and **`libyaml-dev`** as a further *prerequisite*.


Alternatively, you can use **wft4galaxy** over Docker, by simply downloading the corresponding image to your local Docker registry:

``` bash
docker pull docker-registry.phenomenal-h2020.eu/phnmnl/wft4galaxy
```

## Usage Instructions

If you have installed **wft4galaxy** as local Python library, you can launch it from your terminal:

``` bash
wft4galaxy [options]
```

For direct Docker usage:
```bash
$ docker run docker-registry.phenomenal-h2020.eu/phnmnl/wft4galaxy [options]
```

In both cases the main options are:
```bash
Options:
  -h, --help            show this help message and exit
  --server=SERVER       Galaxy server URL
  --api-key=API_KEY     Galaxy server API KEY
  --enable-logger       Enable log messages
  --debug               Enable debug mode
  --disable-cleanup     Disable cleanup
  --disable-assertions  Disable assertions
  -o OUTPUT, --output=OUTPUT
                        absolute path of the output folder
  -f FILE, --file=FILE  YAML configuration file of workflow tests
```

See [documentation](http://wft4galaxy.readthedocs.io/) for more details.
