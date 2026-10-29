# Native build 26260428 (game 1.0.4 / patch v1.1.3)

## Identity and preservation

| Stage | Bytes | SHA-256 |
| --- | ---: | --- |
| Original 1.0.4 EXE | 5,722,112 | `d8bfc47c991f01dffc352c6d836f8f1f8dedbfc738a50d9c2342d9e1ae46cf87` |
| Five fixed literals only | 5,722,112 | `bfebe8b75dde2e2f1291f0ef198d607d96e8b3391cef50ee4c9d60699483888e` |
| Complete localized EXE | 5,732,352 | `27d2ab91d5f66868b41111f355d560e8df35bbd1048e82b7310fb26e4d94cb1d` |

The previous current literal recipe is preserved verbatim as
`locales/zh-CN/builds/26152271-executable-text.json`. The three older native
profiles remain separate. Selection requires the complete known input hash
and the corresponding PE `.data` RVA. This profile uses `.data=0x4cd000`.
Unknown profiles, unknown coordinates and changed source instructions fail
before output publication.

This is a rebuild against the supplied new executable, not replacement with an
old executable or one global offset. Original game/system code outside the
narrow guarded localization sites remains from 1.0.4. No Steam-install file is
written and no game process is started by the offline tools.

## Independently identified coordinates

`.pdata` function boundaries, normalized Capstone instruction sequences,
string/table references, exact imports, Ghidra decompilation, final original
instruction bytes and actual Unicorn execution establish the mapping.
Automatic fuzzy candidates were only search aids: for example, a reference
candidate for the callback initializer pointed into teardown code and was
rejected in favor of its actual stores at `0x1b84e0`.

| Role | Canonical 26099941 RVA | 26260428 RVA |
| --- | --- | --- |
| Debug-label producer | `0x4e300` | `0x50b60` |
| F1 previous-state comparison | `0x4fa2e` | `0x525b9` |
| Unlock branch | `0x4fa49` | `0x525d4` (`7504 -> eb04`) |
| F1 previous-state store | `0x4fa60` | `0x52596` |
| Per-frame focus hook | `0x4fa66` | `0x5259c` |
| UTF-8 renderer entry | `0xb05c0` | `0xb6460` |
| Field draw setup | `0x11b450` | `0x1218c3` |
| Field reader hook | `0x11b4f7` | `0x12193b` |
| Collection draw setup | `0x1232fc` | `0x129a1f` |
| Collection reader hook | `0x123379` | `0x129a5a` |
| Native key input | `0x1a7c50` | `0x1b80d0` |
| Registered WndProc capture gate | `0x2f39cc` | `0x3109e3` |
| Common WndProc forwarding hook | `0x2f3a3e` | `0x310d02` |
| Independent key input object | `0xa2ca78` | `0xb5b338` |
| Native held-key array | `0xa30d20` | `0xb5f620` |
| Main window pointer | `0xa312b0` | `0xb5fbc0` |
| Pad 0 connection byte | `0xa314f0` | `0xb5fdd0` |
| Reader state reservation | `0xa68980` | `0xb975a0` |
| Menu state reservation | `0xa68e80` | `0xb97aa0` |

The original `.data` zero-fill ends at `0xb975a0`; `.pdata` starts at
`0xb98000`. Only this previously uninitialized tail is extended for writable
state. `.locmenu` is read-only/non-executable and `.locui` is RX; no RWX section
or imported function is added. The generated reader occupies 2,548 bytes of
its reserved 4 KiB page.

### F1, Win32 and native ImGui

The current held F1 state uses BL. The original edge/debounce stores and native
menu selection logic remain; only the validated unlock branch opcode changes.
The capture gate now compares `[rbx+0x19]` with immediate zero, not R14B.
The current WndProc message ID is R15D. Focus release is inserted after native
focus flags are updated and then executes the displaced forwarding sequence:
`mov rax,[rbx]`, `mov r9,rdi`, `mov r8d,r15d`.

The independent key-held consumer at `0x2f6b5a` and key callback's actual
input-object load at `0x1b8245` have separate provenance byte guards.
Imported cursor function slots are bound by their current names/addresses.
Replay follows the registered WndProc, native queued input and complete native
ImGui NewFrame/Checkbox/EndFrame, including two clicks, one-second holds,
mouse hover/wheel, capture/focus and relocated-image variants. Win32 and CRT
boundaries are deterministic doubles; native decisions are not stubbed.

The pad packet source loads at `0x339023` and `0x33902a` are guarded separately
from the `0x3390f9: cmp byte ptr [rdx],0` connection consumer. Replay supplies
actual raw int16 stick words to `0x33914c` and executes normalization before
the real axis setter at `0x2ee60`. Reader deadzone/repeat/disconnect behavior
and the untouched gameplay axis values are tested afterward.

### New text measurement and reader wrappers

1.0.4 replaced the inlined line-count loops with the native extent helper
`0xb6320`. It runs before both reader hooks. Its width/height results are
still used by the original drawing code.

