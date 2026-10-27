"""Catálogos públicos de arte, com correção de títulos e identificação da fonte.

Não baixa catálogos completos e não consulta a biblioteca sem ação do usuário.
"""
import json
import re
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from urllib.parse import urlencode, urlparse
from urllib.request import Request

from .covers import Candidate, MAX_IMAGE, normalize_image, normalized, similarity, valid_image_url
from .network import urlopen
from .tasks import Cancelled

USER_AGENT = 'HorasJogadas/3.2 (+https://github.com/JoaoPPolli/HorasJogadas)'
COVER_SOURCES = ('Steam', 'GOG', 'Wikipedia')
ICON_SOURCES = ('Steam', 'GOG')


def _check(cancel):
    if cancel is not None and cancel.is_set():
        raise Cancelled()


def _read(url, opener, cancel=None, limit=2*1024*1024):
    _check(cancel)
    with opener(Request(url, headers={'User-Agent': USER_AGENT}), timeout=10) as response:
        chunks = []; size = 0
        while True:
            _check(cancel)
            chunk = response.read(min(65536, limit + 1 - size))
            if not chunk:
                return b''.join(chunks)
            size += len(chunk)
            if size > limit:
                raise ValueError('Resposta excessiva / Response too large')
            chunks.append(chunk)


def _json(url, opener, cancel=None):
    value = json.loads(_read(url, opener, cancel))
    if not isinstance(value, dict):
        raise ValueError('Resposta inválida / Invalid response')
    return value


def _https(url, hosts):
    try:
        value = urlparse(url)
        return (value.scheme == 'https' and value.hostname in hosts and value.port is None
                and not value.username and not value.password)
    except (TypeError, ValueError):
        return False


def image_url_valid(candidate, url, kind):
    if candidate.source == 'Steam':
        if kind == 'cover':
            return valid_image_url(url, candidate.app_id)
        try:
            p = urlparse(url)
            host = p.hostname or ''
            return (p.scheme == 'https' and (host.endswith('.steamstatic.com') or host == 'cdn.akamai.steamstatic.com')
                    and not p.username and not p.password and p.port is None
                    and re.fullmatch(r'/steamcommunity/public/images/apps/' + str(candidate.app_id) + r'/[a-fA-F0-9]+\.(?:jpg|png|ico)', p.path) is not None)
        except (TypeError, ValueError):
            return False
    if candidate.source == 'GOG':
        return _https(url, {'images.gog-statics.com', 'images-1.gog-statics.com', 'images-2.gog-statics.com', 'images-3.gog-statics.com', 'images-4.gog-statics.com'})
    if candidate.source == 'Wikipedia' and kind == 'cover':
        return _https(url, {'upload.wikimedia.org', 'thumb.wikimedia.org'})
    return False


def _steam(query, opener, cancel):
    from .covers import search
    _check(cancel)
    return search(query, opener=opener)


def _gog(query, opener, cancel):
    url = 'https://catalog.gog.com/v1/catalog?' + urlencode({'query': query, 'limit': 48})
    value = _json(url, opener, cancel)
    result = []
    for item in value.get('products', [])[:48]:
        if not isinstance(item, dict):
            continue
        key = str(item.get('id', '')); name = item.get('title'); image = item.get('coverHorizontal', '')
        page = item.get('storeLink', '')
        if not key.isdigit() or len(key) > 12 or not isinstance(name, str) or not name.strip():
            continue
        if not _https(page, {'www.gog.com', 'gog.com'}):
            continue
        candidate = Candidate(int(key), name[:300], image, similarity(query, name), 'GOG', page)
        if image_url_valid(candidate, image, 'cover'):
            result.append(candidate)
    return result


def _wiki(query, opener, cancel, fuzzy=False):
    # O operador fuzzy do CirrusSearch recupera palavras digitadas incorretamente.
    term = ' '.join(word + '~' if len(word) >= 4 else word for word in normalized(query).split()) if fuzzy else query
    url = 'https://en.wikipedia.org/w/api.php?' + urlencode({
        'action': 'query', 'format': 'json', 'generator': 'search', 'gsrsearch': term,
        'gsrnamespace': 0, 'gsrlimit': 8, 'prop': 'pageimages|description',
        'piprop': 'thumbnail', 'pithumbsize': 1000, 'pilicense': 'any',
    })
    value = _json(url, opener, cancel); result = []
    for item in value.get('query', {}).get('pages', {}).values():
        if not isinstance(item, dict):
            continue
        description = item.get('description', '').lower()
        if re.search(r'\b(?:character|film|soundtrack|album|franchise|company|designer|developer|publisher)\b', description):
            continue
        if not re.search(r'(?:video|computer|arcade|role-playing) game|expansion pack', description):
            continue
        name = re.sub(r'\s*\((?:video|computer|arcade) game\)$', '', item.get('title', ''))
        name = re.sub(r'\((\d{4}) (?:video|computer|arcade) game\)$', r'(\1)', name)
        key = item.get('pageid'); image = item.get('thumbnail', {}).get('source', '')
        if type(key) is not int or key <= 0 or not name:
            continue
        page = 'https://en.wikipedia.org/?curid=' + str(key)
        # Mesmo páginas sem arte ajudam a corrigir o nome antes de consultar as lojas.
        result.append(Candidate(key, name[:300], image, similarity(query, name), 'Wikipedia', page))
    return result


class SearchResults(list):
    """Lista compatível com os consumidores antigos, com falhas parciais visíveis."""
    def __init__(self, values=(), warnings=()):
        super().__init__(values)
        self.warnings = tuple(warnings)


