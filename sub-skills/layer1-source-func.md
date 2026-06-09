---
name: layer1-source-func-skill
description: 用这个 Skill 对二进制运行 vulfunc_rank.py，并输出包含第一层的三类Source函数的JSON文件。
---

# Layer1 Source Func Skill

使用脚本 `./scripts/run_input_parsing.py` 分析输入二进制文件（由它转调 `./scripts/vulfunc_ranker/vulfunc_rank.py`）。

## Python 路径变量（可选）

可通过环境变量指定 Python 解释器：`INPUT_PARSING_FUNC_PYTHON`。
该变量由 `./scripts/run_input_parsing.py` 读取并优先使用。

Python 选择顺序（由入口脚本自动确定）：

1. `$INPUT_PARSING_FUNC_PYTHON`
2. `./scripts/vulfunc_ranker/.venv/Scripts/python.exe`(Windows) 或 `./scripts/vulfunc_ranker/.venv/bin/python`(Unix)
3. `python`

## 输入

将 `$ARGUMENTS` 视为命令行参数。

必填：

- `input_bin`

可选（仅在用户明确指定时传递）：

- `--original_config_path <path>`
- `--output_base_dir <path>`
- `--not_force_add_extern_calls`
- `--merge_string_scores`

默认策略：

1. 不传 `--threshold`（保持脚本默认阈值）
2. 两个路径参数若用户未明确提供则保持脚本默认
3. 默认保留“强制加入外部调用函数”（即不传 `--not_force_add_extern_calls`）
4. 默认不开启字符串/常量评分合并（即不传 `--merge_string_scores`）

当然，用户也可以用自然语言激活该Skill，并激活这些可选参数，例如：

- `解析二进制文件./samples/a.out的输入解析函数` -> 仅传 `input_bin`
- `解析二进制文件./samples/a.out的输入解析函数，输出目录为./outputs` -> 传 `input_bin` 和 `--output_base_dir ./outputs`
- `解析二进制文件./samples/a.out的输入解析函数，考虑字符串常量评分` -> 传 `input_bin` 和 `--merge_string_scores`
- `解析二进制文件./samples/a.out的输入解析函数，输出目录为./outputs，并考虑字符串常量评分` -> 传 `input_bin`、`--output_base_dir ./outputs` 和 `--merge_string_scores`

只要有相关的自然语言提示，用户就可以灵活地选择是否传递这些可选参数。

## 执行

在本 Skill 的父目录执行（即`SKILL.md`所在的路径下执行）（保证相对路径可用）：

`python ./scripts/run_input_parsing.py <input_bin> [可选参数]`

如果脚本输出包含 `[PENDING]` 标记，说明存在缓存未命中的外部函数，需要按以下步骤处理：

1. 读取 `[PENDING]` 行指示的 JSON 文件（如 `{output_name}/origin/pending_extern_judge.json`）
2. 使用 SubAgent 逐个判断其中的函数是否为 Source 函数：
   - Source 函数 = 能从外部接收用户/攻击者控制数据的函数（如 recv、fopen、getenv、websGetVar、system 等）
   - 非 Source 函数 = 纯数学/内存管理/字符串操作/流程控制等不引入外部数据的函数
   - **判定为 Source 时，必须给出 `reason` 理由**：
     - 标准库函数：引用所属标准库/API（如 `fopen` → "C标准库 stdio.h，从文件系统读取外部数据"）
     - 非标准库函数：给出强证据说明为何能接收外部控制数据（如 `cgi_param` → "CGI库函数，从HTTP请求中获取参数值"）
   - 判定为非 Source 时，不需要给出理由
3. SubAgent 判断完成后，调用以下 Python 代码将结果（含理由）写入缓存：
   ```python
   from vulfunc_ranker.tasks.filter_extern_by_llm import apply_subagent_results
   apply_subagent_results({
       "fopen": {"is_source": True, "reason": "C标准库stdio.h，从文件系统读取外部数据，可由用户/攻击者控制文件路径"},
       "strlen": {"is_source": False},
   })
   ```
4. 缓存更新后，重新运行 `python ./scripts/run_input_parsing.py <input_bin> [可选参数]` 获取完整结果

## 输出

令 `output_name = input_bin` 去后缀文件名（无后缀则不去），输出目录为当前工作根目录下的 `{output_name}/`。

需要向用户回报：

- 预期文件：
  - `{output_name}/source.json`
- 脚本实际打印的 `Output Files:` 列表中的真实路径

如果缺少输入二进制路径，返回简短错误并提示用户提供 `input_bin`。

## 示例

- `/input-parsing-func-skill ./samples/a.out`
- `/input-parsing-func-skill ./samples/fw.bin --output_base_dir ./outputs`
- `/input-parsing-func-skill ./samples/a.out --merge_string_scores`
