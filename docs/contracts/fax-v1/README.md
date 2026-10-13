# Existing fax app object/job handoff

The implementation stays in [fax-trident](https://github.com/RicheyWorks/fax-trident): the existing JavaFX desktop app and Spring backend. An in-world fax object is another interface to those jobs. The new backend is transport-ready, default disabled, and tested with a local provider mock. This Daedalus change provides the handoff contract; it does not add a placed fax actor or certify an actual recipient received anything.

The original `FaxEngineService.sendFax` counted PDF pages and marked a record sent without transport. The legacy controller returned a different ID. Those behaviors must be corrected in fax-trident before a realm interface treats any status as evidence. Simulator states must remain visibly simulated.

## Proposed in-world flow

The local player opens the same app's authenticated interface. Select a document explicitly or export a PDF from PhotosToPDFPC; uploading to a configured fax backend is a separate action with its destination disclosed. Never give the backend arbitrary local filesystem paths or fetch document URLs supplied by a realm server. Nothing transfers automatically from the local photo bridge to a cloud fax service.

Use the existing bounded authenticated upload endpoint to obtain an owner-scoped upload ID. Prepare a job with the recipient and a stable idempotency key. Show the immutable document preview, page count, digest and exact recipient. Only an explicit reviewed confirmation submits the job. Cancel is available before submission; a cancellation button must not imply recall of an already submitted fax. Poll the same job ID and display its actual state, including uncertainty and failure.

| Existing-app endpoint | Realm interface responsibility |
|---|---|
| `POST /api/fax/jobs` | Authenticated prepare with `recipient`, `uploadId`, `idempotencyKey`; retain the returned `faxId`. |
| `GET /api/fax/jobs/{id}` | Authenticated owner-scoped status; no global document/job broadcast. |
| `GET /api/fax/jobs/{id}/document` | Owner-only review of the prepared immutable PDF. |
| `POST /api/fax/jobs/{id}/confirm` | Explicit confirmation carrying the reviewed recipient, SHA-256, page count and `confirmed: true`. |
| `POST /api/fax/jobs/{id}/cancel` | Cancel prepared work; report the backend's response honestly once submission has started. |

The configured provider's document-fetch capability and signed callback endpoints are infrastructure, not player actions. They must not be exposed as another unrestricted file-download API. Credentials stay in the backend, never in Unreal levels, NFTs or shared art metadata. The desktop and future realm interface share the same authoritative jobs rather than creating unrelated IDs.

## Reliability and activation

Telnyx submission acceptance means queued. Provider-authenticated delivery evidence establishes delivered. A lost or ambiguous submit response becomes uncertain and requires reconciliation; it must not trigger an automatic duplicate send. Durable job/idempotency state and monotonic status transitions must survive process restarts and concurrent callbacks/polls. Callback replay handling uses the stable event identity/content, while signature verification uses the exact raw request bytes.

Actual sending remains disabled until the user explicitly authorizes provider account/cost/data setup and configures credentials, sender number/connection, persistent database, approved public media/callback endpoints and retention policy. Do not activate against the default ephemeral development database. Mock tests, simulated records, queued responses and a browser launch are not proof of real delivery.

Claude owns the native fax panel/actor and live acceptance after the backend contract is reviewed. Blender owns original physical fax art after explicit acceptance. The photo object is the first implemented adapter; fax native placement is still a separate handoff. No fax transmit action, provider purchase, public deployment or NFT mint/sale is performed by this Daedalus PR.
