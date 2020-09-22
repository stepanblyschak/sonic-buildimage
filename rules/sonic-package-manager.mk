# sonic utilities package
#

SONIC_PACKAGE_MANAGER = python-sonic-package-manager_1.0-1_all.deb
$(SONIC_PACKAGE_MANAGER)_SRC_PATH = $(SRC_PATH)/sonic-package-manager
$(SONIC_PACKAGE_MANAGER)_WHEEL_DEPENDS = $(SONIC_PY_COMMON_PY2) \
                                         $(SONIC_PY_COMMON_PY3) \
                                         $(SONIC_CONFIG_ENGINE)

SONIC_PYTHON_STDEB_DEBS += $(SONIC_PACKAGE_MANAGER)
