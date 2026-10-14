// SPDX-License-Identifier: MIT
const $ = id => document.getElementById(id);
const colors = ['#749d83', '#ae8980', '#668b9a', '#ac965a', '#9084a7', '#818f66'];
const crew = [
  { id: 'buckwild-sol', realm: 'Gallery City', work: 'City exploration, memory-mosaic quest, land inspector and shared atlas.' },
  { id: 'parcels_coder', realm: 'Parcels', work: 'District exploration, addressed plot survey and visitor save.' },
  { id: 'portal_coder', realm: 'Portal Realm', work: 'Seeded DRR map exploration, realm links and expedition journal.' },
  { id: 'realm_audit', realm: 'Shattered Planet', work: 'Ark expedition, land-release catalog and completion outline.' }
];
const fallback = [
  { id: 'shattered-planet', name: 'The Shattered Planet', status: 'LIVE', entryUrl: '/sky-expedition.html', story: 'Arks carry life between the fragments of the old planet.' },
  { id: 'portal', name: 'The Portal Realm', status: 'LIVE', entryUrl: '/portal-expedition.html', story: 'A portal turns your journey into an original 8-bit expedition.' },
  { id: 'parcels', name: 'Parcels', status: 'SERVER', entryUrl: '/parcels-realm.html', story: 'Find a place among sixty plots, streets and a skyward helipad.' },
  { id: 'gallery-city', name: 'Gallery City', status: 'SERVER', entryUrl: '/gallery-city.html', story: 'Named streets and maze art preserve a fragment that remembers.' },
  { id: 'orrery-reach', name: 'The Orrery Reach', status: 'LIVE', entryUrl: '/reach.html', story: 'A village of herbalists keeps time beneath a living sky.' }
];
let catalog = { realms: fallback }, mounted = [], receipt = null;
function element(tag, text, className) {
  const node = document.createElement(tag); if (text !== undefined) node.textContent = text;
  if (className) node.className = className; return node;
}
function safeEntry(path) {
  if (typeof path !== 'string' || !path.startsWith('/') || path.startsWith('//')) return null;
  try { const url = new URL(path, location.origin); return url.origin === location.origin ? url.pathname + url.search + url.hash : null; }
  catch { return null; }
}
function renderRealms() {
  const filter = $('filter').value;
  const realms = catalog.realms.filter(realm => {
    if (filter === 'browser') return !!safeEntry(realm.entryUrl);
    if (filter === 'live') return realm.status === 'LIVE';
    if (filter === 'server') return realm.status === 'SERVER';
    if (filter === 'planned') return ['NAMED', 'PROPOSED', 'DISTRICT'].includes(realm.status);
    return true;
  });
  $('realm-grid').replaceChildren(...realms.map((realm, index) => {
    const card = element('article', undefined, 'realm-card'), art = element('div', undefined, 'realm-art');
    art.style.setProperty('--card-color', colors[index % colors.length]); art.setAttribute('aria-hidden', 'true');
    const copy = element('div', undefined, 'realm-copy'), meta = element('div', undefined, 'realm-meta');
    meta.append(element('span', realm.status), element('small', realm.previewOnly ? 'NEW SOURCE PREVIEW' : 'DOCUMENTED STATUS'));
    copy.append(meta, element('h3', realm.name), element('p', realm.story));
    const url = safeEntry(realm.entryUrl);
    if (url) {
      const link = element('a', realm.previewOnly || /expedition|gallery-city|parcels-realm/.test(url) ? 'Explore browser preview ↗' : 'Open realm entry ↗');
      link.href = url; copy.append(link);
    } else copy.append(element('small', 'Entry is awaiting realm integration.'));
    card.append(art, copy); return card;
  }));
  if (!realms.length) $('realm-grid').append(element('p', 'No realms match this view.', 'small'));
}
function renderReleases() {
  const realms = catalog.realms.filter(r => r.land);
  $('release-list').replaceChildren(...realms.map(realm => {
    const row = element('div', undefined, 'release-row'); row.append(element('h3', realm.name), element('span', realm.land.stage.replaceAll('_', ' ').toLowerCase(), 'stage'), element('p', realm.land.model));
    const details = element('details'), blockers = Array.isArray(realm.land.blockers) ? realm.land.blockers : [];
    details.append(element('summary', `${blockers.length} release dependencies`));
    const list = element('ul'); list.append(...blockers.map(text => element('li', text))); details.append(list); row.append(details); return row;
  }));
  if (!realms.length) $('release-list').append(element('p', 'The detailed release catalog is unavailable. No mint availability has been confirmed.', 'small'));
}
function renderCrew() {
  $('crew-grid').replaceChildren(...crew.map((member, index) => {
    const card = element('article', undefined, 'crew-card');
    card.append(element('span', `0${index + 1}`, 'number'), element('h3', member.realm), element('p', member.id), element('p', member.work));
    const output = receipt?.members?.find(r => r.member === member.id);
    if (output) card.append(element('small', `${output.sourceFiles} source files · ${output.sourceNonblankLines.toLocaleString()} nonblank source lines`));
    else card.append(element('small', 'Separate realm · scoped files'));
    return card;
  }));
  if (receipt?.elapsedMinutes > 0 && receipt?.totals) {
    $('pace').textContent = `${receipt.totals.sourceFiles} source files · ${receipt.totals.sourceNonblankLines.toLocaleString()} nonblank source lines saved in ${receipt.elapsedMinutes.toFixed(1)} elapsed minutes · observed crew pace ${Math.round(receipt.totals.sourceNonblankLinesPerHour).toLocaleString()} lines/hour. Data and documentation counts are separate in the receipt. No tests or builds were run.`;
  }
}
function validateCatalog(body) {
  if (!body || body.schemaVersion !== 1 || !Array.isArray(body.realms)) throw new Error('Invalid catalog.');
  const realms = body.realms.filter(r => r && typeof r.id === 'string' && typeof r.name === 'string' && typeof r.story === 'string' && typeof r.status === 'string').slice(0, 100);
  if (!realms.length) throw new Error('Empty catalog.');
  return { ...body, realms };
}
async function get(url) {
  const response = await fetch(url, { signal: AbortSignal.timeout(6000), headers: { Accept: 'application/json' } });
  if (!response.ok) throw new Error(`Read returned ${response.status}.`); return response.json();
}
async function load() {
  const results = await Promise.allSettled([get('/realm-release-catalog.json'), get('/api/v1/worlds'), get('/buckwild-sprint-receipt.json')]);
  if (results[0].status === 'fulfilled') {
    try { catalog = validateCatalog(results[0].value); $('catalog-status').textContent = 'Realm stages come from the crew’s source audit. Existing LIVE status is documented; these new browser pages await runtime acceptance.'; }
    catch { $('catalog-status').textContent = 'Detailed catalog could not be read; showing the built-in realm guide.'; }
  } else $('catalog-status').textContent = 'Detailed catalog unavailable; showing the built-in realm guide.';
  if (results[1].status === 'fulfilled' && Array.isArray(results[1].value.worlds)) {
    mounted = results[1].value.worlds;
    $('server-status').textContent = `${mounted.length} worlds mounted on this realm server. Visitor pages keep their journal on your device.`;
  } else $('server-status').textContent = 'Realm server unavailable. Visitor drafts and the atlas remain available; shared ownership is unknown.';
  if (results[2].status === 'fulfilled' && results[2].value.schemaVersion === 1) receipt = results[2].value;
  renderRealms(); renderReleases(); renderCrew();
}
$('filter').addEventListener('change', renderRealms);
renderRealms(); renderReleases(); renderCrew(); load();
