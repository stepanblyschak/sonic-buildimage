#include "wjhagent.h"
#include "wjhserialize.h"
#include "socket.h"
#include <swss/select.h>
#include <swss/converter.h>
#include <swss/json.hpp>
#include <sys/stat.h>

extern "C"
{
#include <wjh/wjh_lib.h>
}

static const std::string DEFAULT_RUN_DIR   = "/var/run/wjh/";
static const std::string DEFAULT_SOCK_PATH = DEFAULT_RUN_DIR + "wjh.sock";
static const std::string DEFAULT_PID_PATH  = DEFAULT_RUN_DIR + "wjh.pid";
static const auto DEFAULT_WJH_XML_PATH = "/etc/sonic/wjh/wjh.xml";
static const std::string WJH_TABLE_NAME = "WJH_TABLE";
static const auto gDefaultSelectTimeout = 1000; /* ms */

WjhAgent::WjhAgent():
        m_cfgDbConnector("CONFIG_DB", 0),
        m_wjhTable(&m_cfgDbConnector, WJH_TABLE_NAME),
        m_cliSocket(DEFAULT_SOCK_PATH)
{
    SWSS_LOG_ENTER();

    wjh_status_t status;
    wjh_init_param_t init{};

    /* if we found configuration file, initialize WJH lib
     * with that file, otherwise leave nullptr, so WJH lib will
     * use its own configuration file */
    struct stat stat_buff;
    if (::stat(DEFAULT_WJH_XML_PATH, &stat_buff) == 0)
    {
        SWSS_LOG_INFO("Will initialize WJH library with custom XML file");
        init.conf_xml_path = DEFAULT_WJH_XML_PATH;
    }
    // forcing other clients to shutdown
    init.force = true;
    // In SONiC mapping SDK logical port ID to SAI OID and then to SAIRedis OID and then to SONiC port name is not easy.
    // We are using IF_INDEX mode to map host interface if_index to host interface name.
    init.ingress_info_type = WJH_INGRESS_INFO_TYPE_IF_INDEX;

    status = wjh_init(&init);
    if (status != WJH_STATUS_SUCCESS)
    {
        SWSS_LOG_THROW("Failed to initialize WJH library");
    }

    initializeDefaultWjhChannels();

    m_cliSocket.bind();
    m_cliSocket.listen();
}

void WjhAgent::initializeDefaultWjhChannels()
{
    static const std::map<std::string, std::set<wjh_drop_reason_group_e>> defaultChannels =
    {
        {
            "forwarding",
            {
                WJH_DROP_REASON_GROUP_L2_E,
                WJH_DROP_REASON_GROUP_ROUTER_E,
                WJH_DROP_REASON_GROUP_TUNNEL_E,
            }
        }
    };

    for (const auto& it: defaultChannels)
    {
        auto channel = std::make_unique<WjhChannel>(it.first);
        if (!channel->create())
        {
            SWSS_LOG_THROW("Failed to initialize default channels");
        }

        for (const auto& dropGroup: it.second)
        {
            if (!channel->setDropGroupReason(dropGroup))
            {
                SWSS_LOG_THROW("Failed to initialize default channels");
            }
        }
        m_channels[it.first] = std::move(channel);
    }
}

WjhAgent::~WjhAgent()
{
    wjh_status_t status;
    for (auto& entry: m_channels)
    {
        entry.second->destroy();
    }
    status = wjh_deinit();
    if (status != WJH_STATUS_SUCCESS)
    {
        SWSS_LOG_ERROR("Failed to de-initialize WJH library, status %d", status);
    }
}

void WjhAgent::handleDebugClient(DebugCliClient& client)
{
    nlohmann::json request;
    nlohmann::json reply;
    try
    {
        client.recv(request);
        auto requestType = request["request"];
        if (requestType == "pull")
        {
            auto channelName = request["channel"];
            auto it = m_channels.find(channelName);
            if (it == m_channels.end())
            {
                std::stringstream errstream;
                errstream << "Channel " << channelName << " does not exist";
                reply["err"] = errstream.str();
                client.send(reply);
                return;
            }
            auto channel = it->second.get();
            WjhIfNameCache::refresh();
            channel->pull();
            SWSS_LOG_NOTICE("Number of events from channel \"%s\" : %d",
                    it->first.c_str(), channel->getRawCache().size());
            serializeWjhRawEvents(channel->getRawCache(), reply["data"]);
            channel->clearRawCache();
            client.send(reply);
        }
    }
    catch (const std::exception& e)
    {
        std::stringstream errstream;
        errstream << e.what();
        reply["err"] = errstream.str();
        SWSS_LOG_ERROR("Failed to process request %s", e.what());
        client.send(reply);
    }
}


void WjhAgent::runMainLoop()
{
    SWSS_LOG_ENTER();

    swss::Select select{};
    select.addSelectable(&m_cliSocket);

    while(true)
    {
        int rc{swss::Select::ERROR};
        Selectable* currentSelectable{nullptr};
        rc = select.select(&currentSelectable, gDefaultSelectTimeout);
        if (rc == swss::Select::ERROR)
        {
            SWSS_LOG_ERROR("Select returned error %d", rc);
        }
        else if (rc == swss::Select::OBJECT)
        {
            if (currentSelectable == &m_wjhTable)
            {
                SWSS_LOG_ERROR("configuration change is not implemeneted yet");
            }
            else if (currentSelectable == &m_cliSocket)
            {
                DebugCliClient client;
                m_cliSocket.accept(client);
                client.setSendTimeout(1);
                client.setRecvTimeout(1);
                SWSS_LOG_NOTICE("accepted client connection, fd %d", client.getFd());
                handleDebugClient(client);
                SWSS_LOG_NOTICE("Closing client socket");
                client.close();
            }
            else
            {
                SWSS_LOG_THROW("unknown object returned by Select");
            }
        }
    }
}
