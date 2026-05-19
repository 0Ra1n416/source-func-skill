# level1-source-func-skill

用于对二进制文件执行输入解析函数识别（调用 `vulfunc_rank.py`），并输出可直接用于后续分析的 JSON 文件。

## 改写为独立Skill

**注意**，如果有需要，该部分也可以当作单独的Skill，请按如下步骤操作：

1. 创建一个新skill文件夹，命名`level1-source-func-skill`
2. 将`./sub-skills/level1-source-func.md`中的内容复制到`level1-source-func-skill/SKILL.md`
3. 将`./scripts`复制到`level1-source-func-skill/`下，即`level1-source-func-skill/scripts`

经过上述操作，该部分可以成为单独的Skill，请查看手册剩余内容了解其功能与使用。

## 功能概览

- 识别输入解析函数候选（结构/语义特征）
- 可选合并字符串常量评分（`--merge_string_scores`）
- 可选将外部调用函数强制加入候选集（默认开启）
- 自动输出识别结果与更新后的配置文件

## 目录结构

- Skill 入口说明：`SKILL.md`
- 运行入口脚本：`scripts/run_input_parsing.py`
- 主分析脚本：`scripts/vulfunc_ranker/vulfunc_rank.py`

## 配置说明

1. 将整个`level1-source-func-skill`文件夹放入`.claude/skills/`。
2. 配置Python环境
    - 可以配置环境变量`INPUT_PARSING_FUNC_PYTHON`指定Python
    - 可以在`./scripts/vulfunc_ranker`下创建`.venv`虚拟环境（注意：要想被自动检测，请设置venv名称为`.venv`）
    - 不配置则使用全局`python`，优先级详见[Python 解释器选择顺序](#python-解释器选择顺序)
3. 安装依赖，使用`pip install -r requirements.txt`，其在`./scripts/vulfunc_ranker/requirement.txt`
4. LLM相关配置（可选）
    - 只有字符串常量评分部分需要
    - 可以配置`ZERO_DAY_LLM_BASE_URL`、`ZERO_DAY_LLM_API_KEY`、`ZERO_DAY_LLM_MODEL`环境变量，指定URL、Key和模型。如果需要自定义参数，可以配置环境变量`ZERO_DAY_LLM_TEMPERATURE`、`ZERO_DAY_LLM_MAX_TOKENS`、`ZERO_DAY_LLM_TIMEOUT_SECONDS`。
    - 可以在`./scripts/vulfunc_ranker/scripts`下创建一个`LLM_config.json`文件，其中可以指定`base_url`、`api_key`、`model`、`timeout`参数，该配置优先级高于环境变量。

## 在 Claude Code 中调用

你可以通过自然语言，让Claude Code给你分析某二进制中的输入解析函数，可以显示说明你需要的可选功能，Claude Code会自动带上参数执行。具体参数可参照[参数说明](#参数说明)章节。

例如：

```text
`解析二进制文件./samples/a.out的输入解析函数，输出目录为./outputs，并考虑字符串常量评分`
```

这相当于传入 `input_bin`、`--output_base_dir ./outputs` 和 `--merge_string_scores`

当然，你也可以直接使用该 Skill：

```text
/level1-source-func-skill <binary_path>
```

例如：

```text
/level1-source-func-skill C:\Users\user\Desktop\a.exe --merge_string_scores
```

## 直接运行方式

在本 Skill 根目录执行：

```bash
python ./scripts/run_input_parsing.py <input_bin> [optional_flags]
```

示例：

```bash
python ./scripts/run_input_parsing.py ./samples/a.out
python ./scripts/run_input_parsing.py ./samples/a.out --merge_string_scores
python ./scripts/run_input_parsing.py ./samples/fw.bin --output_base_dir ./outputs
```

## 参数说明

### 必填参数

- `input_bin`：待分析二进制路径

### 可选参数

- `--threshold <float>`：识别阈值（默认 `6.0`）
- `--original_config_path <path>`：原始配置文件路径
- `--output_base_dir <path>`：输出根目录
- `--not_force_add_extern_calls`：不将外部调用函数加入候选（默认是加入）
- `--merge_string_scores`：合并字符串/常量评分到最终候选

## Python 解释器选择顺序

`run_input_parsing.py` 会按以下顺序选择 Python：

1. 环境变量 `INPUT_PARSING_FUNC_PYTHON`
2. `./scripts/vulfunc_ranker/.venv/Scripts/python.exe`（Windows）或 `./scripts/vulfunc_ranker/.venv/bin/python`（Unix）
3. 系统 `python`

## 输出说明

设 `output_name = <input_bin 文件名去后缀>`，默认输出到仓库根目录下：

- `<output_name>/recognize_output_<output_name>.json`
- `<output_name>/config_<output_name>.json`
- `<output_name>/input_funcs_by_string_<output_name>.json`（仅 `--merge_string_scores` 开启时）
- `<output_name>/string_scores_<output_name>.json`（仅 `--merge_string_scores` 开启时，字符串明细）

脚本末尾会打印 `Output Files:`，以该处显示的实际路径为准。

## 常见问题

- **Error: missing input_bin**
  - 未传入二进制路径，请补充 `input_bin`。

- **路径冲突报错（输入文件在输出根目录）**
  - 避免把输入二进制直接放在输出根目录，或通过 `--output_base_dir` 指定其他目录。

- **未生成字符串相关 JSON**
  - 仅在传入 `--merge_string_scores` 时生成 `input_funcs_by_string_*` 与 `string_scores_*`。
