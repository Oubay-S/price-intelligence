FROM apache/nifi:1.23.2
USER root

RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-pip \
    && ln -sf /usr/bin/python3 /usr/local/bin/python \
    && python3 -m pip install --no-cache-dir google-cloud-bigtable \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

USER nifi