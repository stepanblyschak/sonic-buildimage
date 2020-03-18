#include "wjhchannel.h"

#include <map>
#include <swss/logger.h>
#include <swss/converter.h>

static const std::map<WjhChannel::DropGroup, std::string> gDropGroupToStringMap =
{
    {WJH_DROP_REASON_GROUP_L2_E, "L2"},
    {WJH_DROP_REASON_GROUP_ROUTER_E, "L3"},
    {WJH_DROP_REASON_GROUP_TUNNEL_E, "Tunnel"},
    {WJH_DROP_REASON_GROUP_ACL_E, "ACL"},
};

std::string WjhChannel::dropGroupToString(WjhChannel::DropGroup group)
{
    return gDropGroupToStringMap.at(group);
}

static bool stringToDropGroup(std::string groupName, WjhChannel::DropGroup& group)
{
    for (auto groupAndName: gDropGroupToStringMap)
    {
        if (swss::to_upper(groupAndName.second) == swss::to_upper(groupName))
        {
            group = groupAndName.first;
            return true;
        }
    }
    return false;
}

WjhChannel::WjhChannel(std::string name, WjhChannel::Type type):
    m_name(name),
    m_type(type)
{
}

WjhChannel::~WjhChannel()
{
    destroy();
}


bool WjhChannel::create()
{
    SWSS_LOG_ENTER();

    wjh_status_t status;
    wjh_user_channel_attr_t attr{};

    status = wjh_user_channel_create(m_type, &m_id);
    if (status != WJH_STATUS_SUCCESS)
    {
        SWSS_LOG_ERROR("Failed to create channel \"%s\", status %d", m_name.c_str(), status);
        return false;
    }
    // we are always using pull mode, even for periodic pulling
    attr.mode = WJH_USER_CHANNEL_MODE_PULL_E;
    status = wjh_user_channel_set(m_id, &attr);
    if (status != WJH_STATUS_SUCCESS)
    {
        SWSS_LOG_ERROR("Failed to set pulling mode on channel \"%s\", status %d", m_name.c_str(), status);
        return false;
    }

    SWSS_LOG_NOTICE("Created channel \"%s\"", m_name.c_str());
    return true;
}

bool WjhChannel::setDropGroupReason(WjhChannel::DropGroup group)
{
    SWSS_LOG_ENTER();

    wjh_status_t status;
    wjh_drop_reason_group_attr_t attr{};
    wjh_drop_callbacks_t callbacks{};

    callbacks.drop_reason_group = group;

    switch(callbacks.drop_reason_group)
    {
    case WJH_DROP_REASON_GROUP_L2_E:
        callbacks.raw_cb.L2 = rawCallback<WJH_DROP_REASON_GROUP_L2_E, wjh_L2_drop_raw_info_t>;
        break;
    case WJH_DROP_REASON_GROUP_ROUTER_E:
        callbacks.raw_cb.router =rawCallback<WJH_DROP_REASON_GROUP_ROUTER_E, wjh_router_drop_raw_info_t>;
        break;
    case WJH_DROP_REASON_GROUP_TUNNEL_E:
        callbacks.raw_cb.tunnel = rawCallback<WJH_DROP_REASON_GROUP_TUNNEL_E, wjh_tunnel_drop_raw_info_t>;
        break;
    case WJH_DROP_REASON_GROUP_ACL_E:
        callbacks.raw_cb.acl= rawCallback<WJH_DROP_REASON_GROUP_ACL_E, wjh_acl_drop_raw_info_t>;
        break;
    default:
        SWSS_LOG_ERROR("Only L2/L3/Tunnel/ACL drop reason group is supported for now, channel \"%s\"", m_name.c_str());
    }

    if (m_dropReasonGroups.find(group) != m_dropReasonGroups.end())
    {
        return true;
    }

    status = wjh_drop_reason_group_init(group, &attr, &callbacks);
    if (status != WJH_STATUS_SUCCESS)
    {
        SWSS_LOG_ERROR("Failed to initialize drop reason group \"%s\" for channel \"%s\", status %d",
                dropGroupToString(group), m_name.c_str(), status);
        return false;
    }

    status = wjh_drop_reason_group_bind(group, m_id);
    if (status != WJH_STATUS_SUCCESS)
    {
        SWSS_LOG_ERROR("Failed to bind drop reason group \"%s\" for channel \"%s\", status %d",
                dropGroupToString(group), m_name.c_str(), status);
        return false;
    }

    // TODO(stepanb): error currently for all
    status = wjh_drop_reason_group_enable(group, WJH_SEVERITY_ALL_E);
    if (status != WJH_STATUS_SUCCESS)
    {
        SWSS_LOG_ERROR("Failed to enable drop reason group \"%s\" for channel \"%s\", status %d",
                dropGroupToString(group), m_name.c_str(), status);
        return false;
    }

    m_dropReasonGroups.insert(group);
    SWSS_LOG_NOTICE("Drop group reason %s bound to channel %s",
            dropGroupToString(group), m_name.c_str());
    return true;
}

