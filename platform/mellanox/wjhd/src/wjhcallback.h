#pragma once

#include "wjhtypes.h"
#include "wjhchannel.h"

#include <cassert>

class WjhCallback
{
    // L1 specialization
    template<DropGroupT Group = WJH_DROP_REASON_GROUP_L1_E,
        typename RawInfoT = wjh_L1_drop_raw_info>
    static void rawCallbackSingle(WjhRawEvent& event, const wjh_L1_drop_raw_info& rawinfo)
    {
        event.ingressPort = rawinfo.ingress_port;
        event.timestamp = rawinfo.timestamp;
        event.dropGroup = Group;
    }

    template<DropGroupT Group, typename RawInfoT>
    static void rawCallbackSingle(WjhRawEvent& event, const RawInfoT& rawinfo)
    {
        event.ingressPort = rawinfo.ingress_port;
        event.timestamp = rawinfo.timestamp;
        event.packet = ByteVectorT{
            static_cast<unsigned char*>(rawinfo.packet),
            static_cast<unsigned char*>(rawinfo.packet) + rawinfo.packet_size
        };
        event.ingressPort = rawinfo.ingress_port;
        event.timestamp = rawinfo.timestamp;
        event.dropGroup = Group;
        event.dropReason = rawinfo.drop_reason;
    }

    // Generic callback routine for WJH raw events.
    template<DropGroupT Group, typename RawInfoT>
    static wjh_status_t rawCallback(RawInfoT* rawInfoList, std::uint32_t* rawInfoListSize)
    {
        assert(pullingChannel != nullptr);
        for (auto i = 0; i < *rawInfoListSize; ++i)
        {
            WjhRawEvent event{};
            rawCallbackSingle<Group, RawInfoT>(event, rawInfoList[i]);
            WjhCallback::pullingChannel->m_rawCache.push_back(event);
        }
        return WJH_STATUS_SUCCESS;
    }
    static WjhChannel* pullingChannel;
    friend class WjhChannel;
};
