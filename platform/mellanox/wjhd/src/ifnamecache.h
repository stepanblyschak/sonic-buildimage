#pragma once

#include <swss/linkcache.h>

#include <map>
#include <string>

class InterfaceNameCacheIf
{
public:
    virtual ~InterfaceNameCacheIf() = default;
    // Get the interface name from interface index or return empty string when
    // not found.
    virtual std::string tryGetIfName(int ifIndex) = 0;
};

// Interface index to interface name mapping cache
class IfNameCache : public InterfaceNameCacheIf
{
public:
    ~IfNameCache() override = default;
    std::string tryGetIfName(int ifIndex) override;
};
