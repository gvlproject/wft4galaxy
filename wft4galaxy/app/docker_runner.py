#!/usr/bin/env python
from __future__ import print_function

import os as _os
import sys as _sys
import json as _json
import logging as _logging
import argparse as _argparse
import subprocess as _subprocess

# configure logger
_logFormat = "%(asctime)s [wft4galaxy-docker] [%(levelname)-5.5s]  %(message)s"
_logging.basicConfig(format=_logFormat)
_logger = _logging.getLogger("wft4galaxy-docker")
_logger.setLevel(_logging.INFO)

# try to load modules required for running container interactively
try:
    import docker as _docker
    import dockerpty as _dockerpty
except ImportError:
    _logger.debug("Packages 'docker' and 'dockerpty' are not available")

# Exit codes
_SUCCESS_EXIT = 0
_FAILURE_EXIT = -1

# Jupyter port
DEFAULT_JUPYTER_PORT = 9876

# try to load wft4galaxy.properties
_properties = None
try:
    import wft4galaxy as _wft4galaxy

    with open(_os.path.join(_os.path.dirname(_wft4galaxy.__file__), "wft4galaxy.properties")) as fp:
        _properties = _json.load(fp)
        _logger.debug("wft4galaxy.properties: %r", _properties)
except:
    _logger.debug("No wft4galaxy.properties found! Use default settings!")

# Docker image settings
DOCKER_IMAGE_SETTINGS = {
    "registry": None,
    "repository": _properties["Docker"]["repository"] \
        if _properties is not None and "Docker" in _properties and "repository" in _properties["Docker"] else "crs4",
    "tag": _properties["Docker"]["tag"] \
        if _properties is not None and "Docker" in _properties and "tag" in _properties["Docker"] else "develop",
    "production": "wft4galaxy-minimal",
    "develop": "wft4galaxy-develop",
    "supported_os": ["alpine", "ubuntu"]
}

# Docker container settings
DOCKER_CONTAINER_SETTINGS = {
    "modes": ("production", "develop"),
    "entrypoints": {
        "runtest": ("runtest", 'Execute the "wft4galaxy" tool as entrypoint', DOCKER_IMAGE_SETTINGS["production"]),
        "bash": ("bash", 'Execute the "Bash" shell as entrypoint', DOCKER_IMAGE_SETTINGS["develop"]),
        "ipython": ("ipython", 'Execute the "Ipython" shell as entrypoint', DOCKER_IMAGE_SETTINGS["develop"]),
        "jupyter": ("jupyter", 'Execute the "Jupyter" server as entrypoint', DOCKER_IMAGE_SETTINGS["develop"])
    }
}
# WorkflowTest configuration defaults
DEFAULT_HISTORY_NAME_PREFIX = "_WorkflowTestHistory_"
DEFAULT_WORKFLOW_NAME_PREFIX = "_WorkflowTest_"
DEFAULT_OUTPUT_FOLDER = "results"
DEFAULT_CONFIG_FILENAME = "workflow-test-suite.yml"
DEFAULT_WORKFLOW_CONFIG = {
    "file": "workflow.ga",
    "output_folder": DEFAULT_OUTPUT_FOLDER,
    "inputs": {
        "Input Dataset": {"name": "Input Dataset", "file": ["input"]}
    },
    "expected": {
        "output1": {"file": "expected_output", "comparator": "filecmp.cmp", "name": "output1"},
        "output2": {"file": "expected_output", "comparator": "filecmp.cmp", "name": "output2"}
    }
}


