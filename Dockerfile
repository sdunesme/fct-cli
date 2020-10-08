FROM ubuntu:focal
MAINTAINER fct-cli

RUN  export DEBIAN_FRONTEND=noninteractive
ENV  DEBIAN_FRONTEND noninteractive
RUN  dpkg-divert --local --rename --add /sbin/initctl

ARG UID=444542
ARG USER=sdunesme

RUN adduser --uid ${UID} --gid 100 --disabled-password --gecos "" ${USER}

RUN apt-get update -qq && apt-get install -y \
  git-core \
  libssl-dev \
  libcurl4-gnutls-dev \
  libudunits2-dev \
  libgdal-dev \
  libsodium-dev \
  git

RUN apt-get update -qq && apt-get install -y \
  python3 \
  python3-dev \
  python3-rtree \
  python3-pip \
  libcairo2-dev

RUN git clone https://github.com/sdunesme/fct-cli /opt/fct-cli \
 && cd /opt/fct-cli \
 && git checkout hmvt-implementation \
 && python3 -m pip install --upgrade pip \
 && python3 -m pip install scikit-learn sklearn wheel \
 && python3 -m pip install -r requirements.txt \
 && python3 -m pip install -r recommended.txt

RUN cd /opt/fct-cli \
 && git submodule init \
 && git submodule update --remote \
 && python3 -m pip install -e .

USER ${UID}