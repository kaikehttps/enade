import os,json,secrets,hashlib,io
from pathlib import Path
from fastapi import FastAPI,HTTPException,Cookie,Depends,Query,Response
from fastapi.responses import HTMLResponse
from pydantic import BaseModel,Field
from app.services import Cluster,Local
from threading import Lock
local=os.getenv("MODO")=="local"
if local and not os.getenv("DEMO_PASSWORD"): raise RuntimeError("Defina DEMO_PASSWORD")
svc=Local() if local else Cluster()
app=FastAPI(title="Acervo ENADE",version="1.0")
counts={"hit":0,"miss":0}; lock=Lock()
class Cred(BaseModel):
    usuario:str=Field(max_length=48)
    senha:str=Field(min_length=1,max_length=256)
def session(sid:str|None=Cookie(None)):
    data=svc.get("s:"+sid) if sid else None
    if not data: raise HTTPException(401,"Entre para continuar")
    return (sid,json.loads(data))
def professor(s=Depends(session)):
    if s[1]["perfil"]!="professor": raise HTTPException(403,"Acesso exclusivo de professor")
    return s
@app.get("/",response_class=HTMLResponse)
def home(): return Path("app/index.html").read_text()
@app.post("/api/login")
def login(body:Cred,response:Response):
    role=svc.login(body.usuario,body.senha)
    if not role: raise HTTPException(401,"Credenciais inválidas")
    sid=secrets.token_urlsafe(32); user=dict(usuario=body.usuario,perfil=role)
    svc.put("s:"+sid,json.dumps(user),3600); response.set_cookie("sid",sid,max_age=3600,httponly=True,samesite="strict",secure=not local)
    return user
@app.post("/api/sair",status_code=204)
def logout(s=Depends(session)):
    svc.drop("s:"+s[0]);svc.drop("cart:"+s[0]); r=Response(status_code=204);r.delete_cookie("sid");return r
@app.get("/api/eu")
def me(s=Depends(session)): return s[1]
@app.get("/api/busca")
def search(response:Response,q:str=Query("",max_length=180),curso:str="",area:str="",ano:int|None=None,componente:str="",tipo:str="",competencia:str="",pagina:int=Query(1,ge=1,le=1000),s=Depends(session)):
    f=dict(curso=curso,area=area,ano=ano,componente=componente,tipo=tipo,competencias=competencia)
    key="busca:"+str(svc.get("geracao") or 0)+":"+hashlib.sha256(json.dumps([q,f,pagina,s[1]["perfil"]],sort_keys=True).encode()).hexdigest()
    cached=svc.get(key); status="hit" if cached else "miss"
    response.headers["X-Cache"]=status
    with lock: counts[status]+=1
    if cached: return json.loads(cached)
    result=svc.search(q,f,pagina)
    if s[1]["perfil"]!="professor":
        for row in result["itens"]: row.pop("gabarito",None)
    svc.put(key,json.dumps(result),120); return result
@app.get("/api/analises")
def analytics(s=Depends(professor)): return svc.analytics()
@app.get("/api/lista")
def cart(s=Depends(session)): return svc.cart("cart:"+s[0])
@app.put("/api/lista/{item}")
def add(item:str,s=Depends(session)):
    if not svc.docs([item]): raise HTTPException(404,"Questão ausente")
    return svc.cart("cart:"+s[0],"add",item)
@app.delete("/api/lista/{item}")
def remove(item:str,s=Depends(session)): return svc.cart("cart:"+s[0],"del",item)
@app.get("/api/exportar")
def export(s=Depends(professor)):
    return Response(json.dumps(svc.docs(svc.cart("cart:"+s[0])),ensure_ascii=False,indent=2),media_type="application/json",headers={"Content-Disposition":"attachment; filename=simulado.json"})
@app.get("/api/saude")
def health():
    try: return svc.health()
    except Exception: raise HTTPException(503,"Dependência indisponível")
@app.get("/api/metricas")
def metrics(s=Depends(professor)):
    with lock: return dict(counts,hit_rate=counts["hit"]/max(1,sum(counts.values())))

@app.get("/api/item/{item}")
def item(item:str,s=Depends(session)):
    docs=svc.docs([item])
    if not docs: raise HTTPException(404,"Questão ausente")
    d=docs[0]
    if s[1]["perfil"]!="professor": d.pop("gabarito",None)
    return d
from fastapi.staticfiles import StaticFiles
if Path("vendor").exists(): app.mount("/vendor",StaticFiles(directory="vendor"),name="vendor")
