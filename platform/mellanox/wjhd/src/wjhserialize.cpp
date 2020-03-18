#include "wjhserialize.h"
#include <tins/tins.h>

static void serializeWjhDropGroup(wjh_drop_reason_group_e group, nlohmann::json& js)
{
    js["group"] = WjhChannel::dropGroupToString(group);
}

static void serializeWjhSeverity(wjh_severity_e severity, nlohmann::json& js)
{
    const std::map<wjh_severity_e, std::string> severityToString = {
        {WJH_SEVERITY_NOTICE_E, "Notice"},
        {WJH_SEVERITY_WARNING_E, "Warning"},
        {WJH_SEVERITY_ERROR_E, "Error"},

    };

    auto it = severityToString.find(severity);
    if (it == severityToString.cend())
    {
        return;
    }

    js["severity"] = it->second;
}


static void serializeWjhDropReason(wjh_drop_reason_t reason, nlohmann::json& js)
{
    std::stringstream ss;
    if (reason.reason)
    {
        ss << reason.reason;
    }
    if (reason.reason && reason.description)
    {
        ss << " - " << reason.description;
    }
    js["reason"] = ss.str();
}


static void serializeTimetamp(timespec time, nlohmann::json& js)
{
    double timestamp = time.tv_sec + time.tv_nsec / static_cast<double>(1000000000);
    js["timestamp"] = timestamp;
}


static void serializePacketFields(const ByteVector& packet, nlohmann::json& js)
{
    Tins::EthernetII eth;
    try
    {
        eth = Tins::EthernetII(packet.data(), packet.size());
    }
    catch (Tins::malformed_packet)
    {
        // malformed packet, don't know how to parse fields from packet correctly
        // just return, skipping serializing packets
        return;
    }

    js["smac"] = eth.src_addr().to_string();
    js["dmac"] = eth.dst_addr().to_string();
    js["ethtype"] = static_cast<int>(eth.payload_type());
    auto dot1QHeader = eth.find_pdu<Tins::Dot1Q>();
    if (dot1QHeader)
    {
        js["vlan"] = static_cast<int>(dot1QHeader->id());
    }
    auto ipHeader = eth.find_pdu<Tins::IP>();
    auto ip6Header = eth.find_pdu<Tins::IPv6>();
    Tins::TCP* tcpHeader{nullptr};
    Tins::UDP* udpHeader{nullptr};
    if (ipHeader)
    {
        js["sip"] = ipHeader->src_addr().to_string();
        js["dip"] = ipHeader->dst_addr().to_string();
        js["ipproto"] = static_cast<int>(ipHeader->protocol());
        tcpHeader = ipHeader->find_pdu<Tins::TCP>();
        udpHeader = ipHeader->find_pdu<Tins::UDP>();
    }
    else if (ip6Header)
    {
        js["sip"] = ip6Header->src_addr().to_string();
        js["dip"] = ip6Header->dst_addr().to_string();
        js["ipproto"] = static_cast<int>(ip6Header->next_header());
        tcpHeader = ip6Header->find_pdu<Tins::TCP>();
        udpHeader = ip6Header->find_pdu<Tins::UDP>();
    }
    else
    {
        return;
    }

    auto fromL4Header = [&](auto l4Header) -> void
    {
        js["sl4port"] = static_cast<int>(l4Header->sport());
        js["dl4port"] = static_cast<int>(l4Header->dport());
    };

    if (tcpHeader)
    {
        fromL4Header(tcpHeader);
    }
    else if (udpHeader)
    {
        fromL4Header(udpHeader);
    }
    else
    {
        // neither of them, just skip filling entries
    }
}

static void serializeIngressPort(const std::string& ifname, nlohmann::json& js)
{
    if (!ifname.empty())
    {
        js["sport"] = ifname;
    }
}

static void serializeWjhRawEvent(const WjhRawEvent& event, nlohmann::json& js)
{
    serializePacketFields(event.packet, js);
    serializeTimetamp(event.timestamp, js);
    serializeIngressPort(event.ingressPort, js);
    serializeWjhDropGroup(event.dropGroup, js);
    serializeWjhSeverity(event.dropReason.severity, js);
    serializeWjhDropReason(event.dropReason, js);
}


void serializeWjhRawEvents(const RawEventVectorT& events, nlohmann::json& js)
{
    for (const auto& event: events)
    {
        nlohmann::json serializedEvent;
        serializeWjhRawEvent(event, serializedEvent);
        js.push_back(serializedEvent);
    }
}

