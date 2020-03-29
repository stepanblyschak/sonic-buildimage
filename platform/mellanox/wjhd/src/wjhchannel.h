#pragma once

#include "wjhtypes.h"

#include <string>
#include <ctime>
#include <vector>
#include <set>
#include <memory>

#include <iostream>

class WjhChannelIf
{
public:
    virtual ~WjhChannelIf() = default;
    virtual bool create() = 0;
    virtual bool setDropGroupReason(DropGroupT group) = 0;
    virtual bool deleteDropGroupReason(DropGroupT group) = 0;
    virtual bool destroy() = 0;
    virtual bool pull() = 0;
    virtual const RawEventVectorT& getRawCache() const = 0;
    virtual void clearRawCache() = 0;
};

class WjhChannelFactoryIf
{
public:
    virtual std::unique_ptr<WjhChannelIf> createChannel(const std::string& name) = 0;
};

// Represent SONiC What-Just-Happened channel.
class WjhChannel : public WjhChannelIf
{
public:
    // Construct a channel from name and type.
    // Channel creation in WJH library is done in a seperate
    // method call.
    WjhChannel(const std::string& name,
        ChannelTypeT type = WJH_USER_CHANNEL_CYCLIC_E);
    ~WjhChannel() override = default;
    WjhChannel(const WjhChannel&) = delete;
    WjhChannel& operator=(const WjhChannel&) = delete;
    WjhChannel(WjhChannel&&) = default;
    WjhChannel& operator=(WjhChannel&&) = default;

    // Create channel in WJH library.
    bool create() override;

    // Bind a drop group to this channel.
    // Channel can have multiple drop groups bound,
    // while one drop group can be bound only to single
    // raw and/or aggregate channel.
    // Setting drop group which is already set is noop
    // and returns true.
    bool setDropGroupReason(DropGroupT group) override;

    // Unbind drop group from channel.
    bool deleteDropGroupReason(DropGroupT group) override;

    // Unbind all drop groups bound and delete the channel
    bool destroy() override;

    // Pull the channel for drops.
    // Drops are saved into cache associated with channel.
    bool pull() override;

    // Get raw dropped packets cached data after pull.
    const RawEventVectorT& getRawCache() const override;

    // Clear raw drops cache.
    void clearRawCache() override;

private:
    std::string m_name; // SONiC channel name
    wjh_user_channel_id_t m_id {WJH_USER_CHANNEL_ID_INVALID};
    ChannelTypeT m_type;
    // list of drop reason groups associated with this channel
    std::set<DropGroupT> m_dropReasonGroups;
    RawEventVectorT m_rawCache;

    // WjhChannel and WjhCallback are tightly coupled so
    // allowing them accessing private fields of each other
    friend class WjhCallback;
};

class WjhChannelFactory : public WjhChannelFactoryIf
{
public:
    virtual ~WjhChannelFactory() = default;
    std::unique_ptr<WjhChannelIf> createChannel(const std::string& name) override;
};

