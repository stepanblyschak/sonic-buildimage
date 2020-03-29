#include "wjhtypes.h"

#include <swss/converter.h>
#include <algorithm>
#include <sstream>
#include <map>

static const std::map<DropGroupT, std::string> gDropGroupToStringMap =
{
    {WJH_DROP_REASON_GROUP_L1_E,     "L1"},
    {WJH_DROP_REASON_GROUP_L2_E,     "L2"},
    {WJH_DROP_REASON_GROUP_ROUTER_E, "L3"},
    {WJH_DROP_REASON_GROUP_BUFFER_E, "BUFFER"},
    {WJH_DROP_REASON_GROUP_TUNNEL_E, "TUNNEL"},
    {WJH_DROP_REASON_GROUP_ACL_E,    "ACL"},
};

static const std::map<SeverityT, std::string> gSeverityToStringMap =
{
    {WJH_SEVERITY_NOTICE_E,     "Notice"},
    {WJH_SEVERITY_WARNING_E,    "Warn"},
    {WJH_SEVERITY_ERROR_E,      "Error"}
};


std::string dropGroupToString(DropGroupT group)
{
    auto result = gDropGroupToStringMap.find(group);
    if (result == gDropGroupToStringMap.cend())
    {
        return std::string();
    }
    return result->second;
}

DropGroupT stringToDropGroup(std::string groupString)
{
    auto result = std::find_if(std::begin(gDropGroupToStringMap), std::end(gDropGroupToStringMap),
        [groupString](auto groupAndName){
            return swss::to_upper(groupString) == groupAndName.second;
        }
    );
    if (result == gDropGroupToStringMap.cend())
    {
        std::stringstream errstream;
        errstream << "Invalid drop reason group " << groupString;
        throw std::invalid_argument(errstream.str());
    }
    return result->first;
}

std::string severityToString(SeverityT severity)
{
    auto result = gSeverityToStringMap.find(severity);
    if (result == gSeverityToStringMap.cend())
    {
        return std::string();
    }
    return result->second;
}
