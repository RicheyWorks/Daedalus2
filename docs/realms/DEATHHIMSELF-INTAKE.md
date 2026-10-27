# deathhimself local creator intake

The team uses this CLI to receive supplied art and ideas, retain originals,
revise briefs and prepare NFT labels. `deathhimself` remains an independent
world; Labyrinth is its connection point to the user's world. This tool does
not implement environments, travel, a server endpoint or publication.

Run the compiled `com.daedalus.server.realm.intake.CreatorIntakeCli` with the
server runtime classpath. For example, with compiled server/core classes and
their runtime dependencies already in `$cp`, this PowerShell helper runs it:

```powershell
function intake { & java -cp $cp com.daedalus.server.realm.intake.CreatorIntakeCli @args }
```

Commands return JSON on stdout, errors on stderr and exit status 0 or 2. Each
command closes its store handle. Supply a fresh local root to `init` on a
filesystem supporting hard links; new-only atomic publication fails closed
when hard links are unavailable. Export requires an existing output directory.
The optional reserved-ID JSON array should contain the host's existing realm,
session, catalog, asset and item IDs; omitting it checks internal uniqueness.

```text
init ROOT [RESERVED_IDS_JSON]
show ROOT [REVISION]
history ROOT
new ROOT EXPECTED ID ROLE [CREATOR_HANDLE] [SUPERSEDES_ID]
edit ROOT EXPECTED ID EDIT_JSON
idea ROOT EXPECTED ID TEXT_FILE
attach ROOT EXPECTED ENTRY_ID ORIGINAL_ID LOCAL_FILE PROVENANCE_TEXT_FILE [--preview]
finalize-source ROOT EXPECTED ID
save ROOT EXPECTED MANIFEST_JSON
export ROOT REVISION OUTPUT_JSON
```

`init` saves empty revision 1. Every mutation requires the current positive
revision as `EXPECTED`, saves a new immutable snapshot and preserves history.
Reopen the root with `show` or `history` after a conflict before editing again.
`history` returns revision/digest/parent/entry-count summaries; `show` includes
the full saved manifest. `save` imports a complete manifest under the same
validation and preservation rules as individual authoring commands.

`ROLE` is `ASSET`, `ASSEMBLY`, `COMPONENT` or `IDEA`. A new entry has unknown
attribution unless a creator handle is explicitly supplied, which records
`USER_ASSERTED` creative attribution. The CLI infers no creator, name or terms
from filenames. `EDIT_JSON` is a complete `DraftEdit` record:

```json
{"name":"SYNTHETIC fixture","description":"Local contract example only",
 "previewOriginalId":null,"creator":{"handle":"synthetic-fixture","basis":"SYNTHETIC",
 "legalIdentity":null,"accountId":null},"saleIntent":"UNSET","componentIds":[]}
```

For a synthetic local exercise, save that JSON as `fixture-edit.json`; create
`fixture.txt`, `provenance.txt` and `brief.txt` containing clearly marked
synthetic text. Use fresh destinations and the returned revision each time:

```powershell
intake init .\intake-demo
intake new .\intake-demo 1 deathhimself_fixture_asset ASSET
intake edit .\intake-demo 2 deathhimself_fixture_asset .\fixture-edit.json
intake idea .\intake-demo 3 deathhimself_fixture_asset .\brief.txt
intake attach .\intake-demo 4 deathhimself_fixture_asset deathhimself_fixture_original .\fixture.txt .\provenance.txt --preview
intake finalize-source .\intake-demo 5 deathhimself_fixture_asset
intake history .\intake-demo
intake show .\intake-demo 6
intake export .\intake-demo 6 .\fixture-export.json
```

JSON, brief and provenance inputs must be regular files, at most 8 MiB each;
text uses UTF-8. Saved metadata is also limited to 8 MiB per file. Each original
is limited to 256 MiB. `attach` delegates local-byte hashing and retention to the
store and pins an original URI; `--preview` selects that retained original.
Brief edits append revisions. Final source content stays immutable; a later
iteration needs a new ID referencing its predecessor. Assemblies reference
separate labelled assets/components and do not make members saleable.

`finalize-source` is a source-content stage, not sale approval or media/native
acceptance. The export is a local JSON bundle with labels and available offline
metadata drafts. No wallet, chain, contract, token, royalty, marketplace, price
or license is inferred. World readiness, native activation and NFT publication
remain disabled. See [the scaffold contract](DEATHHIMSELF-SCAFFOLD.md).
