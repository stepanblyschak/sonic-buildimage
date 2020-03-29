#include "netdb.h"

#include <arpa/inet.h>
#include <netdb.h>

#include <algorithm>

NetDB::NetDB()
{
    for(servent* entry = getservent(); entry; entry = getservent())
    {
        l4protocols.emplace(ntohs(entry->s_port),
            Servent{
                .servicename = entry->s_name,
                .protocol = entry->s_proto,
            }
        );
    }
    for(protoent* entry = getprotoent(); entry; entry = getprotoent())
    {
        ipprotocols.emplace(entry->p_proto,
	     Protoent{
	         .protocolname = entry->p_name,
	     }
	);
    }
}

bool NetDB::getServiceName(std::string& out, uint16_t port,
    const std::string& protocol)
{
    auto range = l4protocols.equal_range(port);
    auto firstit = range.first;
    auto secondit = range.second;
    if (firstit == l4protocols.cend())
    {
        return false;
    }
    if (protocol.empty())
    {
        out = firstit->second.servicename;
        return true;
    }
    auto foundit = std::find_if(firstit, secondit,
        [&protocol](auto it) { return protocol == it.second.protocol; });
    if (foundit != secondit)
    {
        out = foundit->second.servicename;
        return true;
    }
    return false;
}

bool NetDB::getIpProtocolName(std::string& out, uint16_t port)
{
    auto it = ipprotocols.find(port);
    if (it == ipprotocols.cend())
    {
        return false;
    }
    out = it->second.protocolname;
    return true;
}
