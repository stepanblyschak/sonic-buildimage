BRCM_SAI = libsaibcm_3.3.4.3m-1_amd64.deb
$(BRCM_SAI)_URL = "https://sonicstorage.blob.core.windows.net/packages/bcmsai/3.3/libsaibcm_3.3.4.3m-1_amd64.deb?sv=2015-04-05&sr=b&sig=QVWchl9egDtXKD1GEN5Yfq6DW6sGloANWK1QRmpNTrg%3D&se=2032-10-03T16%3A36%3A10Z&sp=r"

BRCM_SAI_DEV = libsaibcm-dev_3.3.4.3m-1_amd64.deb
$(eval $(call add_derived_package,$(BRCM_SAI),$(BRCM_SAI_DEV)))
$(BRCM_SAI_DEV)_URL = "https://sonicstorage.blob.core.windows.net/packages/bcmsai/3.3/libsaibcm-dev_3.3.4.3m-1_amd64.deb?sv=2015-04-05&sr=b&sig=7WsBGMgJUmElOR%2FCjLUVumNpH8K9A2vCH5P3v%2FDVhIg%3D&se=2032-10-03T16%3A36%3A35Z&sp=r"

SONIC_ONLINE_DEBS += $(BRCM_SAI)
$(BRCM_SAI_DEV)_DEPENDS += $(BRCM_SAI)
