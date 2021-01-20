# docker image for mlnx syncd

DOCKER_SYNCD_PLATFORM_CODE = mlnx
include $(PLATFORM_PATH)/../template/docker-syncd-base.mk

$(DOCKER_SYNCD_BASE)_DEPENDS += $(SYNCD) $(PYTHON_SDK_API)

$(DOCKER_SYNCD_BASE)_DBG_DEPENDS += $(SYNCD_DBG) \
                                $(LIBSWSSCOMMON_DBG) \
                                $(LIBSAIMETADATA_DBG) \
                                $(LIBSAIREDIS_DBG)

ifeq ($(SDK_FROM_SRC), y)
$(DOCKER_SYNCD_BASE)_DBG_DEPENDS += $(MLNX_SDK_DBG_DEBS) $(MLNX_SAI_DBGSYM)
endif

$(DOCKER_SYNCD_BASE)_VERSION = 1.0.0
$(DOCKER_SYNCD_BASE)_PACKAGE_NAME = syncd

$(DOCKER_SYNCD_BASE)_RUN_OPT += -v /host/warmboot:/var/warmboot
$(DOCKER_SYNCD_BASE)_RUN_OPT += -v /var/log/mellanox/sniffer:/var/log/mellanox/sniffer:rw
$(DOCKER_SYNCD_BASE)_RUN_OPT += -v mlnx_sdk_socket:/var/run/sx_sdk
$(DOCKER_SYNCD_BASE)_RUN_OPT += -v mlnx_sdk_ready:/tmp
$(DOCKER_SYNCD_BASE)_RUN_OPT += -v /dev/shm:/dev/shm:rw
$(DOCKER_SYNCD_BASE)_RUN_OPT += -e SX_API_SOCKET_FILE=/var/run/sx_sdk/sx_api.sock

$(DOCKER_SYNCD_BASE)_BASE_IMAGE_FILES += monit_syncd:/etc/monit/conf.d
