BRANDING=branding.inc

include ${BRANDING}
OPENSTACK_RELEASE:=mitaka

PLUGIN_VERSION:=$(shell ./get_plugin_version.sh ${BRANDING} | cut -d' ' -f1)
PLUGIN_REVISION:=$(shell ./get_plugin_version.sh ${BRANDING} | cut -d' ' -f2)

RPM_NAME=${PLUGIN_NAME}-${PLUGIN_VERSION}-${PLUGIN_VERSION}.${PLUGIN_REVISION}-1.noarch.rpm
MD5_FILENAME=${PLUGIN_NAME}-${PLUGIN_VERSION}.${PLUGIN_REVISION}_md5.txt
BUILDROOT=BUILD

DOC_NAMES=user-guide ${PLUGIN_REVISION}-test-plan ${PLUGIN_REVISION}-test-report

.SUFFIXES:

build: rpm docs md5

rpm: output/${RPM_NAME}

md5: output/${MD5_FILENAME}

docs: md5 $(DOC_NAMES:%=output/${PLUGIN_NAME}-${PLUGIN_VERSION}-%.pdf)

iso: suppack/xenapi-plugins-${OPENSTACK_RELEASE}.iso

suppack/xenapi-plugins-${OPENSTACK_RELEASE}.iso: plugin_source/deployment_scripts/patchset/xenhost
	suppack/build-xenserver-suppack.sh ${OPENSTACK_RELEASE} "${HOST_PRODUCT}"

${BUILDROOT}/${PLUGIN_NAME}/branded: ${BRANDING} suppack/xenapi-plugins-${OPENSTACK_RELEASE}.iso plugin_source
	mkdir -p ${BUILDROOT}/${PLUGIN_NAME}
	cp -r plugin_source/* ${BUILDROOT}/${PLUGIN_NAME}
	find ${BUILDROOT}/${PLUGIN_NAME} -type f -print0 | \
		xargs -0 -i sed -i \
			-e s/@HYPERVISOR_NAME@/${HYPERVISOR_NAME}/g \
			-e s/@HYPERVISOR_LOWER@/${HYPERVISOR_LOWER}/g \
			-e s/@PLUGIN_NAME@/${PLUGIN_NAME}/g \
			-e s/@PLUGIN_VERSION@/${PLUGIN_VERSION}/g \
			-e s/@PLUGIN_REVISION@/${PLUGIN_REVISION}/g \
			-e s/@VERSION_HOTFIXES@/${VERSION_HOTFIXES}/g {}
	cp suppack/xenapi-plugins-*.iso ${BUILDROOT}/${PLUGIN_NAME}/deployment_scripts/
	cp suppack/conntrack-tools.iso ${BUILDROOT}/${PLUGIN_NAME}/deployment_scripts/
	touch ${BUILDROOT}/${PLUGIN_NAME}/branded

output/${RPM_NAME}: ${BUILDROOT}/${PLUGIN_NAME}/branded
	mkdir -p output
	(cd ${BUILDROOT}; which flake8 > /dev/null && flake8 ${PLUGIN_NAME}/deployment_scripts --exclude=XenAPI.py)
	(cd ${BUILDROOT}; fpb --check ${PLUGIN_NAME})
	(cd ${BUILDROOT}; fpb --build ${PLUGIN_NAME})
	cp ${BUILDROOT}/${PLUGIN_NAME}/${RPM_NAME} $@

${BUILDROOT}/doc/source ${BUILDROOT}/doc/Makefile: ${BRANDING} doc/Makefile doc/source
	mkdir -p ${BUILDROOT}/doc
	cp -r doc/Makefile doc/source ${BUILDROOT}/doc
	find ${BUILDROOT}/doc -type f -print0 | \
		xargs -0 -i sed -i \
			-e s/@HYPERVISOR_NAME@/${HYPERVISOR_NAME}/g \
			-e s/@PLUGIN_NAME@/${PLUGIN_NAME}/g \
			-e s/@PLUGIN_VERSION@/${PLUGIN_VERSION}/g \
			-e s/@PLUGIN_REVISION@/${PLUGIN_REVISION}/g \
			-e s/@PLUGIN_MD5@/`cat output/${MD5_FILENAME} | cut -d' ' -f1`/g {}

${BUILDROOT}/doc/build/latex/%.pdf: ${BUILDROOT}/doc/Makefile ${shell find ${BUILDROOT}/doc/source}
	make -C ${BUILDROOT}/doc latexpdf

output/${PLUGIN_NAME}-${PLUGIN_VERSION}-${PLUGIN_REVISION}-%.pdf: ${BUILDROOT}/doc/build/latex/%.pdf
	mkdir -p output
	cp $^ $@

output/${PLUGIN_NAME}-${PLUGIN_VERSION}-%.pdf: ${BUILDROOT}/doc/build/latex/%.pdf
	mkdir -p output
	cp $^ $@

output/${MD5_FILENAME}: output/${RPM_NAME}
	md5sum $^ > $@

clean:
	rm -rf ${BUILDROOT} output suppack/xenapi-plugins-${OPENSTACK_RELEASE}* suppack/conntrack-tools.* suppack/build
