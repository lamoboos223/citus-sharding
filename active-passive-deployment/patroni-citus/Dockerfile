FROM citusdata/citus:latest

# Tools + Python venv support
RUN apt-get update \
 && apt-get install -y --no-install-recommends python3-venv curl jq ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# Patroni in its own venv (avoids PEP 668), plus a Postgres driver
RUN python3 -m venv /opt/patroni \
 && /opt/patroni/bin/pip install --no-cache-dir --upgrade pip setuptools wheel \
 && /opt/patroni/bin/pip install --no-cache-dir \
      psycopg2-binary>=2.9 \
      "patroni[etcd]" \
 && ln -s /opt/patroni/bin/patroni /usr/local/bin/patroni

# Config & entrypoint
COPY patroni.yml /etc/patroni.yml
COPY start.sh /usr/local/bin/start-patroni
RUN chmod +x /usr/local/bin/start-patroni

# Pre-create & set perms; re-asserted again at boot
RUN mkdir -p /var/lib/postgresql/data /var/run/postgresql \
 && chown -R postgres:postgres /var/lib/postgresql /var/run/postgresql /etc/patroni.yml \
 && chmod 0700 /var/lib/postgresql/data \
 && chmod 0755 /var/run/postgresql

ENTRYPOINT ["/usr/local/bin/start-patroni"]
