# Reader flag / next New Game section regression (2026-10-22)

## Verified

The full reader patch copied a displaced native renderer-flag instruction but
reassembled its RIP target as RVA `0x4c2200`, one byte after its real target
`0x4c21ff`. The two locations have unrelated roles:

- `0x4c21ff`: native text-rendering gate, set by original field reader instruction
  `0x11b4fa`, cleared by native end-of-draw `0x11b52f`.
- `0x4c2200`: native debug start-section override string. It is **not** a render
  flag or unused padding. Overwriting byte zero with `01` leaves a nonempty
  section override across the close-entry reader reset.

Native `FUN_1400acb30` (`LoadStartLevel`) chooses the configured `StartSection`
then tests `0x4c2200` at `0xacd24`. A nonempty override is copied with native
`strncpy(...,7)` at `0xacd3d`, consumed at `0xacd4a`, and passed to native
`FUN_14015ccf0` (`LoadSection`). Thus one field reader draw changes the next
New Game's section from `p0_000` to the single byte `01`. Returning to a menu
does not repair this overwritten engine string; the native loader consumes it.
The copied player runtime logs end with `LoadStartLevel start` and a
`LoadSection` request for that same control-character string.

The narrow fix is in `tools/document_reader.py`: derive the displaced flag
RIP target from the guarded original instruction, rather than duplicate an
address constant. This also repairs the field text submission gate. No new
lifecycle/null-check patch, section-name workaround, forced world reset, or
save modification is introduced.

## Reproduction and coverage

`tests/test_restart_lifecycle.py` uses the actual supplied PE and the actual
`CONFIG/VILLAGE.INI` chapter starts. The replay performs:

1. Actual patched field reader draw (`0x11b4f7`).
2. Original end-of-draw flag clear (`0x11b52f`).
3. Actual patched close-entry state reset and displaced prologue, stopping at
   `0x11af86` before the external object teardown body.
4. Original native configured-section selection and override consumption
   (`0xaccf9..0xacd54`), with an external `strncpy` boundary that copies real
   emulated memory bytes.
5. Original normal/override call site, stopping exactly at `LoadSection`
   entry (`0x15ccf0`) and asserting its actual native RCX section argument.

Baseline f4c2bfb19253c53357eb57b206ff2f5171c699f9f8638083001837ccd0737fb1:
4 tests / 8 failures. All five chapter starts become byte `01`; a legitimate
`v0_000` override becomes `01 30 5f 30 30 30`. The write trace identifies the
reader store at `0xaf2264`, native renderer clear, and native override consume.
With only the flag displacement corrected: all 4 tests pass, including three
consecutive reader/restart cycles and preserving legitimate debug overrides.

```powershell
$env:DEMENTIUM_UI_TEST_EXE = 'absolute-path-to-test-executable'
python -X utf8 -m unittest discover -s tests -p test_restart_lifecycle.py -v
```

Optional `DEMENTIUM_RESTART_TEST_EXE` and `DEMENTIUM_RESTART_TEST_ROM` fixture
selectors are also accepted. All tests are offline. This proves the exact
invalid loader argument seen in the logs; it does not execute full graphics,
resource I/O, the complete teardown body, or a Windows crash reporter. A new
in-game return-to-menu / New Game run remains the final in-game acceptance step.
Evidence and red/green logs: `build/restart-lifecycle-fix/`.
