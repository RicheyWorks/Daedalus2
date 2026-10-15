# SPDX-License-Identifier: MIT
"""The next exact three-egg profile for the existing retained catalogue runner.

The previous batch/journals stay unchanged. This is an additive asset-only
profile, never permission to replay the completed first batch or import a whole
catalogue. Native geometry, unit/color and duplicate checks are shared.
"""
import argparse
from pathlib import Path

import codex_catalogue_delivery as delivery

FOLDER = delivery.BASE / 'CatalogueEggGemsR1'
RELAY = Path('C:/Users/730ri/Documents/Codex/2026-10-14/task/production-checkpoint-new-egg-candidates-20261015.json')
RELAY_SHA = '6c0f5016b28122284bc28ec76c8bb37e363a160fb2fc03b3056c7006da49281d'
NAMES = ('Prop_Egg_Ruby_Intact', 'Prop_Egg_Sapphire_Intact', 'Prop_Egg_Emerald_Intact')


def configure():
    delivery.FOLDER = FOLDER
    delivery.NAMES = NAMES
    delivery.PRIOR_CATALOGUE = delivery.BASE / 'CatalogueEggR1/readback.json'
    delivery.QUALIFICATION_FP = delivery.fingerprint(FOLDER / 'source-qualification.json')


def qualify():
    witness = delivery.fingerprint(RELAY)
    if witness['sha256'] != RELAY_SHA:
        raise ValueError('exact reviewed relay receipt required')
    relay = delivery.load(RELAY)
    if tuple(row['name'] for row in relay['items']) != NAMES:
        raise ValueError('exact reviewed gem eggs required')
    prior = delivery.load(delivery.BASE / 'CatalogueEggR1/source-qualification.json')
    items = []
    shared = relay['shared_actual_fbx_observations_each_candidate']
    for row in relay['items']:
        items.append({**row, 'triangles': shared['triangles_after_polygon_triangulation'],
                      'source_bounds': {edge: shared['raw_vertex_bounds'][edge] for edge in ('min', 'max')}})
    FOLDER.mkdir(exist_ok=True)
    delivery.write_new(FOLDER / 'source-qualification.json', {
        'schema': 'daedalus.codex-static-gem-eggs-source.v1', 'stage': 'source_qualified_static_eggs_only',
        'items': items, 'reviewed_relay': {'path': str(RELAY), **witness},
        'source_witnesses': prior['source_witnesses'] + [{'path': str(RELAY), **witness}],
        'source_views': [relay['source_image_qualification']],
        'unit_contract': relay['operator_handoff_scope']['compatible_unit_contract'],
        'limits': relay['source_image_qualification']['limits'],
        'preserve_prior': str(delivery.BASE / 'CatalogueEggR1/readback.json')})


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=('prepare', 'ingest', 'readback'))
    stage = parser.parse_args().stage
    if stage == 'prepare':
        qualify()
    configure()
    getattr(delivery, stage)()
