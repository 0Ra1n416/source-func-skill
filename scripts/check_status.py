import argparse
import os
import json

parser = argparse.ArgumentParser()
parser.add_argument("input_bin", help="输入二进制文件路径")

args = parser.parse_args()

# 使用相对于当前文件的路径：当前文件在 .claude/skills/source-func-skill/scripts/vulfunc_ranker/，输出 在 根目录
current_file_dir = os.path.dirname(os.path.abspath(__file__))
# 从 ./.claude/skills/source-func-skill/scripts/vulfunc_ranker/ 回到 ./，保存到根目录下
output_base_dir = os.path.abspath(os.path.join(current_file_dir, "..", "..", "..", "..", ".."))

output_name = os.path.splitext(os.path.basename(args.input_bin))[0]

flagString = "[First Run]"
if os.path.exists(os.path.join(output_base_dir, output_name)):
    if os.path.exists(os.path.join(output_base_dir, output_name, "source.json")):
        with open(os.path.join(output_base_dir, output_name, "source.json"), "r") as f:
            data = json.load(f)
            if "target" in data and data["target"] == output_name:
                for source in data.get("sources", []):
                    if source.get("layer", -1) == 1:
                        flagString = "[Layer1 Found]"
                        break        

# [First Run] - 没有找到输出文件夹，第一次运行 - 完整运行
# [Layer1 Found] - 找到了输出文件夹，并且在source.json中找到了至少一个第一层source函数，说明之前已经运行过一次，并且完成了第一层source函数的识别和输出 - 第一层不用运行
print(flagString)