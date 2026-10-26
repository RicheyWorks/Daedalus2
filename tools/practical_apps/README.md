# Practical app acceptance tools

These tools run off-editor. They do not activate plugins, contact Unreal, change
the world or install/start a companion application.

`Test-AcceptedSource.ps1` checks an explicitly supplied local accepted184 receipt
against one explicit plugin source tree. It validates the selected full commit,
all 184 LF-normalized source hashes/lengths, missing and additional source leaves,
and rejects reparse points and unsafe relative paths. It never uses historical
140-file admission helpers. Content, saved maps and runtime state are outside its
scope, so the asset owner can keep working.

Run with PowerShell 7 using the current operator's receipt and plugin path:

```powershell
pwsh -NoProfile -File tools/practical_apps/Test-AcceptedSource.ps1 `
  -BaselineReceipt $acceptedReceipt -PluginRoot $pluginRoot `
  -ExpectedHead '074c519b70225b36e890531843bc55eb0fd3a363' `
  -OutputReceipt $newReceiptPath
```

The output path must be new, outside the plugin, and its existing parent chain
must contain no reparse points. A failed check
does not mutate the source tree. A matching source receipt is not module-load,
paired-service, file-dialog or gameplay acceptance. Keep the receipt local; it
does not belong in public operational logs.

The focused self-test uses only a new synthetic directory:

```powershell
pwsh -NoProfile -File tools/practical_apps/Test-AcceptedSource.Tests.ps1 `
  -TestRoot $newSyntheticDirectory
```

It covers matching CRLF/LF source, changed/extra source, old140 admission, unsafe
receipt paths, output/source aliases and refusal to overwrite earlier evidence.
The alias case creates a test-only Windows directory junction. No SDK, editor, Pester,
download or external service is required. The synthetic files remain for review.

See [paired workflow acceptance](../../docs/acceptance/practical-apps-paired.md)
for the service/native boundary and a minimal operator sequence.

The [photo fixture](photo/README.md) uses the existing packaged PDF converter;
the [image fixture](image/README.md) compiles only the existing eight app sources
with its cached encoder. Both accept explicit local paths, generate their own
synthetic inputs, keep fresh private links out of stdout, and support brief
service lifecycle checks. They do not automate desktop approval or native UI.
