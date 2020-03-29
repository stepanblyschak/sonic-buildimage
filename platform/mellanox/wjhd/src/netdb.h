#pragma once

#include <map>
#include <string>

class NetDBIf
{
public:
    virtual ~NetDBIf() = default;
    virtual bool getServiceName(std::string& output,
            uint16_t port, const std::string& protocol = "") = 0;
    virtual bool getIpProtocolName(std::string& output, uint16_t proto) = 0;
};

class NetDB : public NetDBIf
{
public:
    NetDB();
    ~NetDB() override = default;

    struct Servent
    {
        std::string servicename;
        std::string protocol;
    };

    struct Protoent
    {
        std::string protocolname;
    };

    bool getServiceName(std::string& output,
            uint16_t port, const std::string& protocol = "") override;
    bool getIpProtocolName(std::string& output, uint16_t proto) override;
private:
    std::multimap<uint16_t, Servent> l4protocols;
    std::map<uint16_t, Protoent> ipprotocols;
};

