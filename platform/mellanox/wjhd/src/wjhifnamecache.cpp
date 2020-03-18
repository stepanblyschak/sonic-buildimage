#include "wjhifnamecache.h"

#include <errno.h>
#include <cstring>
#include <swss/logger.h>

void WjhIfNameCache::refresh()
{
    ifnamecache.clear();

    struct if_nameindex *if_ni, *iface;

    if_ni = if_nameindex();
    if (!if_ni)
    {
        SWSS_LOG_THROW("Failed to refresh interface name cache, %s",
                strerror(errno));
    }

    for (iface = if_ni; !(iface->if_index == 0 && iface->if_name == nullptr); ++iface)
    {
        ifnamecache.insert(std::make_pair(iface->if_index, iface->if_name));
    }

    if_freenameindex(if_ni);
}

std::string WjhIfNameCache::getIfNameOrEmptyString(unsigned int if_index)
{
    auto it = ifnamecache.find(if_index);
    if (it == ifnamecache.end())
    {
        return std::string{};
    }
    return it->second;
}

std::map<unsigned int, std::string> WjhIfNameCache::ifnamecache;
