"""python -m scripts.extrair manifest.json > questoes.jsonl"""
import json,re,sys
from pathlib import Path
import fitz
from app.data import Questao

HEADER=re.compile(r"^\s*QUESTÃO\s+(?:(DISCURSIVA)\s*)?(D)?\s*0*(\d{1,3})\s*$",re.I)
ALT=re.compile(r"^\s*([A-E])(?:[).:]|\s)\s*(.*)$")
def respostas(texto):
    return {int(n):v.upper() for n,v in re.findall(r"QUESTÃO\s+(\d+)\s*(?:\|\s*Gabarito\s*)?(ANULAD[AO]|[A-E])\b",texto,re.I)}

def extrair(meta,root):
    refs=meta.get("questoes",{})
    answers={}
    if meta.get("arquivo_gabarito"):
        with fitz.open(root/meta["arquivo_gabarito"]) as pdf:
            answers=respostas("\n".join(p.get_text(sort=True) for p in pdf))
    current=None
    def finish(q):
        if not q: return
        info=refs.get(q["ref"],{})
        if "componente" not in info:
            raise ValueError(f'Classifique FG/CE no manifesto: {q["ref"]}')
        stem=[]; opts={}; key=None
        for line in q["linhas"]:
            match=ALT.match(line) if q["tipo"]=="objetiva" else None
            if match and match[1]==chr(65+len(opts)):
                key=match[1]; opts[key]=match[2]
            elif key: opts[key]+=" "+line
            else: stem.append(line)
        answer=answers.get(q["numero"]) if q["tipo"]=="objetiva" else None
        record={k:meta[k] for k in ("ano","area","curso","pdf","caderno") if k in meta}
        record.update(numero=q["numero"],tipo=q["tipo"],enunciado=" ".join(stem),alternativas=opts,
                      pagina=q["pagina"],pagina_final=q["fim"],gabarito=answer if answer in list("ABCDE") else None,
                      anulada=bool(answer and answer.startswith("ANULAD")),objetos=[],competencias=[])
        record.update(info)
        if info.get("regiao_tabela"):
            import pymupdf
            page_no,rect=info["regiao_tabela"]
            with pymupdf.open(root/meta["arquivo"]) as original:
                tables=original[page_no-1].find_tables(clip=pymupdf.Rect(rect)).tables
                if not tables: raise ValueError("Tabela sem células detectáveis")
                record.setdefault("midia",[]).extend({"formato":"markdown","conteudo":t.to_markdown()} for t in tables)
        if info.get("formula_fracao"):
            num,den=info["formula_fracao"]
            record.setdefault("midia",[]).append({"formato":"latex","conteudo":r"\frac{"+str(num)+"}{"+str(den)+"}"})
        if info.get("arestas"):
            edges=info["arestas"]
            if not all(re.fullmatch("[A-Za-z][A-Za-z0-9_]*",v) for edge in edges for v in edge): raise ValueError("Identificador de diagrama inválido")
            record.setdefault("midia",[]).append({"formato":"mermaid","conteudo":"flowchart TD\n"+"\n".join(a+" --> "+b for a,b in edges)})
        return Questao.model_validate(record)
    with fitz.open(root/meta["arquivo"]) as doc:
        for page in doc:
            for line in page.get_text(sort=True).splitlines():
                if line.strip().startswith("CADERNO DIDÁTICO |") or any(re.fullmatch(pattern,line.strip()) for pattern in meta.get("ignorar_linhas",[])): continue
                if "QUESTIONÁRIO DE PERCEPÇÃO" in line.upper() and current:
                    yield finish(current); return
                match=HEADER.match(line)
                if match:
                    if current: yield finish(current)
                    disc=bool(match[1] or match[2]); n=int(match[3])
                    current=dict(ref=("D" if disc else "")+str(n),tipo="discursiva" if disc else "objetiva",numero=n,pagina=page.number+1,fim=page.number+1,linhas=[])
                elif current and line.strip():
                    current["linhas"].append(line.strip()); current["fim"]=page.number+1
        if current: yield finish(current)

if __name__=="__main__":
    path=Path(sys.argv[1]); manifest=json.loads(path.read_text())
    for q in extrair(manifest,path.parent): print(q.model_dump_json())

