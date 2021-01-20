# docker image for mlnx saiserver

DOCKER_SAISERVER_MLNX = docker-saiserver-mlnx.gz
$(DOCKER_SAISERVER_MLNX)_PATH = $(PLATFORM_PATH)/docker-saiserver-mlnx
$(DOCKER_SAISERVER_MLNX)_DEPENDS += $(SAISERVER) $(PYTHON_SDK_API)
$(DOCKER_SAISERVER_MLNX)_PYTHON_DEBS += $(MLNX_SFPD)
$(DOCKER_SAISERVER_MLNX)_LOAD_DOCKERS += $(DOCKER_CONFIG_ENGINE_STRETCH)
SONIC_DOCKER_IMAGES += $(DOCKER_SAISERVER_MLNX)
SONIC_STRETCH_DOCKERS += $(DOCKER_SAISERVER_MLNX)

$(DOCKER_SAISERVER_MLNX)_CONTAINER_NAME = saiserver
$(DOCKER_SAISERVER_MLNX)_RUN_OPT += --net=host --privileged -t
$(DOCKER_SAISERVER_MLNX)_RUN_OPT += -v /var/log/mellanox/sniffer:/var/log/mellanox/sniffer:rw
$(DOCKER_SAISERVER_MLNX)_RUN_OPT += -v mlnx_sdk_socket:/var/run/sx_sdk
$(DOCKER_SAISERVER_MLNX)_RUN_OPT += -v mlnx_sdk_ready:/tmp
$(DOCKER_SAISERVER_MLNX)_RUN_OPT += -v /dev/shm:/dev/shm:rw
$(DOCKER_SAISERVER_MLNX)_RUN_OPT += -e SX_API_SOCKET_FILE=/var/run/sx_sdk/sx_api.sock
$(DOCKER_SAISERVER_MLNX)_RUN_OPT += -v /host/machine.conf:/etc/machine.conf
$(DOCKER_SAISERVER_MLNX)_RUN_OPT += -v /etc/sonic:/etc/sonic:ro
$(DOCKER_SYNCD_BASE)_RUN_OPT += --tmpfs /run/criu
