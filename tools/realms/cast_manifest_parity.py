# SPDX-License-Identifier: MIT
"""Offline DCS talker-to-manifest audit; matches ADaedalusTalker::ArtIds spelling rules."""
import argparse
import json
from pathlib import Path
import re

SPELLINGS = {'gallery-city': ['Gallery'], 'parcels': ['Parcels'], 'bricks': ['Brick', 'Bricks'],
             'labyrinth': ['Labyrinth', 'Lab'], 'world-zero': ['Zero'], 'ocean': ['Ocean']}


def candidates(cast, who):
    clean = who.replace("'s ", ' ').replace("'", '')
    forms = [who]
    if clean != who: forms.append(clean)
    if clean.startswith('The '): forms.append(clean[4:])
    realms = SPELLINGS.get(cast.lower(), [cast.split('-')[0].capitalize()])
    return list(dict.fromkeys('Mob_' + realm + '_' + ''.join(w[:1].upper()+w[1:] for w in re.findall(r'[^\W_]+', form))
                              for realm in realms for form in forms))


def audit(cast, text, records):
    ids = [r['id'] for r in records]
    if len(ids) != len(set(ids)): raise ValueError('duplicate manifest IDs')
    rows = []
    names = [line[4:].strip() for line in text.splitlines() if line.startswith('who ')]
    if not names or len(names) != len(set(names)): raise ValueError('empty or duplicate DCS who list')
    for who in names:
        want = candidates(cast, who)
        hits = [x for x in want if x in ids]
        rows.append({'who': who, 'candidates': want, 'matches': hits, 'ok': bool(hits)})
    used = {x for row in rows for x in row['matches']}
    return {'cast': cast, 'ok': all(r['ok'] for r in rows), 'matched': sum(r['ok'] for r in rows),
            'total': len(rows), 'roles': rows, 'unbound_manifest_ids': sorted(set(ids)-used),
            'scope': 'manifest identity only; files/imported assets/runtime behavior unverified'}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--dcs',type=Path,required=True);ap.add_argument('--manifest',type=Path,required=True)
    ap.add_argument('--overlay',type=Path,action='append',default=[]);ap.add_argument('--out',type=Path)
    a=ap.parse_args()
    def records(path):
        d=json.loads(path.read_text(encoding='utf-8'));return d if isinstance(d,list) else d['assets']
    rows=records(a.manifest)
    for overlay in a.overlay: rows+=records(overlay)
    result=audit(a.dcs.stem,a.dcs.read_text(encoding='utf-8'),rows)
    out=json.dumps(result,indent=2)
    if a.out:a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(out,encoding='utf-8')
    print(out);return 0 if result['ok'] else 1

if __name__=='__main__':raise SystemExit(main())
