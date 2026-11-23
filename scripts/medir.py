"""Mede a API real do alvo. Senha lida por variável; certifique a CA em HTTPS."""
import os,json,math,sys,time,ssl,http.cookiejar,urllib.request,urllib.parse
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
BASE=os.environ.get("BASE","https://localhost:8443")
ctx=ssl.create_default_context(cafile=os.getenv("CA"))
jar=http.cookiejar.CookieJar()
op=urllib.request.build_opener(urllib.request.ProxyHandler({}),urllib.request.HTTPSHandler(context=ctx),urllib.request.HTTPCookieProcessor(jar))
def call(path,payload=None):
    req=urllib.request.Request(BASE+path,data=json.dumps(payload).encode() if payload else None,headers={"Content-Type":"application/json"})
    with op.open(req,timeout=30) as r: return r.headers,json.load(r)
call("/api/login",dict(usuario="professor",senha=os.environ["SENHA"]))
# Consultas inéditas e respectivamente repetidas; ambas as fases têm os mesmos termos.
base=str(time.time_ns()); n=int(os.getenv("N","100")); c=int(os.getenv("CLIENTES","4"))
urls=["/api/busca?"+urllib.parse.urlencode(dict(q="ética "+base+" "+str(i))) for i in range(n)]
def once(path):
    t=time.perf_counter();headers,data=call(path)
    return [(time.perf_counter()-t)*1000,headers["X-Cache"],data["total"]]
result={"alvo":BASE,"clientes":c,"n_por_fase":n,"observacao":"As consultas únicas têm resultado vazio. A medição inclui HTTP, autenticação da sessão e serialização."}
for phase in ["fria","quente"]:
    with ThreadPoolExecutor(c) as pool: values=list(pool.map(once,urls))
    times=sorted(x[0] for x in values)
    result[phase]={f"p{p}_ms":times[math.ceil(p/100*n)-1] for p in [50,95,99]}
    result[phase]["hits"]=sum(x[1]=="hit" for x in values)
# Termo com resultados, usado para explicitar o custo do payload.
call("/api/busca?q=%C3%A9tica")
with ThreadPoolExecutor(c) as pool: populated=list(pool.map(once,["/api/busca?q=%C3%A9tica"]*n))
times=sorted(x[0] for x in populated)
result["etica"]={"resultados":populated[0][2],"hits":sum(x[1]=="hit" for x in populated),**{f"p{p}_ms":times[math.ceil(p/100*n)-1] for p in (50,95,99)}}
print(json.dumps(result,indent=2,ensure_ascii=False))

