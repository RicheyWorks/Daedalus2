# Ocean chunk persistence

OceanChunkStore owns a configured directory with an OS lifetime writer lock.
The immutable metadata records store format, seed and generator version. Another
writer, incompatible metadata, or a data directory without its metadata refuses.
Missing chunk records generate deterministically and save before returning.
Existing records always win, including a saved empty world representing a fully
cleared chunk. Returned chunks are independent copies; edits require explicit save.
There is no resident cache and no whole-realm allocation.

Each chunk uses the existing DAEW WorldStore format and a bounded signed address.
Records larger than 64 KiB, symlink records, malformed saves or saves naming a
foreign world/chunk refuse. Routine saving also refuses to replace corrupt data.
The store never repairs bad files by regenerating terrain. Restores or deliberate
repairs belong to an explicit operator workflow with backups.

WorldStore has a compatibility fallback that copies over a file non-atomically.
OceanChunkStore leaves that shared behavior unchanged: it writes through WorldStore
into private staging, forces that file, then requires an atomic replace of the
public record. If atomic moves are unsupported, the operation fails. Metadata is
also staged/forced/atomically published. File forcing and atomic visibility do not
prove directory-entry survival under power loss; host backup/restore and crash
fault-injection tests remain required. Failed staging may leave private temporary
files after a killed process; these are never treated as authoritative chunk data.

Lock ownership is per store directory, so separate district directories can have
separate writers. Cross-directory routing, authorization, eviction transactions,
concurrent edits to returned chunks and distributed writer leases are not provided.
A host must save before eviction and avoid directly modifying record files while
this store owns them. Absence after storage loss is not distinguishable from an
unvisited chunk; production storage/backup policy is still necessary.

Validation: 12 focused Ocean tests and all 712 core tests passed. A separate-JVM
writer/reader preserved an edited block and a completely empty chunk, an actual
competing JVM was denied the writer lock, and a new reader reopened after release.
The probe took 2.640 seconds including Java source compilation/startup and used
148 bytes for its two tiny records plus metadata/lock. This is not a server sizing
estimate. See ocean-store-proof.json.

Run the process probe after compiling daedalus-core, choosing fresh paths:

```powershell
python tools/ocean/check_store.py --java JAVA_EXE --classpath daedalus-core/target/classes --probe tools/ocean/OceanStoreProbe.java --directory FRESH_STORE_DIRECTORY --output FRESH_PROOF_JSON
```

The Windows/Ubuntu Ocean CI now repeats this probe. WorldHub/WorldService and the
Unreal realm loader are unchanged. This module is ready for host integration;
server realm registration, nearby streaming, public recovery and visible Play
acceptance are not completed by these tests.
