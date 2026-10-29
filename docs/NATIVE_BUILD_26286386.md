# Native Steam build26286386 (game resource version1.0.4)

## Identity and profile selection

The original EXE is5,721,600 bytes with SHA-256
`e569f03ce6c1bc3c30bd360592266d9efee9c6587dde5b5fb19b34aa1430b957`.
The five fixed menu literals produce
`a2804aef3fd18daf509145db54a95e6b83635864747e8055b5f37661c5dd6d2d`.
The prior26260428 literal recipe is retained verbatim in
`locales/zh-CN/builds/26260428-executable-text.json`.

Both official EXEs report1.0.4.0 and use `.data` RVA0x4cd000. Neither value alone
identifies the native coordinate space. Full input SHA-256 selects production
profiles. An independent section-layout check distinguishes raw `.data` sizes
0x23400(old) and0x23200(new); replay fixtures use the same explicit distinction.
Existing historical profiles remain separate. Unknown addresses and source-byte
changes fail before a localized EXE is published.

## Independently verified mapping

Normalized Capstone instruction sequences, `.pdata` boundaries, typed RIP/data
references, explicit leaf-function comparisons, imported names, Ghidra
observations, and native Unicorn execution establish the new mapping.
10,165 function fragments match exact normalized instruction sequences; this
is comparison evidence, not a claim that every official change was inspected.
The remaining required leaf functions, pointer-dispatch block, pause-coordinate
site, entity table and new zero-fill reservation have separate exact checks.
No global address shift is assumed.

| Role |26260428 RVA|26286386 RVA|
|---|---:|---:|
| F1 unlock branch |0x525d4|0x525d4|
| Field reader hook |0x12193b|0x12193b|
| Collection reader hook |0x129a5a|0x129a3a|
| Pause label X/Y immediates |0x12da22|0x12da52|
| Native key input |0x1b80d0|0x1b8110|
| Native held-key consumer |0x2f6b5a|0x2f6b9a|
| Registered WndProc capture gate |0x3109e3|0x310a23|
| Common WndProc forwarding hook |0x310d02|0x310d42|
| Independent key-input pointer |0xb5b338|0xb5b2b8|
| Native held-key array |0xb5f620|0xb5f5d0|
| Render-enable byte |0x4f0a2b|0x4f09eb|
| Reader state reservation |0xb975a0|0xb97540|
| Menu state reservation |0xb97aa0|0xb97a40|

The new state begins at the original `.data` zero-fill end0xb97540 and remains
below `.pdata` at0xb98000. `.locmenu` remains read-only/non-executable;
`.locui` remains RX. No RWX section or new import is introduced. All untouched
instructions and data remain from the new official EXE.

## Official49-row option expansion

The new `EN/OPTIONSNEW.TBL` contains49 real rows. Row48 is now the official
`MELEE CROSSHAIRS` label, localized as“近战准星”. The actual loader0x12e8b0
compares its row count with0x31 at0x12ebf9. Its backing-buffer pointer moved
from object offset0x180(slot48) to0x188(slot49). The original49-row capacity
and both new locations are preserved; no table-extension patch is introduced.

The getter0x12b5b0 retains head-bob option10 in settings+0x94 bits0..2 and adds
melee-crosshair option11 in bit3. The context-only head-bob hook moves to
0x12b6da, with original index array[16,41,18] at0x440a70. Display strings remain
“普通/轻微/关闭”; minimap remains“关/半透明/不透明”. The melee option uses the
original“关/开” value rows and retains the shipped setting bit and defaults.

Replay executes the real loader and getter against both English and Chinese
ROMs. It checks all eight head-bob values with melee bit both clear and set,
melee OFF/ON values, exact row count, backing-pointer position and unchanged
settings bytes. Negative controls on the same ROM redirect head-bob to row48
(the melee label) or slot49(the backing string); neither is mistaken for a
valid head-bob translation. Changed capacity, getter code, hook, context stub
or context indices are rejected.

Ghidra getter evidence:
`ev_f90233d065540e528cf8e753f39f98c565563e6145f8cc00f52efea16ada7a77`.
Ghidra loader evidence:
`ev_d0c347d76d474fe16ced904f2cc9f5ecc56b4db09f6387300fafbd07ad004b1c`.
Complete returned records and comparison details are retained in
`build/update-26286386/native/`.

## Reproduction and acceptance

```powershell
$env:PYTHONPATH='tests;tools'
$env:DEMENTIUM_26286386_TEST_EXE=(Resolve-Path 'build/full-zh-CN/Dementium II.exe').Path
$env:DEMENTIUM_MODIFIED_EXE=$env:DEMENTIUM_26286386_TEST_EXE
$env:DEMENTIUM_PREVIEW_ROM=(Resolve-Path 'build/full-zh-CN/rom.zar').Path
python -B -X utf8 -m unittest test_native_profile_26286386 test_native_profile_26286386_guards test_option_context_loader_26286386 test_document_draw_26286386 -v
```

The suite covers native F1 debounce, registered mouse dispatch, actual native
ImGui frames, held-input/focus lifecycle, real XInput normalization, reader
scrolling, pause layout, all12 postcards and short/long illustrated letters,
including relocated-image cases and nonempty glyph-submit assertions.
Win32, file/allocator and final glyph-submit boundaries are deterministic
fixtures; native decisions and the UTF-8 measurement helper execute unchanged.
The game process is not launched. Offline CPU/layout results are distinct from
in-game visual, physical-controller and complete-playthrough acceptance.

## Completed evidence

- Current native suite: `Ran 56 tests in 201.183s`, `OK`, exit0;56 passed/0 skipped.
- Nonvacuous render sentinel: `FIELD_CARD glyphs=41 flag_at_renderer=[1] sentinel_preserved=True`.
- Original and localized option-loader records both report49 rows, slot49 backing buffer and unchanged settings.
- Isolated native rollback restores SHA-256 `e569f03ce6c1bc3c30bd360592266d9efee9c6587dde5b5fb19b34aa1430b957` and the English melee option; the localized EXE remains `910278feef507f8a8a541be0b8783f5fa302753148e4cdbce55fe3176af5c4ab`.
- Exact stage commands, inputs, literal results and exit statuses are retained in `build/update-26286386/native/VERIFICATION.txt`; the full test output is `native-tests-first.log` in the same directory.
