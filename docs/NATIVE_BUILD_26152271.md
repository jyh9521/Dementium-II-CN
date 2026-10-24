# Native build 26152271 (game 1.0.3 / patch v1.1.2)

## Shipped identity and preserved update

- Clean EXE SHA-256: `1d1024c52dbe73ab2d449bb677bbea58ba9a102addd2e6b97393dc7f66b3f93d` (5,541,888 bytes).
- Five localized literals plus the HEAD BOB table index produce SHA-256 `e1a19724d983d1fa8cfa1f5747291ab5568308aff6325b5c4ac725dca33efdcf`.
- Final localized native EXE SHA-256: `36a578418ce15e282f05a72ceb0bdea1df5360f5232dec06bd29b61bf6eefc72`.
- Old build 26123896's fixed-string recipe is retained separately in `locales/zh-CN/builds/26123896-executable-text.json`; its production native mapping remains unchanged.
- Production selection requires the complete localized-input hash and the matching `.data` layout (`0x4a4000` for 26152271). Unknown profiles and unmapped coordinates fail closed.

The original EXE is read-only input. There is no global rollback to an old EXE. New title-selection, game simulation, interaction/subtitle and platform code remain in the supplied 1.0.3 binary. Only version-guarded localization references and the existing localized UI/reader hooks are rebuilt. No game process is launched.

## Native matching and non-uniform changes

Old/current shipped `.pdata` function boundaries, normalized Capstone instruction streams, exact import identities, RIP-relative data consumers, string/table contents and exact final source guards establish the new mapping. A single executable delta is invalid.

| Canonical 26099941 coordinate | 26152271 coordinate | Role |
| --- | --- | --- |
| `0x4e300` | `0x4e3b0` | native debug labels |
| `0x4fa2e` | `0x4fcf4` | F1 previous-state consumer |
| `0x4fa49` | `0x4fd18` | unlock branch, `7508 -> eb08` |
| `0x4fa60` | `0x4fb77` | native previous-state store |
| `0x4fa66` | `0x4fb7e` | existing frame-rate load / localized focus hook |
| `0xb05c0` | `0xb0560` | actual UTF-8 renderer |
| `0x11b450` | `0x11ba70` | field draw setup |
| `0x1232fc` | `0x123c3c` | collection draw setup |
| `0x1a7c50` | `0x1a88e0` | native input handler |
| `0x2f39cc` | `0x2f617c` | registered WndProc capture gate |
| `0x2f537c` | `0x2f7bbc` | inner pointer dispatch gate |
| `0xa2ca78` | `0xa31ab8` | independent key callback input object |
| `0xa30d20` | `0xa35db0` | OS held-key array |
| `0xa312b0` | `0xa36340` | main window |
| `0xa314f0` | `0xa36560` | first controller connection flag |
| `0xa68980` | `0xa6da20` | newly reserved reader state |
| `0xa68e80` | `0xa6df20` | newly reserved menu state |

The new `.data` zero-fill ends at `0xa6da20`, and `.pdata` begins at `0xa6e000`. Reservation stays in that previously uninitialized gap. New code is RX `.locui`; translated strings are read-only/non-executable `.locmenu`. Existing imports and their exact names are retained; IAT ordering changed and is matched by name, not a common displacement.

### F1 and native pointer-to-ImGui transfer

The F1 branch moves into another basic block. The original current/previous-state operands use R14B/R15B instead of CL/SIL, and the native unlock branch skips eight bytes instead of four. The production patch changes only the validated branch opcode, keeping its original displacement and surrounding official code.

The native input-to-ImGui transfer now uses RSI/R14 instead of R8/RSI. Replay fixtures explicitly provide those current registers; the production code is not rewritten to resemble the old compiler allocation.

### Controller packets and input-global regression

Game 1.0.3 copies native controller packets to the stack before normalization. The connection consumer is now `0x31e019: cmp byte ptr [rdx],0`; the source packet loads at `0x31df43` / `0x31df4a` are individually guarded. The reader checks the actual source connection byte at `0xa36560`; four actual raw stick-word pointers enter the shipped normalization instructions at `0x31e06c`.

A provisional adjacent-global shift was rejected by the real native key-callback replay: KEY_INPUT is `0xa31ab8`, not `0xa31ac8`, and VK_HELD is `0xa35db0`, not `0xa35d70`. New provenance guards bind both actual native consumers before hook generation. Focus-release and key-repeat tests then exercise the same source-bound state. Synthetic state written to the wrong guessed location is not accepted as native evidence.

## Context-specific wording and exact slots

- The English option getter is now `0x125540`; the verifier selects it by the shipped data profile and exact SHA-256 of its code span, not a guessed jump.
- HEAD BOB's three-index table starts at raw `0x41b700`; only its middle index at `0x41b704` changes `41 -> 48`.
- The new `HI-RES` literal slot is eight bytes instead of twelve. The audited UTF-8 target still fits; adjacent `2`/`1` literals remain untouched.
- The preserved standalone `ALTA RES.` candidate is recorded at raw `0x41b538`, not the suffix of `CRT ALTA RES.`.

## Reproduction and test boundary

```powershell
$env:DEMENTIUM_V103_TEST_EXE = (Resolve-Path 'build/full-zh-CN/Dementium II.exe').Path
python -X utf8 -m unittest discover -s tests -p test_native_profile_v103.py -v
python -X utf8 -m unittest discover -s tests -p test_native_profile_v103_guards.py -v
python -X utf8 tools/verify_option_context.py build/full-zh-CN
```

The current suite independently binds build 26152271, while the historical 26123896 suite uses `build/previous-26123896/`. Existing helpers execute current native machine code through a current version fixture, including the registered WndProc → native queue → complete native ImGui frame → actual Checkbox path, relocated-image variants, reader keys and controller scrolling, actual field/collection UTF-8 renderer boundaries, all twelve postcards, short/long letters and pause coordinates. Win32, heap/math and final glyph submission use explicit deterministic boundary doubles.

The negative suite checks unknown profile/address rejection, complete source-hash rejection, new/old layout mismatch, mutated actual held-key consumer and mutated unlock branch. These are offline CPU/layout results, not controller-device or in-game visual acceptance.

### Completed current-build evidence

- `build/update-26152271/native-tests-final.log`: `Ran 38 tests in 127.224s`, `OK`, exit `0`; actual EXE SHA-256 `36a578418ce15e282f05a72ceb0bdea1df5360f5232dec06bd29b61bf6eefc72`.
- Nonempty rendering sentinel: `FIELD_CARD glyphs=41 flag_at_renderer=[1] sentinel_preserved=True`.
- `build/update-26152271/native-guards-final.log`: all 5 negative guard tests pass, exit `0`.
- Option replay: `OPTION_CONTEXT {"head_bob":["普通","轻微","关"],"minimap":["关","半透明","不透明"]} result=PASS`, exit `0`.

### Completed run

`build/update-26152271/native-tests-final.log`: `Ran 38 tests in 127.224s`, `OK`, exit 0. `native-guards-final.log`: 5 tests, `OK`, exit 0. The renderer boundary reports `FIELD_CARD glyphs=41 flag_at_renderer=[1] sentinel_preserved=True`. Final production EXE identity remains `36a578418ce15e282f05a72ceb0bdea1df5360f5232dec06bd29b61bf6eefc72`.
