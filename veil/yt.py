"""Envio para o YouTube do canal Veil Frequency.
python3 veil/yt.py me                              -> mostra o canal da chave
python3 veil/yt.py up video.mp4 episodio.json [agora|agendar|pt|longo] [capa.jpg]
A chave vem do Secret VF_YT_TOKEN_JSON (nunca salve no repositório)."""
import os, sys, json, datetime
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request

c = Credentials.from_authorized_user_info(json.loads(os.environ['YT_TOKEN_JSON']))
if not c.valid:
    c.refresh(Request())
yt = build('youtube', 'v3', credentials=c)
me = yt.channels().list(part='snippet', mine=True).execute()['items'][0]

if sys.argv[1] == 'me':
    print(me['id'], me['snippet']['title']); sys.exit()

# trava de segurança: só publica no Veil Frequency
esperado = os.environ.get('VF_CHANNEL_ID', '').strip() or 'UCoe34hx015k4fnSI9IwwElg'
if (esperado and me['id'] != esperado) or (not esperado and 'veil' not in me['snippet']['title'].lower()):
    sys.exit('ERRO: a chave não é do canal Veil Frequency (' + me['snippet']['title'] + ')')

if sys.argv[1] == 'tornar_publico':   # botão do app: a prévia privada vira pública na hora
    vid = sys.argv[2]
    v = yt.videos().list(part='status', id=vid).execute()['items'][0]
    st = v['status']; st['privacyStatus'] = 'public'; st.pop('publishAt', None)
    yt.videos().update(part='status', body={'id': vid, 'status': st}).execute()
    print('PUBLICO=' + vid); sys.exit()

r = json.load(open(sys.argv[3], encoding='utf-8'))
modo = sys.argv[4] if len(sys.argv) > 4 else 'agendar'
desc = r['descricao']
if r.get('creditos'):
    desc += '\n\nImages:\n' + '\n'.join('• ' + x for x in r['creditos'])
desc += '\n\n' + r.get('hashtags', '#horror #analoghorror #creepy')
# containsSyntheticMedia: o vídeo imita gravação real, então marcamos como conteúdo alterado/sintético
status = {'selfDeclaredMadeForKids': False, 'containsSyntheticMedia': True}
lingua = 'en'
if modo == 'longo_pt':   # versão dublada do vídeo longo: não listada
    lingua = 'pt'
    status['privacyStatus'] = 'unlisted'
    desc = (r.get('resumo_pt') or '') + '\n\nVersão em português (não listada) só para conferência.'
elif modo in ('longo', 'longo_privado'):   # vídeo longo deitado, sem #Shorts (privado = prévia esperando o botão)
    status['privacyStatus'] = 'private' if modo == 'longo_privado' else 'public'
    desc = r['descricao']
elif modo == 'pt':   # versão dublada: não listada (só abre pelo link do painel), não aparece no canal
    lingua = 'pt'
    status['privacyStatus'] = 'unlisted'
    desc = (r.get('resumo_pt') or '') + '\n\nVersão em português (não listada) só para conferência.'
elif modo == 'agora':
    status['privacyStatus'] = 'public'
else:  # agenda para as 18h de Brasília (21:00 UTC)
    agora = datetime.datetime.now(datetime.timezone.utc)
    alvo = agora.replace(hour=21, minute=0, second=0, microsecond=0)
    if alvo - agora < datetime.timedelta(minutes=20):
        alvo += datetime.timedelta(days=1)
    status['privacyStatus'] = 'private'
    status['publishAt'] = alvo.isoformat().replace('+00:00', 'Z')
titulo = ('[PT] ' + (r.get('titulo_pt') or r['titulo'])) if lingua == 'pt' else r['titulo']
body = {'snippet': {'title': titulo[:100], 'description': desc[:4900], 'tags': r.get('tags', []), 'categoryId': '24',
                    'defaultLanguage': lingua, 'defaultAudioLanguage': lingua}, 'status': status}
v = yt.videos().insert(part='snippet,status', body=body,
                       media_body=MediaFileUpload(sys.argv[2], chunksize=-1, resumable=True)).execute()
print('VIDEO_ID=' + v['id'], status.get('publishAt', 'publicado agora'))
capa = sys.argv[5] if len(sys.argv) > 5 else ''
if capa and os.path.exists(capa):
    try:
        yt.thumbnails().set(videoId=v['id'], media_body=MediaFileUpload(capa, mimetype='image/jpeg')).execute(); print('capa ok')
    except Exception as e:
        print('AVISO: capa não enviada (o canal precisa de verificação por telefone):', str(e)[:200])
