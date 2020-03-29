#include "usock.h"

#include <swss/logger.h>

#include <arpa/inet.h>
#include <cerrno>
#include <string>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>

#include <stdexcept>
#include <cassert>

USockSeqPacket::USockSeqPacket()
{
    int err;
    fd = socket(AF_UNIX, SOCK_SEQPACKET, 0);
    if (fd < 0)
    {
        SWSS_LOG_THROW("socket(): failed to create socket: %s",
                strerror(errno));
    }
}

USockSeqPacket::USockSeqPacket(const std::string& usockpath) :
    USockSeqPacket()
{
    int err;
    sockaddr_un addr{};
    unlink(usockpath.c_str());
    addr.sun_family = AF_UNIX;
    strncpy(addr.sun_path, usockpath.c_str(), usockpath.length());
    err = bind(fd, reinterpret_cast<const sockaddr*>(&addr),
            sizeof(addr));
    if (err)
    {
        SWSS_LOG_THROW("bind(): failed to bind socket to %s: %s",
                usockpath.c_str(), strerror(errno));
    }
    err = listen(fd, 1);
    if (err)
    {
        SWSS_LOG_THROW("listen(): failed to listen on socket: %s",
                strerror(errno));
    }
}

USockSeqPacket::~USockSeqPacket()
{
    int err;
    if (fd == -1)
    {
        return;
    }
    err = close(fd);
    if (err)
    {
        SWSS_LOG_THROW("close(): failed to close socket %s",
                strerror(errno));
    }
    fd = -1;
}

int USockSeqPacket::getFd()
{
    return fd;
}

uint64_t USockSeqPacket::readData()
{
    // don't let Select to read data
    return 0;
}

std::unique_ptr<Connection> USockSeqPacket::accept()
{
    sockaddr addr{};
    socklen_t len = sizeof(addr);

    int clientfd = ::accept(fd, &addr, &len);
    if (clientfd < 0)
    {
        SWSS_LOG_THROW("accept(): failed to accept connection: %s",
                strerror(errno));
    }
    auto conn = std::make_unique<USockSeqPacket>(clientfd);
    return conn;
}

void USockSeqPacket::connect(const std::string& path)
{
    sockaddr_un addr{};
    addr.sun_family = AF_UNIX;
    strncpy(addr.sun_path, path.c_str(), sizeof(addr.sun_path));
    int err = ::connect(fd, reinterpret_cast<struct sockaddr*>(&addr),
            sizeof(addr));
    if (err)
    {
        SWSS_LOG_THROW("connect() failed to connect to daemon: %s",
                strerror(errno));
    }
}

bool USockSeqPacket::send(const std::string& data)
{
    ssize_t sent;
    size_t totalsent = 0;
    int sockbuffsize;
    unsigned int paramsize = sizeof(sockbuffsize);
    int err = getsockopt(fd, SOL_SOCKET, SO_SNDBUF,
            reinterpret_cast<void*>(&sockbuffsize), &paramsize);
    if (err)
    {
        SWSS_LOG_THROW("getsockopt(): failed to get buffer size, %s",
                strerror(errno));
    }
    sockbuffsize /= 2; // see man 7 socket
    while (totalsent < data.size())
    {
        sent = ::send(fd, data.data() + totalsent,
                std::min(data.size() - totalsent,
                   static_cast<size_t>(sockbuffsize)), 0);
        if (sent < 0)
        {
            if (errno == EINTR)
            {
                // interrupted by a signal, ignore and proceed
                continue;
            }
            else if (errno == EAGAIN || errno == EWOULDBLOCK)
            {
                // timeout, exit
                SWSS_LOG_NOTICE("client connection timeout");
                return false;
            }
            else
            {
                SWSS_LOG_WARN("send(): failed to sent data to client: %s",
                        strerror(errno));
                return false;
            }
        }
        else
        {
            totalsent += sent;
        }
    }
    return true;
}

bool USockSeqPacket::recv(std::string& msg)
{
    ssize_t rcv;
    int dataavailable;
    int err = ioctl(fd, FIONREAD, &dataavailable);
    if (err)
    {
        SWSS_LOG_ERROR("ioctl(): failed to get data size to read in socket: %s",
                strerror(errno));
    }
    std::vector<unsigned char> buffer;
    buffer.resize(dataavailable);
    do
    {
        rcv = ::recv(fd, buffer.data(), buffer.size(), 0);
        if (rcv < 0)
        {
            if (errno == EINTR)
            {
                // interrupted by a signal, ignore and proceed
                continue;
            }
            else if (errno == EAGAIN || errno == EWOULDBLOCK)
            {
                // timeout, exit
                SWSS_LOG_NOTICE("connection timeout");
                return false;
            }
            SWSS_LOG_WARN("recv(): failed to read data from socket: %s",
                    strerror(errno));
            return false;
        }
        else if (rcv == 0)
        {
            // shutdown
        }
    } while(false);
    msg = std::string(std::begin(buffer), std::end(buffer));
    return true;
}

void USockSeqPacket::setTimeout(int timeout)
{
    struct timeval tv;
    tv.tv_sec = timeout;
    tv.tv_usec = 0;

    for (auto opt: {SO_SNDTIMEO, SO_RCVTIMEO})
    {
        int err = setsockopt(fd, SOL_SOCKET, opt, (const char*)&tv, sizeof tv);
        if (err == -1)
        {
            SWSS_LOG_THROW("setsockopt(): failed to set socket timeout: %s",
                    strerror(errno));
        }
    }
}

