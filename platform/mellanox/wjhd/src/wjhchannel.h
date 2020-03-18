#pragma once

#include "wjhifnamecache.h"

#include <string>
#include <ctime>
#include <vector>
#include <set>

#include <iostream>

extern "C"
{
#include <wjh/wjh_lib.h>
}

using ByteVector = std::vector<unsigned char>;

struct WjhRawEvent
{
    ByteVector              packet;      // raw packet
    timespec                timestamp;   // timestamp of the drop
    std::string             ingressPort; // SONiC ingress port linux name
    wjh_drop_reason_group_e dropGroup;
    wjh_drop_reason_t       dropReason;
};

using RawEventVectorT = std::vector<WjhRawEvent>;

// Represent SONiC What-Just-Happened channel
class WjhChannel
{
public:
    using Type = wjh_user_channel_type_e;
    using DropGroup = wjh_drop_reason_group_e;

    // Create a channel from name and type.
    // Channel created in WJH library is done in a seperate
    // method call.
    WjhChannel(std::string name, Type type = WJH_USER_CHANNEL_CYCLIC_E);
    WjhChannel(const WjhChannel&) = delete;
    WjhChannel& operator=(const WjhChannel&) = delete;
    ~WjhChannel();

    bool create();
    bool setDropGroupReason(DropGroup group);
    bool deleteDropGroupReason(DropGroup group);
    bool destroy();
    bool pull();
    const RawEventVectorT& getRawCache() const;
    void clearRawCache();

    static std::string dropGroupToString(DropGroup);
    static bool stringToDropGroup(std::string, DropGroup&);
private:
    std::string m_name;
    wjh_user_channel_id_t m_id {WJH_USER_CHANNEL_ID_INVALID};
    Type m_type;
    // list of drop reason groups associated with this channel
    std::set<DropGroup> m_dropReasonGroups;
    RawEventVectorT m_rawCache;
private:
    static WjhChannel* pullingChannel;
    // Callback for WJH raw events
    template<DropGroup Group, typename RawInfoT>
    static wjh_status_t rawCallback(RawInfoT* rawInfoList, std::uint32_t* rawInfoListSize)
    {
        if (!WjhChannel::pullingChannel)
        {
            return WJH_STATUS_SUCCESS;
        }
        for (auto i = 0; i < *rawInfoListSize; ++i)
        {
            auto& rawinfo = rawInfoList[i];
            WjhRawEvent event{};
            event.packet = ByteVector{static_cast<unsigned char*>(rawinfo.packet),
                static_cast<unsigned char*>(rawinfo.packet) + rawinfo.packet_size};
            event.ingressPort = WjhIfNameCache::getIfNameOrEmptyString(rawinfo.ingress_port);
            event.timestamp = rawinfo.timestamp;
            event.dropGroup = Group;
            event.dropReason = rawinfo.drop_reason;
            WjhChannel::pullingChannel->m_rawCache.push_back(event);
        }
        return WJH_STATUS_SUCCESS;
    }
};
