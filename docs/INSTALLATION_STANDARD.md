# Installation, Upgrade and Recovery

This specification applies to installers, patch scripts and documented manual installation procedures.
This document defines requirements; adopting it does not add installer capabilities or verify the existing installer. Acceptance is [G4](ACCEPTANCE.md).

## 1. Installation manifest

Record package version, locale, supported-input manifest, payload digests and each relative target path.
For every path, record operation (`add`, `replace`, `remove`), expected before/after hash, ownership, backup locator and restore action.
Include settings changes, generated runtime files and save-format/locale compatibility when relevant.
Keep backups per installation/version; never overwrite the only clean original with an already-patched file.
Do not modify player saves by default. Explicit migrations require dedicated backup and compatibility tests.

## 2. Transaction sequence

1. **Preflight:** resolve the installation root, validate all paths and supported input identities, check space/permissions and ensure the game is closed when required.
2. **Plan:** show intended changes; detect other mods, unknown versions and partial installations before writing.
3. **Stage:** create payloads in an isolated location, verify every output and prepare verified backups.
4. **Commit:** apply the verified plan with a durable operation journal. A single-file atomic rename does not make a multi-file install atomic.
5. **Verify:** hash/read back installed files and run appropriate launch/resource checks.
6. **Recover:** on failure, resume or reverse only journaled operations; verify the restored state and retain diagnostics.

Reject traversal, absolute/drive-qualified target paths, symlink/reparse escapes and case-colliding manifest entries.
Use one well-defined root and validate that every filesystem operation stays inside it or an explicitly selected backup location.
Make repeat installation a verified no-op or an explicit repair operation, not a second patch over unknown bytes.
Unknown conflicts stop with a report; they are not silently replaced.

## 3. Upgrade and uninstall

An upgrade checks the installed-version manifest and supports documented source versions only. Recognized patched hashes belong to that installed-state manifest, not to the clean-original input manifest. A listed donor-file set is allowed only as declared in the build profile.
Verify compatibility of saves, custom glyph mappings and resource IDs across versions/locales.
Uninstall removes only owned added files and restores only owned replacements with valid backups.
If a file was edited manually or by another mod after installation, report the conflict and preserve it for explicit resolution.
Preserve unrelated files, saves and settings. Restore settings individually rather than replacing an entire local configuration blindly.
Record hashes before install, after install and after recovery; original behavior also needs a smoke test, not only matching bytes.

## 4. Required tests

| Case | Expected result |
|---|---|
| Clean supported input | Intended payload installed and verified |
| Wrong input, unlisted mixed set or unrecognized modification | Rejected before any changes |
| Repeated installation | Verified no-op or documented repair |
| Supported upgrade | New payload verified; backups remain valid |
| Unsupported upgrade/mod conflict | Explicit failure; existing state preserved |
| Missing/corrupt payload or backup | Preflight failure, no partial changes |
| Disk-full/permission failure | Failed state reported; journal supports recovery |
| Interrupt after each commit step | Restart recovery restores consistent old or new state |
| Uninstall | Owned changes reversed; unrelated/local files preserved |
| Changed file before uninstall | Conflict detected without destructive overwrite |

Inject failures at each multi-file write boundary in a disposable copy. Record the exact restored hashes and baseline behavior.
Document recovery instructions that work when the installer process itself is interrupted.
Manual installations need an equivalent verified backup/restore procedure and clearly stated limitations.
