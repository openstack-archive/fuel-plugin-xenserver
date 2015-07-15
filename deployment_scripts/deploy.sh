#!/bin/bash

dockerctl copy newrelease.yaml nailgun:/tmp/newrelease.yaml
dockerctl shell nailgun manage.py loaddata /tmp/newrelease.yaml