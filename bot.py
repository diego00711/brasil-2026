# Bot de notícias — roda de hora em hora e escreve dados/noticias.json
#
# O QUE ELE FAZ E O QUE ELE NÃO FAZ
#
# Ele é um AGREGADOR: lê feeds RSS públicos e guarda manchete + resumo curto +
# fonte + link. Ele NÃO copia o texto da matéria e NÃO reescreve nada. Quem
# clica vai ler no site de origem.
#
# Isso é de propósito, por dois motivos:
#   1. Republicar texto inteiro de jornal é violação de direito autoral — foi o
#      que matou o canal de cortes.
#   2. O site não afirma nada por conta própria, então não há o que checar.
#      Ele mostra quem afirmou, com link. Numa época de eleição isso é a
#      diferença entre um agregador e um problema jurídico.
#
# Se um dia entrar texto opinativo próprio, ele entra por outro caminho, com
# alguém lendo antes de publicar.

import json, re, sys, html, hashlib
import urllib.request
from datetime import datetime, timezone, timedelta
from pathlib import Path
from email.utils import parsedate_to_datetime

BR = timezone(timedelta(hours=-3))
RAIZ = Path(__file__).parent
SAIDA = RAIZ / "dados" / "noticias.json"
MAX_POR_FONTE = 12       # evita uma fonte dominar a home
MAX_TOTAL = 90
GUARDA_HORAS = 72        # notícia mais velha que isso sai da lista

# Fontes testadas em 14/10/2026. Todas responderam e todas têm feed público.
# A ordem aqui não importa; o site ordena por data.
FONTES = [
    ("Gazeta do Povo",  "https://www.gazetadopovo.com.br/feed/rss/politica.xml"),
    ("Gazeta do Povo",  "https://www.gazetadopovo.com.br/feed/rss/eleicoes.xml"),
    ("Gazeta do Povo",  "https://www.gazetadopovo.com.br/feed/rss/republica.xml"),
    ("Revista Oeste",   "https://revistaoeste.com/politica/feed/"),
    ("O Antagonista",   "https://oantagonista.com.br/brasil/feed/"),
    ("Poder360",        "https://www.poder360.com.br/feed/"),
    ("Metrópoles",      "https://www.metropoles.com/colunas/igor-gadelha/feed"),
    ("Agência Brasil",  "https://agenciabrasil.ebc.com.br/rss/politica/feed.xml"),
    ("G1 Política",     "https://g1.globo.com/rss/g1/politica/"),
]

CABECALHO = {
    "User-Agent": "Mozilla/5.0 (compatible; agregador de noticias; +contato no site)",
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
}


def limpa(texto: str) -> str:
    """Tira tag HTML, resolve entidade e normaliza espaço."""
    if not texto:
        return ""
    texto = re.sub(r"<[^>]+>", " ", texto)
    texto = html.unescape(texto)
    return re.sub(r"\s+", " ", texto).strip()


def tag(bloco: str, nome: str) -> str:
    """Pega o conteúdo da primeira <nome>, com ou sem CDATA."""
    m = re.search(rf"<{nome}\b[^>]*>(.*?)</{nome}>", bloco, re.S | re.I)
    if not m:
        return ""
    v = m.group(1)
    c = re.search(r"<!\[CDATA\[(.*?)\]\]>", v, re.S)
    return (c.group(1) if c else v).strip()


def acha_link(bloco: str) -> str:
    """RSS usa <link>texto</link>; Atom usa <link href="...">."""
    v = tag(bloco, "link")
    if v and v.startswith("http"):
        return v
    m = re.search(r'<link[^>]+href="([^"]+)"', bloco, re.I)
    return m.group(1) if m else ""


def acha_imagem(bloco: str) -> str:
    for padrao in (r'<media:content[^>]+url="([^"]+)"',
                   r'<media:thumbnail[^>]+url="([^"]+)"',
                   r'<enclosure[^>]+url="([^"]+\.(?:jpg|jpeg|png|webp)[^"]*)"',
                   r'<img[^>]+src="([^"]+)"'):
        m = re.search(padrao, bloco, re.I)
        if m:
            return html.unescape(m.group(1))
    return ""


def acha_data(bloco: str) -> datetime:
    for nome in ("pubDate", "published", "updated", "dc:date"):
        v = tag(bloco, nome)
        if not v:
            continue
        try:
            return parsedate_to_datetime(v).astimezone(BR)
        except Exception:
            pass
        try:
            return datetime.fromisoformat(v.replace("Z", "+00:00")).astimezone(BR)
        except Exception:
            pass
    return datetime.now(BR)


def busca(url: str) -> str:
    req = urllib.request.Request(url, headers=CABECALHO)
    with urllib.request.urlopen(req, timeout=25) as r:
        bruto = r.read(900_000)
    # O charset vem no cabeçalho ou na declaração XML; na dúvida, utf-8.
    enc = "utf-8"
    m = re.search(rb'encoding=["\']([\w-]+)["\']', bruto[:200])
    if m:
        enc = m.group(1).decode("ascii", "ignore")
    return bruto.decode(enc, "ignore")


def le_fonte(nome: str, url: str) -> list:
    xml = busca(url)
    blocos = re.findall(r"<item\b.*?</item>|<entry\b.*?</entry>", xml, re.S | re.I)
    itens = []
    for b in blocos[:MAX_POR_FONTE]:
        titulo = limpa(tag(b, "title"))
        link = acha_link(b)
        if not titulo or not link:
            continue
        resumo = limpa(tag(b, "description") or tag(b, "summary") or tag(b, "content:encoded"))
        itens.append({
            "id": hashlib.sha1(link.encode()).hexdigest()[:12],
            "titulo": titulo[:180],
            # Resumo curto DE PROPÓSITO: é chamada, não substituto da matéria.
            "resumo": resumo[:240] + ("…" if len(resumo) > 240 else ""),
            "link": link,
            "fonte": nome,
            "imagem": acha_imagem(b),
            "data": acha_data(b).isoformat(),
        })
    return itens


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    todas, falhas = [], []
    for nome, url in FONTES:
        try:
            itens = le_fonte(nome, url)
            todas.extend(itens)
            print(f"  ok    {len(itens):>2} de {nome} ({url.split('/')[-1]})")
        except Exception as e:
            falhas.append(nome)
            print(f"  FALHA    {nome}: {str(e)[:70]}")

    # Dedupe por link. Feeds da mesma casa repetem matéria entre editorias.
    vistos, unicas = set(), []
    for n in todas:
        if n["id"] in vistos:
            continue
        vistos.add(n["id"])
        unicas.append(n)

    corte = datetime.now(BR) - timedelta(hours=GUARDA_HORAS)
    unicas = [n for n in unicas if datetime.fromisoformat(n["data"]) >= corte]
    unicas.sort(key=lambda n: n["data"], reverse=True)
    unicas = unicas[:MAX_TOTAL]

    SAIDA.parent.mkdir(parents=True, exist_ok=True)
    SAIDA.write_text(json.dumps({
        "atualizado": datetime.now(BR).isoformat(),
        "total": len(unicas),
        "fontes_com_falha": falhas,
        "noticias": unicas,
    }, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"\n{len(unicas)} notícias em {SAIDA}")
    if falhas:
        print(f"⚠ fontes que falharam nesta rodada: {', '.join(falhas)}")


if __name__ == "__main__":
    main()
