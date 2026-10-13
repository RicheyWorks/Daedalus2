"""Deterministic Portal production roster, not manufactured art/gameplay proof.

User-approved scope: fifty enemy types and fifty friendly types, ten individuals
per type. Bosses are a separate register. New type names and quests are proposals.
"""
import argparse
import json
import re
from pathlib import Path

FRIEND_TYPES = '''Knight Tinker Herbalist Bard King Queen Prince Princess RoyalScribe
RoyalGuard Ambassador Steward Innkeeper Smith ItemMerchant Keymaker FerryCaptain
WellKeeper Farmer Miller Baker Fisher Shepherd StableKeeper Cartographer Scout
Ranger Healer Apothecary Scholar Librarian Musician Storyteller Mason Carpenter
Weaver Tailor Miner Jeweller Cook Messenger RescueGuide LostTraveller Refugee
DragonKeeper RainbowWarden UnicornGuide UnicornMedic UnicornSentinel UnicornQuestgiver'''.split()
NEW_ENEMIES = '''BriarBoar IronjawWolf RockBeetle ThornCrawler RiverSnapper SandScorpion
EmberLizard IceNewt StormHawk CaveMantis CopperCrab MossbackOgre CrystalGolem
MudGolem RustKnight BrokenAutomaton CliffHarrier GlassViper CinderRam TunnelWorm
ReefStalker AshDrake BrambleHound QuartzTurtle BoulderToad SmokeRaptor ThistleWasp
SaltbackLurker SlateSerpent IronMole RazorFinch GraniteBrute SiltCrawler StormRay
ObsidianCrab'''.split()
BOSSES = ['GatebreakerColossus', 'StormCrownDrake', 'IronrootBehemoth',
          'DeepRiverLeviathan', 'CinderSpireGuardian']


def build(source):
    existing = re.findall(r'^\s*([A-Z_]+)\("', source, re.M)
    if len(existing) != 15 or len(set(existing)) != 15:
        raise ValueError('Existing bestiary changed; reconcile fifty-type roster')
    enemies = existing + NEW_ENEMIES
    if len(enemies) != 50 or len(FRIEND_TYPES) != 50:
        raise ValueError('Population requires fifty types per side')
    rows = []
    for faction, types in [('enemy', enemies), ('friendly', FRIEND_TYPES)]:
        for kind in types:
            for individual in range(1, 11):
                rows.append(dict(id=f'Portal_{faction}_{kind}_{individual:02d}',
                                 faction=faction, type=kind, individual=individual,
                                 existing_rules_key=kind if kind in existing else None,
                                 design_status='existing rules' if kind in existing else 'proposal',
                                 art_status='Planned', unreal_status='Pending',
                                 variant_seed=f'{faction}/{kind}/{individual}',
                                 role_count=1))
    quests = [
        dict(id='Portal_KingsRoad', giver_type='King', goal='Restore safe passage to an isolated town',
             steps=['Speak to royal steward', 'Locate stranded caravan', 'Escort survivors home',
                    'Report to the king'], reward='Proposed royal favour and realm equipment'),
        dict(id='Portal_RiverRescue', giver_type='RescueGuide', goal='Save travellers trapped beyond the river',
             steps=['Find ferry captain', 'Recover repair supplies', 'Open crossing', 'Escort travellers'],
             reward='Proposed supplies and rescued-town services'),
        dict(id='Portal_UnicornBidding', giver_type='UnicornQuestgiver', goal='Help a frightened unicorn herd',
             steps=['Follow a sparse rainbow dust trail', 'Speak to the unicorn guide',
                    'Clear the threatened route', 'Return to the herd'],
             reward='Proposed guidance and companion trust; exact rewards require review'),
    ]
    return dict(realm='Portal Realm', enemy_count=500, friendly_count=500,
                types_per_side=50, individuals_per_type=10, population=rows,
                bosses=[dict(id='Portal_Boss_'+name, design_status='proposal',
                             art_status='Planned', unreal_status='Pending') for name in BOSSES],
                quests=quests, quest_status='Story proposals; runtime bindings pending',
                unicorn_register='Separate existing 500-unicorn collection; no automatic duplication',
                story='Royal roads connect towns cut off by dangerous crossings. Rescued people '
                      'restore local services; unicorn guides reveal safe paths toward unique rainbows. '
                      'The party earns royal favours while investigating the blocked routes. '
                      'Causes, villains, dialogue and reward values remain proposals.',
                proof='Planning metadata only; no generated meshes or live gameplay claimed')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    source = Path(__file__).resolve().parents[2]/'daedalus-core/src/main/java/com/daedalus/world/retro/RetroMonster.java'
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(build(source.read_text()), indent=2), encoding='utf8')


if __name__ == '__main__':
    main()
