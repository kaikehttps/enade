#!/bin/sh
set -eu
umask 077
if [ ! -e /var/lib/krb5kdc/principal ]; then
 kdb5_util create -s -r ENADE.LAB -P "$(openssl rand -hex 32)"
fi
for dir in api worker producer kafka elastic ldap redis admin; do mkdir -p "/keys/$dir"; done
if [ ! -s /keys/admin/ca.key ]; then
 openssl req -x509 -newkey rsa:3072 -nodes -keyout /keys/admin/ca.key -out /keys/admin/ca.crt -days 365 -subj /CN=ENADE-Lab-CA
fi
for dir in api worker producer kafka elastic ldap admin; do cp -f /keys/admin/ca.crt "/keys/$dir/ca.crt.tmp"; mv "/keys/$dir/ca.crt.tmp" "/keys/$dir/ca.crt"; done
for service in api kafka elastic ldap; do
 if [ ! -s "/keys/$service/tls.crt" ]; then
  sans="DNS:$service"
  if [ "$service" = api ]; then sans="DNS:localhost,DNS:api,IP:127.0.0.1"; fi
  openssl req -new -newkey rsa:2048 -nodes -keyout "/keys/$service/tls.key" -out /tmp/csr -subj "/CN=$service"
  echo "subjectAltName=$sans" >/tmp/ext
  openssl x509 -req -in /tmp/csr -CA /keys/admin/ca.crt -CAkey /keys/admin/ca.key -CAcreateserial -out "/keys/$service/tls.crt" -days 365 -extfile /tmp/ext
 fi
done
for pair in kafka:kafka/kafka elastic:HTTP/elastic api:api/api worker:indexador/worker producer:produtor/producer; do
 dir="${pair%%:*}"; principal="${pair#*:}@ENADE.LAB"
 if [ ! -s "/keys/$dir/service.keytab" ]; then
  kadmin.local -q "addprinc -randkey $principal"
  kadmin.local -q "ktadd -norandkey -k /keys/$dir/service.keytab $principal"
 fi
done
for s in redis elastic estudante professor ldap; do
 test -s "/keys/admin/$s" || openssl rand -hex 18 >"/keys/admin/$s"
done
for dir in api worker redis; do cp /keys/admin/redis "/keys/$dir/redis"; done
for s in estudante professor ldap; do cp "/keys/admin/$s" "/keys/ldap/$s"; done
cp /keys/admin/elastic /keys/elastic/bootstrap
# Kafka lê PKCS12. A senha e a chave ficam no mesmo volume privado de laboratório.
if [ ! -s /keys/kafka/server.p12 ]; then
 openssl rand -hex 16 >/keys/kafka/storepass
 openssl pkcs12 -export -in /keys/kafka/tls.crt -inkey /keys/kafka/tls.key -out /keys/kafka/server.p12 -password file:/keys/kafka/storepass
fi
chown -R 1000:0 /keys/elastic /keys/kafka
chmod 700 /keys/admin
touch /keys/ready
exec krb5kdc -n

