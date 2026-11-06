#!/usr/bin/env python3
"""Stage the Sára gamebook for the store screenshots, in all 12 languages.

The live release (gamebook-sara-v1) is Czech-only; the translations already exist in the repo
(data/stories/gb_sara_*/storyboard.json bubble `i18n`, data/gamebooks/sara/graph.yaml
`title_i18n` / `text_i18n`) but have not been exported yet. This script downloads the live zip
and merges those translations in (same panels, same bubble order: it checks), writing
store/screenshots/.staging/gamebook-sara.zip which the screenshot test installs over HTTP.

    python3 store/screenshots/tools/stage_sara.py
"""
import hashlib
import io
import json
import os
import sys
import urllib.request
import zipfile

import yaml  # PyYAML

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
URL = ('https://github.com/lioilsources/webtoon-content/releases/download/'
       'gamebook-sara-v1/gamebook-sara.zip')
OUT = os.path.join(ROOT, 'store', 'screenshots', '.staging')
LANGS = ['en', 'de', 'it', 'fr', 'pl', 'pt-BR', 'ja', 'ko', 'vi', 'ru', 'uk']


def main():
    os.makedirs(OUT, exist_ok=True)
    cache = os.path.join(OUT, 'gamebook-sara-live.zip')
    if not os.path.exists(cache):
        print('downloading', URL)
        urllib.request.urlretrieve(URL, cache)
    graph = yaml.safe_load(open(os.path.join(ROOT, 'data/gamebooks/sara/graph.yaml')))
    src = zipfile.ZipFile(cache)
    pack = json.loads(src.read('pack.json'))
    book = json.loads(src.read('gamebook.json'))

    book['title_i18n'] = graph['title_i18n']
    eps = {e['id']: e for e in pack['episodes']}
    stories = {s['id']: s for s in pack['stories']}
    for nid, node in book['nodes'].items():
        gnode = graph['nodes'][nid]
        by_id = {c['id']: c for c in gnode.get('choices') or []}
        for c in node.get('choices') or []:
            c['text_i18n'] = by_id[c['id']].get('text_i18n') or {}
        sb = json.load(open(os.path.join(ROOT, f'data/stories/gb_sara_{nid}/storyboard.json')))
        ep = eps[node['episode']]
        if len(sb['panels']) != len(ep['panels']):
            sys.exit(f'{nid}: panel count differs')
        langs = set(LANGS)
        for a, b in zip(ep['panels'], sb['panels']):
            if [x['text'] for x in a['bubbles']] != [x['text'] for x in b['bubbles']]:
                sys.exit(f'{nid}: bubbles differ')
            for x, y in zip(a['bubbles'], b['bubbles']):
                x['i18n'] = y.get('i18n') or {}
                langs &= set(x['i18n'])
        ep['languages'] = [l for l in LANGS if l in langs]
        ep['title_i18n'] = sb.get('title_i18n') or {}
        st = stories[node['story']]
        st['title_i18n'] = sb.get('title_i18n') or {}
        st['languages'] = ['cs'] + ep['languages']
        print(nid, 'languages', len(ep['languages']), 'choices', len(node.get('choices') or []))

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_STORED) as dst:
        for info in src.infolist():
            if info.filename == 'pack.json':
                dst.writestr('pack.json', json.dumps(pack, ensure_ascii=False))
            elif info.filename == 'gamebook.json':
                dst.writestr('gamebook.json', json.dumps(book, ensure_ascii=False))
            else:
                dst.writestr(info, src.read(info.filename))
    data = buf.getvalue()
    path = os.path.join(OUT, 'gamebook-sara.zip')
    open(path, 'wb').write(data)
    print(path, len(data), hashlib.sha256(data).hexdigest())


if __name__ == '__main__':
    main()
