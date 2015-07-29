#!/bin/sh

VM_NAMES="$@"

for VM_NAME in $VM_NAMES
do
	xe vm-cd-insert uuid=$(xe vm-list name-label="$VM_NAME") cd-name="xs-tools.iso"
done
