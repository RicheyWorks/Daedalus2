import {readFileSync,writeFileSync,mkdirSync} from 'node:fs';
import {genomeFromTraits,renderCoat,breedCoat,encodePNG} from '/workspace/rd-music-nft/packages/rd-coat/src/index.js';
const H=JSON.parse(readFileSync('/workspace/rd-music-nft/out/contact_sheet_v3_hashes.json'));
const OUT='/workspace/prom_ue/coats8/';mkdirSync(OUT,{recursive:true});
const R=['Solitons','Labyrinth','Coral','Fingerprint','Honeycomb','Mitosis','Wanderers','Worms'];const S={};const man=[];
for(const r of R){const t=H.find(h=>h.traits.Pattern===r);const g=genomeFromTraits(t.hash,t.traits);const {image,sim,kind}=renderCoat(g,{seed:t.hash,body:'none',size:512});
 S[r]={g,sim,t};const n=`T_Coat_${r}_${kind}`;writeFileSync(OUT+n+'.png',encodePNG(image));man.push({name:n,regime:r,kind,hash:t.hash});console.log(n)}
for(const [a,b] of [['Labyrinth','Mitosis'],['Coral','Solitons'],['Worms','Honeycomb']]){const seed=`${S[a].t.hash}+${S[b].t.hash}#child-1`;
 const br=breedCoat(S[a].g,S[b].g,S[a].sim,S[b].sim,seed);const C=renderCoat(br.genome,{seed,init:br.init,initA:br.initA,steps:br.steps,size:512});
 const n=`T_Coat_Child_${a}x${b}_${C.kind}`;writeFileSync(OUT+n+'.png',encodePNG(C.image));man.push({name:n,parents:[a,b],kind:C.kind,seed});console.log(n)}
writeFileSync(OUT+'manifest.json',JSON.stringify(man,null,1));
