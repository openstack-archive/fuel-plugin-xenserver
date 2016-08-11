BRANDING=branding.inc

include ${BRANDING}

RPM_NAME=${PLUGIN_NAME}-${PLUGIN_VERSION}-${PLUGIN_VERSION}.${PLUGIN_REVISION}-1.noarch.rpm
BUILDROOT=BUILD

DOC_NAMES=user-guide test-plan test-report

.SUFFIXES:

build: rpm docs

rpm: output/${RPM_NAME}

docs: $(DOC_NAMES:%=output/${PLUGIN_NAME}-${PLUGIN_VERSION}-%.pdf)

iso: plugin_source/deployment_scripts/patchset/xenhost
	suppack/build-xenserver-suppack.sh

${BUILDROOT}/${PLUGIN_NAME}: ${BRANDING} iso
	mkdir -p ${BUILDROOT}/${PLUGIN_NAME}
	cp -r plugin_source/* ${BUILDROOT}/${PLUGIN_NAME}
	find ${BUILDROOT}/${PLUGIN_NAME} -type f -print0 | \
		xargs -0 -i sed -i \
			-e s/@HYPERVISOR_NAME@/${HYPERVISOR_NAME}/g \
			-e s/@HYPERVISOR_LOWER@/${HYPERVISOR_LOWER}/g \
			-e s/@PLUGIN_NAME@/${PLUGIN_NAME}/g {} \
			-e s/@PLUGIN_VERSION@/${PLUGIN_VERSION}/g {} \
			-e s/@PLUGIN_REVISION@/${PLUGIN_REVISION}/g {}
	cp suppack/xenapi-plugins-*.iso ${BUILDROOT}/${PLUGIN_NAME}/deployment_scripts/

${BUILDROOT}/doc/source ${BUILDROOT}/doc/Makefile: ${BRANDING}
	mkdir -p ${BUILDROOT}/doc
	cp -r doc/Makefile doc/source ${BUILDROOT}/doc
	find ${BUILDROOT}/doc -type f -print0 | \
		xargs -0 -i sed -i \
			-e s/@HYPERVISOR_NAME@/${HYPERVISOR_NAME}/g \
			-e s/@PLUGIN_NAME@/${PLUGIN_NAME}/g {} \
			-e s/@PLUGIN_VERSION@/${PLUGIN_VERSION}/g {} \
			-e s/@PLUGIN_REVISION@/${PLUGIN_REVISION}/g {}

output/${RPM_NAME}: ${BUILDROOT}/${PLUGIN_NAME}
	mkdir -p output
	(cd ${BUILDROOT}; fpb --check ${PLUGIN_NAME})
	(cd ${BUILDROOT}; fpb --build ${PLUGIN_NAME})
	cp ${BUILDROOT}/${PLUGIN_NAME}/${RPM_NAME} $@

${BUILDROOT}/doc/build/latex/%.pdf: ${BUILDROOT}/doc/Makefile ${shell find ${BUILDROOT}/doc/source}
	make -C ${BUILDROOT}/doc latexpdf

output/${PLUGIN_NAME}-${PLUGIN_VERSION}-%.pdf: ${BUILDROOT}/doc/build/latex/%.pdf
	mkdir -p output
	cp $^ $@

clean:
	rm -rf ${BUILDROOT} output
