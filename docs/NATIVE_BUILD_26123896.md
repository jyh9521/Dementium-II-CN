# Native build 26123896 port (patch v1.1)

## Identity and boundaries

- Current clean Steam PE SHA-256: `1cc03e74444d956acdde25852209b85f9166d068a2468fafb2c002746ccaf1df`.
- Five-literal localized input SHA-256: `a248805bb809a08d3ddeb94af343409f1f142bfbf7accaa84cf37511fd26d208`.
- Previous profile: Steam build `26099941`; current profile: `26123896`.
- The REA native target was opened read-only, matching the current clean hash. Source-byte comparisons, PE section/import/exception metadata and Capstone decoding then verified the individual native hooks. No game process was launched.
- `debug_menu.build_menu` selects its profile from the verified localized input digest. The context is scoped to that build and restored afterward. Locale text and native address infrastructure remain separate.

## Why a single displacement is incorrect

The native UTF-8 draw function is reorganized from `0xb05c0` to `0xb0320` (`-0x2a0`), confirmed by its direct current field-reader call and nonempty draw-boundary replay. Native field reader hooks move by `+0x2f0`; collection hooks by `+0x590`; pause controls by `+0x630`; input/gameplay/Win32 key functions by `+0x640`; platform cursor/WndProc hooks by `+0x1450`; pointer dispatch/XInput by `+0x14e0`. Early mutable globals move by `+0x2000`, later globals by `+0x2040`. Read-only tables do not all share one shift: the test window virtual table moves from `0x433850` to `0x435160` and is identified by its native common-message translator entry at `0x435168 -> 0x1402dede0`.

The writable reader reservation moves from `.data` zero-fill tail `0xa68980` to `0xa6a9c0`; menu state moves from `0xa68e80` to `0xa6aec0`; the next section starts at `0xa6b000`. Only newly declared zero-fill bytes are reserved. Code stays in non-writable `.locui` RX; strings stay in read-only/non-executable `.locmenu`. No imports or RWX sections are added.

`native_profile.rva` has an explicit audited address set and rejects unmapped addresses. It is not an arbitrary executable relocator. `guard` re-encodes the original RIP target displacement for the selected profile and still requires exact final source bytes before writing. Capstone 5 reports `disp_size=2` on `66 0f 6e` RIP MOVD even though its actual displacement encoding remains four bytes; that instruction is handled explicitly.

## Guard coverage

- Debug unlock branch `7504`, native hotkey compare `83fa7e`, direct-mode conditional branch and 15-byte INT3 bridge cave.
- All translated native debug labels must be found; all native entity-name pointer slots must retain DIR64 relocation entries.
- Menu keyboard mode gate; engine wheel callback; raw wheel callback; native cursor predicate; inner pointer dispatch capture gate; queued pointer polling write; registered WndProc first-click gate; focus-release displaced load; OS-repeat image-base LEA; gameplay capture write; reader action mask gate; debug-menu frame-rate load.
- Reader native axis setter and consumer, controller-connected indexed global, field render subtraction/render flag, collection render subtraction, field/collection open and close entry points.
- Pause status X/Y instruction immediates, allowing only the two authored coordinate changes.
- New section header space, absent overlay/signature, executable image base, non-overlap/empty code reservation, writable zero-fill state bounds, unchanged existing imports.

## Explicit native address profile

These are canonical old RVA -> current RVA entries. Unchanged entry points used by the native builder remain explicitly allowlisted in `native_profile.py`. Test-only address spans in `tests/test_native_profile_v11.py` describe the audited function/array coordinate spaces needed to reuse the original behavioral assertions; unknown entries fail instead of silently falling back.

