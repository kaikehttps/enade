import os,time,json,sqlite3,secrets,hmac
from pathlib import Path

class Local:
    """Adaptador didático isolado. Estado volátil exceto índice SQLite."""
    def __init__(self):
        from threading import RLock
        self.cache={}; self.lock=RLock()
        self.db=sqlite3.connect(":memory:",check_same_thread=False)
        self.db.execute("create table docs(id text primary key,payload text)")
        from app.data import Questao
        for line in Path("amostras/questoes.jsonl").read_text().splitlines():
            q=Questao.model_validate_json(line); self.db.execute("insert or replace into docs values(?,?)",(q.chave(),q.model_dump_json()))
        self.db.commit()
    def login(self,u,p):
        if u in ["estudante","professor"] and hmac.compare_digest(p,os.environ["DEMO_PASSWORD"]): return u
    def get(self,k):
        with self.lock:
            v=self.cache.get(k)
            if v and v[0]>time.monotonic(): return v[1]
    def put(self,k,v,t): 
        with self.lock: self.cache[k]=(time.monotonic()+t,v)
    def drop(self,k):
        with self.lock: self.cache.pop(k,None)
    def rows(self):
        with self.lock: return [(k,json.loads(v)) for k,v in self.db.execute("select * from docs")]
    def docs(self,ids):
        rows=dict(self.rows()); return [dict(rows[i],id=i) for i in ids if i in rows]
    def search(self,q,f,p):
        import re,unicodedata
        def norm(s): return "".join(c for c in unicodedata.normalize("NFD",s.casefold()) if not unicodedata.combining(c))
        result=[]
        for i,d in self.rows():
            if any(v and (v not in d[k] if isinstance(d[k],list) else v!=d[k]) for k,v in f.items()): continue
            words=norm(q).split()
            blob=norm(" ".join([d["enunciado"],d["texto_base"],*d["competencias"],*d["objetos"]]))
            if not all(w in blob or (w in ["etica","moral"] and any(x in blob for x in ["etica","moral"])) for w in words): continue
            excerpt=re.sub(re.escape(q),lambda m:"⟦"+m[0]+"⟧",d["enunciado"],flags=re.I) if q else d["enunciado"]
            result.append(dict(d,id=i,trecho=excerpt))
        return {"total":len(result),"itens":result[(p-1)*10:p*10]}
    def analytics(self):
        from collections import Counter
        rows=[d for _,d in self.rows()]
        return {"cursos":dict(Counter(d["curso"] for d in rows)),"competencias":[{"competencia":c,"ano":a,"total":n} for (c,a),n in Counter((c,d["ano"]) for d in rows for c in d["competencias"]).items()]}
    def health(self): return {"modo":"local","questoes":len(self.rows())}
    def cart(self,key,op=None,item=None):
        with self.lock:
            v=json.loads(self.get(key) or "[]")
            if op=="add" and item not in v: v.append(item)
            if op=="del" and item in v: v.remove(item)
            self.put(key,json.dumps(v),3600)
            return v

class Cluster:
    def __init__(self):
        import redis
        self.redis=redis.Redis(host="redis",decode_responses=True,password=Path("/run/cred/redis").read_text().strip(),socket_timeout=5)
    def login(self,u,p):
        import ldap3,ssl,re
        if not p or not re.fullmatch(r"[a-zA-Z0-9._-]{1,48}",u): return
        server=ldap3.Server("ldap",port=636,use_ssl=True,tls=ldap3.Tls(validate=ssl.CERT_REQUIRED,ca_certs_file="/run/cred/ca.crt"),get_info=ldap3.NONE)
        dn=f"uid={u},ou=pessoas,dc=enade,dc=lab"
        c=ldap3.Connection(server,user=dn,password=p,receive_timeout=6)
        if not c.bind(): return
        try:
            c.search("ou=grupos,dc=enade,dc=lab",f"(&(objectClass=groupOfNames)(member={dn}))",attributes=["cn"])
            groups={str(e.cn) for e in c.entries}
            return next((r for r in ("professor","estudante") if r in groups),None)
        finally: c.unbind()
    def get(self,k): return self.redis.get(k)
    def put(self,k,v,t): self.redis.setex(k,t,v)
    def drop(self,k): self.redis.delete(k)
    def cart(self,key,op=None,item=None):
        with self.redis.pipeline() as pipe:
            if op=="add": pipe.sadd(key,item)
            if op=="del": pipe.srem(key,item)
            pipe.expire(key,3600); pipe.smembers(key); return sorted(pipe.execute()[-1])
    def search(self,q,f,p):
        from app.search import INDEX,consulta
        res=elastic("POST",f"/{INDEX}/_search",consulta(q,f,p))["hits"]
        return {"total":res["total"]["value"],"itens":[dict(h["_source"],id=h["_id"],trecho=next(iter(h.get("highlight",{}).values()),[h["_source"]["enunciado"]])[0]) for h in res["hits"]]}
    def docs(self,ids):
        from app.search import INDEX
        if not ids: return []
        return [dict(h["_source"],id=h["_id"]) for h in elastic("POST",f"/{INDEX}/_mget",{"ids":ids})["docs"] if h.get("found")]
    def analytics(self):
        from app.search import INDEX
        agg={"c":{"terms":{"field":"curso","size":1000}},"a":{"terms":{"field":"competencias","size":1000},"aggs":{"ano":{"histogram":{"field":"ano","interval":1,"min_doc_count":1}}}}}
        r=elastic("POST",f"/{INDEX}/_search",{"size":0,"aggs":agg})["aggregations"]
        return {"cursos":{x["key"]:x["doc_count"] for x in r["c"]["buckets"]},"competencias":[dict(competencia=x["key"],ano=int(y["key"]),total=y["doc_count"]) for x in r["a"]["buckets"] for y in x["ano"]["buckets"]]}
    def health(self): return {"modo":"cluster","redis":self.redis.ping(),"elastic":elastic("GET","/_cluster/health")["status"]}

def elastic(method,path,body=None):
    import requests
    from requests_gssapi import HTTPSPNEGOAuth,REQUIRED
    resp=requests.request(method,"https://elastic:9200"+path,json=body,verify="/run/cred/ca.crt",auth=HTTPSPNEGOAuth(mutual_authentication=REQUIRED,opportunistic_auth=True),timeout=20)
    resp.raise_for_status()
    return resp.json()

