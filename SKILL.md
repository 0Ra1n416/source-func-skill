---
name: source-func-skill
description: 用这个 Skill 来寻找 Source 函数，输出相关 JSON 文件位置。
---

# Source Func Skill

调用各个位于 `./sub-skills` 目录下的子技能（如 `level1-source-func-skill`）来寻找 Source 函数，并输出相关 JSON 文件位置。

## 输入

将 `$ARGUMENTS` 视为命令行参数。

必填：
- `input_bin`

## 执行

以下命令均在本 Skill 目录执行（保证相对路径可用）：

1. 检测目前状态，``python ./scripts/check_status.py <input_bin>``，查看是否已经存在相关输出文件。其返回值会打印在标准输出中，格式：`[<flag>]`。
  - `[First Run]`：未检测到相关输出文件，说明这是第一次运行该 Skill。
  - `[Layer1 Found]`：检测到Layer1的输出文件，说明之前已经运行过Layer1的分析。

2. 如果检测结果是 `[First Run]`，则需要运行 Layer1 Source Func Skill
  - 请你读取[Layer1 Source Func Skill](./sub-skills/layer1-source-func.md)中 Layer1 Source Func Skill 的说明，了解它的输入、执行方式和输出。
  - 请以默认选项运行 Layer1 Source Func Skill（即仅传 `input_bin`，不传任何可选参数）。

3. 如果检测结果是 `[Layer1 Found]`，则直接告知用户 Layer1 的输出文件位置，无需重复运行 Layer1 分析。

4. 无论检测结果如何，都需要运行 TODO SKILL（目前还没完成，请你先忽略，跳过这一条）

## 输出

令 `output_name = input_bin` 去后缀文件名（无后缀则不去），输出目录为当前工作根目录下的 `{output_name}/`。

其中会输出一些相关的 JSON 文件，例如：
- `{output_name}/source.json`：包含所有Source函数的列表及其相关信息。

注意：`{output_name}/origin/` 目录下会保留一些原始文件，请你忽略它们。

如果缺少输入二进制路径，返回简短错误并提示用户提供 `input_bin`。

## 示例

- `/source-func-skill ./samples/a.bin`