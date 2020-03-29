# docker image for Mellanox What-Just-Happened container

DOCKER_WJH_STEM = docker-wjh
DOCKER_WJH = $(DOCKER_WJH_STEM).gz
DOCKER_WJH_DBG = $(DOCKER_WJH_STEM)-$(DBG_IMAGE_MARK).gz

$(DOCKER_WJH)_PATH = $(PLATFORM_PATH)/docker-wjh
$(DOCKER_WJH)_FILES += $(SUPERVISOR_PROC_EXIT_LISTENER_SCRIPT)
$(DOCKER_WJH)_LOAD_DOCKERS += $(DOCKER_CONFIG_ENGINE_STRETCH)
$(DOCKER_WJH)_DBG_DEPENDS += $($(DOCKER_CONFIG_ENGINE_STRETCH)_DBG_DEPENDS)
$(DOCKER_WJH)_DBG_IMAGE_PACKAGES = $($(DOCKER_CONFIG_ENGINE_STRETCH)_DBG_IMAGE_PACKAGES)
$(DOCKER_WJH)_DEPENDS += $(WJH_LIBS) $(MLNX_SDK_RDEBS) $(WJHD)

SONIC_DOCKER_IMAGES += $(DOCKER_WJH)
SONIC_STRETCH_DOCKERS += $(DOCKER_WJH)
SONIC_DOCKER_DBG_IMAGES += $(DOCKER_WJH_DBG)
SONIC_STRETCH_DBG_DOCKERS += $(DOCKER_WJH_DBG)
SONIC_INSTALL_DOCKER_IMAGES += $(DOCKER_WJH)
SONIC_INSTALL_DOCKER_DBG_IMAGES += $(DOCKER_WJH)

$(DOCKER_WJH)_CONTAINER_NAME = what-just-happened
$(DOCKER_WJH)_RUN_OPT += -t
$(DOCKER_WJH)_RUN_OPT += --privileged
$(DOCKER_WJH)_RUN_OPT += --net=host # host network namespace is required for WJH_INGRESS_INFO_TYPE_IF_INDEX ingress_info_type
$(DOCKER_WJH)_RUN_OPT += -v /host/machine.conf:/etc/machine.conf
$(DOCKER_WJH)_RUN_OPT += -v /etc/sonic:/etc/sonic:ro
$(DOCKER_WJH)_RUN_OPT += -v /var/run/wjh:/var/run/wjh
$(DOCKER_WJH)_RUN_OPT += --mount type=bind,source=/sys/kernel/debug/,target=/sys/kernel/debug/
$(DOCKER_WJH)_RUN_OPT += -v /dev/shm:/dev/shm:rw
$(DOCKER_WJH)_RUN_OPT += -v mlnx_sdk_socket:/var/run/sx_sdk
$(DOCKER_WJH)_RUN_OPT += -e SX_API_SOCKET_FILE=/var/run/sx_sdk/sx_api.sock
$(DOCKER_WJH)_RUN_OPT += -v /var/log/mellanox:/var/log/mellanox:rw
