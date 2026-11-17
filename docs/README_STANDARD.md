# README Authoring Standard for AI and Humans

The README is the shortest reliable entry point for its audience, not a development diary or a copy of every technical document.

## 1. Establish facts before drafting

Inspect the actual repository, release artifacts, build entry points, dependency files and test evidence.
Identify whether this is a template, research project, playable patch or supported release.
Separate observed facts, untested behavior and planned work. State the target reader: player first for a released patch, developer first for a template/tool.
Use the requested language. Preserve locale-neutral architecture even when the README is written in Chinese.
Do not infer completion from a directory name, a previous chat, a translated-string count or a successful unit test.

## 2. Recommended order

1. **Identity and status:** what it is, target game/platform/locale, current release state, important limitations.
2. **Player quick start:** exact supported inputs, real download location, backup/preconditions and numbered installation/start steps.
3. **Coverage and compatibility:** what is included/excluded/untested, supported builds and runtime environments.
4. **Uninstall/upgrade:** concise tested path and link to recovery details.
5. **Build from source:** prerequisites, working directory, minimal verified commands and expected output.
6. **Contribute:** translation/data entry point, tests and issue-report fields.
7. **Technical navigation:** a small map to the owning documents rather than repeated instructions.
8. **Licensing and credits:** actual license split, source/input boundaries and upstream acknowledgements.

For a baseline, replace player download/install sections with adoption and reference-check instructions; do not invent a release.
Omit irrelevant sections. Keep crucial limitations near the affected quick-start step instead of burying them at the end.

## 3. Claims, commands and links

- Game support/completion claims map to [acceptance evidence](ACCEPTANCE.md). For template/tool claims, use the actual document checks, synthetic tests and tool commands; do not invent game G0-G4 evidence.
- Distinguish implemented, tested and planned functionality; avoid vague “fully supports” claims.
- Put each copyable command in a code block with shell/working directory/prerequisites stated.
- Execute included commands in a clean/disposable environment where practical; record the candidate, prerequisites, shell, working directory, command/input, stdout/stderr, exit status and expected output. Destructive/install/publish commands are demonstrated in disposable fixtures or documented as unexecuted, not run against live data merely to validate prose.
- A command not executed must be labeled untested/example, never presented as verified.
- Placeholders belong only in a clearly marked template; remove them from player-ready instructions.
- Use relative links for repository documents and actual URLs for releases/issues. Check exact filename case, fragment anchors, reference-style links and image targets, not just file existence. Verify external destinations when accessible; link resolution alone does not prove the page supports a claim.
- Match capitalization and filenames. Use `README.md` consistently.
- Publish build/status badges only if their real target exists and their meaning is accurate.
- Screenshots must come from the described candidate; label mockups and reference images.
- Avoid absolute developer-machine paths, secrets, transient logs and unsubstantiated quality slogans.

## 4. Keep it maintainable

Keep commands owned by the build tooling and detailed rules in their specialized documents.
The README may repeat a short critical limitation but should link to the complete source of truth.
Keep release history in a changelog/release notes, not a growing wall above the quick start.
Update affected instructions in the same change as behavior. Use concise headings, small tables and numbered procedures.
The owner's in-game punctuation rule does not apply to README explanatory prose. Quoted game translations and translation examples must still follow the game-text policy; label before/incorrect examples clearly.
Choose an explicit versioned download when behavior depends on it; distinguish source archives from installable patches and match the instructions to the shipped package. Link the known-issues/recovery page and request game version, patch version, locale, scene, reproduction, evidence and unpatched-baseline behavior in bug reports.

## 5. README acceptance checklist

- [ ] A new reader can identify what this is and whether it is usable now.
- [ ] Supported, untested and unsupported inputs are distinct.
- [ ] Quick-start commands/steps match current files and the tested package.
- [ ] Installation and recovery assumptions are explicit.
- [ ] Coverage language matches the inventory and verification level.
- [ ] Local links, exact path case, anchors and images resolve; external links point to intended destinations or are labeled unverified.
- [ ] Recorded command outcomes include exit status; examples and unexecuted side effects are clearly distinguished.
- [ ] Examples, placeholders, plans and screenshots are labeled accurately.
- [ ] Detailed content is linked, not inconsistently duplicated.
- [ ] Licenses/credits and issue-report guidance reflect actual contents.

Select a checker that actually exists in this project or record a manual link review. This documentation-only migration does not install the baseline `tools/check_docs.py` command. Check inline/reference links, images, exact path case and fragments against tracked files; distinguish external checks and rendered-page review from static checks.

## 6. Reusable AI prompt

```text
Write or revise this repository's README.md for its actual current state.
First inspect the repository instructions, build entry points, dependency files,
release artifacts and acceptance evidence. Follow docs/README_STANDARD.md.
Identify the reader and distinguish template/research/test-release/supported-release.
Keep verified facts, untested behavior and plans visibly separate.
Use the recommended reader-first order, omit irrelevant sections, and link to
the owning documents instead of copying their detailed rules.
Use only real commands, paths and URLs. Check exact path case, anchors and images.
Run relevant commands in disposable copies and record inputs, outputs and exit status;
label examples and untested steps. Do not invent releases, badges or game QA.
Use tool/document evidence for a template; use game acceptance evidence for a patch.
Keep ordinary README prose separate from the in-game punctuation policy; follow
that policy in quoted game translations and label incorrect/before examples.
Describe translation, review and runtime coverage separately with known scope.
Include tested installation, upgrade/recovery and developer entry points as applicable.
Preserve locale-neutral engineering and actual license/credit boundaries.
Check the README acceptance list, then report the changed sections, checks run,
literal results and remaining unknowns. Preserve unrelated existing work.
```
