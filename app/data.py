"""Modelo comum ao extrator, consumidor e cliente de busca."""
import hashlib
from pydantic import BaseModel, Field, model_validator
from typing import Literal

class Media(BaseModel):
    formato: Literal["latex","mermaid","markdown"]
    conteudo: str

class Questao(BaseModel):
    curso: str = Field(min_length=1)
    area: str = Field(min_length=1)
    ano: int = Field(ge=2004,le=2100)
    componente: Literal["FG","CE"]
    tipo: Literal["objetiva","discursiva"]
    numero: int = Field(gt=0)
    caderno: str = "regular"
    texto_base: str = ""
    enunciado: str = Field(min_length=1)
    alternativas: dict[str,str] = Field(default_factory=dict)
    gabarito: str | None = None
    anulada: bool = False
    competencias: list[str]
    objetos: list[str]
    pdf: str
    pagina: int = Field(ge=1)
    pagina_final: int = Field(ge=1)
    midia: list[Media] = Field(default_factory=list)
    @model_validator(mode="after")
    def consistency(self):
        if self.pagina_final < self.pagina or (self.anulada and self.gabarito):
            raise ValueError("Página ou gabarito incompatível")
        if self.tipo=="objetiva" and (len(self.alternativas)<2 or (self.gabarito and self.gabarito not in self.alternativas)):
            raise ValueError("Alternativas incompletas ou chave incompatível")
        return self
    def chave(self):
        fields=(self.ano,self.curso,self.caderno,self.tipo,self.numero)
        import json
        return hashlib.sha256(json.dumps(fields,ensure_ascii=False).encode()).hexdigest()

