# v1.1 verification — 2026-10-23

## Deliverable and supported inputs

Installer `Dementium-II-CN-v1.1.exe`, internal version `1.1.0`, 78,507,545 bytes:

```text
bffe3e670fda5647036085e17835366697e4a46ae8d3c8bac2bf26eb5e3796a6
```

Prepared for the maintainer's manual publication; no new GitHub Release or tag is created by this task.

- Current reference: Steam AppID 5342930, build 26123896, depot manifest 2475804801624517511.
- Previous verified build 26099941 is supported through the exact sparse native recipe recovered from the hash-verified v1.0 installer. Its historical playthrough remains historical evidence, not a new playthrough.
- The footer identifies both supported build IDs and v1.1. Title and file version identify v1.1/1.1.0.
- The only new source-text record is `EN/OPTIONSNEW.TBL:0047`, `HEAD BOB` → `行走晃动`. The previous 676 source strings remain unchanged.

| Current input/output | SHA-256 |
|---|---|
| Original EXE | `1cc03e74444d956acdde25852209b85f9166d068a2468fafb2c002746ccaf1df` |
| Original ROM | `6ca108be2af076b99eae1a423f3b8c7f56384489b89804e22607a10707c28dc8` |
| Localized EXE | `8ae566d57374715dafef8addb49f672a8c982d82b366843bf446ec730bb7b6f0` |
| Localized ROM | `a50f55624eca5f3ffb594897a4016444911de3a185c58533e74d2a3099d826ab` |

## Compatibility, not universal-version support

The installer recognizes independently verified resource/EXE source variants. Unknown EXE whole-file hashes require the same file length, every original patch byte, the complete PE header/section table, and matching hashes of every non-resource section. These checks bind code, data, imports, relocations, unwind metadata and layout. The installer computes target-side hashes too, preserving unknown unrelated resource bytes during install, idempotence and restore.

All components are inspected before backups or replacements are created. A mismatch is not bypassed. Installation and restore continue to use the exact identities of the actual supplied files and transactional receipts.

Real-file copy tests, using the current input above:

- Normal install, repeat install and restore: `RESOURCE_BASELINE`, `RESOURCE_MODIFIED`, `RESOURCE_ROLLBACK`, all PASS; restored files byte-identical, backup directory removed.
- Unrelated `.rsrc` byte at offset 5319424 changed: unknown original hash `0b07526db46008650caf9778e18d9599d5b1afcd766b6c239896be9d06eff78c`; guards pass, changed byte is retained, repeat install passes, exact unknown input is restored.
- Unpatched `.text` byte at offset 1829376 changed: unknown hash `6955fdb344a292e2c88ad89c9a8e862db3a7a62089fe4f607f3b81731b0095f8`; feature mismatch rejected, both original files unchanged, no backup directory created.
- Native installer synthetic regression: 81 tests PASS, compared with the original installer's 76 PASS.

## Content and native execution evidence

- 677 records, 521 translated, 156 preserved, 179 text resources.
- Full text layout, all 989 PNGs (41 localized / 188 labels), body fallback and UI correction gates: PASS.
- Current-profile native replay: 38 tests PASS, including complete registered WndProc → queue → actual ImGui NewFrame/Checkbox/EndFrame, normal/relocated image, keyboard/focus/repeat, cursor, wheel, XInput and right-stick reader lifecycle.
- Actual native measure/UTF-8 draw/glyph-submit replay covers postcards and short/long letters; nonempty renderer calls and adjacent state integrity are asserted. Pause coordinates are checked against real localized glyph ink.
- Portable packaging and isolated standard-library-only patch imports: 3 tests PASS.
- Final repository run: 366 tests, `OK (skipped=178)`; the 178 optional historical-fixture skips are not counted as current-build passes. The final self-contained installer verification completed all 13 stages with exit status 0.

Native address findings, replay doubles and legacy-fixture skip boundaries are documented in [NATIVE_BUILD_26123896.md](NATIVE_BUILD_26123896.md). Historical tests requiring absent legacy fixtures are explicitly skipped; those skips do not count as current-profile execution evidence.

## Reproduction and limits

See [BUILDING.md](../BUILDING.md) for verified legacy payload import, current build and full installer verification commands. Detailed local command/input/stdout/exit records are generated under `build/installer/VERIFICATION.txt` and `build/v1.1-verification/VERIFICATION.txt`. Generated files are not game assets committed to this repository.

Automated verification does not install into the actual Steam directory or launch the game. During final verification the maintainer independently opened the delivered installer and game; that live installation is preserved, and remaining verification uses an isolated copy of its hash-verified original backup. Offline replay, file-copy installation and offscreen installer previews are not a new in-game playthrough or physical controller-device acceptance.