| 26099941 RVA | 26123896 RVA | Delta |
|---|---|---|
| `0xb05c0` | `0xb0320` | `-2a0` |
| `0x111800` | `0x111af0` | `+2f0` |
| `0x1118e0` | `0x111bd0` | `+2f0` |
| `0x111950` | `0x111c40` | `+2f0` |
| `0x11a7b0` | `0x11aaa0` | `+2f0` |
| `0x11af80` | `0x11b270` | `+2f0` |
| `0x11b450` | `0x11b740` | `+2f0` |
| `0x11b4f7` | `0x11b7e7` | `+2f0` |
| `0x11b536` | `0x11b826` | `+2f0` |
| `0x121e50` | `0x1223e0` | `+590` |
| `0x122a10` | `0x122fa0` | `+590` |
| `0x1232fc` | `0x12388c` | `+590` |
| `0x123379` | `0x123909` | `+590` |
| `0x123383` | `0x123913` | `+590` |
| `0x1233bf` | `0x12394f` | `+590` |
| `0x126da7` | `0x1273d7` | `+630` |
| `0x126dac` | `0x1273dc` | `+630` |
| `0x1557a5` | `0x155de5` | `+640` |
| `0x15587b` | `0x155ebb` | `+640` |
| `0x155882` | `0x155ec2` | `+640` |
| `0x1a7c50` | `0x1a8290` | `+640` |
| `0x1a7c54` | `0x1a8294` | `+640` |
| `0x1a7c5b` | `0x1a829b` | `+640` |
| `0x1a7c61` | `0x1a82a1` | `+640` |
| `0x1a7d4b` | `0x1a838b` | `+640` |
| `0x1a7d50` | `0x1a8390` | `+640` |
| `0x1a7d57` | `0x1a8397` | `+640` |
| `0x1a7d81` | `0x1a83c1` | `+640` |
| `0x1a7d90` | `0x1a83d0` | `+640` |
| `0x1a7d9b` | `0x1a83db` | `+640` |
| `0x2dd940` | `0x2ddf80` | `+640` |
| `0x2de833` | `0x2dee73` | `+640` |
| `0x2de83a` | `0x2dee7a` | `+640` |
| `0x2deb38` | `0x2df178` | `+640` |
| `0x2f3236` | `0x2f4686` | `+1450` |
| `0x2f3241` | `0x2f4691` | `+1450` |
| `0x2f3250` | `0x2f46a0` | `+1450` |
| `0x2f34d0` | `0x2f4920` | `+1450` |
| `0x2f39cc` | `0x2f4e1c` | `+1450` |
| `0x2f39d2` | `0x2f4e22` | `+1450` |
| `0x2f39e3` | `0x2f4e33` | `+1450` |
| `0x2f3a3e` | `0x2f4e8e` | `+1450` |
| `0x2f3a45` | `0x2f4e95` | `+1450` |
| `0x2f537c` | `0x2f685c` | `+14e0` |
| `0x2f5386` | `0x2f6866` | `+14e0` |
| `0x2f5439` | `0x2f6919` | `+14e0` |
| `0x31ad26` | `0x31c206` | `+14e0` |
| `0x37d6f0` | `0x37e6f0` | `+1000` |
| `0x37d748` | `0x37e748` | `+1000` |
| `0x37d758` | `0x37e758` | `+1000` |
| `0x37d760` | `0x37e760` | `+1000` |
| `0x37d7b0` | `0x37e7b0` | `+1000` |
| `0x37d818` | `0x37e818` | `+1000` |
| `0x3bebf0` | `0x3bfbf0` | `+1000` |
| `0x3c08c0` | `0x3c18c0` | `+1000` |
| `0x3c09d0` | `0x3c19d0` | `+1000` |
| `0x3c0e30` | `0x3c1e30` | `+1000` |
| `0x49f1a5` | `0x4a11a5` | `+2000` |
| `0x4a2f1d` | `0x4a4f1d` | `+2000` |
| `0x4a4a58` | `0x4a6a58` | `+2000` |
| `0x4c2158` | `0x4c4198` | `+2040` |
| `0x4c21ff` | `0x4c423f` | `+2040` |
| `0x4c2200` | `0x4c4240` | `+2040` |
| `0x4c2228` | `0x4c4268` | `+2040` |
| `0x4c2248` | `0x4c4288` | `+2040` |
| `0xa121a0` | `0xa141e0` | `+2040` |
| `0xa25e28` | `0xa27e68` | `+2040` |
| `0xa2ca78` | `0xa2eab8` | `+2040` |
| `0xa30d20` | `0xa32d60` | `+2040` |
| `0xa312b0` | `0xa332f0` | `+2040` |
| `0xa314f0` | `0xa33530` | `+2040` |
| `0xa344f4` | `0xa36534` | `+2040` |
| `0xa34522` | `0xa36562` | `+2040` |
| `0xa68980` | `0xa6a9c0` | `+2040` |
| `0xa68990` | `0xa6a9d0` | `+2040` |
| `0xa68e80` | `0xa6aec0` | `+2040` |
| `0xa69000` | `0xa6b000` | `+2000` |

