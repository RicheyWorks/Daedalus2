"""Package actual Blender sources, exports and inspected views; execute no models/tests."""
from pathlib import Path
import argparse
import hashlib
import html
import json
import struct
import zipfile


def record(path, base):
    return {'path': path.relative_to(base).as_posix(), 'bytes': path.stat().st_size,
            'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}


def check_record(folder, expected):
    path = (folder / expected['file']).resolve()
    if not path.is_relative_to(folder.resolve()):
        raise ValueError('Artifact identity escapes its stage directory.')
    if path.stat().st_size != expected['bytes'] or hashlib.sha256(path.read_bytes()).hexdigest() != expected['sha256']:
        raise ValueError('Saved artifact differs from its production manifest: ' + str(path))
    return path


def glb_summary(path):
    data = path.read_bytes()
    magic, version, length = struct.unpack_from('<4sII', data)
    if magic != b'glTF' or version != 2 or length != len(data):
        raise ValueError('Export is not a complete GLB 2 file: ' + str(path))
    json_length, kind = struct.unpack_from('<II', data, 12)
    if kind != 0x4E4F534A:
        raise ValueError('GLB JSON chunk is missing.')
    body = json.loads(data[20:20 + json_length].decode('utf-8'))
    primitives = [p for mesh in body.get('meshes', []) for p in mesh.get('primitives', [])]
    nodes = body.get('nodes', [])
    return {'nodes': len(body.get('nodes', [])), 'meshes': len(body.get('meshes', [])),
            'materials': len(body.get('materials', [])),
            'vertexColorPrimitives': sum('COLOR_0' in p.get('attributes', {}) for p in primitives),
            'externalImages': [i.get('uri') for i in body.get('images', []) if i.get('uri')],
            'externalBuffers': [b.get('uri') for b in body.get('buffers', []) if b.get('uri')],
            'plotRoots': [{'name': n.get('name'), 'authoringPlotId': n['extras'].get('authoring_plot_id')}
                          for n in nodes if n.get('extras', {}).get('is_plot_root')],
            'socketNodes': sum(bool(n.get('extras', {}).get('socket_side')) for n in nodes),
            'towAnchors': [{'name': n.get('name'), 'authoringPlotId': n['extras'].get('authoring_plot_id')}
                           for n in nodes if n.get('extras', {}).get('tow_anchor')]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base', type=Path, default=Path('artifacts/islands/lumenwake'))
    args = parser.parse_args()
    base = args.base.resolve()
    stages = [('Showcase', 'final', 'Lumenwake_Sanctuary'),
              ('Template', 'template-final', 'Riverjoin_Commons'),
              ('SuperIsland', 'super-final', 'Lumenwake_Super_Island')]
    files, entries = [], []
    for label, directory, title in stages:
        folder = base / directory
        manifest = folder / (title + '_manifest.json')
        body = json.loads(manifest.read_text(encoding='utf-8'))
        src = check_record(folder, body['source'])
        export = check_record(folder, body['export'])
        views = [check_record(folder, view) for view in body['views']]
        recipes = [check_record(folder / 'recipe-source', item) for item in body['sourceSnapshots'] + body.get('viewCorrectionRecipes', [])]
        files.extend([src, export, manifest, *views, *recipes])
        entries.append({'label': label, 'directory': directory, 'name': title, 'source': record(src, base),
                        'export': record(export, base), 'views': [record(v, base) for v in views],
                        'geometry': body['geometry'], 'glb': glb_summary(export), 'units': 'metres',
                        'actualBlenderVersion': body['blenderVersion'], 'nativeImported': False})
    super_body = json.loads((base / 'super-final/Lumenwake_Super_Island_manifest.json').read_text())
    members = [p['authoringPlotId'] for p in super_body['distinctPlots']]
    if len(members) < 4 or len(set(members)) != len(members):
        raise ValueError('The delivered Super Island must retain four or more distinct members.')
    exported_members = [r['authoringPlotId'] for r in entries[-1]['glb']['plotRoots']]
    if sorted(exported_members) != sorted(members):
        raise ValueError('Delivered GLB plot roots differ from the recorded authoring members.')
    for plot in super_body['distinctPlots']:
        expected = entries[0 if plot['authoringPlotId'] == 'DEMO-A' else 1]['source']
        actual = plot['inputSource']
        if actual['sha256'] != expected['sha256'] or actual['bytes'] != expected['bytes']:
            raise ValueError('Assembly input differs from its delivered unique source: ' + plot['authoringPlotId'])
    blueprint = base / 'Connection_Standard.svg'
    files.append(blueprint)
    documents = []
    repo = Path(__file__).resolve().parents[2]
    for name in ('LUMENWAKE-ISLAND-STANDARD.md', 'SUPER-ISLAND-DESIGN.md'):
        original = repo / 'docs/production' / name
        document = base / name
        document.write_bytes(original.read_bytes())
        files.append(document); documents.append(record(document, base))
    package = {'schemaVersion': 1, 'title': 'Lumenwake Island Standard',
               'stage': 'BLENDER_AUTHORED_EXPORTED_AND_RENDERED',
               'definition': 'A Super Island connects four or more distinct island plots. Two or three are ordinary connected groups.',
               'distinctDemoPlots': members, 'geometryConnectivity': super_body['authoringLayout']['graph'],
               'nominalConnectionStandard': {'plotEnvelopeM': 240, 'centrePitchM': 256, 'socketOffsetM': 120,
                                             'jointSpanM': 16, 'clearWalkingWidthM': 8, 'deckDatumM': 10},
               'entries': entries, 'blueprint': record(blueprint, base), 'crewDocuments': documents,
               'ownership': 'DEMO IDs are authoring labels. No deed, owner, allocation, land registry or server state was changed.',
               'towing': 'Original visual tow ark and compatible authoring sockets. Runtime ship towing, reservations and authority remain integration work.',
               'verification': 'Actual Blender authoring/export/render plus source/artifact inspection. No tests, native build, Unreal import or live gameplay run.'}
    package_path = base / 'Lumenwake_Package_Manifest.json'
    package_path.write_text(json.dumps(package, indent=2) + '\n', encoding='utf-8')
    files.append(package_path)
    readme = base / 'README.txt'
    readme.write_text(
        'LUMENWAKE ISLAND STANDARD\n\n'
        'Open index.html for the artwork gallery. Open the .blend files in Blender 4.3+ for editable scenes.\n'
        'Showcase: final/Lumenwake_Sanctuary.blend\n'
        'Connectable template: template-final/Riverjoin_Commons.blend\n'
        'Four-plot Super Island: super-final/Lumenwake_Super_Island.blend\n\n'
        'Every plot has a named PlotRoot and E/N/W/S socket empties. Move an entire PlotRoot, not separate contents.\n'
        '240m authoring envelope, 256m root spacing, nominal10m walkway datum, 8m width,16m bridge.\n'
        'This mature art envelope illustrates the proposed growth tier; it does not silently enlarge deployed92m starter lands.\n'
        'Two or three connected islands are ordinary groups. Four or more distinct connected islands form a Super Island.\n'
        'Original IDs, edits and owner permissions stay separate; joining geometry does not merge deeds.\n\n'
        'The Super Island contains one Sanctuary plus three differently oriented Commons modules, using distinct DEMO-A/B/C/D IDs.\n'
        'The tow ark is a visual model. Actual networked tug physics, authorization, move commits and collision/nav need the existing owners.\n'
        'GLBs carry authored meshes and materials; stage snapshots/manifests record their exact source and hashes.\n'
        'Renderer: actual Blender4.3, CyclesCPU,4threads,48samples,1800x1350 overview; other view sizes recorded in files.\n'
        'No tests or Unreal changes were made. Artistic views are original Blender renders, not ImageGen or runtime captures.\n', encoding='utf-8')
    files.append(readme)
    cards = []
    for entry in entries:
        title = entry['name'].replace('_', ' ')
        views = ''.join(f'<figure><img loading="lazy" src="{html.escape(v["path"])}" alt="{html.escape(Path(v["path"]).stem.replace("_", " "))}"><figcaption>{html.escape(Path(v["path"]).stem.replace("_", " "))}</figcaption></figure>' for v in entry['views'])
        cards.append(f'<section><h2>{html.escape(title)}</h2><p><a href="{html.escape(entry["source"]["path"])}">Editable Blender scene</a> · <a href="{html.escape(entry["export"]["path"])}">GLB export</a></p><div class="views">{views}</div></section>')
    gallery = base / 'index.html'
    gallery.write_text('<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Lumenwake Island Standard</title><style>body{margin:0;background:#142c30;color:#eef4e4;font:16px/1.6 system-ui}main{max-width:1400px;margin:auto;padding:40px}h1,h2{font-weight:500;letter-spacing:-.04em}h1{font-size:46px}p{color:#bacfc6}a{color:#f0cf8f}section{padding:35px 0;border-top:1px solid #456460}.views{display:grid;grid-template-columns:repeat(2,1fr);gap:20px}figure{margin:0;background:#203e40;padding:10px;border-radius:8px}img{max-width:100%;height:auto;display:block;border-radius:5px}figcaption{font-size:12px;color:#c0d4ca;padding-top:8px}.rule{padding:15px;background:#294b48;border-left:4px solid #f0cf8f}.blueprint{background:#eef5ef;padding:12px}small{color:#a9c3b8}@media(max-width:700px){main{padding:20px}.views{grid-template-columns:1fr}h1{font-size:32px}}</style><main><small>ORIGINAL BLENDER ART · BUCKWILD SOL</small><h1>Lumenwake Island Standard</h1><p>One showcase sanctuary, one connection template, and four distinct islands assembled into a Super Island.</p><p class="rule">Super Island = four or more distinct connected plots. Two or three are ordinary connected groups.</p>' + ''.join(cards) + '<section><h2>The connection standard</h2><img class="blueprint" src="Connection_Standard.svg" alt="Four distinct plots and their connection geometry"><p>240m mature authoring envelope · 256m centres · 16m joints · 8m walking width · nominal10m datum.</p><p>Editable art and authoring geometry. Deed identity stays separate; live towing and game integration remain with the existing runtime owners.</p><p><a href="Lumenwake_Package_Manifest.json">Exact artifact and source manifest</a> · <a href="Lumenwake_Standard_Package.zip">Complete package</a></p></section></main></html>', encoding='utf-8')
    files.append(gallery)
    archive = base / 'Lumenwake_Standard_Package.zip'
    with zipfile.ZipFile(archive, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=6) as bundle:
        for path in sorted(set(files)):
            bundle.write(path, path.relative_to(base).as_posix())
    print(json.dumps({'package': str(archive), 'bytes': archive.stat().st_size, 'files': len(set(files)),
                      'plots': members, 'geometryObjects': [e['geometry']['objects'] for e in entries],
                      'triangleCounts': [e['geometry']['triangles'] for e in entries]}, indent=2))


if __name__ == '__main__': main()
