#include "wjhtable.h"

#include <iomanip>
#include <chrono>
#include <string>
#include <sstream>
#include <time.h>
#include <netdb.h>
#include <arpa/inet.h>

#include <tins/tins.h>

const auto NotAssigned              = "N/A";
const auto DropReasonColumnMaxWidth = 52;

struct WjhRawTableEntry
{
    int         index     = 0;           // table entry index (1-based)
    std::string timestamp = NotAssigned;
    std::string sPort     = NotAssigned;
    std::string dPort     = NotAssigned;
    std::string sMac      = NotAssigned;
    std::string dMac      = NotAssigned;
    std::string vlan      = NotAssigned;
    std::string ethType   = NotAssigned;
    std::string sIpPort   = NotAssigned;
    std::string dIpPort   = NotAssigned;
    std::string ipProto   = NotAssigned;
    std::string group     = NotAssigned;
    std::string severity  = NotAssigned;
    std::string reason    = NotAssigned;
};


static std::stringstream reduceLinesWidth(
        const std::string& input,
        std::size_t width)
{
    std::string temp;
    std::stringstream oss;
    std::istringstream iss(input);
    std::size_t linewidth = 0;
    while(iss >> temp)
    {
        oss << temp;
        linewidth += temp.size() + 1;
        if (linewidth >= width)
        {
            oss << std::endl;
            linewidth = 0;
        }
        else
        {
            oss << ' ';
        }
    }
    return oss;
}

// format timestamp column
// e.g: 2021/04/13 11:33:31.432
static std::string formatTimestamp(struct timespec tv)
{
    const auto TimeStringBufferSize = 30;
    char buffer[TimeStringBufferSize];
    auto nsec = std::chrono::nanoseconds(tv.tv_nsec);
    auto msec = std::chrono::duration_cast<
        std::chrono::milliseconds>(nsec);
    auto* tm = gmtime(&tv.tv_sec);
    strftime(buffer, sizeof(buffer), "%y/%m/%d %T", tm);
    std::stringstream ss;
    ss << buffer << "." << msec.count();
    return ss.str();
}

static std::string formatDropReason(const DropReasonT& reason)
{
    std::stringstream ss;
    if (!reason.reason)
    {
        return NotAssigned;
    }
    ss << reduceLinesWidth(std::string(reason.reason), DropReasonColumnMaxWidth).str();
    if (reason.description)
    {
        ss << std::endl
           << reduceLinesWidth(
                   std::string(reason.description), DropReasonColumnMaxWidth).str();
    }
    return ss.str();
}

static std::string formatEthType(std::uint16_t ethType)
{
    std::stringstream ss;
    ss << std::hex << "0x" << ethType;
    return ss.str();
}

static std::string formatIpProto(NetDBIf& netdb,
        std::uint16_t ipproto)
{
    std::string protoname;
    std::stringstream ss;
    if (!netdb.getIpProtocolName(protoname, ipproto))
    {
        ss << std::hex << "0x" << ipproto;
    }
    else
    {
        ss << protoname;
    }
    return ss.str();
}

static std::string formatIpPort(
        NetDBIf& netdb, std::string ipAddress,
        int port, uint16_t ipproto)
{
    std::stringstream ss;
    if (port != -1 && (ipAddress.find(":") != std::string::npos))
    {
        ss << "[" << ipAddress << "]";
    }
    else
    {
        ss << ipAddress;
    }
    if (port != -1)
    {
        std::string protoname;
        std::string servicename;
        ss << ":" << port;
        if (netdb.getIpProtocolName(protoname, ipproto) &&
                netdb.getServiceName(servicename, port, protoname));
        {
            ss << " (" << servicename << ")";
        }
    }
    return ss.str();
}

static void fillPacketFields(
        NetDBIf& netdb, WjhRawTableEntry& entry,
        const ByteVectorT& packet)
{
    Tins::EthernetII eth;
    std::string      sourceIpAddress;
    std::string      destIpAddress;
    int              ipproto {-1};
    int              sourceL4Port {-1};
    int              destL4Port {-1};

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

    entry.sMac    = eth.src_addr().to_string();
    entry.dMac    = eth.dst_addr().to_string();
    entry.ethType = formatEthType(eth.payload_type());

    auto dot1QHeader = eth.find_pdu<Tins::Dot1Q>();
    if (dot1QHeader)
    {
        entry.vlan = std::to_string(dot1QHeader->id());
    }
    auto ipHeader = eth.find_pdu<Tins::IP>();
    auto ip6Header = eth.find_pdu<Tins::IPv6>();
    Tins::TCP* tcpHeader{nullptr};
    Tins::UDP* udpHeader{nullptr};
    if (ipHeader)
    {
        sourceIpAddress = ipHeader->src_addr().to_string();
        destIpAddress   = ipHeader->dst_addr().to_string();
        ipproto         = ipHeader->protocol();
        tcpHeader       = ipHeader->find_pdu<Tins::TCP>();
        udpHeader       = ipHeader->find_pdu<Tins::UDP>();
    }
    else if (ip6Header)
    {
        sourceIpAddress = ip6Header->src_addr().to_string();
        destIpAddress   = ip6Header->dst_addr().to_string();
        ipproto         = ip6Header->next_header();
        tcpHeader       = ip6Header->find_pdu<Tins::TCP>();
        udpHeader       = ip6Header->find_pdu<Tins::UDP>();
    }
    else
    {
        return;
    }

    entry.ipProto = formatIpProto(netdb, ipproto);

    auto fromL4Header = [&](auto l4Header) -> void
    {
        sourceL4Port = l4Header->sport();
        destL4Port   = l4Header->dport();
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
        return;
    }

    entry.sIpPort = formatIpPort(netdb, sourceIpAddress,
            sourceL4Port, ipproto);
    entry.dIpPort = formatIpPort(netdb, destIpAddress,
            destL4Port, ipproto);
}

WjhRawTable::WjhRawTable(NetDBIf& netdb, InterfaceNameCacheIf& ifcache):
    netdb(netdb),
    ifcache(ifcache)
{
    // SONiC common style for table output
    table.set_border_style(FT_SIMPLE_STYLE);
    table.set_cell_text_align(fort::text_align::left);
    table.set_cell_left_padding(0);
    table.set_cell_right_padding(1);

    table << fort::header
          << "#" << "Timestamp" << "sPort" << "dPort"
          << "VLAN" << "sMAC" << "dMAC" << "EthType"
          << "sIP:Port" << "dIP:Port" << "IP Proto"
          << "Drop\nGroup" << "Severity"
          << "Drop reason / Recommended action"
          << fort::endr;
}

void WjhRawTable::addEntry(const WjhRawEvent& event)
{
    WjhRawTableEntry entry;
    entry.index = ++count;

    entry.timestamp = formatTimestamp(event.timestamp);
    entry.sPort     = ifcache.tryGetIfName(event.ingressPort);
    entry.group     = dropGroupToString(event.dropGroup);
    entry.severity  = severityToString(event.dropReason.severity);
    entry.reason    = formatDropReason(event.dropReason);

    fillPacketFields(netdb, entry, event.packet);

    table << entry.index << entry.timestamp << entry.sPort << entry.dPort
          << entry.vlan << entry.sMac << entry.dMac << entry.ethType
          << entry.sIpPort << entry.dIpPort << entry.ipProto
          << entry.group << entry.severity << entry.reason
          << fort::endr;
}

std::string WjhRawTable::toString() const
{
    return table.to_string();
}
