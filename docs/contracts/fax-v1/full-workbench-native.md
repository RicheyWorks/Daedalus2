# Fax private workbench native host

Source implementation on the published Synapse browser host baseline `1b97a8b9be19a2067a9039ab634415c26cab6c3c`. This adds `/Script/DaedalusLink.DaedalusFaxWorkbenchTerminal`, a physical-object source actor that hosts the existing Fax Trident local workbench page. The cube is a source placeholder; no asset placement or finished object art is supplied here. Existing prepared-PDF export remains its separate grant and terminal.

Native UHT, module compilation, CEF loading, SaveAs dialogs, installed binaries, cooking and Play have not been verified. The baseline still requires the root-owned public `WebBrowser` dependency handoff. This increment does not edit build configuration or operate an editor, application, database, provider or personal document.

## Existing app authority

The companion baseline is Fax Trident PR 5 commit `4e3e4f50d3c7253fcf137a4b1593ecff0153a45d`; its separate native-save page adapter is published at final commit `5e005c2afb0b8a46308b069a653da57f2649d5b8`. The app handoff records 62 passing offline Java tests, 25 passing actual packaged-script Node cases and a passing synthetic production HTTP page smoke for the marker and exact three-argument calls. Those are app/fixture results, not CEF or native SaveAs proof. The native host does not implement another contact, history, suggestion, PDFBox, QR, statistics or authentication service.

Desktop consent creates one immutable mode: USER for explicitly approved private tools, or ADMIN for separately approved scalar statistics only. Native pairing has no role switch. The existing page verifies `faxworkbench.local.v1`, product `fax-trident`, the immutable capabilities/selected tuple/expiry and the nonextending remaining lease returned by `GET /v1/capabilities`. USER never gains ADMIN statistics through a later role change. The desktop client retains its server JWT and checks current DB/token authority around each relay. The native binding cannot call server APIs or acquire additional data.

The pasted link accepts only `http://127.0.0.1:PORT/realm/fax-workbench/#token=TOKEN`, with a decimal port 1 through 65535, no leading zero, and exactly 43 base64url token characters. Aliases, credentials, queries, remote hosts, encoded paths and extra fragment fields are rejected. Internally the native host appends the single literal nonprivileged fragment suffix `&host=daedalus-fax-v1`; this is not an accepted pasted-link extension. The page immediately removes token and marker from browser history. A known native page fails clearly if its native binding is absent; an ordinary browser retains its existing Blob download path.

## Shared browser implementation

The existing `SDaedalusSynapseWorkbenchPanel` now has a fixed native-only Synapse/Fax profile. Synapse's original actor and constructor arguments still select its original paths, binding, and behavior. Fax supplies weak-owner callbacks and its separate UObject; no web data chooses a profile, owner, binding, URL allowlist or reflected method.

The host reuses the nearby local Hero/controller/pawn/realm/viewport checks, UIOnly input capture, focus restoration, generation invalidation and isolated CEF context. One Fax workbench is admitted at a time. The context uses an empty cache/cookie-storage path and nonpersistent session cookies. Pairing text and its Undo history are removed. Popups, devtools/context menus, JavaScript dialogs, subframes, redirects, external navigation, browser error pages and console forwarding are suppressed. No engine-wide browser settings change.

The Fax page has nonce-protected inline assets. The fixed resource methods are:

| Method | Exact paths |
| --- | --- |
| GET | `/realm/fax-workbench/`, `/v1/capabilities`, same-origin UUID image blobs |
| POST | `/v1/contacts/search`, `/v1/history/by-number`, `/v1/history/recent`, `/v1/status`, `/v1/metadata`, `/v1/suggestions`, `/v1/selected-text`, `/v1/admin/stats`, `/v1/qr` |
| DELETE | `/v1/grant` |

No wildcard route, query, upload, arbitrary server URL, external provider, confirmation or send route is admitted. Main-document navigation permits only the selected literal origin and app document, with its exact token/internal marker form or the page's stripped base path. Invalid main navigation disables Fax exports. A document-generation counter also invalidates in-progress file actions when loading replaces the approved document. Observing the exact DELETE route atomically disables further native exports before forwarding the request.

The engine's public resource interceptor is not a network firewall: installed CEF source bypasses read-only interception in some paths. The existing server's restrictive CSP, exact Host/Origin checks and private bearer remain necessary. Neither CEF traffic nor this limitation was exercised by an engine run here.

## Separate narrow file binding

The only Fax object is `window.ue.faxfiles`, a transient `UDaedalusFaxWorkbenchBridge`. The existing engine lowercases reflected function names. Both methods return an asynchronous `FWebJSResponse` containing a JSON **string** with exactly `{ "canceled": boolean }`; cancellation is neutral, and failures reject with a bounded local message.

