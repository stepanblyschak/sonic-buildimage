#pragma once

#include "wjhtypes.h"
#include "ifnamecache.h"
#include "netdb.h"
#include "usock.h"
#include "wjhchannel.h"

#include <swss/consumertablebase.h>

#include <atomic>
#include <map>
#include <memory>
#include <string>

class WjhDaemon
{
public:
    WjhDaemon(Listener& listener, NetDBIf& netdb,
            InterfaceNameCacheIf& ifnamecache,
            WjhChannelFactoryIf& channelFactory,
            swss::ConsumerTableBase& wjhTable,
            swss::ConsumerTableBase& wjhChannelTable);
    ~WjhDaemon() = default;

    // Initialize wjhd, library and start service.
    void initialize();

    // Deinitialize wjhd, library and stop service.
    void deinitialize();

    // Run main DB event loop.
    void runMainLoop();

    // Set shutdown flag, so runMainLoop will gracefully exit
    void setShutdownFlag();
private:
    // Get WjhChannel from channel name string or
    // return nullptr if channel with name passed
    // does not exist
    WjhChannelIf* getChannel(const std::string&);
    void createAndBindSocket();
    void initializeDefaultWjhChannels();
    void handleCliClient(Connection& conn);
    void handleWjhTable();
    void handleWjhChannelTable();
    void setSelfNiceValue(int);
private:
    std::atomic<bool> running{true};
    std::map<std::string, std::unique_ptr<WjhChannelIf>> m_channels;
    Listener& listener;
    NetDBIf& netdb;
    InterfaceNameCacheIf& ifnamecache;
    WjhChannelFactoryIf& wjhChannelFactory;
    swss::ConsumerTableBase& wjhTable;
    swss::ConsumerTableBase& wjhChannelTable;
};

