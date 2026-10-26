# Practical object art and placement handoff

This is an owner request, not an accepted or shipped art claim. Follow `bot-team/art/BRIEF.md` and use `bot-team/art/QUEUE.md` for art status. Blender owns creation/export and Claude owns native import, collision/reach, placement and Play evidence. Do not mark a prop READY without its export; do not mark it SHIPPED from code compilation.

Prefer compatible existing props for this pilot. Queue row 102 records `Prop_Workbench`, 396 triangles and 1.04 m, as shipped at `/Game/Daedalus/Art/Prop/Prop_Workbench`. That queue record is a candidate, not verification that the asset is currently present or suitable in the active realm. Claude/Blender must inspect it. Preserve existing workbench objects and source assets; place an additive instance.

| Interface | Existing native adapter | Requested physical role | Accepted owner/status |
| --- | --- | --- | --- |
| PhotosToPDFPC | `ADaedalusPhotoPdfMachine` | Small scanner/PDF printer; explicitly selected image exports | Pending Blender art and Claude placement/Play |
| Image Optimizer | `ADaedalusLocalAppMachine`, `ImageOptimizer` | Photo workbench, existing workbench candidate preferred | Pending Blender art and Claude placement/Play |
| Synapse | `ADaedalusLocalAppMachine`, `Synapse` | Study desk/card station | Pending Blender art and Claude placement/Play |

If new props are necessary, propose `Prop_PhotoPdfPrinter`, `Prop_ImageWorkbench` and `Prop_StudyDesk` as original blocky props in their own collections. Use metres, applied scale, bottom-centre origin, Blender -Y front, no more than 3,000 triangles and one to three flat-colour material slots. Preserve the original companion/service identifiers regardless of art names. Add requested rows to the shared queue only under the art owner's normal process; this draft changes no queue or shared art file.

No sensitive pairing URL, file name, document, answer or review receipt belongs on a mesh, texture, actor default, map, material or asset/NFT metadata. A local runtime pairing UI obtains a link from the chosen running app and calls `PairLocalApp`; generic preset changes use `SetApplication`. The app grants user-selected data access. Art never grants an entitlement or provider credit.

Live acceptance should separately record: correct nearby local-player interaction; mismatched/invalid pairing refusal and clearing; switching presets away/back requires re-pairing; repeated/failed Use respects cooldown; photo chooser produces downloadable validated PDFs; image workbench downloads copies while originals remain unchanged; Synapse explicitly selected cards reveal only on action, save once and revoke access. Keep mock fax/preparation clearly labelled; the native fax interface and real receipt remain separate work.
