FROM debian:12-slim AS builder

# Build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    automake \
    autoconf \
    pkg-config \
    libssl-dev \
    ca-certificates \
    wget \
    && rm -rf /var/lib/apt/lists/*

# Build openfortivpn 1.22.1 from source (SAML cookie support added in 1.22.0)
RUN wget -q https://github.com/adrienverge/openfortivpn/archive/refs/tags/v1.22.1.tar.gz \
    && tar xzf v1.22.1.tar.gz \
    && cd openfortivpn-1.22.1 \
    && aclocal && autoconf && automake --add-missing \
    && ./configure --prefix=/usr --sysconfdir=/etc \
    && make -j$(nproc) \
    && make install DESTDIR=/install

FROM debian:12-slim

# Copy compiled openfortivpn
COPY --from=builder /install/usr /usr

# Runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    iproute2 \
    ppp \
    curl \
    ca-certificates \
    libssl3 \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Script untuk monitoring & reconnect
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