class _CommandLineHelper:
    def __init__(self, omit_subparsers=False):
        self._parser, self._entrypoint_parsers = self.setup(omit_subparsers)

    def setup(self, omit_subparsers=False):
        main_parser = _argparse.ArgumentParser(add_help=True, formatter_class=_argparse.RawTextHelpFormatter)
        main_parser.add_argument('--registry', help='Alternative Docker registry', default=None)
        main_parser.add_argument('--repository', default=None,
                                 help='Alternative Docker repository \n'
                                      'containing the "wft4galaxy" Docker image')
        main_parser.add_argument('--image', help='Alternative "wft4galaxy" Docker image <NAME:TAG>', default=None)
        main_parser.add_argument('--os', choices=DOCKER_IMAGE_SETTINGS["supported_os"],
                                 help='Base OS of the Docker image (default: "{0}"). \n'
                                      'Ignored when the "--image" option is specified.'
                                 .format(DOCKER_IMAGE_SETTINGS["supported_os"][0]),
                                 default=DOCKER_IMAGE_SETTINGS["supported_os"][0])
        main_parser.add_argument('--local', action="store_true", default=False,
                                 help='Force to use the local version '
                                      'of the required Docker image')
        main_parser.add_argument('--server', help='Galaxy server URL', default=None)
        main_parser.add_argument('--api-key', help='Galaxy server API KEY', default=None)
        main_parser.add_argument('-p', '--port', help='Docker port to expose', action="append", default=[])
        main_parser.add_argument('-v', '--volume', help='Docker volume to mount', type=str, action="append", default=[])
        main_parser.add_argument('--debug', help='Enable debug mode', action='store_true')

        # reference to the global options
        epilog = "NOTICE: Type \"{0} -h\" to see the global options.".format(main_parser.prog)

        # add entrypoint subparsers
        entrypoint_parsers = None
        if omit_subparsers:
            main_parser.add_argument('--entrypoint', help='Absolute path of a log file.', default="runtest")
        else:
            entrypoint_parsers = {}
            entrypoint_subparsers_factory = \
                main_parser.add_subparsers(title="Container entrypoint", dest="entrypoint",
                                           description="Available entrypoints for the 'wft4galaxy' Docker image.",
                                           help="Choose one of the following options:")
            for ep_name, ep_help, ep_image in DOCKER_CONTAINER_SETTINGS["entrypoints"].values():
                entrypoint_parsers[ep_name] = \
                    entrypoint_subparsers_factory.add_parser(ep_name, help=ep_help, epilog=epilog)

            # add bash options
            entrypoint_parsers["bash"].add_argument("cmd", nargs="*", help="BASH commands")

            # add jupyter options
            entrypoint_parsers["jupyter"].add_argument("--web-port", default=DEFAULT_JUPYTER_PORT, type=int,
                                                       help="Jupyter port (default is {0})".format(
                                                           DEFAULT_JUPYTER_PORT))

        # add wft4galaxy options to a subparser or directly to the main_parser
        wft4g_parser = main_parser if omit_subparsers else entrypoint_parsers["runtest"]
        wft4g_parser.add_argument("-f", "--file",
                                  default=DEFAULT_CONFIG_FILENAME,
                                  help="YAML configuration file of workflow tests (default is \"{0}\")"
                                  .format(DEFAULT_CONFIG_FILENAME))
        wft4g_parser.add_argument("-o", "--output", metavar="output",
                                  default=DEFAULT_OUTPUT_FOLDER,
                                  help="Absolute path of the output folder (default is \"{0}\")"
                                  .format(DEFAULT_OUTPUT_FOLDER))
        wft4g_parser.add_argument('--enable-logger', help='Enable log messages', action='store_true')
        wft4g_parser.add_argument('--disable-cleanup', help='Disable cleanup', action='store_true')
        wft4g_parser.add_argument('--disable-assertions', help='Disable assertions', action='store_true')
        wft4g_parser.add_argument("test", help="Workflow Test Name", nargs="*")

        return main_parser, entrypoint_parsers

    def parse_args(self):
        args = self._parser.parse_args()
        # add port Jupyter web port
        if "web_port" in args:
            args.port.append("8888:{0}".format(args.web_port))
        _logger.debug("Parsed arguments %r", args)
        return args

    def print_usage(self):
        self._parser.print_usage()

    def print_help(self):
        self._parser.print_help()


class ContainerRunner:
    @staticmethod
    def run(options):
        if options.entrypoint == "runtest":
            return NonInteractiveContainer().run(options)
        else:
            return InteractiveContainer().run(options)


