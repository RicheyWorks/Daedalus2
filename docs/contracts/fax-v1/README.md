# Existing fax app object/job handoff

The implementation remains in [Fax Trident](https://github.com/RicheyWorks/fax-trident): its Spring-free JavaFX desktop talks to the existing authenticated Spring backend. The backend has an owner-scoped immutable PDF/job service and a default-disabled provider adapter. This contract is not evidence of real transmission or a native fax actor.

The legacy engine originally counted pages and manufactured sent state without transport. At inspected backend checkpoint `b5e999f93e92135be510bb2a42157cd88ba5fc5f`, legacy states are explicitly simulated and `/api/fax/send` rejects transmission in favor of exact-review confirmed jobs. The provider source remains disabled and unverified against a real recipient. Historical transport/mock/restart evidence does not qualify the new local bridge.

## Preparation-only companion increment

The next additive source closes the missing local handoff from the **already logged-in existing desktop** to one explicitly approved prepared job. Its exact app source, hashes, scope and limits are recorded in [realm-preparation.json](realm-preparation.json). It is source written but unbuilt/unrun; tests, builds, application/services and native operation remain deferred.

After later authorized installation, the desktop's separate Realm preparation action accepts an explicitly selected bounded PDF and E.164 recipient. It uses the existing configured **literal `http://127.0.0.1:<port>`** server upload and prepare routes, freezes the selected bytes/upload ID/request key through uncertainty, and shows the immutable recipient/digest/page/byte tuple before granting local access. It never calls the existing send-capable `MainView.sendFax` workflow. Existing desktop send behavior remains separate. Default `localhost` and IPv6 configurations do not enable this pilot; authentication and relay must use the same direct literal origin.

A new random, expiring literal-loopback capability exposes only this one approved job's status, exact reviewed PDF, pre-submission cancellation and local revoke. The backend JWT stays inside the desktop; no account-wide list, arbitrary route, job ID, document URL, local path or recipient is accepted from the realm. Logout/re-login and close invalidate the local grant. A syntactically valid link is not installed-app or server-identity proof.

| Local route | Purpose |
| --- | --- |
| `GET /v1/capabilities` | Verify `faxprep.local.v1`, `productId:fax-trident`, read/cancel scope and actual limits |
| `GET /v1/job` | Read the one approved immutable job and truthful current state |
| `GET /v1/document` | Download that exact validated snapshot |
| `POST /v1/cancel` | Explicit cancellation only while the existing server permits it |
| `DELETE /v1/grant` | Revoke local access; leave upstream job/login unchanged |

There is **no local confirm/send route**. Mutations require the exact local Origin; every API request carries the local grant Bearer capability and exact literal Host. The private launch link is `http://127.0.0.1:<port>/realm/fax-preparation/#token=<43-base64url-characters>`. Browser permission is transient and separate from server authentication. No CORS or arbitrary backend proxy is added.

## Existing backend authority

| Existing backend endpoint | Authorized use in this increment |
| --- | --- |
| `POST /api/fax/uploads` | Explicit desktop-selected PDF only; opaque upload ID |
| `POST /api/fax/jobs` | Prepare with recipient/upload ID/stable key; never transmit |
| `GET /api/fax/jobs/{id}` | Owner-scoped status of the one approved job |
| `GET /api/fax/jobs/{id}/document` | Exact immutable review snapshot |
| `POST /api/fax/jobs/{id}/cancel` | Existing pre-submission cancellation and honest uncertainty |
| `POST /api/fax/jobs/{id}/confirm` | **Not called or exposed by this integration**; existing desktop route can transmit when separately configured |

The source PDF limit is 25 MiB, 1–100 unencrypted pages and finite positive page dimensions at most 14,400 points. Existing PDFBox/backend validation remains authoritative; the local adapter rechecks actual snapshot bytes, digest and page bounds. No automatic photo-to-fax transfer occurs. Server upload is a distinct explicit action with the local destination disclosed.

A separate existing desktop operation can submit a prepared job. The local bridge must show its actual state and refuse unsupported cancellation, rather than infer that access to preparation prevents another authorized desktop action. An accepted provider request is queued, not delivered; a real delivery claim requires the existing correlated authenticated evidence. No fax send or provider access was performed here.

## Lifetime, ownership and remaining binding

Local revoke/close/expiry does not cancel the backend job or delete its upload. Uploads retain the existing one-hour lease; uncanceled job PDFs retain the existing 24-hour lease. Explicit confirmed cancellation revokes the snapshot, subject to the server's cleanup/retry behavior; it is not a secure-erasure receipt. Lost upload or prepare responses can leave leased server work. Retry the frozen action; after losing its transient recovery identity, inspect the existing desktop/server recovery before deliberately making another job. Downloaded files remain user files.

Native fax actor/panel binding is still missing. The current typed native app enum accepts Image Optimizer/Synapse links, not this fax protocol. A future additive adapter must preserve the preparation-only surface and user approval; it must not open or invoke the send-capable desktop action by name. Only the user-designated `codex-play-guard` owns future Unreal installation, placement and Play. Blender physical fax art remains a separate explicit handoff; no art or map was changed.

The four-app capability map records bridge source separately from missing native binding and intentionally unexposed desktop features. No credential creation, external server activation, real fax transmission, provider purchase, public deployment or NFT action is part of this increment. Compilation/package compatibility, synthetic connected behavior, actual file cleanup and native acceptance remain unverified.
