#!/bin/sh
set -eu
mkdir -p /run/slapd /var/lib/enade-ldap
cat >/tmp/ldap.conf <<EOF
include /etc/ldap/schema/core.schema
include /etc/ldap/schema/cosine.schema
include /etc/ldap/schema/inetorgperson.schema
pidfile /run/slapd/slapd.pid
modulepath /usr/lib/ldap
moduleload back_mdb
TLSCertificateFile /run/cred/tls.crt
TLSCertificateKeyFile /run/cred/tls.key
TLSCACertificateFile /run/cred/ca.crt
database mdb
suffix "dc=enade,dc=lab"
rootdn "cn=admin,dc=enade,dc=lab"
rootpw $(slappasswd -s "$(cat /run/cred/ldap)")
directory /var/lib/enade-ldap
access to attrs=userPassword by anonymous auth by self auth by * none
access to * by users read by * none
EOF
if [ ! -e /var/lib/enade-ldap/data.mdb ]; then
 cat >/tmp/base.ldif <<EOF
dn: dc=enade,dc=lab
objectClass: organization
objectClass: dcObject
o: ENADE
dc: enade

dn: ou=pessoas,dc=enade,dc=lab
objectClass: organizationalUnit
ou: pessoas

dn: ou=grupos,dc=enade,dc=lab
objectClass: organizationalUnit
ou: grupos
EOF
 for u in estudante professor; do
 cat >>/tmp/base.ldif <<EOF

dn: uid=$u,ou=pessoas,dc=enade,dc=lab
objectClass: inetOrgPerson
cn: $u
sn: $u
uid: $u
userPassword: $(slappasswd -s "$(cat /run/cred/$u)")

dn: cn=$u,ou=grupos,dc=enade,dc=lab
objectClass: groupOfNames
cn: $u
member: uid=$u,ou=pessoas,dc=enade,dc=lab
EOF
 done
 slapadd -f /tmp/ldap.conf -l /tmp/base.ldif
fi
exec slapd -f /tmp/ldap.conf -h 'ldaps://0.0.0.0:636/' -d 0

