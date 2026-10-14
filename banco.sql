-- Banco do site Brasil 2026 — rodar num projeto Supabase NOVO.
--
-- ⚠️ NOVO, não o do Inksa. Site público de política não divide banco com dado
-- de cliente de delivery: uma falha de política aqui exporia a outra coisa.
--
-- ⚠️ TODA TABELA NOVA NASCE ABERTA AO ANON no Supabase. Já aconteceu duas vezes
-- no Inksa. Por isso cada tabela aqui liga o RLS e declara as políticas na
-- mesma migração que a cria — nunca "depois".

-- ============================================================
-- 1. APOIOS  — o contador do botão "Eu acredito na virada"
-- ============================================================
create table if not exists public.apoios (
  id    smallint primary key default 1,
  total bigint   not null default 0,
  constraint apoios_linha_unica check (id = 1)   -- a tabela tem UMA linha, só
);
insert into public.apoios (id, total) values (1, 0) on conflict (id) do nothing;

alter table public.apoios enable row level security;

-- Visitante LÊ o total, mas não escreve direto: se pudesse dar UPDATE,
-- qualquer um com a chave anon zeraria ou inflaria o contador do navegador.
drop policy if exists apoios_leitura on public.apoios;
create policy apoios_leitura on public.apoios
  for select to anon, authenticated using (true);

-- A escrita acontece só por esta função, que soma 1 e devolve o novo total.
-- security definer = roda com o dono da função, furando o RLS de propósito e
-- apenas para esta operação.
create or replace function public.soma_apoio()
returns bigint
language sql
security definer
set search_path = public
as $$
  update public.apoios set total = total + 1 where id = 1 returning total;
$$;

revoke all on function public.soma_apoio() from public;
grant execute on function public.soma_apoio() to anon, authenticated;

-- ============================================================
-- 2. COMENTARIOS  — com moderação
-- ============================================================
create table if not exists public.comentarios (
  id         bigserial primary key,
  noticia_id text        not null,
  nome       text        not null default 'Anônimo',
  texto      text        not null,
  aprovado   boolean     not null default false,   -- nasce ESCONDIDO
  criado_em  timestamptz not null default now(),
  constraint comentario_tamanho check (char_length(texto) between 1 and 600),
  constraint nome_tamanho       check (char_length(nome)  between 1 and 40)
);
create index if not exists comentarios_por_noticia
  on public.comentarios (noticia_id, criado_em desc) where aprovado;

alter table public.comentarios enable row level security;

-- Lê só o que já foi aprovado.
drop policy if exists comentarios_leitura on public.comentarios;
create policy comentarios_leitura on public.comentarios
  for select to anon, authenticated using (aprovado = true);

-- Qualquer um escreve, mas entra desaprovado. ⚠️ O `with check` precisa travar
-- o aprovado em false — senão o visitante manda aprovado=true no corpo do POST
-- e publica sozinho, furando a moderação inteira.
drop policy if exists comentarios_escrita on public.comentarios;
create policy comentarios_escrita on public.comentarios
  for insert to anon, authenticated with check (aprovado = false);

-- Sem política de UPDATE e DELETE de propósito: ninguém edita nem apaga
-- comentário pelo site. Moderação é feita no painel do Supabase.

-- ============================================================
-- 3. PRESENCA  — "quantas pessoas online agora"
-- ============================================================
-- Cada aba aberta avisa que está viva a cada 30s. O site conta quem avisou nos
-- últimos 60s. É contagem de verdade: se ninguém estiver no site, mostra o que
-- for real, e o selo some.
create table if not exists public.presenca (
  sessao   uuid        primary key,
  visto_em timestamptz not null default now()
);
create index if not exists presenca_recente on public.presenca (visto_em desc);

alter table public.presenca enable row level security;

drop policy if exists presenca_leitura on public.presenca;
create policy presenca_leitura on public.presenca
  for select to anon, authenticated using (true);

drop policy if exists presenca_entra on public.presenca;
create policy presenca_entra on public.presenca
  for insert to anon, authenticated with check (true);

drop policy if exists presenca_renova on public.presenca;
create policy presenca_renova on public.presenca
  for update to anon, authenticated using (true) with check (true);

-- Limpeza: sem isto a tabela cresce para sempre e a contagem fica lenta.
-- Agende em Database → Cron (pg_cron) de hora em hora:
--     select public.limpa_presenca();
create or replace function public.limpa_presenca()
returns void
language sql
security definer
set search_path = public
as $$
  delete from public.presenca where visto_em < now() - interval '10 minutes';
$$;

-- ⚠️ ESTE REVOKE NÃO É OPCIONAL. O advisor do Supabase pegou isto em 14/10:
-- sem ele, a função fica exposta em /rest/v1/rpc/limpa_presenca e QUALQUER UM
-- apaga a tabela de presença, zerando o contador de "pessoas online" na hora.
-- O pg_cron roda como dono e não precisa deste grant.
revoke execute on function public.limpa_presenca() from anon, authenticated, public;

-- ============================================================
-- 4. CONTATOS  — quem quer anunciar, pelo formulário da aba "Anuncie aqui"
-- ============================================================
-- Sem e-mail no site de propósito: e-mail exposto vira alvo de robô de spam em
-- poucos dias, e ainda exigiria criar uma conta só para isso.
create table if not exists public.contatos (
  id        bigserial primary key,
  nome      text        not null,
  contato   text        not null,      -- whatsapp ou e-mail, como a pessoa preferir
  espaco    text,
  mensagem  text,
  criado_em timestamptz not null default now(),
  constraint nome_ok     check (char_length(nome)    between 2 and 80),
  constraint contato_ok  check (char_length(contato) between 5 and 120),
  constraint mensagem_ok check (mensagem is null or char_length(mensagem) <= 800)
);
alter table public.contatos enable row level security;

drop policy if exists contatos_escrita on public.contatos;
create policy contatos_escrita on public.contatos
  for insert to anon, authenticated with check (true);

-- ⚠️ NÃO EXISTE POLICY DE SELECT, E ISSO É DE PROPÓSITO.
-- Aqui ficam nome e telefone de pessoas reais. A chave anon é pública (está no
-- HTML); se houvesse leitura, qualquer um baixaria a lista inteira de
-- interessados com uma linha de fetch. Testado em 14/10: a tentativa devolve [].
-- Para ler, use o painel do Supabase (chave de serviço).

-- ============================================================
-- Conferir no fim: Database → Advisors não pode acusar tabela sem RLS.
-- ============================================================
