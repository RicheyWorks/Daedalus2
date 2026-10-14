// SPDX-License-Identifier: MIT
#pragma once
#include "DaedalusPortalQuestCore.h"
namespace daedalus { namespace shardstead {
struct Mission {const char* Id;const char* Giver;const char* Title;bool GoodAligned;std::vector<DaedalusPortalQuest::Step> Steps;};
inline const std::vector<Mission>& Missions(){
    static const std::vector<Mission> All{
        {"twaker_first_claim","Twaker_Prospector","A stake in Shardstead",false,{{"talk","Twaker_Prospector",1},{"survey","island_deposit",1},{"claim","permitted_plot",1},{"assign","worker",1},{"produce","island_goods",1}}},
        {"tree_sunken_chart","TalkingTree_Willow","Roots remember the tide",true,{{"talk","TalkingTree_Willow",1},{"deliver","fresh_water",3},{"acquire","root_compass",1},{"align","tidal_map_room",1},{"recover","tide_archive",1},{"return","TalkingTree_Willow",1}}},
        {"tree_cave_accord","TalkingTree_Cedar","The crystal accord",true,{{"talk","TalkingTree_Cedar",1},{"talk","Twaker_Cachekeeper",1},{"repair","cave_supports",3},{"escort","lost_prospector",1},{"return","stolen_crystals",5}}},
        {"unicorn_rescue_convoy","Unicorn_Guide","The midnight rescue run",true,{{"talk","Unicorn_Guide",1},{"scout","captive_convoy",1},{"disable","convoy_trap",2},{"rescue","captives",3},{"escort","sanctuary",1}}},
        {"unicorn_storm_medicine","Unicorn_Guide","Medicine over the pass",true,{{"talk","Unicorn_Guide",1},{"collect","healing_herbs",5},{"craft","medicine",2},{"deliver","mountain_refuge",2},{"protect","refuge",1}}},
        {"unicorn_sea_herd","Unicorn_Alpha","Cool the burning herd",true,{{"talk","Unicorn_Alpha",1},{"prepare","safe_sea_route",1},{"guide","distinct_burning_bull_to_sea",10},{"return","Unicorn_Alpha",1}}},
        {"unicorn_hearthwake_ark","Unicorn_Guide","All life aboard",true,{{"talk","Unicorn_Guide",1},{"prepare","ark_rescue_habitats",1},{"board","threatened_ecosystem_life",6},{"escort","island_rescue_ark",1},{"land","hearthwake_sanctuary",6},{"restore","sanctuary_habitats",3}}},
        {"unicorn_marine_rescue","Unicorn_Alpha","The sea has a heartbeat",true,{{"talk","Unicorn_Alpha",1},{"prepare","ark_marine_tank",1},{"rescue","stranded_marine_life",3},{"land","hearthwake_marine_sanctuary",3}}},
        {"unicorn_roots_and_spores","Unicorn_Guide","Small lives count",true,{{"talk","Unicorn_Guide",1},{"prepare","ark_seed_and_fungi_bank",1},{"rescue","threatened_plants_and_fungi",5},{"restore","hearthwake_living_soil",1}}},
        {"twaker_crystal_cache","Twaker_Cachekeeper","Shard Lord's hidden ledger",false,{{"talk","Twaker_Cachekeeper",1},{"survey","crystal_seam",1},{"collect","crystal",5},{"deposit","guarded_cave_chest",5}}}
    };return All;
}
}}
