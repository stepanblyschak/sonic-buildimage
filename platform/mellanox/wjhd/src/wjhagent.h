#pragma once

#include "wjhchannel.h"
#include "socket.h"
#include <swss/dbconnector.h>
#include <swss/subscriberstatetable.h>
#include <swss/select.h>
#include <map>

class WjhAgent
{
private:
    swss::DBConnector m_cfgDbConnector;
    swss::SubscriberStateTable m_wjhTable;
    std::map<std::string, std::unique_ptr<WjhChannel>> m_channels;
    Socket m_cliSocket;
public:
    WjhAgent();
    ~WjhAgent();
    void initializeDefaultWjhChannels();
    void handleDebugClient(DebugCliClient&);
    void runMainLoop();
};
