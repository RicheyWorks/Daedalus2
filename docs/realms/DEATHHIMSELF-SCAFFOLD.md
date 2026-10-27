# deathhimself source scaffold

`deathhimself` is a whole independent world with its own environments and
identity. The Labyrinth is only the connection point to the user's world; it
does not define this world's content type, environment, style or design. The
display name remains exactly `deathhimself`. He submits art and ideas; the
development team builds the realm, manages implementation, validates content
and maintains the NFT labels. The intake does not require him to implement
engine code or deliver a finished game.

The working contract is
[`CreatorRealmScaffold.java`](../../daedalus-server/src/main/java/com/daedalus/server/realm/CreatorRealmScaffold.java).
It supplies immutable Java records, intake/update validation, brief revision
helpers, labels and an offline metadata draft adapter. It performs no file or
network I/O. There is no runtime endpoint, provider mount or playable world.

## Identity and connection

| Field | Reserved value |
|---|---|
| Technical realm ID | `deathhimself` |
| Display name | `deathhimself` |
| Proposed session ID | `DEATHHIMSELF` |
| Proposed catalog stem | `deathhimself` |
| Creative attribution | `deathhimself`, `USER_ASSERTED` |
| Realm enabled / ready | `false` / `false` |
| Connection | `labyrinth` / `LABYRINTH` / `labyrinth` to `deathhimself` / `DEATHHIMSELF` / `deathhimself` |
| Relationship | `CONNECTED_SEPARATE` |
| Connection enabled / native adapter | `false` / `PENDING` |

The new session and catalog identities are reserved by this descriptor and are
not registered or mounted. The existing Labyrinth identity, catalog and readiness
remain unchanged; this scaffold grants neither realm readiness. The connection
describes two separate endpoints, without inheriting Labyrinth's maze design,
world style, generator or environments. The new world's environments and
creative direction await his art and ideas. It is not an operational portal or
travel API.

The realm attribution records the user's creative ownership instruction. It
does not authenticate a legal person, account, wallet, chain owner or rights in
an individual submitted asset. Entry-level attribution records the actual
submission's declared creator separately.

## Manifests and intake

[`scaffold-v1.json`](../../config/realms/deathhimself/scaffold-v1.json) is the
version 1 empty baseline returned by `CreatorRealmScaffold.empty()`. It has no
entries. Theme, visual direction, lore, gameplay and presentation are explicitly
unset. Chain, contract, token ID, wallet, royalty, marketplace, price and license
choices are also unset. The version 1 validator preserves these baseline choices
and disabled states; configuring the later world is a separate implementation
change using creator input.

[`intake-example-v1.json`](../../config/realms/deathhimself/intake-example-v1.json)
is a complete synthetic manifest. Its four `DRAFT` entries demonstrate `ASSET`,
`COMPONENT`, `ASSEMBLY` and `IDEA`. All example entry and original IDs use the
`deathhimself_fixture_` namespace. The example creator is `synthetic-fixture`
with basis `SYNTHETIC`; the sample content is not attributed to deathhimself.
There are no art files, public asset URLs or invented creative concepts.

For a real submission, the team records the supplied art and creative brief,
obtains its declared creator/provenance, allocates stable IDs, and attaches the
original references. The team can then append clarification briefs and implement
derived content. Preserve the submitted originals independently of those edits.
The artist need only supply art, ideas and the information needed to understand
the submission; code, import settings and native integration belong to the team.

An entry ID is at most 48 characters and matches
`deathhimself_[a-z0-9_-]+`. Original source IDs use the same namespace and share
the collision domain with entries. `validate(manifest, existingIds)` rejects
duplicate or host-reserved IDs. The host must provide its existing realm,
session, catalog, item and asset IDs; an empty set only proves internal uniqueness.

## Originals and revisions

Each original records its own stable ID, lowercase 64-character SHA-256 digest,
`originalUri` equal to `urn:sha256:<digest>`, and declared provenance. This URI
pins content identity without publishing or fetching the content. The team must
hash the actual submitted bytes and retain a private mapping to the original;
the validator checks the descriptor's digest and URI agreement, not the bytes,
authenticity, legal rights or existence of a remotely stored asset.

The synthetic example computes each digest from the exact tiny ASCII string
shown in that original's provenance, including its final newline. It demonstrates
the contract without providing an art file. A URI may later be resolved by an
approved storage adapter, but the source contract does not add that adapter.

