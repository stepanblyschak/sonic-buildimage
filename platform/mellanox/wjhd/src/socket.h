#pragma once

#include <swss/selectable.h>
#include <swss/logger.h>
#include <swss/json.hpp>
#include <unistd.h>
#include <sys/socket.h>
#include <sys/ioctl.h>
#include <sys/un.h>
#include <arpa/inet.h>
#include <string.h>
#include <errno.h>
#include <string>

using swss::Selectable;

class Socket : public Selectable {
public:
    int m_fd{-1};
    std::string m_path;
    sockaddr_un m_addr{};
public:
    Socket() : Socket(-1) {}
    Socket(int fd) : m_fd(fd) {}
    Socket(std::string path, int type = SOCK_STREAM)
    {
        m_path = path;
        m_addr.sun_family = AF_UNIX;
        strncpy(m_addr.sun_path, m_path.c_str(), m_path.size());
        m_fd = socket(AF_UNIX, type, 0);
        if (m_fd == -1) {
            SWSS_LOG_THROW("Failed to create unix domain socket: %s", strerror(errno));
        }
    }
    virtual ~Socket() { if (m_fd != -1) close(); }

    virtual int getFd()
    {
        return m_fd;
    }

    virtual uint64_t readData()
    {
        return 0;
    }

    void close()
    {
        if (m_fd != -1) (void)::close(m_fd);
        m_fd = -1;
    }

    virtual bool hasData()
    {
        return true;
    }

    virtual bool hasCachedData()
    {
        return false;
    }

    void bind() const
    {
        ::unlink(m_path.c_str());
        int err = ::bind(m_fd, reinterpret_cast<const sockaddr*>(&m_addr), sizeof(m_addr));
        if (err) {
            SWSS_LOG_THROW("Failed to bind unix domain socket to %s: %s", m_path.c_str(), strerror(errno));
        }
    }

    void listen(int n = 1) const
    {
        int err = ::listen(m_fd, n);
        if (err)
        {
            SWSS_LOG_THROW("Failed to listen on unix domain socket %s", strerror(errno));
        }
    }

    void accept(Socket& client) const
    {
        sockaddr addr{};
        socklen_t len;

        int fd = ::accept(m_fd, &addr, &len);
        if (fd == -1)
        {
            SWSS_LOG_THROW("Failed to accept connection: %s", strerror(errno));
        }
        client.m_fd = fd;
    }

    void setRecvTimeout(int seconds)
    {
        struct timeval tv;
        tv.tv_sec = seconds;
        tv.tv_usec = 0;
        auto err = setsockopt(m_fd, SOL_SOCKET, SO_RCVTIMEO, (const char*)&tv, sizeof tv);
        if (err)
        {
            SWSS_LOG_THROW("Failed to set recv timeout on socket: %s", strerror(errno));
        }
    }

    void setSendTimeout(int seconds)
    {
        struct timeval tv;
        tv.tv_sec = seconds;
        tv.tv_usec = 0;
        auto err = setsockopt(m_fd, SOL_SOCKET, SO_SNDTIMEO, (const char*)&tv, sizeof tv);
        if (err)
        {
            SWSS_LOG_THROW("Failed to set recv timeout on socket: %s", strerror(errno));
        }
    }

};


class DebugCliClient : public Socket
{
public:
    DebugCliClient() : Socket(-1) {}
    bool send(const nlohmann::json& js)
    {
        std::size_t sentBytes = 0;
        std::string serializedjs = js.dump();
        std::uint32_t size = serializedjs.size();

        SWSS_LOG_ENTER();

        size = htonl(size);
        while(sentBytes < sizeof(size))
        {
            int rv = ::send(m_fd, reinterpret_cast<unsigned char*>(&size) + sentBytes,
                    sizeof(size) - sentBytes, 0);
            if (rv > 0)
            {
                sentBytes += rv;
            }
            else if (rv == EAGAIN || rv == EWOULDBLOCK || rv == EINTR)
            {
                continue;
            }
            else
            {
                return false;
            }
        }

        size = ::ntohl(size);
        sentBytes = 0;

        while(sentBytes < size)
        {
            int rv = ::send(m_fd, serializedjs.data() + sentBytes,
                    size - sentBytes, 0);
            if (rv > 0)
            {
                sentBytes += rv;
            }
            else if (rv == EAGAIN || rv == EWOULDBLOCK || rv == EINTR)
            {
                continue;
            }
            else
            {
                SWSS_LOG_ERROR("Failed to send data to client: %s", strerror(errno));
                return false;
            }
        }

        return true;
    }

    bool recv(nlohmann::json& js)
    {
        std::size_t recvBytes = 0;
        std::vector<unsigned char> serializedjs;
        std::uint32_t size;

        while (recvBytes < sizeof(size))
        {
            int rv = ::recv(m_fd, reinterpret_cast<unsigned char*>(&size),
                    sizeof(size) - recvBytes, 0);
            if (rv > 0)
            {
                recvBytes += rv;
            }
            else if (rv == EAGAIN || rv == EWOULDBLOCK || rv == EINTR)
            {
                continue;
            }
            else
            {
                return false;
            }
        }


        recvBytes = 0;
        size = ::ntohl(size);
        serializedjs.resize(size);

        while (recvBytes < size)
        {
            int rv = ::recv(m_fd, serializedjs.data() + recvBytes,
                    size - recvBytes, 0);
            if (rv > 0)
            {
                recvBytes += rv;
            }
            else if (rv == EAGAIN || rv == EWOULDBLOCK || rv == EINTR)
            {
                continue;
            }
            else
            {
                SWSS_LOG_ERROR("Failed to receive data from client: %s", strerror(errno));
                return false;
            }
        }

        js = nlohmann::json::parse(std::string(serializedjs.begin(), serializedjs.end()));
        return true;
    }
};

