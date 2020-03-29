#include "wjhdaemon.h"
#include "wjhtable.h"

#include <swss/converter.h>
#include <swss/logger.h>
#include <swss/select.h>
#include <swss/selectable.h>
#include <swss/table.h>
#include <swss/tokenize.h>

#include <cerrno>
#include <sys/resource.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/un.h>
#include <unistd.h>

#include <cstring>
#include <deque>

const auto DefaultWjhSonicCfg        = "/etc/sonic/wjh/wjh.xml";
const auto gCfgDbName                 = "CONFIG_DB";
const auto DefaultWjhPciBandwidth    = 50;   // %
const auto DefaultSelectTimeout      = 1000; // ms
const auto DefaultSocketTimeout      = 1;    // s

WjhDaemon::WjhDaemon(Listener& listener, NetDBIf& netdb,
        InterfaceNameCacheIf& ifnamecache,
        WjhChannelFactoryIf& wjhChannelFactory,
        swss::ConsumerTableBase& wjhTable,
        swss::ConsumerTableBase& wjhChannelTable):
    listener(listener),
    netdb(netdb),
    ifnamecache(ifnamecache),
    wjhChannelFactory(wjhChannelFactory),
    wjhTable(wjhTable),
    wjhChannelTable(wjhChannelTable)
{}

void WjhDaemon::initialize()
{
    SWSS_LOG_ENTER();

    wjh_status_t status{WJH_STATUS_ERROR};
    wjh_init_param_t init{};
    std::deque<swss::KeyOpFieldsValuesTuple> vkco;
    unsigned int pciBandwidth = DefaultWjhPciBandwidth;

    wjhTable.pops(vkco);

    /* if we found configuration file, initialize WJH lib
     * with that file, otherwise leave nullptr, so WJH lib will
     * use its own configuration file */
    struct stat stat_buff;
    if (::stat(DefaultWjhSonicCfg, &stat_buff) == 0)
    {
        SWSS_LOG_INFO("Initialize WJH library with custom XML file: %s",
                DefaultWjhSonicCfg);
        init.conf_xml_path = DefaultWjhSonicCfg;
    }

    // forcing other clients to shutdown
    init.force = true;

    // In SONiC mapping SDK logical port ID to SAI OID and then
    // to SAIRedis OID and then to SONiC port name is complex.
    // We are using IF_INDEX mode to map host interface if_index
    // to host interface name.
    init.ingress_info_type = WJH_INGRESS_INFO_TYPE_IF_INDEX;

    for (const auto& kvf: vkco)
    {
        const auto& key = kfvKey(kvf);
        const auto& op = kfvOp(kvf);
        const auto& fvs = kfvFieldsValues(kvf);
        for (const auto& fv: fvs)
        {
            const auto& field = fvField(fv);
            const auto& value = fvValue(fv);
            if (key != "global" || op != "SET")
            {
                continue;
            }
            if (field == "pci_bandwidth")
            {
                pciBandwidth = swss::to_uint<decltype(pciBandwidth)>(value);
                SWSS_LOG_NOTICE("Setting PCI bandwidth value to %d", pciBandwidth);
            }
            else if (field == "nice_level")
            {
                unsigned int nice = swss::to_uint<decltype(nice)>(value);
                SWSS_LOG_NOTICE("Setting nice value to %d", nice);
                setSelfNiceValue(nice);
            }
        }
    }

    init.max_bandwidth_percent = pciBandwidth;

    status = wjh_init(&init);
    if (status != WJH_STATUS_SUCCESS)
    {
        SWSS_LOG_THROW("Failed to initialize WJH library");
    }

    initializeDefaultWjhChannels();
}

void WjhDaemon::deinitialize()
{
    wjh_status_t status {WJH_STATUS_ERROR};
    for (const auto& it: m_channels)
    {
        it.second->destroy();
    }
    status = wjh_deinit();
    if (status != WJH_STATUS_SUCCESS)
    {
        SWSS_LOG_ERROR("Failed to de-initialize WJH library, status %d",
                status);
    }
}

void WjhDaemon::initializeDefaultWjhChannels()
{
    static const std::map<std::string, std::set<wjh_drop_reason_group_e>>
        defaultChannels =
    {
        {
            "forwarding",
            {
                WJH_DROP_REASON_GROUP_L2_E,
                WJH_DROP_REASON_GROUP_ROUTER_E,
                WJH_DROP_REASON_GROUP_TUNNEL_E,
            }
        },
        {
            "acl",
            {
                WJH_DROP_REASON_GROUP_ACL_E,
            }
        },
        {
            "l1",
            {
                WJH_DROP_REASON_GROUP_L1_E,
            }
        }
    };

    for (const auto& it: defaultChannels)
    {
        const auto& name = it.first;
        const auto& drops = it.second;
        auto channel = wjhChannelFactory.createChannel(name);
        if (!channel->create())
        {
            SWSS_LOG_THROW("Failed to initialize default channels");
        }

        for (const auto& dropGroup: drops)
        {
            if (!channel->setDropGroupReason(dropGroup))
            {
                SWSS_LOG_THROW("Failed to initialize default channels");
            }
        }
        m_channels[name] = std::move(channel);
    }
}

