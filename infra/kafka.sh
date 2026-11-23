#!/bin/bash
set -eu
cd /opt/kafka
pass=$(cat /run/cred/storepass)
if [ ! -f /tmp/trust.p12 ]; then keytool -importcert -noprompt -alias ca -file /run/cred/ca.crt -keystore /tmp/trust.p12 -storetype PKCS12 -storepass "$pass"; fi
cat >/tmp/kafka.properties <<EOF
process.roles=broker,controller
node.id=1
controller.quorum.voters=1@kafka:9093
listeners=SASL_SSL://:9092,CONTROLLER://:9093
advertised.listeners=SASL_SSL://kafka:9092
listener.security.protocol.map=SASL_SSL:SASL_SSL,CONTROLLER:SASL_SSL
inter.broker.listener.name=SASL_SSL
controller.listener.names=CONTROLLER
sasl.enabled.mechanisms=GSSAPI
sasl.mechanism.inter.broker.protocol=GSSAPI
sasl.mechanism.controller.protocol=GSSAPI
sasl.kerberos.service.name=kafka
ssl.keystore.type=PKCS12
ssl.keystore.location=/run/cred/server.p12
ssl.keystore.password=$pass
ssl.key.password=$pass
ssl.truststore.type=PKCS12
ssl.truststore.location=/tmp/trust.p12
ssl.truststore.password=$pass
offsets.topic.replication.factor=1
transaction.state.log.replication.factor=1
transaction.state.log.min.isr=1
default.replication.factor=1
num.partitions=3
auto.create.topics.enable=false
log.dirs=/var/lib/kafka/data
EOF
cat >/tmp/jaas <<EOF
KafkaServer { com.sun.security.auth.module.Krb5LoginModule required useKeyTab=true storeKey=true keyTab="/run/cred/service.keytab" principal="kafka/kafka@ENADE.LAB"; };
EOF
export KAFKA_HEAP_OPTS="-Xms256m -Xmx384m"
export KAFKA_OPTS="-Djava.security.krb5.conf=/etc/krb5.conf -Djava.security.auth.login.config=/tmp/jaas -Dsun.security.krb5.disableReferrals=true"
if [ ! -e /var/lib/kafka/data/meta.properties ]; then bin/kafka-storage.sh format -t "$(bin/kafka-storage.sh random-uuid)" -c /tmp/kafka.properties; fi
exec bin/kafka-server-start.sh /tmp/kafka.properties

