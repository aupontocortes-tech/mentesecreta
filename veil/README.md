# Veil Frequency
Canal de terror em inglês (YouTube Shorts). **Uma história de terror completa por vídeo.**
Mora dentro do repositório do Mente Secreta, na pasta `veil/`, mas é um canal separado (chave e workflow próprios).

**Como funciona**
1. Uma vez por semana o Claude escreve histórias até a fila `veil/historias/fila/` ter 7 (ver `PROMPT_ROTEIROS_SEMANAL.txt`).
2. Todo dia às 16h de Brasília o GitHub Actions (`.github/workflows/veil.yml`) pega a próxima história, gera as imagens com IA
   (Pollinations, grátis, sem conta), as vozes em inglês (Edge TTS: narrador homem/mulher, idosa, criança, voz sombria),
   a trilha e monta o vídeo — e AGENDA para 18h de Brasília.
3. A história publicada vai para `historias/publicados/` com o ID do vídeo. (`serie/publicados/` guarda os 2 episódios antigos da série.)

**Secret do repositório**: `VF_YT_TOKEN_JSON`.
**Pausar**: em `CONFIG_CANAL.md`, seção `## PAUSAS`, a linha `- pausado`.
**Teste local**: `python3 veil/historia.py veil/historias/fila/01_basement.json out`
