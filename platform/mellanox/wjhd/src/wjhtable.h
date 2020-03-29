#pragma once

#include "wjhtypes.h"
#include "netdb.h"
#include "ifnamecache.h"

#include <fort.hpp>

class WjhRawTable
{
public:
    WjhRawTable(NetDBIf& netdb, InterfaceNameCacheIf& ifcache);
    void addEntry(const WjhRawEvent&);
    std::string toString() const;
private:
    NetDBIf& netdb;
    InterfaceNameCacheIf& ifcache;
    fort::char_table table{};
    size_t count{0};
};

