# docker image for teamd agent

DOCKER_TEAMD_STEM = docker-teamd
DOCKER_TEAMD = $(DOCKER_TEAMD_STEM).gz
DOCKER_TEAMD_DBG = $(DOCKER_TEAMD_STEM)-$(DBG_IMAGE_MARK).gz

$(DOCKER_TEAMD)_PATH = $(DOCKERS_PATH)/$(DOCKER_TEAMD_STEM)

$(DOCKER_TEAMD)_DEPENDS += $(SWSS) $(LIBTEAMDCTL) $(LIBTEAM_UTILS)
$(DOCKER_TEAMD)_DBG_DEPENDS = $($(DOCKER_CONFIG_ENGINE_BUSTER)_DBG_DEPENDS)
$(DOCKER_TEAMD)_DBG_DEPENDS += $(SWSS_DBG) $(LIBSWSSCOMMON_DBG)
$(DOCKER_TEAMD)_DBG_DEPENDS += $(LIBTEAMDCTL_DBG) $(LIBTEAM_UTILS_DBG)

$(DOCKER_TEAMD)_DBG_IMAGE_PACKAGES = $($(DOCKER_CONFIG_ENGINE_BUSTER)_DBG_IMAGE_PACKAGES)

$(DOCKER_TEAMD)_LOAD_DOCKERS += $(DOCKER_CONFIG_ENGINE_BUSTER)

$(DOCKER_TEAMD)_VERSION = 1.0.0
$(DOCKER_TEAMD)_PACKAGE_NAME = teamd

SONIC_DOCKER_IMAGES += $(DOCKER_TEAMD)
SONIC_INSTALL_DOCKER_IMAGES += $(DOCKER_TEAMD)

SONIC_DOCKER_DBG_IMAGES += $(DOCKER_TEAMD_DBG)
SONIC_INSTALL_DOCKER_DBG_IMAGES += $(DOCKER_TEAMD_DBG)

$(DOCKER_TEAMD)_CONTAINER_NAME = teamd
$(DOCKER_TEAMD)_RUN_OPT += --privileged -t
$(DOCKER_TEAMD)_RUN_OPT += --tmpfs /tmp
$(DOCKER_TEAMD)_RUN_OPT += --tmpfs /var/tmp
$(DOCKER_TEAMD)_RUN_OPT += -v /etc/sonic:/etc/sonic:ro
$(DOCKER_TEAMD)_RUN_OPT += -v /host/warmboot:/var/warmboot

$(DOCKER_TEAMD)_BASE_IMAGE_FILES += teamdctl:/usr/bin/teamdctl
$(DOCKER_TEAMD)_BASE_IMAGE_FILES += monit_teamd:/etc/monit/conf.d
$(DOCKER_TEAMD)_FILES += $(SUPERVISOR_PROC_EXIT_LISTENER_SCRIPT)
