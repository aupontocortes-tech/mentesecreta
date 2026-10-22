"""Envio para o YouTube do canal Veil Frequency.
python3 veil/yt.py me                              -> mostra o canal da chave
python3 veil/yt.py up video.mp4 episodio.json [agora|agendar]
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
esperado = os.environ.get('VF_CHANNEL_ID', '').strip()
if (esperado and me['id'] != esperado) or (not esperado and 'veil' not in me['snippet']['title'].lower()):
    sys.exit('ERRO: a chave não é do canal Veil Frequency (' + me['snippet']['title'] + ')')

r = json.load(open(sys.argv[3], encoding='utf-8'))
modo = sys.argv[4] if len(sys.argv) > 4 else 'agendar'
desc = r['descricao']
if r.get('creditos'):
    desc += '\n\nImages:\n' + '\n'.join('• ' + x for x in r['creditos'])
desc += '\n\n' + r.get('hashtags', '#horror #analoghorror #creepy')
# containsSyntheticMedia: o vídeo imita gravação real, então marcamos como conteúdo alterado/sintético
status = {'selfDeclaredMadeForKids': False, 'containsSyntheticMedia': True}
if modo == 'agora':
    status['privacyStatus'] = 'public'
else:  # agenda para as 19h de Nova York (23:00 UTC)
    agora = datetime.datetime.now(datetime.timezone.utc)
    alvo = agora.replace(hour=23, minute=0, second=0, microsecond=0)
    if alvo - agora < datetime.timedelta(minutes=20):
        alvo += datetime.timedelta(days=1)
    status['privacyStatus'] = 'private'
    status['publishAt'] = alvo.isoformat().replace('+00:00', 'Z')
body = {'snippet': {'title': r['titulo'][:100], 'description': desc[:4900], 'tags': r.get('tags', []), 'categoryId': '24',
                    'defaultLanguage': 'en', 'defaultAudioLanguage': 'en'}, 'status': status}
v = yt.videos().insert(part='snippet,status', body=body,
                       media_body=MediaFileUpload(sys.argv[2], chunksize=-1, resumable=True)).execute()
print('VIDEO_ID=' + v['id'], status.get('publishAt', 'publicado agora'))