- Field: owner RSI, text RDI, node RBX; the seven-byte hook at `0x12193b`
  replaces only the native render-enable store. Original Y is already computed.
- Collection: owner RSI, text R14, node RDI; the ten-byte hook at `0x129a5a`
  displaces `mov r8d,160; sub r8d,[rbp+0x63]`.
- Wrappers temporarily normalize these registers for the shared reader logic,
  count NUL-terminated runtime text's LF-separated lines, and restore the
  original allocation. The intended text result is returned through RDI for
  field pages and R14 for collection pages. R12 and unrelated registers remain
  preserved; viewport Y remains the explicit output.
- New draw fixtures live beyond the PE image and reject image/data overlap.
  The new extent helper is observed, not replaced. Rendering must submit
  nonzero glyphs with flag 1, clear the flag afterward and preserve the adjacent
  data sentinel. All 12 postcards and short/long illustrated letters retain
  their existing classification and full source text.

### Fixed-capacity option loader and wording

The current shipped loader is `0x12e870`, getter `0x12b5d0`, context hook
`0x12b6fa`, and three-index table `0x440a80`. The table remains exactly
48 row pointers. Object slot `+0x180` remains the backing-buffer pointer,
not a usable 49th row. The new loader includes UTF-8 processing; it is actually
executed with both the original English and localized Chinese table.

The loader span `0x399` and getter-plus-jump-table span `0x328` are independently
SHA-256 guarded by `tools/replay_option_loader.py`. Native allocation, VFS
read/size/close and memset are explicit boundaries. The real pointer loader
and getter execute without a fabricated 49th row.

HEAD BOB uses read-only context strings for states 1/2, giving
`普通 / 轻微 / 关闭`; minimap remains `关 / 半透明 / 不透明`. All eight stored
states are evaluated, invalid states normalize through original code, and
settings bytes are asserted unchanged. The same-ROM negative control
reintroduces index 48 and demonstrably reads row 0 before the correct context
hook restores the intended wording.

Five fixed literal raw offsets are `0x43f540`, `0x43fdd4`, `0x43fde0`,
`0x43fdec`, `0x43fdf8`. The `HI-RES` slot is 12 bytes in this build (8 bytes
in 1.0.3). Adjacent language variants and graphics-mode values remain intact.

## Reproduction

```powershell
$env:PYTHONPATH = 'tests;tools'
$env:DEMENTIUM_V104_TEST_EXE = (Resolve-Path 'build/full-zh-CN/Dementium II.exe').Path
$env:DEMENTIUM_MODIFIED_EXE = $env:DEMENTIUM_V104_TEST_EXE
python -B -X utf8 -m unittest test_native_profile_v104 test_native_profile_v104_guards test_option_context_loader_v104 -v
python -B -X utf8 -m unittest test_document_draw_v104 -v
python -B -X utf8 tools/replay_option_loader.py --exe 'build/full-zh-CN/Dementium II.exe' --rom 'build/full-zh-CN/rom.zar' --output 'build/update-26260428/native/option-loader.json'
```

`test_native_profile_v104.py` binds the current PE layout independently from
historical suites. Explicit fixture adapters match the current compiler's
register allocation; production code is not rewritten to resemble old code.
The negative guard suite covers unknown profile/address, whole-file source
identity, caller-supplied old/new layout mismatch, actual held-key-consumer
mutation and unlock-branch mutation. Loader tests additionally reject changed
capacity, jump targets, context code and table-extension indices.

REA/Ghidra observations include debug-title xref
`ev_3c9c11ed781bab81f0fc348c39f741e4077d71a841c7c143c346299e7396d901`,
getter function bounds
`ev_060e8feb0868ba78db4152cb10ef78b366bc071d67bf523d587fcfb20f59e468`,
and current loader decompilation
`ev_7b2ec70c01d82a02436e75e36a9b2545db20a9c358f81f3f06cf6c228c81895c`.
The analysis session was closed after inspection. These results are offline
CPU/layout evidence; in-game visuals and physical controller acceptance remain
separate in-game tests.

## Completed evidence

- `build/update-26260428/native/native-tests-final.log`: `Ran 50 tests in 155.008s`,
  `OK`, exit 0, **50 passed / 0 skipped**. This comprises 38 native UI/input/
  reader cases, 5 production guard cases and 7 real option-loader cases.
- The same run's nonvacuous renderer sentinel is
  `FIELD_CARD glyphs=41 flag_at_renderer=[1] sentinel_preserved=True`.
- Parent integration additionally ran `test_document_draw_v104.py`: 4 passed,
  covering 12 postcards in both views, short-letter no-scroll and long-letter
  wheel/key behavior with the actual new extent helper.
- `build/update-26260428/native/option-loader.json` records actual loader rows
  48, resource rows 48, backing-buffer slot 48, all 8 HEAD BOB states and
  `settings_preserved=true` against the final EXE identity above.
- The final production EXE remained byte-identical while the current-build
  fixture register mappings and tests were completed.
