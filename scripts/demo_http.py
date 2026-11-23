"""Sequência da demonstração. Registra somente respostas sem identificadores de sessão."""
from http.cookiejar import CookieJar
import json,os,urllib.request as http,urllib.error as errors,urllib.parse as parse
from pathlib import Path
base=os.environ.get("BASE","http://127.0.0.1:8137")
import ssl
op=http.build_opener(http.ProxyHandler({}),http.HTTPSHandler(context=ssl.create_default_context(cafile=os.getenv("CA"))),http.HTTPCookieProcessor(CookieJar()))
events=[]
def call(method,path,data=None):
    req=http.Request(base+path,data=json.dumps(data).encode() if data else None,headers={"Content-Type":"application/json"},method=method)
    try: r=op.open(req)
    except errors.HTTPError as e: r=e
    body=r.read();return r.status,r.headers,json.loads(body) if body else None
def enter(role):
    pw=os.environ.get("SENHA_"+role.upper()) or os.environ["SENHA"]
    status,_,data=call("POST","/api/login",dict(usuario=role,senha=pw))
    assert status==200
    return data
def event(title,path,payload,caption): events.append(dict(titulo=title,requisicao=path,resposta=payload,legenda=caption))
status,_,data=call("GET","/api/saude"); assert status==200
event("Ambiente de demonstração","GET /api/saude",data,"Seis questões extraídas de dois cadernos didáticos. O adaptador local usa SQLite e cache em memória.")
user=enter("estudante");event("Entrada como estudante","POST /api/login",user,"O servidor associa o perfil à sessão. As credenciais são omitidas na gravação.")
url="/api/busca?"+parse.urlencode(dict(q="ética"))
status,h,d=call("GET",url)
assert status==200 and len({i["curso"] for i in d["itens"]})>=2 and all("gabarito" not in i for i in d["itens"])
event("Uma busca, dois cursos","GET /api/busca?q=ética",{"total":d["total"],"cursos":sorted({i["curso"] for i in d["itens"]}),"gabarito presente":False,"X-Cache":h["X-Cache"]},"A consulta encontra questões de Administração e Sistemas de Informação. O perfil de estudante recebe os enunciados.")
status,h,_=call("GET",url);assert h["X-Cache"]=="hit"
event("Repetição da consulta","GET /api/busca?q=ética",{"status":status,"X-Cache":h["X-Cache"]},"O cabeçalho confirma o reaproveitamento da resposta. No cluster, o mesmo serviço usa Redis.")
i=d["itens"][0]["id"];assert call("PUT","/api/lista/"+i)[0]==200
ids=call("GET","/api/lista")[2];assert ids==[i]
event("Questão adicionada","PUT /api/lista/{id}  →  GET /api/lista",{"itens":len(ids),"numero":d["itens"][0]["numero"],"curso":d["itens"][0]["curso"]},"A lista pertence à sessão do estudante.")
status,_,payload=call("GET","/api/exportar");assert status==403
assert call("GET","/api/analises")[0]==403
event("Acesso negado ao estudante","GET /api/exportar",{"HTTP":status,**payload},"A restrição ocorre na API. Abrir a rota diretamente também devolve 403.")
call("POST","/api/sair");enter("professor")
assert call("GET","/api/lista")[2]==[]
call("PUT","/api/lista/"+i);status,_,items=call("GET","/api/exportar"); assert status==200 and items[0]["gabarito"]
event("Exportação do professor","GET /api/exportar",{"HTTP":status,"numero":items[0]["numero"],"gabarito":items[0]["gabarito"],"pdf":items[0]["pdf"],"pagina":items[0]["pagina"]},"A exportação JSON leva a resposta e a página do caderno. A sessão do professor tem lista própria.")
status,_,stats=call("GET","/api/analises");assert status==200
event("Painel analítico","GET /api/analises",stats["cursos"],"O professor consulta a distribuição por curso. O endpoint também agrega competência e ano.")
Path("evidencias/demo-http.json").write_text(json.dumps(events,ensure_ascii=False,indent=2))

