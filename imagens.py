"""Acha pinturas de DOMÍNIO PÚBLICO para cada cena que tem "busca" e não tem "src".
Ordem: Art Institute of Chicago -> Metropolitan Museum -> Wikimedia Commons (só PD/CC0) -> Pexels (se tiver PEXELS_KEY).
Uso: python3 imagens.py roteiro.json   (grava src/credito em cada cena do próprio arquivo)"""
import sys, json, os, time, urllib.request, urllib.error, urllib.parse, random

UA = {'User-Agent': 'MenteSecretaBot/1.0 (YouTube Shorts; contato via GitHub aupontocortes-tech)'}
usadas = set()

def get(url, headers=None, timeout=20):
    for tent in range(4):
        try:
            req = urllib.request.Request(url, headers=headers or UA)
            with urllib.request.urlopen(req, timeout=timeout) as r: return json.loads(r.read().decode('utf-8'))
        except urllib.error.HTTPError as e:
            if e.code != 429 or tent == 3: raise
            time.sleep(8 * (tent + 1))
    return {}

def aic(q):
    u = ('https://api.artic.edu/api/v1/artworks/search?' + urllib.parse.urlencode({
        'q': q, 'limit': 15, 'fields': 'id,title,image_id,artist_title,is_public_domain,thumbnail',
        'query[term][is_public_domain]': 'true'}))
    for a in get(u).get('data', []):
        if not a.get('image_id') or not a.get('is_public_domain'): continue
        th = a.get('thumbnail') or {}
        if th.get('width') and th.get('height') and th['width'] > th['height'] * 1.9: continue  # muito panorâmica
        url = f"https://www.artic.edu/iiif/2/{a['image_id']}/full/1686,/0/default.jpg"
        if url in usadas: continue
        return url, f"{a.get('title','')} — {a.get('artist_title') or 'autor desconhecido'} (Art Institute of Chicago, CC0)"

def met(q):
    ids = get('https://collectionapi.metmuseum.org/public/collection/v1/search?' +
              urllib.parse.urlencode({'q': q, 'hasImages': 'true', 'medium': 'Paintings'})).get('objectIDs') or []
    for i in ids[:12]:
        o = get(f'https://collectionapi.metmuseum.org/public/collection/v1/objects/{i}')
        url = o.get('primaryImage')
        if o.get('isPublicDomain') and url and url not in usadas:
            return url, f"{o.get('title','')} — {o.get('artistDisplayName') or 'autor desconhecido'} (The Met, domínio público)"

def smk(q):
    """Statens Museum for Kunst (Dinamarca) — obras em domínio público, CC0."""
    r = get('https://api.smk.dk/api/v1/art/search/?' + urllib.parse.urlencode({
        'keys': q, 'filters': '[has_image:true],[public_domain:true],[object_names:painting]', 'rows': 20, 'lang': 'en'}))
    for it in r.get('items', []) or []:
        w, h = it.get('image_width') or 0, it.get('image_height') or 1
        th = it.get('image_thumbnail') or ''
        if not it.get('public_domain') or w < 700 or w > h * 1.9 or 'iiif' not in th: continue
        url = th.replace('!1024,', '!1600,')
        if url in usadas: continue
        t = (it.get('titles') or [{}])[0].get('title', ''); a = (it.get('production') or [{}])[0].get('creator', 'autor desconhecido')
        return url, f"{t} — {a} (SMK, domínio público)"

def commons(q):
    r = get('https://commons.wikimedia.org/w/api.php?' + urllib.parse.urlencode({
        'action': 'query', 'format': 'json', 'generator': 'search', 'gsrnamespace': 6, 'gsrlimit': 20,
        'gsrsearch': f'{q} "oil on canvas" filetype:bitmap', 'prop': 'imageinfo', 'iiprop': 'url|extmetadata|size',
        'iiurlwidth': 1600}))
    pages = sorted((r.get('query') or {}).get('pages', {}).values(), key=lambda p: p.get('index', 99))
    for p in pages:
        ii = (p.get('imageinfo') or [{}])[0]; md = ii.get('extmetadata') or {}
        lic = (md.get('LicenseShortName') or {}).get('value', '')
        if not any(k in lic.lower() for k in ('public domain', 'pd', 'cc0')): continue
        if ii.get('width', 0) < 800 or ii.get('width', 1) > ii.get('height', 1) * 1.9: continue
        url = ii.get('thumburl') or ii.get('url')
        if url in usadas: continue
        return url, f"{p['title'].replace('File:', '')} (Wikimedia Commons, {lic})"

def pexels(q):
    k = os.environ.get('PEXELS_KEY')
    if not k: return None
    r = get('https://api.pexels.com/v1/search?' + urllib.parse.urlencode({'query': q, 'orientation': 'portrait', 'per_page': 10}),
            {**UA, 'Authorization': k})
    for ph in r.get('photos', []):
        url = ph['src']['large2x']
        if url not in usadas: return url, f"Foto: {ph.get('photographer','')} (Pexels)"

FONTES_TODAS = {'aic': aic, 'met': met, 'smk': smk, 'commons': commons, 'pexels': pexels}
FONTES = [FONTES_TODAS[f] for f in os.environ.get('MS_FONTES', 'aic,met,smk,commons,pexels').split(',')]

def achar(buscas):
    for q in buscas:
        for fonte in FONTES:
            try:
                r = fonte(q)
                if r: return r
            except Exception as e:
                print(f'  {fonte.__name__} falhou para "{q}": {e}')
    return None

def main():
    arq = sys.argv[1]; spec = json.load(open(arq, encoding='utf-8'))
    for sc in spec['scenes']:
        if sc.get('src'): usadas.add(sc['src'])
    reserva = spec.get('busca_reserva', ['dark portrait oil painting', 'renaissance portrait', 'baroque painting shadow'])
    for i, sc in enumerate(spec['scenes']):
        if sc.get('src'): continue
        b = sc.get('busca') or []
        if isinstance(b, str): b = [b]
        r = achar(b) or achar(random.sample(reserva, len(reserva)))
        if not r: sys.exit(f'ERRO: nenhuma imagem para a cena {i}')
        sc['src'], sc['credito'] = r; usadas.add(r[0]); print(f'cena {i}: {r[1]}')
    json.dump(spec, open(arq, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)

if __name__ == '__main__':
    main()
