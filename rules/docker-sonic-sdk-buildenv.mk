# SONiC SDK Docker Image

DOCKER_SONIC_SDK_BUILDENV_STEM = sonic-sdk-buildenv
DOCKER_SONIC_SDK_BUILDENV = $(DOCKER_SONIC_SDK_BUILDENV_STEM).gz

$(DOCKER_SONIC_SDK_BUILDENV)_PATH = $(DOCKERS_PATH)/docker-sonic-sdk-buildenv

$(DOCKER_SONIC_SDK_BUILDENV)_DEPENDS += $(LIBSAIVS) \
                                        $(LIBSAIVS_DEV) \
                                        $(LIBSAIVS_DBG) \
                                        $(LIBSAIREDIS_DEV) \
                                        $(LIBSAIMETADATA_DEV) \
                                        $(LIBSWSSCOMMON_DEV) \
                                        $(LIBHIREDIS_DEV) \
                                        $(LIBNL3_DEV) \
                                        $(LIBNL_GENL3_DEV) \
                                        $(LIBNL_ROUTE3_DEV) \
                                        $(LIBNL_NF3_DEV) \
                                        $(LIBNL_CLI_DEV)

$(DOCKER_SONIC_SDK_BUILDENV)_LOAD_DOCKERS += $(DOCKER_SONIC_SDK_DBG)

SONIC_DOCKER_IMAGES += $(DOCKER_SONIC_SDK_BUILDENV)
