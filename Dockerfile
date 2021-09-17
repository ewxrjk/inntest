FROM debian:buster
ENV DEBIAN_FRONTEND noninteractive
RUN apt-get -y update \
    && apt-get install -y --no-install-recommends \
    ca-certificates \
    eatmydata \
    gnupg \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

COPY sources.buster /etc/apt/sources.buster
RUN cat /etc/apt/sources.buster /etc/apt/sources.list > /etc/apt/sources.list.new \
    && mv /etc/apt/sources.list.new /etc/apt/sources.list

RUN eatmydata -- apt-get -y update \
    && eatmydata -- apt-get install -y --no-install-recommends \
    bison \
    chiark-really \
    cron \
    curl \
    debhelper \
    dpkg-dev \
    exim4-daemon-light \
    fakeroot \
    flex \
    gnupg1 \
    groff-base \
    less \
    libdb-dev \
    libgd-perl \
    libkrb5-dev \
    libmime-tools-perl \
    libpam0g-dev \
    libperl-dev \
    libpython3.7 \
    libsasl2-dev \
    libssl-dev \
    netbase \
    perl \
    perl-openssl-defaults \
    procps \
    python3 \
    python3-dev \
    rsyslog \
    sensible-utils \
    strace \
    time \
    wget \
    zlib1g-dev \
    && eatmydata -- apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /work
ENV DIR=/work/inn
ENV USER=news
RUN chsh -s /bin/bash news
RUN mkdir -p /var/spool/news && chown news:news /var/spool/news
ADD build configure install shutdown start test* trigger valgrind* *.py /work/
ADD inntest /work/inntest
ADD nntpbits /work/nntpbits
ADD config /work/
VOLUME /work/inn.tar.gz