class Container():
    def get_image_name(self, options, pull_latest=True):
        img_name_parts = []
        # base default config
        config = DOCKER_CONTAINER_SETTINGS["entrypoints"][options.entrypoint]
        # set registry
        if options.registry is not None:
            img_name_parts.append(options.registry)
        elif DOCKER_IMAGE_SETTINGS["registry"]:
            img_name_parts.append(DOCKER_IMAGE_SETTINGS["registry"])
        # set repository
        if options.repository:
            img_name_parts.append(options.repository)
        else:
            img_name_parts.append(DOCKER_IMAGE_SETTINGS["repository"])
        # set image name
        if options.image:
            img_name_parts.append(options.image)
        else:
            repo_ref = "develop"
            if _properties is not None and "Repository" in _properties:
                repo_tag = _properties["Repository"]["tag"] if "tag" in _properties["Repository"] else None
                repo_branch = _properties["Repository"]["branch"] \
                    if "branch" in _properties["Repository"] else "develop"
                repo_ref = repo_tag if repo_tag is not None else repo_branch
            image_tag = "{0}-{1}".format(options.os or "alpine", repo_ref)
            img_name_parts.append("{0}:{1}".format(config[2], image_tag))
        docker_image_name = "/".join(img_name_parts)
        _logger.debug("Using Docker image: %s", docker_image_name)

        if pull_latest:
            _logger.info("Updating Docker imge '{0}'".format(docker_image_name))
            p = _subprocess.Popen(["docker", "pull", docker_image_name], shell=False, close_fds=False)
            try:
                p.communicate()
            except KeyboardInterrupt:
                print("\n")
                _logger.warn("Pull of Docker image %s interrupted by user", docker_image_name)
        else:
            _logger.info("Using the local version of the Docker image '{0}'".format(docker_image_name))

        return docker_image_name


class InteractiveContainer(Container):
    def _parse_volumes(self, volumes):
        result = {}
        if volumes:
            for v_str in volumes:
                v_info = v_str.split(":")
                if len(v_info) != 2:
                    raise ValueError(
                        "Invalid volume parameter '{0}'. See 'docker run' syntax for more details.".format(v_str))
                result[v_info[0]] = {"bind": v_info[1]}
        return result

    def _parse_ports(self, ports):
        result = {}
        if ports:
            for p_str in ports:
                p_info = p_str.split(":")
                if len(p_info) == 1:
                    result[p_info[0]] = None
                elif len(p_info) == 2:
                    result[p_info[0]] = p_info[1]
                else:
                    raise ValueError(
                        "Invalid port parameter '{0}'. See 'docker run' syntax for more details.".format(p_str))
        return result

    def run(self, options):
        """

        :param options: 
        :return: 
        """
        if options.entrypoint == "runtest":
            raise ValueError("You cannot use the entrypoint 'runtest' in interactive mode!")
        try:

            # prepare the Docker image (updating it if required)
            docker_image = self.get_image_name(options, not options.local)

            # volumes
            volumes = self._parse_volumes(options.volume)

            # ports
            ports = self._parse_ports(options.port)

            # environment
            environment = ["GALAXY_URL={0}".format(options.server),
                           "GALAXY_API_KEY={0}".format(options.api_key)]

            # command
            command = [
                options.entrypoint,
                "--server", options.server,
                "--api-key", options.api_key
            ]

            # create and run Docker containers
            client = _docker.APIClient()
            container = client.create_container(
                image=docker_image,
                stdin_open=True,
                tty=True,
                command=command,
                environment=environment,
                volumes=volumes,
                ports=list(ports.keys()),
                host_config=client.create_host_config(port_bindings=ports)
            )
            _logger.info("Started Docker container %s", container["Id"])
            _dockerpty.start(client, container)
            client.remove_container(container["Id"])
            _logger.info("Removed Docker container %s", container["Id"])
            return _SUCCESS_EXIT
        except NameError as ne:
            if options and options.debug:
                _logger.exception(ne)
            print("\n ERROR: To use wft4galaxy-docker in development mode "
                  "you need to install 'docker' and 'dockerpty' Python libries \n"
                  "\tType \"pip install docker dockerpty\" to install the required libraries.\n")
            return _FAILURE_EXIT
        except Exception as e:
            _logger.error("ERROR: Unable to start the Docker container: {0}".format(str(e)))
            if options and options.debug:
                _logger.exception(e)
            return _FAILURE_EXIT


