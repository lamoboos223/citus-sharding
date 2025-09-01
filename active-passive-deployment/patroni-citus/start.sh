#!/bin/sh
set -e
mkdir -p /var/lib/postgresql/data /var/run/postgresql
chown -R postgres:postgres /var/lib/postgresql /var/run/postgresql /etc/patroni.yml || true
chmod 0700 /var/lib/postgresql/data || true
chmod 0755 /var/run/postgresql || true
exec su -s /bin/sh postgres -c 'exec /opt/patroni/bin/patroni /etc/patroni.yml'
