# Mente Secreta
Canal dark de psicologia no YouTube Shorts — série "O lado oculto da mente humana".

**Como funciona**
1. Uma vez por semana o Claude escreve 7 roteiros em `roteiros/fila/` (ver `PROMPT_ROTEIROS_SEMANAL.txt`).
2. Todo dia às 11h (Brasília) o GitHub Actions pega o próximo roteiro, busca pinturas em domínio público,
   gera a voz (Edge TTS, voz Antonio grave), a trilha escura e monta o vídeo — e AGENDA para 12h no YouTube.
3. O roteiro publicado vai para `roteiros/publicados/` com o ID do vídeo.
4. Painel: pausa o horário de 12h (`## PAUSAS` → `- 12h`) e o botão "rodar agora" publica na hora.

**Secrets do repositório**: `YT_TOKEN_JSON` (chave da conta do Mente Secreta, gerada com `auth.py`).
Opcional: `PEXELS_KEY` (fotos atuais grátis). Variável opcional: `MS_CHANNEL_ID`.

**Teste local**: `python3 imagens.py r.json && python3 tts.py r.json out && python3 musica.py out && python3 render.py r.json out`
