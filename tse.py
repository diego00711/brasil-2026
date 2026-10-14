# Resultado da eleição direto do TSE — escreve dados/eleicao.json
#
# ⚠️ POR QUE ESTE ARQUIVO EXISTE E NÃO FOI ESCRITO NA MÃO
#
# A eleição de 04/10/2026 aconteceu depois do meu corte de conhecimento. Eu NÃO
# sei de cabeça quem venceu onde, e mapa eleitoral preenchido de memória é
# exatamente como se publica informação falsa sem querer.
#
# Então todo número daqui vem do endpoint oficial do TSE, e o site mostra a data
# e a hora da apuração que o próprio TSE carimbou. Se o TSE sair do ar, o site
# mostra o último dado bom com a data dele — nunca um número inventado.
#
# Fonte: https://resultados.tse.jus.br/oficial/ele2026/
#   6257 = Federal 1º turno (Presidente)   | 6258 = Federal 2º turno
#   6259 = Estadual 1º turno (Governador)  | 6260 = Estadual 2º turno (só AM e RN)

import json, sys, urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path

BR = timezone(timedelta(hours=-3))
RAIZ = Path(__file__).parent
SAIDA = RAIZ / "dados" / "eleicao.json"
BASE = "https://resultados.tse.jus.br/oficial/ele2026"
CAB = {"User-Agent": "Mozilla/5.0", "Accept": "application/json,*/*"}

UFS = ["ac","al","am","ap","ba","ce","df","es","go","ma","mg","ms","mt","pa",
       "pb","pe","pi","pr","rj","rn","ro","rr","rs","sc","se","sp","to"]

# ⚠️ CLASSIFICAÇÃO EDITORIAL, NÃO DADO DO TSE.
# O TSE informa partido, não "campo político". Agrupar partido em direita ou
# esquerda é opinião — defensável, mas opinião. Por isso ela mora aqui, visível,
# e o site publica esta tabela junto com o mapa, para o leitor discordar se
# quiser. O que NUNCA pode acontecer é a cor do mapa parecer dado oficial.
CAMPO = {
    "direita": ["PL", "PP", "REPUBLICANOS", "NOVO", "PRD", "UNIÃO", "UNIÃO BRASIL", "PSDB", "PSD", "MDB", "PODE", "SOLIDARIEDADE", "AVANTE", "DC", "PMB", "AGIR", "MOBILIZA"],
    "esquerda": ["PT", "PSOL", "PCDOB", "PC DO B", "PDT", "PSB", "REDE", "PV", "UP", "PCB", "PSTU", "PCO"],
}


def campo_do(sigla: str) -> str:
    s = (sigla or "").upper().strip()
    for nome, siglas in CAMPO.items():
        if s in siglas:
            return nome
    return "indefinido"


def pega(url: str):
    req = urllib.request.Request(url, headers=CAB)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8", "ignore"))


def candidatos(j: dict) -> list:
    """Achata carg[0].agr[].par[].cand[] numa lista simples e ordenada."""
    saida = []
    for carg in j.get("carg", []):
        for agr in carg.get("agr", []):
            for par in agr.get("par", []):
                for c in par.get("cand", []):
                    try:
                        votos = int(c.get("vap", "0") or 0)
                    except ValueError:
                        votos = 0
                    saida.append({
                        "nome": c.get("nmu") or c.get("nm", ""),
                        "numero": c.get("n", ""),
                        "partido": par.get("sg", ""),
                        "coligacao": agr.get("com", ""),
                        "votos": votos,
                        "percentual": c.get("pvap", ""),
                        "eleito": c.get("e", "") == "s" or c.get("st", "") in ("Eleito", "Eleito por QP"),
                        "campo": campo_do(par.get("sg", "")),
                    })
    saida.sort(key=lambda c: c["votos"], reverse=True)
    return saida


def resultado(eleicao: str, cargo: str, uf: str):
    j = pega(f"{BASE}/{eleicao}/dados/{uf}/{uf}-c{cargo}-e{int(eleicao):06d}-u.json")
    cands = candidatos(j)
    v = j.get("v", {})
    s = j.get("s", {})
    return {
        "uf": uf.upper(),
        "apurado": s.get("pst", ""),
        "atualizado_tse": f"{j.get('dg','')} {j.get('hg','')}",
        "votos_validos": v.get("vvc", ""),
        "candidatos": cands[:8],
        "vencedor": cands[0] if cands else None,
    }


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    dados = {"gerado_em": datetime.now(BR).isoformat(), "fonte": "TSE — resultados.tse.jus.br"}

    print("Presidente — 1º turno, Brasil")
    dados["presidente_br"] = resultado("6257", "0001", "br")
    v = dados["presidente_br"]["vencedor"]
    print(f"  {dados['presidente_br']['apurado']}% apurado | 1º lugar: {v['nome']} ({v['partido']}) {v['percentual']}%")

    print("\nPresidente — 1º turno, por estado")
    dados["presidente_uf"] = {}
    for uf in UFS:
        try:
            r = resultado("6257", "0001", uf)
            dados["presidente_uf"][uf.upper()] = r
            v = r["vencedor"]
            print(f"  {uf.upper()}  {v['nome'][:26]:<26} {v['partido']:<14} {v['percentual']:>6}%  [{v['campo']}]")
        except Exception as e:
            print(f"  {uf.upper()}  FALHA: {str(e)[:50]}")

    print("\nGovernador — 1º turno, por estado")
    dados["governador_uf"] = {}
    for uf in UFS:
        try:
            r = resultado("6259", "0003", uf)
            dados["governador_uf"][uf.upper()] = r
            v = r["vencedor"]
            print(f"  {uf.upper()}  {v['nome'][:26]:<26} {v['partido']:<14} {v['percentual']:>6}%  [{v['campo']}]")
        except Exception as e:
            print(f"  {uf.upper()}  FALHA: {str(e)[:50]}")

    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(json.dumps(dados, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\ngravado em {SAIDA}")


if __name__ == "__main__":
    main()