bool WjhChannel::deleteDropGroupReason(WjhChannel::DropGroup group)
{
    SWSS_LOG_ENTER();

    wjh_status_t status;

    if (m_dropReasonGroups.find(group) == m_dropReasonGroups.end())
    {
        SWSS_LOG_WARN("Tried to remove drop group \"%s\" which is not bound to channel \"%s\"",
                dropGroupToString(group), m_name.c_str());
        return true;
    }

    status = wjh_drop_reason_group_disable(group, WJH_SEVERITY_ALL_E);
    if (status != WJH_STATUS_SUCCESS)
    {
        SWSS_LOG_ERROR("Failed to disable drop group \"%s\" on channel \"%s\", status %d",
                dropGroupToString(group), m_name.c_str(), status);
        return false;
    }

    status = wjh_drop_reason_group_unbind(group);
    if (status != WJH_STATUS_SUCCESS)
    {
        SWSS_LOG_ERROR("Failed to unbind drop group \"%s\" on channel \"%s\", status %d",
                dropGroupToString(group), m_name.c_str(), status);
        return false;
    }

    status = wjh_drop_reason_group_deinit(group);
    if (status != WJH_STATUS_SUCCESS)
    {
        SWSS_LOG_ERROR("Failed to de-initialize drop group \"%s\" on channel \"%s\", status %d",
                dropGroupToString(group), m_name.c_str(), status);
        return false;
    }

    m_dropReasonGroups.erase(group);
    SWSS_LOG_NOTICE("Drop group reason %s unbound from channel %s",
            dropGroupToString(group), m_name.c_str());
    return true;
}

bool WjhChannel::destroy()
{
    SWSS_LOG_ENTER();

    bool ret{true};
    wjh_status_t status;

    for (auto group: m_dropReasonGroups)
    {
        ret &= deleteDropGroupReason(group);
    }

    status = wjh_user_channel_destroy(m_id);
    if (status != WJH_STATUS_SUCCESS)
    {
        SWSS_LOG_ERROR("Failed to destroy channel \"%s\", status %d", m_name.c_str(), status);
        ret = false;
    }

    SWSS_LOG_NOTICE("Destroyed channel \"%s\"", m_name.c_str());

    return ret;
}

bool WjhChannel::pull()
{
    SWSS_LOG_ENTER();

    wjh_status_t status;
    WjhChannel::pullingChannel = this;

    status = wjh_user_channel_pull(m_id);

    WjhChannel::pullingChannel = nullptr;
    if (status != WJH_STATUS_SUCCESS)
    {
        SWSS_LOG_ERROR("Failed to pull channel \"%s\", status %d", m_name.c_str(), status);
        return false;
    }
    return true;
}

const RawEventVectorT& WjhChannel::getRawCache() const
{
    return m_rawCache;
}

void WjhChannel::clearRawCache()
{
    m_rawCache.clear();
}


WjhChannel* WjhChannel::pullingChannel = nullptr;

