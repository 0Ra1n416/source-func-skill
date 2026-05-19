import argparse
import os

parser = argparse.ArgumentParser()
parser.add_argument("input_bin", help="输入二进制文件路径")

args = parser.parse_args()

# 使用相对于当前文件的路径：当前文件在 .claude/skills/source-func-skill/scripts/vulfunc_ranker/，输出 在 根目录
current_file_dir = os.path.dirname(os.path.abspath(__file__))
# 从 ./.claude/skills/source-func-skill/scripts/vulfunc_ranker/ 回到 ./，保存到根目录下
output_base_dir = os.path.abspath(os.path.join(current_file_dir, "..", "..", "..", "..", ".."))

output_name = os.path.splitext(os.path.basename(args.input_bin))[0]

flagString = "[First Run]"
if not os.path.exists(os.path.join(output_base_dir, output_name)):
    if os.path.exists(os.path.join(output_base_dir, output_name, "Source_Level1_TypeC.json")):
        flagString = "[Level1 Found]"
    # TODO: 继续检测Level2以上文件是否存在，来区分Level1和Level2以上
    if 1:
        pass

print(flagString)