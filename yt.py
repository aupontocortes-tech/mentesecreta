"""Envio para o YouTube do canal Mente Secreta.
python3 yt.py me                          -> mostra o canal da chave
python3 yt.py up video.mp4 roteiro.json [agora|agendar]
A chave vem do Secret YT_TOKEN_JSON (nunca salve no repositório)."""
import os, sys, json, datetime
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request

c = Credentials.from_authorized_user_info(json.loads(os.environ['YT_TOKEN_JSON']))
if not c.valid: c.refresh(Request())
yt = build('youtube', 'v3', credentials=c)
me = yt.channels().list(part='snippet', mine=True).execute()['items'][0]

if sys.argv[1] == 'me':
    print(me['id'], me['snippet']['title']); sys.exit()

# trava de segurança: só publica no Mente Secreta
esperado = os.environ.get('MS_CHANNEL_ID', '').strip()
if (esperado and me['id'] != esperado) or (not esperado and 'mente secreta' not in me['snippet']['title'].lower()):
    sys.exit('ERRO: a chave não é do canal Mente Secreta (' + me['snippet']['title'] + ')')

r = json.load(open(sys.argv[3], encoding='utf-8')); modo = sys.argv[4] if len(sys.argv) > 4 else 'agendar'
desc = r['descricao']
if r.get('fontes'): desc += '\n\nFontes:\n' + '\n'.join('• ' + f for f in r['fontes'])
cred = [s.get('credito') for s in r['scenes'] if s.get('credito')]
if cred: desc += '\n\nImagens (domínio público):\n' + '\n'.join('• ' + x for x in dict.fromkeys(cred))
desc += '\n\n' + r.get('hashtags', '#psicologia #mentesecreta')
status = {'selfDeclaredMadeForKids': False, 'containsSyntheticMedia': False}
if modo == 'agora':
    status['privacyStatus'] = 'public'
else:  # agenda para o próximo meio-dia de Brasília (15:00 UTC)
    agora = datetime.datetime.now(datetime.timezone.utc)
    alvo = agora.replace(hour=15, minute=0, second=0, microsecond=0)
    if alvo - agora < datetime.timedelta(minutes=20): alvo += datetime.timedelta(days=1)
    status['privacyStatus'] = 'private'; status['publishAt'] = alvo.isoformat().replace('+00:00', 'Z')
body = {'snippet': {'title': r['titulo'][:100], 'description': desc[:4900], 'tags': r.get('tags', []), 'categoryId': '27',
                    'defaultLanguage': 'pt-BR', 'defaultAudioLanguage': 'pt-BR'}, 'status': status}
v = yt.videos().insert(part='snippet,status', body=body, media_body=MediaFileUpload(sys.argv[2], chunksize=-1, resumable=True)).execute()
print('VIDEO_ID=' + v['id'], status.get('publishAt', 'publicado agora'))