Draft brief revisions are an ordered list beginning at version 1. Use
`appendIdea(draft, text)` to produce a new entry value with the next revision;
earlier text remains in the history. Original lists are append-only across saved
intakes. `validateUpdate(previous, next, existingIds)` rejects removal of entries,
replacement/removal of originals, loss of brief history and role changes.

Final content requires original provenance. A final assembly must have at least
one member, and each referenced asset/component must also be final. Draft
assemblies may await members. Once an entry is `FINAL`, its value
is immutable under update validation. Its next creative iteration receives a new
entry ID and a `supersedesId` pointing to the retained predecessor of the same
role. Lineage cycles are invalid. `IDEA` entries stay draft and keep briefs
separate from art entries.

## Labels and metadata

`labels(entry)` reuses the existing `TokenAttribute` DTO to label every role with
realm ID, content ID, role, content stage, creator handle, attribution basis and
derived sale eligibility. Assembly membership references separately labelled
asset/component IDs and never grants a member sale eligibility.

| Sale intent / role | Derived eligibility |
|---|---|
| `IDEA`, or `NOT_FOR_SALE` | `INELIGIBLE` |
| `UNSET` | `UNREVIEWED` |
| `REVIEW_REQUESTED` on other roles | `REVIEW_REQUIRED` |

No state means approved for sale. `saleReady()` always returns `false` in this
scaffold. Components can be labelled without being sale candidates; the fixture
component is explicitly `NOT_FOR_SALE`. A later team review must determine which
whole assets or assemblies, if any, should proceed.

`metadataDraft(manifest, entryId, existingIds)` reuses `IslandTokenMetadata`
without allocating an island slot or token. It returns empty for unfinished
entries or missing name, description, creator handle or pinned preview. A final
entry's preview must equal one of its original URIs. A produced offline draft
contains the labels, original URI/SHA-256 traits, predecessor ID (when present)
and numbered component IDs (for assemblies). It is preparation for later
review, not NFT publication, token ownership, marketplace acceptance or sale
readiness. The synthetic draft fixture produces no metadata drafts.

## Source use and checks

The caller supplies source data and the host's current IDs; this helper adds no
service or automatic activation:

```java
var empty = CreatorRealmScaffold.empty();
var problems = CreatorRealmScaffold.validate(empty, existingIds);
var nextProblems = CreatorRealmScaffold.validateUpdate(previous, next, existingIds);
var labels = CreatorRealmScaffold.labels(entry);
var metadata = CreatorRealmScaffold.metadataDraft(next, entry.id(), existingIds);
```

Deserialize either manifest into `CreatorRealmScaffold.Manifest` with the
repository's JSON mapper before validation. JSON field names follow the record
components; enum labels are uppercase. The server's focused contract tests check
the files and source behavior:

```text
mvn -pl daedalus-server -am -Dtest=CreatorRealmScaffoldTest -Dsurefire.failIfNoSpecifiedTests=false test
```

Portable checks establish source contract behavior. They do not establish native
registration, compilation, input, collision, rendering, saves or travel.

## Later inputs and acceptance

Creator inputs still needed are his art, briefs, declared attribution/provenance,
and creative decisions about the realm. The team implements from those inputs
and gathers the required rights, production and marketplace decisions before
any sale-ready claim. Those choices remain unset here.

Native work still needs normal ownership coordination and acceptance: register
the distinct session/catalog identity; implement the pending adapter against the
established native connection interface; select and validate landing/return
behavior from the approved design; verify the actual two-way traversal, failure
states, persistence and separate realm identities. These are future native
inputs, not implemented portal behavior or permission to resume held work.
The editor, runtime activation and NFT publication holds remain in force.

## Appendix: a later final revision

Suppose the team has finalized `deathhimself_asset_a001` from the creator's
submission. Preserve that entry and its original records unchanged. A later
finished iteration can use `deathhimself_asset_a002` with
`supersedesId: "deathhimself_asset_a001"`, the same `ASSET` role and its own
original IDs/digests. Keep both entries in the next manifest and run
`validateUpdate`. These illustrative IDs are not allocated assets and supply no
art or creative direction. Do not overwrite a final entry, reuse an original ID
for different bytes or infer a token ID from the entry ID.
