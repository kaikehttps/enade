"""Bootstrap com credencial administrativa isolada do processo da API."""
import time,requests
from pathlib import Path
from app.search import mapping,INDEX
url="https://elastic:9200"
session=requests.Session();session.verify="/run/cred/ca.crt";session.auth=("elastic",Path("/run/cred/elastic").read_text().strip())
for attempt in range(100):
    try:
        if session.get(url,timeout=3).ok: break
    except requests.RequestException: pass
    time.sleep(3)
else: raise RuntimeError("Elastic indisponível")
for name,priv,idx,principal in [("leitura",["monitor"],["read"],"api/api"),("escrita",[],["write"],"indexador/worker")]:
    session.put(url+"/_security/role/"+name,json={"cluster":priv,"indices":[{"names":[INDEX],"privileges":idx}]}).raise_for_status()
    session.put(url+"/_security/role_mapping/"+name,json={"roles":[name],"enabled":True,"rules":{"all":[{"field":{"realm.name":"krb"}},{"field":{"username":principal+"@ENADE.LAB"}}]}}).raise_for_status()
res=session.head(url+"/"+INDEX)
if res.status_code==404: session.put(url+"/"+INDEX,json=mapping).raise_for_status()
else: res.raise_for_status()

