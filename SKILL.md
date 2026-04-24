---
name: input-parsing-func-skill
description: 用这个 Skill 对二进制运行 vulfunc_rank.py，并输出输入解析函数与配置相关 JSON 文件位置。
---

# Input Parsing Func Skill

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

在本 Skill 目录执行（保证相对路径可用）：

`python ./scripts/run_input_parsing.py <input_bin> [可选参数]`

## 输出

令 `output_name = input_bin` 去后缀文件名（无后缀则不去），输出目录为当前工作根目录下的 `{output_name}/`。

需要向用户回报：
- 预期文件：
  - `{output_name}/recognize_output_{output_name}.json`
  - `{output_name}/config_{output_name}.json`
  - `{output_name}/input_funcs_by_string_{output_name}.json`（仅开启 `--merge_string_scores` 时）
- 脚本实际打印的 `Output Files:` 列表中的真实路径

如果缺少输入二进制路径，返回简短错误并提示用户提供 `input_bin`。

## 示例

- `/input-parsing-func-skill ./samples/a.out`
- `/input-parsing-func-skill ./samples/fw.bin --output_base_dir ./outputs`
- `/input-parsing-func-skill ./samples/a.out --merge_string_scores`