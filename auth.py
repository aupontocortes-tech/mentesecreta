"""Gera a chave do YouTube (uma vez só). Rode no computador, logado na conta do canal Mente Secreta.
1) python3 auth.py url client_secret.json      -> abre o link, autoriza, copia a URL final (http://localhost/?...)
2) python3 auth.py fim client_secret.json "URL" -> cria token.json (cole o conteúdo no Secret YT_TOKEN_JSON e APAGUE o arquivo)"""
import sys, os, pickle
from google_auth_oauthlib.flow import Flow
CS = sys.argv[2]; SC = ['https://www.googleapis.com/auth/youtube.upload', 'https://www.googleapis.com/auth/youtube.readonly']
ST = os.path.join(os.path.dirname(os.path.abspath(CS)), 'ms_state.pkl')
if sys.argv[1] == 'url':
    f = Flow.from_client_secrets_file(CS, scopes=SC, redirect_uri='http://localhost')
    url, state = f.authorization_url(access_type='offline', prompt='consent')
    pickle.dump({'state': state, 'cv': f.code_verifier}, open(ST, 'wb')); print(url)
else:
    s = pickle.load(open(ST, 'rb'))
    f = Flow.from_client_secrets_file(CS, scopes=SC, redirect_uri='http://localhost', state=s['state']); f.code_verifier = s['cv']
    os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'; os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'
    f.fetch_token(authorization_response=sys.argv[3])
    open(os.path.join(os.path.dirname(os.path.abspath(CS)), 'token.json'), 'w').write(f.credentials.to_json())
    os.remove(ST); print('OK', bool(f.credentials.refresh_token))
