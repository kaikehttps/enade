"""Publica registros inéditos e espera todos os IDs no índice; inclui tempo do refresh."""
import json,time,uuid,tempfile
from pathlib import Path
from app.data import Questao
from app.worker import publicar
from app.services import Cluster
# Execute a publicação no produtor e a observação pela API para não misturar principals.
import os,ssl,http.cookiejar,urllib.request
base=os.environ.get("BASE","https://api:8443")
ctx=ssl.create_default_context(cafile="/run/cred/ca.crt"); client=urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPSHandler(context=ctx),urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
def get(path,data=None):
    req=urllib.request.Request(base+path,data=json.dumps(data).encode() if data else None,headers={"Content-Type":"application/json"})
    return json.load(client.open(req,timeout=15))
get("/api/login",dict(usuario="professor",senha=os.environ["SENHA"]))
batch=uuid.uuid4().hex; rows=[]
for l in Path("/dados/questoes.jsonl").read_text().splitlines():
    q=Questao.model_validate_json(l); q.caderno="benchmark-"+batch;rows.append(q)
with tempfile.NamedTemporaryFile(mode="w") as f:
    f.writelines(q.model_dump_json()+"\n" for q in rows);f.flush()
    start=time.perf_counter();publicar(f.name)
    import urllib.error
    pending={q.chave() for q in rows}
    while pending and time.perf_counter()-start<240:
        for i in list(pending):
            try: get("/api/item/"+i);pending.remove(i)
            except urllib.error.HTTPError as err:
                if err.code!=404: raise
        if pending: time.sleep(.2)
    elapsed=time.perf_counter()-start; seen=len(rows)-len(pending)
    print(json.dumps(dict(lote=batch,esperados=len(rows),visiveis=seen,segundos=elapsed,docs_s=seen/elapsed)))
    if pending: raise SystemExit(1)

