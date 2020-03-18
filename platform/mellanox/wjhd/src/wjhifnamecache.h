#pragma once

#include <net/if.h>

#include <string>
#include <map>


// Interface index to interface name mapping cache
class WjhIfNameCache
{
public:
    // Refresh the if_index -> if_name mapping cache.
    // In case of dymanic port breakout interfaces might
    // be removed and new interfaces might be added.
    static void refresh();

    // Get the interface name from interface index or return empty string when
    // not found.
    static std::string getIfNameOrEmptyString(unsigned int);

private:
    static std::map<unsigned int, std::string> ifnamecache;
};