def search_artwork(query, opener=urlopen, *, source=None, kind='cover', cancel=None):
    query = query.strip()[:200]
    if not query:
        return SearchResults()
    available = ICON_SOURCES if kind == 'icon' else COVER_SOURCES
    if source is not None and source not in available:
        raise ValueError('Fonte inválida / Invalid source')
    sources = (source,) if source else available
    providers = {'Steam': _steam, 'GOG': _gog, 'Wikipedia': _wiki}
    # Ícones também aproveitam os títulos canônicos da Wikipedia, quando todas as fontes foram escolhidas.
    lookup_sources = sources + (('Wikipedia',) if kind == 'icon' and source is None else ())
    collected = {}; warnings = []; successful = set()
    def run(name, term, fuzzy=False):
        _check(cancel)
        try:
            values = _wiki(term, opener, cancel, True) if fuzzy else providers[name](term, opener, cancel)
            return name, values, None
        except Cancelled:
            raise
        except Exception as error:
            return name, [], str(error)
    def absorb(results):
        for name, values, error in results:
            if error:
                warnings.append(name + ': ' + error)
            else:
                successful.add(name)
            for item in values:
                item = replace(item, score=similarity(query, item.name))
                collected[item.cache_key] = item
    with ThreadPoolExecutor(max_workers=3, thread_name_prefix='artwork') as pool:
        absorb(pool.map(lambda name: run(name, query), lookup_sources))
        _check(cancel)
        confident = any(item.score >= .93 for item in collected.values())
        if not confident and 'Wikipedia' in lookup_sources:
            absorb([run('Wikipedia', query, True)])
        canonical = sorted((item for item in collected.values() if item.score >= .65 and
                            (item.source == 'Wikipedia' or item.score >= .88)),
                           key=lambda item: item.score, reverse=True)
        # Consulta novamente as fontes que não reconheceram o título; mantém a
        # pontuação contra o texto digitado, sem transformar sugestão em certeza.
        corrected = canonical[0].name if canonical else ''
        if corrected and normalized(corrected) != normalized(query):
            missing = [name for name in lookup_sources if not any(
                item.source == name and normalized(item.name) == normalized(corrected)
                for item in collected.values())]
            absorb(pool.map(lambda name: run(name, corrected), missing))
        elif not canonical:
            # Busca parcial cobre pequenos erros mesmo se a enciclopédia estiver indisponível.
            words = normalized(query).split()
            token = max(words, key=len, default='')
            partial = token[:max(3, len(token)-2)]
            if len(partial) >= 3 and partial != normalized(query):
                absorb(pool.map(lambda name: run(name, partial), [name for name in sources if name != 'Wikipedia']))
    _check(cancel)
    if not successful:
        raise ValueError('\n'.join(warnings) or 'Busca indisponível / Search unavailable')
    values = [item for item in collected.values() if item.source in sources and
              image_url_valid(item, item.image_url, 'cover') and item.score >= .35]
    values.sort(key=lambda item: (-item.score, sources.index(item.source), item.name))
    # Limite por fonte preserva alternativas de arte para o mesmo jogo.
    counts = {}; selected = []
    for item in values:
        counts[item.source] = counts.get(item.source, 0) + 1
        if counts[item.source] <= 8:
            selected.append(item)
    return SearchResults(selected, warnings)


def _steam_icon_url(app_id, opener, cancel):
    # APIs oficiais públicas retornam o hash do ícone sem conta, chave ou HTML.
    inputs = [
        ('ICommunityService/GetApps', {'appids': [app_id]}),
        ('IStoreBrowseService/GetItems', {'ids': [{'appid': app_id}],
          'context': {'language': 'english', 'country_code': 'US'},
          'data_request': {'include_assets': True}}),
    ]
    for method, payload in inputs:
        _check(cancel)
        try:
            endpoint = 'https://api.steampowered.com/' + method + '/v1/?' + urlencode({'input_json': json.dumps(payload)})
            value = _json(endpoint, opener, cancel).get('response', {})
            items = value.get('apps', []) if method.startswith('ICommunity') else value.get('store_items', [])
            for item in items:
                if not isinstance(item, dict) or item.get('appid') != app_id:
                    continue
                digest = item.get('icon') if method.startswith('ICommunity') else item.get('assets', {}).get('community_icon')
                if isinstance(digest, str) and re.fullmatch(r'[a-fA-F0-9]{40}', digest):
                    return 'https://shared.fastly.steamstatic.com/steamcommunity/public/images/apps/' + str(app_id) + '/' + digest + '.jpg'
        except Cancelled:
            raise
        except Exception:
            continue
    raise ValueError('Ícone indisponível na Steam / Steam icon unavailable')


def download_artwork(candidate, cancel, opener=urlopen, kind='cover'):
    _check(cancel)
    if type(candidate.app_id) is not int or not 0 < candidate.app_id < 10**12:
        raise ValueError('ID inválido / Invalid ID')
    url = candidate.image_url
    if kind == 'icon':
        if candidate.source == 'Steam':
            url = _steam_icon_url(candidate.app_id, opener, cancel)
        elif candidate.source == 'GOG':
            value = _json('https://api.gog.com/products/' + str(candidate.app_id), opener, cancel)
            images = value.get('images', {})
            url = images.get('icon') or images.get('sidebarIcon') or ''
            if isinstance(url, str) and url.startswith('//'):
                url = 'https:' + url
        else:
            raise ValueError('Fonte sem ícones / Source has no icons')
    if not image_url_valid(candidate, url, kind):
        raise ValueError('Imagem indisponível nesta fonte / Image unavailable from this source')
    return normalize_image(_read(url, opener, cancel, MAX_IMAGE), kind)
