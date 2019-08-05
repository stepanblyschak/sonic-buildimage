.ONESHELL:
SHELL = /bin/bash

MAIN_TARGET = sx-kernel_1.mlnx.$(MLNX_SDK_DEB_VERSION)_amd64.deb
DERIVED_TARGETS = sx-kernel-dev_1.mlnx.$(MLNX_SDK_DEB_VERSION)_amd64.deb
PACKAGE_NAME = sx_kernel

$(addprefix $(DEST)/, $(MAIN_TARGET)): $(DEST)/% :
	# build
	pushd Switch-SDK-drivers
	git stash
	patch -p1 < ../sx_kernel_makefile_sonic_build.patch

	debuild -e KVERSION=$(KVERSION) -e KSRC_EXT=/lib/modules/$(KVERSION)/source/ -b -us -uc -j$(SONIC_CONFIG_MAKE_JOBS)

	popd

	mv $(DERIVED_TARGETS) $* $(DEST)/

$(addprefix $(DEST)/, $(DERIVED_TARGETS)): $(DEST)/% : $(DEST)/$(MAIN_TARGET)
