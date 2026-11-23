"""Inventário incremental dos links publicados pelo Inep. Retém falhas para inspeção."""
from bs4 import BeautifulSoup
from pathlib import Path
from urllib.parse import urljoin,urlparse,unquote
import hashlib,json,re,requests
from collections import deque

base="https://www.gov.br/inep/pt-br/"
roots=[base+"areas-de-atuacao/avaliacao-e-exames-educacionais/enade/provas-e-gabaritos",base+"centrais-de-conteudo/legislacao/enade"]
def coleta(out):
    out.mkdir(exist_ok=True); queue=deque((u,0) for u in roots); seen=set(); rows=[]; errors=[]
    while queue:
        url,depth=queue.popleft()
        if url in seen: continue
        seen.add(url)
        try:
            resp=requests.get(url,timeout=40); resp.raise_for_status()
            if resp.content.startswith(b"%PDF"):
                name=hashlib.sha256(resp.content).hexdigest()+".pdf"
                (out/name).write_bytes(resp.content); rows.append(dict(url=url,arquivo=name)); continue
            soup=BeautifulSoup(resp.content,"html.parser"); scope=soup.select_one("#content-core") or soup.select_one("main") or soup
            for a in scope.select("a[href]"):
                link=urljoin(resp.url,a["href"]).split("#")[0]; host=urlparse(link).hostname or ""
                if host not in {"www.gov.br","download.inep.gov.br","inep.gov.br","www.in.gov.br","in.gov.br"}: continue
                if re.search(r"\.pdf(?:$|[?/])",unquote(link),re.I) or (depth<3 and any(link.startswith(root+"/") for root in roots)):
                    queue.append((link,depth+1))
                elif "portaria" in a.get_text(" ",strip=True).lower():
                    rows.append(dict(url=link,tipo="diretriz_html",titulo=a.get_text(" ",strip=True)))
        except requests.RequestException as exc: errors.append(dict(url=url,erro=str(exc)))
        finally: (out/"inventario.json").write_text(json.dumps(dict(arquivos=rows,erros=errors),ensure_ascii=False,indent=2))
if __name__=="__main__": coleta(Path("acervo"))

