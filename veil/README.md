# Veil Frequency
Canal de terror em inglês (YouTube Shorts). Série fictícia: "Transmissions That Should Never Have Been Received".
Mora dentro do repositório do Mente Secreta, na pasta `veil/`, mas é um canal separado (chave e workflow próprios).

**Como funciona**
1. Uma vez por semana o Claude escreve episódios até a fila `veil/serie/fila/` ter 7 (ver `PROMPT_ROTEIROS_SEMANAL.txt`), seguindo a bíblia `serie/BIBLIA.md`.
2. Todo dia às 16h de Brasília o GitHub Actions (`.github/workflows/veil.yml`) pega o próximo episódio, busca fotos grátis
   (Openverse: domínio público / CC BY, com crédito na descrição), gera a voz em inglês (Edge TTS, Christopher grave + filtro de rádio),
   monta o vídeo e AGENDA para 18h de Brasília.
3. O episódio publicado vai para `serie/publicados/` com o ID do vídeo.

**Secret do repositório**: `VF_YT_TOKEN_JSON` (chave da conta do Veil Frequency, gerada com `auth.py` da raiz, logado no canal Veil Frequency).
Variável opcional: `VF_CHANNEL_ID` (trava no ID do canal).

**Teste local**: `python3 veil/vf.py veil/serie/fila/01_ligacao_911.json out`