## Offline verification

Command:

```powershell
python -m unittest discover -s tests -p test_native_profile_v11.py -v
```

The default fixture is the actual generated `build/full-zh-CN/Dementium II.exe`, not the temporary native-only build. `DEMENTIUM_V11_TEST_EXE` may explicitly select another generated current-build fixture.

Coverage includes:

- Native keyboard mode gates, menu ownership, long-reader arrow ownership, F1 rising-edge debounce, wheel routing and original gameplay callback.
- Focus loss releases native held-key latches and F1 previous-state; OS auto-repeat does not create a new fresh key event.
- Cursor open/center/clip, focus loss/refocus, close/capture restore, and image-base relocation.
- Native XInput packet normalization and axis-three setter; deadzone, NaN/infinity, pad/axis isolation, hold repeat, direction reversal, clamping, last-line reachability, menu/focus/disconnect gates, short documents, close/reset and unchanged axis fields.
- Real inner pointer dispatch -> native queue -> native ImGui hover/click/hold/release and wheel, including relocated image.
- Complete registered WndProc -> native queue -> actual native NewFrame -> actual Checkbox -> End/EndFrame; one-second hold and two complete click cycles, normal and relocated image bases.
- Real native document setup/measurement/UTF-8 render/glyph-submit boundaries using the actual generated archive: all 12 postcards in both field and collection paths, long and illustrated letters, short collection letters 092/093, trailing-padding extent, internal blank preservation, and adjacent level-name sentinel integrity.
- Pause status native immediate coordinates against the actual localized label and status-glyph alpha/ink bounds.
- Existing IAT slot identities for all six Win32 cursor APIs.

The font-metadata lookup, glyph submission, Win32 boundary and CRT allocation/memory/math callbacks are deterministic replay doubles. The branch, input dispatch, row measurement, UTF-8 renderer, ImGui frame and widget instructions execute from the supplied PE. This is offline CPU/layout evidence, not in-game visual or controller-device acceptance.

## Legacy fixture isolation

`tests/native_replay.require_native_fixture` recognizes only `.data RVA 0x49f000` as profile 26099941 and `0x4a1000` as profile 26123896; other layouts are unknown. Historical tests retain historical coordinates and skip with a named missing/mismatched-build reason when their legacy fixture is absent. New tests explicitly request profile 26123896 and reuse the original assertions through their versioned fixture adapter. Legacy postcard/collection/short-letter/pause suites also check fixture identity before legacy native helpers execute. A skipped historical suite is not counted as current-build verification.

The initial unadapted whole-suite run was stopped while using legacy collection coordinates; that interrupted run is not evidence of success. Use the completed current-profile suite and final repository verification logs instead.

### Completed current-profile run

`build/v11-native-tests-final.log`: `Ran 38 tests in 108.368s`, `OK`, exit status `0`. The nonempty renderer-boundary assertion reports `FIELD_CARD glyphs=41 flag_at_renderer=[1] sentinel_preserved=True`.

`python -m unittest test_packaging -v`: `Ran 3 tests in 0.253s`, `OK`, exit status `0`; the portable bundle includes `native_profile.py` and imports with Capstone, pefile and Keystone actively blocked. Those engines remain build/replay-time lazy dependencies, not portable sparse-install requirements.
