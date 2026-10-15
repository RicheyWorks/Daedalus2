# Windows file-helper compile correction

The combined native snapshot `f4983b977df1fef8fd96f2003e2a55154b21100f` passed UHT but failed C++ compilation in the Photo, Image and shared Synapse file helpers. Three primary errors involved `FILE_DISPOSITION_INFO.DeleteFile`; four involved `FALSE`, with four additional initializer diagnostics caused by those undefined identifiers.

Under `UNICODE`, the Windows SDK defines `DeleteFile` as `DeleteFileW` before declaring the structure's one `BOOLEAN` member. Unreal's Windows wrapper then removes that macro. Accessing the member by the original macro spelling after wrapper cleanup fails. Unreal also removes `FALSE` after the Windows include boundary.

Source correction `c3625e189d68eec798c19bef0b9158718d51832e` changes only three aggregate initializers and four dialog-result comparisons:

```cpp
FILE_DISPOSITION_INFO Disposition = { static_cast<BOOLEAN>(bDelete) };
const bool Selected = ::GetSaveFileNameW(&Dialog) != 0;
```

The aggregate initializes the SDK's actual `BOOLEAN` without spelling a macro-sensitive member. Converting `bool` preserves the existing zero/one delete marker. A WinAPI `BOOL` result remains selected for every nonzero value. The open-dialog result uses the same comparison. Windows wrappers remain closed at the original boundaries; no macro is reintroduced.

The correction preserves handle ownership, temporary-file cleanup, no-replace publication, input/output validation, dialog flags, cancellation, expiry and lifecycle predicates. Fax exports continue using the shared Synapse helper. It changes no public API, transport, credentials or provider behavior.

The focused offline check uses the matching cached SDK headers and compiler in syntax-only mode. It must reproduce the old member and `FALSE` diagnostics, then accept the corrected form and compile-time assertions for structure layout, delete-marker values and zero/nonzero dialog results. This fixture does not compile an Unreal translation unit or establish a corrected UHT/module/link/runtime result. The corrected full snapshot needs a separate native build and runtime acceptance before installation.

Current file hashes are recorded in the adjacent capability map and applicable install manifests. The shared parent and Fax continuation have different complete Synapse helper bodies; each delivery records its own complete-file hash while retaining the same bounded correction.
