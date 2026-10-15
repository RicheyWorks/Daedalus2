# Synapse full workbench native host

Source only. Native UHT/compilation, CEF loading, installation, placement, cooking,
file dialogs and Play behavior have not been verified. The sole Unreal operator
owns those actions. No editor or application was launched for this change.

The new actor /Script/DaedalusLink.DaedalusSynapseWorkbenchTerminal hosts the
existing Synapse Svelte interface through SWebBrowser; it does not reproduce
authoring, scheduling, graph, settings, analytics or backup logic in C++.
The selected-track ADaedalusSynapseTerminal remains a separate permission
surface. The new actor's cube is a source placeholder, not finished object art.

## Pairing and ownership

Enable **Realm workbench** in desktop Synapse. Explicitly approve vault-wide
read access and the desired authoring, images, settings, analytics, graph,
backup and review permissions. Paste its private single-use link in the realm
panel. The only accepted format is
http://127.0.0.1:PORT/realm/synapse-workbench/#token=TOKEN, with a decimal port
and 43 base64url token characters. No aliases, remote hosts, credentials, queries
or alternate application paths are accepted. Pairing text and its Undo history
are removed after opening.

One workbench browser may be open at a time in this process. The actor reuses
the existing nearby local Hero, matching controller/pawn/realm/viewport,
game-world and UIOnly ownership rules. Close, destruction and ownership changes
invalidate the bridge generation. Input/focus restoration follows the existing
terminal pattern and avoids consuming unrelated ignore-input counters.

Every browser receives a fresh context ID, an empty CEF cache/cookie storage
path and nonpersistent session cookies. Popups, devtools/context menus,
subframes, external navigation and redirects are denied. Browser error
documents and console forwarding are suppressed to avoid displaying/logging
private URLs. The context is unregistered at shutdown; no engine-wide browser,
file-dialog, cache, credentials or devtools settings are changed.

Navigation permits only the selected literal origin and application document.
The load interceptor permits its built assets, same-origin image blobs and
fixed workbench API routes; other requests receive an empty local response.
This is paired with the server's restrictive CSP and exact-host/session checks.
The public UE interceptor cannot act as a general network firewall: its CEF
implementation explicitly bypasses read-only requests. No such bypass or
foreign request was exercised here. Do not weaken the server CSP.

## Native file contract

UE 5.8 client CEF blocks file dialogs by default and its browser client provides
no download handler. A bare browser therefore cannot complete the original
file forms. The only bound object is window.ue.workspace, a transient
UDaedalusSynapseWorkbenchBridge with three functions. The installed engine's
default binding policy lowercases function names. FWebJSResponse supplies
asynchronous promises; results are JSON strings:

| JavaScript function | Input | Successful result |
| --- | --- | --- |
| pickimage() | none | canceled=false, MIME and bytes_b64 |
| pickimport() | none | canceled=false, application/json and bytes_b64 |
| savejson(bytesBase64) | exported memory JSON bytes | canceled=false after no-replace commit |

User cancellation returns canceled=true. Failure rejects with a bounded
local message. The binding returns no paths, original filenames, URLs, shell
commands, credentials or generic object/command dispatch. Names shown by the
frontend are generated labels. No other actor or UObject is bound.

The existing platform adapter chooses these methods only inside UE, keeps
Tauri and ordinary browser paths, uploads selected bytes to the same local
session and invokes the same existing commands. It fences selection/export
awaits by session and generation, including immediately before native save.
No mutation is retried automatically.

Native limits are one operation at a time, 64 operations per panel and at least
500 ms between starts; 8 MiB raw bytes and 11,184,812 base64 characters per
transfer. JSON must be UTF-8, an array of at most 1,000 objects, and no deeper
than 64 containers. Actual memory fields, merge rules, image decoding,
dimensions and normalization remain the existing local service's authority.
The native image helper checks PNG/JPEG signatures and matching selected
extensions; it does not claim to decode images.

Every picker and JSON save requires a user-selected local file. Only fixed,
removable or RAM drives are allowed; network/device/drive-relative paths,
ambiguous names, links and mount points fail closed. Ancestor identities remain
pinned while each opened leaf is checked and read. Files are read in bounded
chunks and checked for size changes.

JSON export suggests only synapse-memories.json. It creates a private,
exclusively held sibling, arms cleanup, writes bounded chunks, flushes and
renames relative to the retained parent handle with replacement disabled.
Weak owner, panel generation and same-document policy are checked around the
modal dialog, reads/writes, flush, publication and promise delivery. A canceled
or failed incomplete save cleans up the owned handle; existing files survive.
Already committed saves are not rolled back when a panel closes.

Page closure attempts the frontend's authenticated keepalive revocation, then
closes the browser and invalidates its binding. Delivery is best effort.
Desktop revocation and the service's expiry remain authoritative; no cleanup,
rollback or revocation receipt is fabricated.

## Memory JSON semantics

Import merges IDs, replacing matching memories and their review history.
Restore replaces memories from a listed snapshot. Both use the original
service and its safety snapshots. Exports/snapshots contain memory JSON and
image references, not image bytes or settings. Existing serde compatibility
rules may ignore unknown JSON fields; an import is not a portable asset archive
or a settings import. Legacy unmanaged/remote image references are unavailable
in browser DTOs, and no remote image is fetched by the native adapter.

## Integration and remaining verification

The root coordinator added the single public WebBrowser module dependency after explicit Team Codex source-claim acceptance,
and owns commit/push, source pins and handoff. It is required because the public bridge
header exposes the engine's FWebJSResponse USTRUCT. The one-entry Build.cs change preserves all other dependencies and runtime staging. Source wiring is complete; native compilation remains unverified. No plugin enablement,
engine build, binary installation or level edit is part of this source slice.

The app's narrow src/lib/platform.ts extension must be rebuilt into its
embedded Svelte bundle. Frontend type/build checks are separate from CEF/UHT
verification. Before marking the object usable in Play, the native owner must
verify the actual generated bridge, isolated context and asset requests, every
permission group, selected image/import flows, JSON save/cancel, existing-file
refusal, actor/realm/controller loss during dialogs, repeated actions and final
input restoration with synthetic fixtures. Record actual source pins and
outcomes. Source inspection or module availability is not a passing playtest.

## Shared Fax continuation

The Fax full-workbench packet reuses this same C++ browser and Win32 SaveAs implementation through a fixed native profile and fixed-format C++ wrappers. It does not widen the Synapse JavaScript object: `pickimage`, `pickimport` and `savejson` retain their signatures, selectors, image/JSON validation and limits. The Synapse actor defaults to its original profile and API routes; only the separate Fax actor binds `window.ue.faxfiles`. The manifest refreshes the four changed shared-source hashes while retaining the two unchanged Synapse actor hashes and exact companion pin. The shared implementation remains unbuilt and unexercised in CEF/Win32; the required PUBLIC WebBrowser dependency still awaits its source-owner handoff.