void WjhDaemon::runMainLoop()
{
    SWSS_LOG_ENTER();

    swss::Select select{};
    std::unique_ptr<Connection> conn;
    select.addSelectable(&wjhTable);
    select.addSelectable(&wjhChannelTable);
    select.addSelectable(&listener);

    while(running.load())
    {
        int rc {swss::Select::ERROR};
        swss::Selectable* currentSelectable {nullptr};
        rc = select.select(&currentSelectable, DefaultSelectTimeout);

        if (rc == swss::Select::ERROR)
        {
            SWSS_LOG_ERROR("Select returned error %d", rc);
        }
        else if (rc == swss::Select::OBJECT)
        {
            if (currentSelectable == &wjhTable)
            {
                handleWjhTable();
            }
            else if (currentSelectable == &wjhChannelTable)
            {
                handleWjhChannelTable();
            }
            else if (currentSelectable == &listener)
            {
                conn = listener.accept();
                conn->setTimeout(DefaultSocketTimeout);
                select.addSelectable(conn.get());
                select.removeSelectable(&listener);
            }
            else if (conn && (currentSelectable == conn.get()))
            {
                handleCliClient(*conn);
                select.removeSelectable(conn.get());
                select.addSelectable(&listener);
                conn.reset();
            }
            else
            {
                SWSS_LOG_THROW("unknown object returned by Select");
            }
        }
        else if (rc == swss::Select::TIMEOUT)
        {
            continue;
        }
        else
        {
            SWSS_LOG_THROW("unknown result returned by Select");
        }
    }
}

void WjhDaemon::handleCliClient(Connection& conn)
{
    std::string msg;
    std::string request;
    std::set<std::string> channels;
    if (!conn.recv(msg))
    {
        return;
    }
    auto toks = swss::tokenize(msg, ' ');
    for (const auto& tok: toks)
    {
        auto keyval = swss::tokenize(tok, '=');
        if (keyval.size() != 2)
        {
            SWSS_LOG_ERROR("Invalid CLI request: %s", msg.c_str());
            return;
        }
        auto key = keyval[0];
        auto val = keyval[1];
        if (key == "request")
        {
            request = val;
        }
        else if (key == "channel")
        {
            channels.insert(val);
        }
    }

    if (request == "pull")
    {
        // TODO: need to check first channel type (raw/aggregate)
        WjhRawTable table{netdb, ifnamecache};
        for (const auto& channel: channels)
        {
            auto chan = getChannel(channel);
            if (!chan)
            {
                std::stringstream errstream;
                errstream << "Channel " << channel << " does not exists"
                          << std::endl;
                if (!conn.send(errstream.str()))
                {
                    return;
                }
                continue;
            }
            chan->pull();
            for (const auto& entry: chan->getRawCache())
            {
                table.addEntry(entry);
            }
            chan->clearRawCache();
        }
        if (!conn.send(table.toString()))
        {
	    return;
        }
    }
    else
    {
        // ignore
    }
}

void WjhDaemon::handleWjhChannelTable()
{
    // TODO:
}

void WjhDaemon::handleWjhTable()
{
    std::deque<swss::KeyOpFieldsValuesTuple> vkco;
    wjhTable.pops(vkco);
    for (const auto& kvf: vkco)
    {
        const auto& key = kfvKey(kvf);
        const auto& op = kfvOp(kvf);
        auto fvs = kfvFieldsValues(kvf);
        for (const auto& fv: fvs)
        {
            const auto& field = fvField(fv);
            const auto& value = fvValue(fv);
            if (key != "global" || op != "SET")
            {
                continue;
            }
            if (field == "nice_level")
            {
                unsigned int nice = swss::to_uint<decltype(nice)>(value);
                SWSS_LOG_NOTICE("Setting nice value to %d", nice);
                setSelfNiceValue(nice);
            }
        }
    }
}

void WjhDaemon::setSelfNiceValue(int nice)
{
    auto err = setpriority(PRIO_PROCESS, 0, nice);
    if (err == -1)
    {
        SWSS_LOG_THROW("Failed to set nice level value to process: %s", strerror(errno));
    }
}

WjhChannelIf* WjhDaemon::getChannel(const std::string& channelName)
{
    auto found = m_channels.find(channelName);
    if (found == m_channels.end())
    {
        return nullptr;
    }
    return found->second.get();
}

void WjhDaemon::setShutdownFlag()
{
    running.store(false);
}
