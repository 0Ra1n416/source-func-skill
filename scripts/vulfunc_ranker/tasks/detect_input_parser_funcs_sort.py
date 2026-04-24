# -*- coding: utf-8 -*-
# 扫描目录下所有单函数 .c 文件，寻找输入解析函数
import os
import re
import time
import sys



# ===== 特征定义 =====
INPUT_APIS = ["recv", "read", "fread", "recvfrom", "accept"]
DANGER_FUNCS = ["memcpy", "strcpy", "sprintf", "vsprintf", "snprintf", "strcat", "memmove","malloc","system"]
PROTO_KEYWORDS = ["GET ", "POST ", "password", "HTTP/1.1", "login"]

# 在输入API之后若20行内出现以下解析行为关键字，则视为“输入解析”逻辑
PARSER_KEYWORDS = [
    "strncmp", "strcmp", "strstr", "memcmp", "sscanf", "atoi", "json", "xml", "token",
    "split", "case", "switch", "cmd", "parse"
]

WEIGHTS = {
    "input_api": 5,
    "danger_copy": 6,
    "switch": 4,
    "if_chain": 3,
    "proto_string": 4,
    "no_boundary": 5
}

# ===== 文件输出 =====
def write_header(OUTPUT_TXT, THRESHOLD):
    os.makedirs(os.path.dirname(OUTPUT_TXT), exist_ok=True)
    with open(OUTPUT_TXT, "w", encoding="utf-8") as f:
        f.write("Input Parser Analysis Report (split C files)\n")
        f.write(f"Generated: {time.ctime()}\n")
        f.write(f"Threshold: {THRESHOLD}\n")
        f.write("="*80 + "\n\n")

def append_line(text, OUTPUT_TXT):
    with open(OUTPUT_TXT, "a", encoding="utf-8") as f:
        f.write(text + "\n")

# ===== 工具函数：检测输入API附近是否有解析行为 =====
def has_parser_near_input(func_text, input_api):
    lines = func_text.splitlines()
    for i, line in enumerate(lines):
        if input_api in line:
            # 在 recv/read 后20行内找解析特征
            for j in range(i + 1, min(i + 21, len(lines))):
                if any(pkw in lines[j] for pkw in PARSER_KEYWORDS):
                    return True
    return False

# ===== 特征检测逻辑 =====
def detect_features(func_text):
    matched, score = [], 0

    # ==== 输入 API 检测====
    for api in INPUT_APIS:
        if re.search(r'\b' + re.escape(api) + r'\b', func_text):
            if has_parser_near_input(func_text, api):
                matched.append(f"input_api_with_parse:{api}")
                score += WEIGHTS["input_api"] + 2  # 解析型输入加权
            else:
                matched.append(f"input_api_no_parse:{api}")
                score += 1  # 单纯读取输入仅略加分

    # ==== 危险函数 ====
    for df in DANGER_FUNCS:
        if re.search(r'\b' + re.escape(df) + r'\b', func_text):
            matched.append(f"danger_copy:{df}")
            score += WEIGHTS["danger_copy"]

    # ==== if/switch ====
    if_count = func_text.count("if (")
    if if_count > 10:
        matched.append(f"if_chain:{if_count}")
        score += WEIGHTS["if_chain"]

    if "switch" in func_text:
        matched.append("switch")
        score += WEIGHTS["switch"]

    # ==== 协议关键字 ====
    for kw in PROTO_KEYWORDS:
        if kw in func_text:
            matched.append(f"proto:{kw.strip()}")
            score += WEIGHTS["proto_string"]

    # ==== 无边界 memcpy ====
    if re.search(r'\bmemcpy\b', func_text) and not re.search(r'if\s*\(.*(len|size|count|n).*(<=|<|>=|>)', func_text, re.I):
        matched.append("no_boundary_check:memcpy")
        score += WEIGHTS["no_boundary"]

    return score, matched

# ===== 主逻辑 =====
def execute(decompiled_results, OUTPUT_TXT, THRESHOLD):
    write_header(OUTPUT_TXT, THRESHOLD)
    total_files = 0
    candidates = []  # 收集满足阈值的条目 (score, func_name, matched, fname)

    for file in decompiled_results:
            
            if isinstance(file, dict):
                total_files += 1
                func_text = file["decompiled"]
                score, matched = detect_features(func_text)
                func_name = file["name"]

                if score >= THRESHOLD:
                    candidates.append((score, func_name, matched))
                    print(f"[+] {func_name} => score={score} queued.")
                else:
                    print(f"[-] {func_name} => score={score}")

    # 按 score 从大到小排序（相同分数时按函数名升序）
    candidates.sort(key=lambda x: (-x[0], x[1]))

    # 将排序后的结果写入输出文件
    hits = 0
    for idx, (score, func_name, matched) in enumerate(candidates, start=1):
        hits += 1
        line = f"{idx}. {func_name} | Score: {score} | Features: {', '.join(matched)}"
        
        append_line(line, OUTPUT_TXT)
        print(f"[W] Saved: {func_name} => score={score}")

    append_line("="*80, OUTPUT_TXT)
    append_line(f"Total files: {total_files}, Candidates: {hits}", OUTPUT_TXT)
    append_line(f"Completed: {time.ctime()}", OUTPUT_TXT)
    print(f"\n[✓] Completed. {hits}/{total_files} candidates saved to {OUTPUT_TXT}")


""" # ...existing code...
if __name__ == "__main__":
    # 如果输入的参数小于4个，则提示用法并退出
    if len(sys.argv) != 3:
        print("Usage: python detect_input_parser_funcs_sort.py <OUTPUT_TXT> <THRESHOLD>")
        sys.exit(1)
    
    OUTPUT_TXT = sys.argv[1]
    THRESHOLD = int(sys.argv[2])
    execute(OUTPUT_TXT, THRESHOLD) """
