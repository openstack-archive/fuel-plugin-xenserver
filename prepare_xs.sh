#!/bin/bash

set +x

host="$1"
name="$2"
eth0="$3"
eth1="$4"
memory="$5"
disksize="$6"

cmd="~/add_node.sh \"$name\" \"$eth0\" \"$eth1\" $memory $disksize"

scp add_node.sh root@$host:~
ssh root@$host "$cmd"
ssh root@$host "rm ~/add_node -f"
