#include "usock.h"

#include <iostream>
#include <string>
#include <cstring>
#include <stdexcept>
#include <sstream>
#include <set>

#include <sys/types.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>
#include <signal.h>

#include <swss/converter.h>
#include <swss/select.h>
#include <swss/logger.h>

const auto gDefaultSocketPath    = "/var/run/wjh/wjh.sock";
const auto gDefaultTimeout       = 10; // s
const auto gDefaultRecvBatch     = 4096;

std::string gSocketPath = gDefaultSocketPath;
unsigned gTimeout       = gDefaultTimeout;
std::set<std::string> gChannels;

void printHelp()
{
    std::cerr << "Usage: wjhcli [-s PATH] [-t TIMEOUT]"
              << std::endl
              << "              [-c CHANNEL]"
              << std::endl;
}

void handleCliArguments(int argc, char** argv)
{
    int opt;
    while ((opt = getopt(argc, argv, "s:t:c:h?")) != -1)
    {
        switch(opt)
        {
        case 's':
            gSocketPath = optarg;
            break;
        case 't':
            try
            {
                gTimeout = swss::to_uint<decltype(gTimeout)>(optarg);
            }
            catch (const std::invalid_argument&)
            {
                std::cerr << "Invalid timeout parameter: "
                          << optarg
                          << std::endl;
                exit(EXIT_FAILURE);
            }
            break;
        case 'c':
            gChannels.insert(optarg);
            break;
        case 'h':
        case '?':
            printHelp();
            exit(EXIT_SUCCESS);
            break;
        default:
            printHelp();
            exit(EXIT_SUCCESS);
            break;
        }
    }
}

void pullChannel(USockSeqPacket& sock, const std::set<std::string>& channels, std::ostream& out)
{
    swss::Select select;
    swss::Selectable* selectable {nullptr};
    std::stringstream requeststream;
    requeststream << "request=pull ";
    for (const auto& channel: channels)
    {
        requeststream << "channel=" << channel << " ";
    }
    std::string request = requeststream.str();
    if (!sock.send(request))
    {
        SWSS_LOG_THROW("Failed to send request to daemon");
    }

    SWSS_LOG_DEBUG("sent request \"%s\" to daemon", request.c_str());

    select.addSelectable(&sock);
    auto rc = select.select(&selectable, gTimeout * 1000 /* to ms */);
    if (rc == swss::Select::ERROR)
    {
        SWSS_LOG_THROW("Failed to pull channel");
    }
    else if (rc == swss::Select::TIMEOUT)
    {
        SWSS_LOG_THROW("Timeout waiting for daemon reply");
    }
    else if (rc != swss::Select::OBJECT)
    {
        SWSS_LOG_THROW("Unexpected return value from select, %d", rc);
    }

    if (selectable != &sock)
    {
        SWSS_LOG_THROW("Unexpected object returned by select");
    }

    while (true)
    {
        std::string recvmsg;
        if (!sock.recv(recvmsg))
        {
            SWSS_LOG_THROW("Failed to receive reply from daemon");
        }
        if (recvmsg.empty())
        {
            // output end
            return;
        }
        out << recvmsg;
    }
}

int main(int argc, char** argv)
{
    handleCliArguments(argc, argv);
    if (gChannels.empty())
    {
        std::cerr << "channel name is empty" << std::endl;
        printHelp();
        exit(EXIT_FAILURE);
    }

    signal(SIGPIPE, SIG_IGN);

    try
    {
        USockSeqPacket sock{};
        sock.connect(gSocketPath);
        sock.setTimeout(gTimeout);
        pullChannel(sock, gChannels, std::cout);
    }
    catch(const std::exception& exception)
    {
        std::cerr << exception.what() << std::endl;
        return EXIT_FAILURE;
    }

    return EXIT_SUCCESS;
}
