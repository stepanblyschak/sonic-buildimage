#include "wjhdaemon.h"

#include <iostream>
#include <memory>
#include <string>
#include <cstring>
#include <stdexcept>
#include <sstream>

#include <sys/types.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>
#include <getopt.h>
#include <signal.h>

#include <swss/converter.h>
#include <swss/dbconnector.h>
#include <swss/subscriberstatetable.h>

static const char* DefaultSocketPath    = "/var/run/wjh/wjh.sock";
static const char* DefaultPidPath       = "/var/run/wjh/wjh.pid";
static const unsigned  DefaultTimeout   = 10; // s

static std::string usockpath {DefaultSocketPath};
static std::string pidpath {DefaultPidPath};
static int timeout {DefaultTimeout};
static const char* executableName {nullptr};

static const struct option LongOptions[] = {
    {"socket",    optional_argument, 0, 's'},
    {"timeout",   optional_argument, 0, 't'},
    {"help",      no_argument, 0, 'h'},
    {nullptr,     0, 0, 0},
};

static std::unique_ptr<WjhDaemon> wjhdaemon;

void printHelp()
{
    std::cerr << "Usage: " << executableName << "[OPTIONS]\n\n"
              << "    Options:\n"
              << "     -h --help             Print this help message\n"
              << "     -s --socket path      UNIX socket file path\n"
              << "     -t --timeout seconds  Client connection timeout\n"
              << "\n";
}

void signalHandler(int sig)
{
    SWSS_LOG_ENTER();

    switch(sig)
    {
    case SIGINT:
        SWSS_LOG_NOTICE("Caught SIGINT, exiting ...");
        wjhdaemon->setShutdownFlag();
        signal(SIGINT, SIG_DFL);
        break;
    case SIGTERM:
        SWSS_LOG_NOTICE("Caught SIGTERM, exiting ...");
        wjhdaemon->setShutdownFlag();
        signal(SIGTERM, SIG_DFL);
        break;
    default:
        SWSS_LOG_NOTICE("Unhandled signal: %d, ignoring ...", sig);
        break;

    }
}

int main(int argc, char** argv)
{
    int value, optionIndex = 0, ret;
    executableName = *argv;

    swss::Logger::getInstance().setMinPrio(swss::Logger::SWSS_DEBUG);

    SWSS_LOG_ENTER();

    swss::Logger::linkToDbNative("wjhd");

    while((value = getopt_long(argc, argv, "s:t:p:dh", LongOptions, &optionIndex)) != -1)
    {
        switch(value)
        {
        case 's':
            usockpath = optarg;
            break;
        case 't':
            timeout = (std::atoi(optarg) ?: timeout);
            break;
        case 'h':
            printHelp();
            return EXIT_SUCCESS;
        case '?':
            printHelp();
            return EXIT_FAILURE;
        default:
            break;
        }
    }

    USockSeqPacket usock{usockpath};
    NetDB netdb{};
    IfNameCache ifnamecache{};
    WjhChannelFactory wjhChannelFactory{};
    swss::DBConnector cfgDbConnector{"CONFIG_DB", 0};
    swss::SubscriberStateTable wjhTable(&cfgDbConnector, "WJH");
    swss::SubscriberStateTable wjhChannelTable(&cfgDbConnector, "WJH_CHANNEL");

    wjhdaemon = std::make_unique<WjhDaemon>(usock, netdb, ifnamecache,
            wjhChannelFactory, wjhTable, wjhChannelTable);

    signal(SIGINT, signalHandler);
    signal(SIGTERM, signalHandler);

    wjhdaemon->initialize();

    try
    {
        wjhdaemon->runMainLoop();
    } catch(const std::exception& e)
    {
        SWSS_LOG_ERROR("exception: %s", e.what());
        wjhdaemon->deinitialize();
        return EXIT_FAILURE;
    }

    wjhdaemon->deinitialize();
    return EXIT_SUCCESS;
}
