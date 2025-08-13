FROM postgres:16

RUN apt-get update \
    && apt-get install -y --no-install-recommends postgresql-16-hypopg \
    && rm -rf /var/lib/apt/lists/*

# HypoPG will be created by init script copied via compose volume


