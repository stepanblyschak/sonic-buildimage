#pragma once

#include <vector>
#include <string>
#include <time.h>

extern "C"
{
#include <wjh/wjh_lib.h>
}

struct WjhRawEvent;

using ChannelTypeT    = wjh_user_channel_type_e;
using DropGroupT      = wjh_drop_reason_group_e;
using SeverityT       = wjh_severity_e;
using DropReasonT     = wjh_drop_reason_t;
using ByteVectorT     = std::vector<unsigned char>;
using RawEventVectorT = std::vector<WjhRawEvent>;

// Single raw event struct combining fields
// from different drop groups.
struct WjhRawEvent
{
    ByteVectorT             packet;      // raw packet
    timespec                timestamp;   // timestamp of the drop
    int                     ingressPort; // SONiC ingress Linux interface ifindex
    DropGroupT              dropGroup;
    DropReasonT             dropReason;
};

std::string dropGroupToString(DropGroupT);
DropGroupT stringToDropGroup(std::string);
std::string severityToString(SeverityT);
