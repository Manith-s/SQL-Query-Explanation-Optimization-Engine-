FROM postgres:16
RUN apt-get update && apt-get install -y --no-install-recommends postgresql-16-hypopg && rm -rf /var/lib/apt/lists/*
# init scripts will run from /docker-entrypoint-initdb.d
