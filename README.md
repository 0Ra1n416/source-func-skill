# source-func-skill

反编译二进制文件，分析其中的Source函数，并输出可直接用于后续分析的 JSON 文件。

## 功能概览

识别二进制中的Source函数，采用多级架构，使用了自学习机制。

相关子Skills:

- **layer1-source-func-skill:** 调用脚本找出三类第一层Source函数，并创建包含所有第一层source函数的初始json文件。其也可作为skill单独运行，详见[该部分的说明](./L1SourceFuncSkill_README.md)。
  - 预定义的通用Source函数
  - 提取的整个二进制中的所有外部函数
  - 我们的输入解析函数价值评估算法判断出的输入解析函数

## 目录结构

- Skill 入口说明：`SKILL.md`
- 子Skills目录：`./sub-skills/`
- 脚本目录：`./scripts/`

## 配置说明

1. 将整个`source-func-skill`文件夹放入`.claude/skills/`。
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

你可以通过自然语言，让Claude Code给你分析某二进制中的Source函数。

例如：

```bash
解析二进制文件./samples/a.out的Source函数。
```

当然，你也可以直接使用该 Skill：

```bash
/source-func-skill <binary_path>
```

例如：

```bash
/source-func-skill C:\Users\user\Desktop\a.exe
```

## 参数说明

### 必填参数

- `input_bin`：待分析二进制路径

## Python 解释器选择顺序

`run_input_parsing.py` 会按以下顺序选择 Python：

1. 环境变量 `INPUT_PARSING_FUNC_PYTHON`
2. `./scripts/vulfunc_ranker/.venv/Scripts/python.exe`（Windows）或 `./scripts/vulfunc_ranker/.venv/bin/python`（Unix）
3. 系统 `python`

## 输出说明

设 `output_name = <input_bin 文件名去后缀>`，默认输出到仓库根目录下：

- 该二进制的输出文件夹：`./<output_name>/`
- Source函数JSON文件：`./<output_name>/source.json`

## 常见问题

- **Error: missing input_bin**
  - 未传入二进制路径，请补充 `input_bin`。

- **路径冲突报错（输入文件在输出根目录）**
  - 避免把输入二进制直接放在输出根目录，或通过 `--output_base_dir` 指定其他目录。

## 直接运行`输入解析函数价值评估算法`

输入解析函数价值评估算法是一套可独立运行的Python程序。

你可以在本 Skill 根目录执行：

```bash
python ./scripts/run_input_parsing.py <input_bin> [optional_flags]
```

其相关输出可以在`./<output_name>/origin`中查看。

示例：

```bash
python ./scripts/run_input_parsing.py ./samples/a.out
python ./scripts/run_input_parsing.py ./samples/a.out --merge_string_scores
python ./scripts/run_input_parsing.py ./samples/fw.bin --output_base_dir ./outputs
```
