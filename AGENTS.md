# NuSrcAgent contributor instructions

- Use `run_agent_wrap.py` as the sole public analysis entry point.
- Read `.agents/skills/nusrcagent/SKILL.md` before analysis execution.
- Preserve scientific definitions, catalog membership, weights, PDFs, fit bounds
  and recorded trial strategies. Ask only about unresolved material ambiguity.
- Execute an analysis only after its persistent task reaches `READY`.
- Keep source data in `data_input/`, numerical outputs in `data_output/` and
  figures in `figures/`; never overwrite frozen inputs during an analysis.
- The production DR2 background package is frozen v3. Verify its mapped
  numerical hashes; do not rebuild, retune or silently fall back to another version.
- Keep PDF construction, owner tests, specific-source comparisons, transcripts
  and local configuration out of this checkout.
- Keep module imports, CLI examples, artifact paths and manifest references
  consistent when renaming files; do not leave compatibility entry points.
- Preserve substantive comments when removing generation markers.
- Inspect scientific and artifact reviews. Warning-bearing results remain
  preliminary; failed reviews must not be reported as valid results.
- Report the maximized likelihood statistic as `TS`. Analytic local p-values
  do not establish empirical significance or parameter coverage.
- Time-dependent analysis is planned but not implemented in this copy. Do not
  claim support or run time-dependent background trials.
- Review source changes and perform relevant isolated verification before
  publication. No release tag or public availability is implied by this copy.

## Progress update 与总耗时

- 执行本项目的任何任务时，从本次用户请求开始记录 wall-clock time；每条 progress update 都说明预计还需多久，并优先根据当前配置下已完成的同类计算外推。重复计算采用 `已完成计算耗时 / 已完成数量 × 剩余数量`；例如 100/1000 个 sources 用时 1 分钟，则该阶段预计还需 9 分钟，总计约 10 分钟。
- 区分当前阶段与整个请求的剩余时间，随新完成的计算更新估算；不得将不同 fit procedures、worker configurations 或已恢复的 checkpoints 混为本次测速样本。缺少可用样本时说明“暂无法可靠估算，等待首个计算完成”；continuous scrambling 没有目标 trial count 时说明“持续运行，未设结束时间”，不得编造 ETA 或自行添加停止条件。
- Wrapper 的 `NuSrcAgent progress:` stderr events 和 stdout JSON 的 `execution_timing` 提供实测时间与当前阶段 ETA；读取这些信息组织面向用户的 progress update，不直接粘贴内部 JSON。准备、绘图、verification 和 review 等阶段也遵守本规则；没有可量化进度时，根据已完成工作给出明确标注依据的粗略范围，确实无法估算则说明原因。
- 每次 final answer 在本次请求实际总耗时严格超过 60 秒时给出总耗时；不超过 60 秒时省略。包括失败或中断后的答复；分两阶段的 analysis 各按本轮实际处理时间记录，不计入等待用户回复的时间，不以最后一条 wrapper command 的耗时代替整个请求耗时。