class NonInteractiveContainer(Container):
    def run(self, options):
        """

        :param options: 
        :return: 
        """
        ## extract folder of the configuration file
        options.volume.append(_os.path.abspath(_os.path.dirname(options.file)) + ":/data_input")
        options.volume.append(_os.path.abspath(_os.path.dirname(options.output)) + ":/data_output")

        # prepare the Docker image (updating it if required)
        docker_image = self.get_image_name(options, not options.local)

        ########################################################
        # build docker cmd
        ########################################################
        # main command
        cmd = ['docker', 'run', '-i', '--rm']
        # add Docker volumes
        for v in options.volume:
            cmd += ["-v", v]
        # add Docker ports
        for p in options.port:
            cmd += ["-p", p]
        # Galaxy environment variables
        cmd.extend(["-e", "GALAXY_URL={0}".format(options.server)])
        cmd.extend(["-e", "GALAXY_API_KEY={0}".format(options.api_key)])
        # image
        cmd.append(docker_image)
        # entrypoint
        cmd.append("wft4galaxy")
        # enable logger option
        if options.enable_logger:
            cmd.append("--enable-logger")
        # log debug option
        if options.debug:
            cmd.append("--debug")
        # Galaxy settings server (redundant)
        cmd += ["--server ", options.server]
        cmd += ["--api-key ", options.api_key]
        # configuration file
        cmd += ["-f", "/data_input/" + _os.path.basename(options.file)]
        # output folder
        cmd += ["-o", options.output]
        # cleanup option
        if options.disable_cleanup:
            cmd.append("--disable-cleanup")
        # assertion option
        if options.disable_assertions:
            cmd.append("--disable-assertions")

        # add test filter
        cmd += options.test

        # output the Docker command (just for debugging)
        _logger.debug("Command parts: %r", cmd)
        _logger.debug("Command string: %s", ' '.join(cmd))
        #########################################################

        # launch the Docker container
        p = _subprocess.Popen(cmd, stdout=_subprocess.PIPE)
        try:
            # wait for termination and report the exit code
            return p.wait()
        except KeyboardInterrupt:
            p.kill()
            _logger.warn("wft4galaxy terminated by user")
            return _FAILURE_EXIT


def _set_galaxy_env(options):
    ENV_KEY_GALAXY_URL = "GALAXY_URL"
    if options.server is None:
        if ENV_KEY_GALAXY_URL in _os.environ:
            options.server = _os.environ[ENV_KEY_GALAXY_URL]
        else:
            raise ValueError("Galaxy URL not defined! "
                             "Use --server or the environment variable {}.\n".format(ENV_KEY_GALAXY_URL))
    ENV_KEY_GALAXY_API_KEY = "GALAXY_API_KEY"
    if options.api_key is None:
        if ENV_KEY_GALAXY_API_KEY in _os.environ:
            options.api_key = _os.environ[ENV_KEY_GALAXY_API_KEY]
        else:
            raise ValueError("Galaxy API key not defined! "
                             "Use --api-key or the environment variable {}.\n".format(ENV_KEY_GALAXY_API_KEY))


def main():
    options = None
    try:
        # arguments set
        args = set(_sys.argv[1:])

        # check if we need to print help
        print_help = len(args & set(["-h", "--help"])) != 0

        # check at list one entrypoint is specified
        # if not, it is assumed to be "runtest"
        omit_subparsers = len(args & set(DOCKER_CONTAINER_SETTINGS["entrypoints"])) == 0 and not print_help

        # initialize the CLI helper
        p = _CommandLineHelper(omit_subparsers=omit_subparsers)

        # print help and exit
        if print_help:
            p.print_help()
            _sys.exit(_SUCCESS_EXIT)

        # parse cli options/arguments
        options = p.parse_args()
        _logger.debug("Command line options %r", options)

        # update logger
        if options.debug:
            _logger.setLevel(_logging.DEBUG)

        # set galaxy_env
        _set_galaxy_env(options)

        # log Python version
        _logger.debug("Python version: %s", _sys.version)

        # run container
        ctr = ContainerRunner()
        exit_code = ctr.run(options)
        _logger.debug("Docker container terminated with %d exit code", exit_code)

        # report the Docker container exit code
        _sys.exit(exit_code)

    except Exception as e:
        _logger.error("ERROR: {0}".format(str(e)))
        if options and options.debug:
            _logger.exception(e)
        _sys.exit(_FAILURE_EXIT)


if __name__ == '__main__':
    main()
