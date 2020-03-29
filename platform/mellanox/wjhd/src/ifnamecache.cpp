#include "ifnamecache.h"

std::string IfNameCache::tryGetIfName(int ifIndex)
{
    return swss::LinkCache::getInstance().ifindexToName(ifIndex);
}
