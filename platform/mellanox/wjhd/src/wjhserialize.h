#pragma once

#include "wjhchannel.h"
#include <swss/json.hpp>

void serializeWjhRawEvents(const RawEventVectorT& events, nlohmann::json& js);
