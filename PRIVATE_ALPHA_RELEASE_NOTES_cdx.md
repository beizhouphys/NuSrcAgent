# NuSrcAgent 0.2.0 Private Alpha 1

## Audience

Owner and explicitly invited collaborators only. This version is not a public scientific release.

## Repository

- GitHub: `https://github.com/beizhouphys/NuSrcAgent`
- Visibility: private
- Initial source commit: `774c2e7`

## Included

- Repository-local Codex Skill for Chinese, English, and mixed-language requests.
- Persistent AgentTask state, confirmation gate, planner, recovery policy, and completion gate.
- Deterministic single-source, catalog scan, and stacking execution paths.
- Run review, workbook and figure output support, and multilingual agent tests.
- Pinned Python 3.8/NumPy environment and GitHub Actions wrapper tests.

## Data asset

- File: `NuSrcAgent_data_v0.2.0_cdx.tar.gz`
- Size: approximately 46 MB compressed
- SHA-256: `cf6972ddc893d7ad0b15a02c844791b3d0957c53b258733b93373d705d02020a`

The data asset is not stored in Git history. It restores the 20 files listed in `data_manifest_private_alpha_cdx.json` and has passed clean-extraction hash verification.

## Verification

- 21 deterministic agent tests passed in a clean clone.
- 16-case language corpus validation passed.
- All 20 private data files passed SHA-256 verification after clean extraction.
- A real-backend TXS 0506+056 single-source task completed in the clean clone with expected review warnings preserved.

## Known limitations

Scientific limitations are documented in `project_audit_cdx.md` and `AGENT_EVALUATION_cdx.md`. A warning-bearing run must not be described as publication-ready. Legacy research scripts still contain historical absolute paths and are not part of the clean callable-agent path.
