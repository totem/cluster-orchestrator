# cluster-orchestrator [![Build Status](https://travis-ci.org/totem/cluster-orchestrator.svg)](https://travis-ci.org/totem/cluster-orchestrator) [![Coverage Status](https://img.shields.io/coveralls/totem/cluster-orchestrator.svg)](https://coveralls.io/r/totem/cluster-orchestrator) [![Documentation Status](https://readthedocs.org/projects/cluster-orchestrator/badge/?version=latest)](https://readthedocs.org/projects/cluster-orchestrator/?badge=latest)[![](https://badge.imagelayers.io/totem/cluster-orchestrator.svg)](https://imagelayers.io/?images=totem/cluster-orchestrator:develop 'Get your own badge on imagelayers.io')

Provides orchestration for continuous deployment to Totem Cluster. 

## Development Status
This project is ready to be used in production.

## Documentation
Project uses Sphinx for code/api documentation.

### Location
The latest code/api documentation can be found at:
[http://cluster-orchestrator.readthedocs.org/](http://cluster-orchestrator.readthedocs.org/)

### Building documentation
To generate html documentation, use command: 

```
cd docs && make html
```

The documentation will be generated in docs/build folder.

## Requirements

The project has following dependencies  
- python 2.7.x or 3.4.x 
- Virtualenv (Recommended)
- Python pip
- etcd 0.4.6
- docker 1.7+ (Required if using docker based deployment)

### Dependencies

To install dependencies for the project, run command:  

```
pip install -r requirements.txt
```

In addition if you are developing on the project, run command: 

```
pip install -r dev-requirements.txt
```

## Testing

Tests are located in tests folder. Project uses nose for testing.

### Unit Tests

To run all unit tests , run command :

```
nosetests -w tests/unit
```

## Running Server

### Local
To run the server locally , run command:

```
python local-server.py
```

To run celery locally, run command:

```
python local-celery.py
```

Once server is up you can access the root api using:  
[http://localhost:9400](http://localhost:9400)

### Using Docker

In order to run fully integrated server using docker using latest docker , run
command: 

```
sudo docker run -it --rm -h cluster-orchestrator-${USER} --name cluster-orchestrator -v /dev/log:/dev/log -P totem/cluster-orchestrator
```

### Run Configuration (Environment Variables)  
| Env Variable | Description |  Default Value (Local) | Default Value (Docker)|
| ------------ | ----------- | ---------------------- | --------------------- |
| QUAY_ORGANIZATION | Organization in quay to pull images from | totem | totem|
| HOST_IP | HOST IP address | 127.0.0.1 | Determined using default route in routing table|
| ETCD_HOST | Etcd server host. | 127.0.0.1 | ${HOST_IP} |
| ETCD_PORT | Etcd server port. | 4001 | 4001 |
| ETCD_TOTEM_BASE | Base path for totem configurations | /totem | /totem |
| API_EXECUTORS | No. of uwsgi processes to be created for serving API | Not Used | 2 |
| FLASK_DEBUG | Reloadable flask flag (true/false) | false | Not Used |
| HOOK_SECRET | The secret to be used for web hooks | changeit | changeit |
| HIPCHAT_TOKEN | Default hipchat token to be used for notifications | | |
| GITHUB_TOKEN | Github token for fetching fleet templates and for commit notifications.| | |
| HIPCHAT_ENABLED | Set it to true to enable hipchat notifications | false | false |
| HIPCHAT_ROOM | Room to be used for hipchat notifications | not-set | not-set |
| GITHUB_NOTIFICATION_ENABLED | Set it to true to enable github commit notifications. | false | false |
| CLUSTER_NAME | Name of the cluster where orchestrator is deployed | local | local |
| TOTEM_ENV | Name of totem environment (e.g. production, local, development) | local | local |
| LOG_IDENTIFIER | Program name/tag used for syslog | N/A | yoda-proxy |
 

## Coding Standards and Guidelines

### flake8
In order to ensure that code follows PEP8 standards, run command: 

```
flake8 .
```
