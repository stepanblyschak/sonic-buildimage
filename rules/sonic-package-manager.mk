# sonic package manager python package

SONIC_PACKAGE_MANAGER_PY3 = sonic_package_manager-1.0-py3-none-any.whl
$(SONIC_PACKAGE_MANAGER_PY3)_SRC_PATH = $(SRC_PATH)/sonic-package-manager/
$(SONIC_PACKAGE_MANAGER_PY3)_PYTHON_VERSION = 3
$(SONIC_PACKAGE_MANAGER_PY3)_DEPENDS += $(SONIC_PY_COMMON_PY3) \
                                        $(SWSSSDK_PY3) # Temporary dependency till issue with py-swsscommon is resolved
$(SONIC_PACKAGE_MANAGER_PY3)_DEBS_DEPENDS += $(PYTHON3_SWSSCOMMON)
SONIC_PYTHON_WHEELS += $(SONIC_PACKAGE_MANAGER_PY3)

