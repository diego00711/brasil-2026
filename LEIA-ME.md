# Brasil 2026 — site de notícias + mapa da eleição

Feito em 14/10/2026. Roda sozinho, custo **R$ 0**.

## O que já está pronto e funcionando

| peça | estado |
|---|---|
| Contador regressivo até 25/10 (dias, horas, min, seg, em verde) | ✅ |
| Bandeira do Brasil no cabeçalho (SVG, não foto) | ✅ |
| Agregador de notícias — 9 feeds, ~71 matérias | ✅ |
| Mapa do Brasil com o resultado por estado | ✅ |
| Espaços "Anuncie aqui" | ✅ |
| Botão "Eu acredito na virada" + contador de apoios | ⚠️ falta o banco |
| Comentários nas notícias | ⚠️ falta o banco |
| "Pessoas online agora" | ⚠️ falta o banco |

## Como rodar aqui

```bash
python bot.py     # busca as notícias  -> dados/noticias.json
python tse.py     # busca o TSE        -> dados/eleicao.json
```

Depois abra pelo servidor local (abrir o arquivo direto **não funciona** — o
navegador bloqueia a leitura dos JSON):

```bash
python -m http.server 4174
```

## ⚠️ As três coisas que faltam, e por que faltam juntas

Contador de apoios, comentários e "pessoas online" são **dados compartilhados
entre visitantes**. Isso não existe sem banco de dados — e eu **não** coloquei
número falso no lugar enquanto não tem.

Isso é decisão, não preguiça. Quando a gente desmontou o golpe do
*edificareprosperar* em 13/10, um dos marcadores era exatamente isto:

```js
Math.floor(Math.random()*(t-n+1)+n)   // "29 pessoas estão vendo agora"
```

Site que inventa prova social é site de golpe. Então, sem banco, o selo de
online **não aparece** e o contador de apoios mostra "Seja o primeiro a apoiar".

### Para ligar os três

1. Criar um projeto **novo** no Supabase (grátis). Novo, não o do Inksa — site
   público de política não compartilha banco com dado de cliente de delivery.
2. Rodar o SQL de `banco.sql`.
3. Preencher no `index.html`:

```js
const CONFIG = {
  SUPABASE_URL: "https://xxxx.supabase.co",
  SUPABASE_ANON_KEY: "...",
};
```

## Publicar

1. `git init`, subir para um repositório no GitHub.
2. Importar na **Vercel** (grátis). Framework: *Other*. Build: nenhum.
3. Em *Settings → Actions → General*, deixar "Read and write permissions"
   ligado, senão o bot não consegue comitar.

Pronto: o GitHub Actions roda `bot.py` de hora em hora, comita, a Vercel
republica sozinha.

## Regras que o site segue de propósito

- **É agregador.** Mostra manchete, resumo curto, fonte e link. Não copia nem
  reescreve o texto da matéria. Republicar matéria inteira é violação de direito
  autoral.
- **Nada de texto político gerado por IA sem revisão.** Afirmação sobre pessoa
  real, em época de eleição, publicada de hora em hora sem ninguém ler, é
  problema jurídico esperando acontecer.
- **A cor do mapa não se confunde com dado oficial.** O TSE informa partido, não
  "campo político". Quem é direita e quem é esquerda é classificação nossa, está
  escrita em `tse.py` e aparece declarada na própria página.
- **AM e RN não aparecem como vitória.** O governo lá vai a 2º turno; quem
  lidera não venceu, e o mapa diz isso em amarelo.

## Antes de publicar, trocar

- O e-mail de contato na aba "Anuncie aqui" (está `SEU-EMAIL-AQUI`).
- ⚠️ Conferir as regras do **TSE sobre propaganda eleitoral paga na internet**
  antes de aceitar anúncio de candidato ou campanha. As regras para anúncio
  político são diferentes das de anúncio comum, e a responsabilidade é de quem
  publica.

## Por que o Inksa não está aqui dentro

Conversamos isso em 14/10. Site de política nacional traz gente do Brasil
inteiro; o Inksa entrega em **Lages**. Anúncio do app aqui seria mostrado para
~99% de gente que não pode pedir. Pior: o problema medido do Inksa nunca foi
falta de tráfego — foram 14 cliques na vida do app, zero carrinho abandonado, e
só 6 lojas abrindo à noite. Tráfego nacional em cima disso não vira cadastro.