| Method | Arguments | Fixed native export |
| --- | --- | --- |
| `savepng` | `Base64Bytes`, `GrantExpiresAt`, `RemainingLeaseMillis` | New `fax-qr.png`, at most 262144 bytes |
| `savetext` | Same | New `fax-selected-text.txt`, at most 393216 UTF-8 bytes and 131072 UTF-16 code units; empty text is valid |

There are exactly two Fax UFUNCTIONs. There is no selector, filename/path argument or result, URL, credential, MIME selector, generic dispatcher, owner identifier, server command, or role-setting method. Synapse keeps exactly its original three UFUNCTIONs: `PickImage`, `PickImport`, `SaveJson`. Its existing image/JSON selection and 8 MiB/1000-object JSON validation remain in place.

PNG validation checks its signature; fixed 200 by 200 IHDR and legal format fields; bounded complete chunk framing and CRCs; palette/IDAT ordering; required IDAT/IEND and exact end of input; unknown critical chunks; and rejects APNG chunks. This validates a PNG envelope, **not** pixel decompression or QR content. The existing server and desktop generate and actually decode the PNG, and the page verifies its supplied SHA-256 before export. Plain text validation accepts only well-formed UTF-8, rejects overlong encodings, surrogates and out-of-range code points, and counts resulting UTF-16 units while checking the byte limit. Transfers use bounded canonical base64.

## Lease and local-copy boundary

Immediately before an export, the page refreshes actual capabilities and rejects any changed immutable grant. After encoding, it computes `floor(deadline - performance.now())` from its nonextending deadline, requires 1 through 900000 milliseconds and passes the exact unchanged Java `Instant.toString()` expiry. Native captures its entry clock before decoding, accepts only strict UTC Java Instant syntax with zero through nine fractional digits, floors submillisecond precision and pins the exact expiry string on the first export. Later exports cannot change it or extend the deadline.

Native's deadline is the minimum of its prior deadline, entry time plus supplied remaining lease, conservatively clamped UTC expiry, and pairing start plus 900 seconds. Both UTC expiry and the monotonic deadline are checked inside the same ownership predicate used before/after the modal dialog, bounded writes, flush and no-replace commit. This does not depend on a JavaScript timer running while a native modal is open. The exact observed DELETE route, owner loss, actor destruction, generation change and document replacement also prevent further publication.

Desktop revocation or a server role change **after authorized bytes were supplied** cannot atomically recall those local bytes; no new service polling is introduced. The page suppresses new calls and late UI success after access loss, and native honors a revoke it observes. An already committed local file remains a user-created copy. A rejected late Promise is never presented as erasing that copy. Closing/pagehide clears the page and binding; it does not fabricate a server revocation, job cancellation or rollback receipt. Desktop revoke/expiry remains authoritative for future server reads.

## Shared no-replace filesystem primitive

Fax delegates to the existing Synapse Win32 SaveAs engine through fixed native C++ wrappers. There is one directory/leaf validation and owned-temporary implementation, not another independent copy. Only fixed, removable or RAM drives are permitted. Network/device/drive-relative paths, ambiguous names, mount points, reparse points, changed ancestors and unresolved handles fail closed. The user's selected extension must remain PNG or TXT.

Ancestor directory identities remain pinned without delete sharing through I/O and cleanup. The engine opens one exclusive `CREATE_NEW` sibling with DELETE access, arms by-handle cleanup before writing, writes bounded chunks, flushes, and performs by-handle rename relative to the retained parent with replacement disabled. No path-based deletion/move fallback exists. Existing destination files survive. Weak owner, panel and document generation, approved document and lease are checked throughout. At most one operation runs, with 64 starts per panel and 500 ms spacing. Unsupported platforms return a clear unavailable result.

## Verification handoff

The exact portable UTF-8/PNG parser region was extracted unchanged and compiled separately with cached MSVC 14.44 (`/std:c++17 /W4 /WX /EHsc`). All 54 independent synthetic fixture cases passed. The extracted region SHA-256 is `68e8d9525bb7edf356e3962a5bc6960a2463915caef2af0356994fcfe9185b9a`; the workspace evidence packet is `evidence/fax-native-portable-parser/receipt.json` with the extraction driver, real zlib/CRC fixtures and compiler log alongside. A deliberate complete-envelope/invalid-zlib case is accepted to demonstrate the documented absence of pixel decoding. Independent source review found no open P1/P2 issues, explicitly checked Synapse preservation and the startup guard, and verified all ten file hashes. These narrow results do not compile Unreal, exercise UHT/Slate/Win32/CEF or demonstrate a working installed object.

Before runtime acceptance, the sole Unreal operator must verify the public dependency and UHT build, actual binding serialization, known-native marker/missing-binding behavior, USER versus ADMIN views, strict pairing and routes, explicit revoke, PNG/text save and empty/truncated text, existing-file refusal, cancellation/expiry during the modal and I/O, document/actor/realm/controller loss, repeated actions, cooked browser support and input restoration using synthetic fixtures. No real transmission or personal file is needed for those checks.
