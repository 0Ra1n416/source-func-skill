#!/usr/bin/env python3
"""
对外部库函数的识别：检查缓存获取已知结果，未命中则输出待判断文件供 SubAgent 处理。

流程：
1. 集中收集外部导入函数列表
2. 检查缓存：命中则直接使用结果（命中即当成Source函数加入JSON）
3. 缓存未命中 → 写入待判断文件（pending_extern_judge.json）
4. 由 Claude Code SubAgent 读取待判断文件并进行判断
5. SubAgent 将判断结果写入缓存 (extern_source_cache.json)
6. 重新运行分析流程，此时所有函数均已命中缓存
"""

import os
import json
from datetime import datetime


# 缓存文件名（存放于 caches_data/ 目录下，全局共享）
CACHE_FILENAME = "extern_source_cache.json"

# 待判断文件名（存放于 {output_name}/origin/ 目录下，每次分析独立）
PENDING_FILENAME = "pending_extern_judge.json"


class ExternSourceFilter:
    """
    外部函数Source过滤器。

    负责管理外部函数→Source判断的持久化缓存。
    缓存命中时直接返回结果（视为Source函数），
    缓存未命中时输出待判断列表，交由 SubAgent 判断。
    """

    def __init__(self, cache_dir: str = None):
        """
        :param cache_dir: 缓存目录路径，默认为 caches_data/
        """
        if cache_dir is None:
            cache_dir = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "..", "caches_data"
            )
        self.cache_path = os.path.join(cache_dir, CACHE_FILENAME)
        self.cache: dict[str, dict] = {}
        self._load_cache()

    # ── 缓存读写 ─────────────────────────────────────────────

    def _load_cache(self):
        """从持久化缓存文件加载已有的判断结果。"""
        if os.path.exists(self.cache_path):
            try:
                with open(self.cache_path, "r", encoding="utf-8") as f:
                    self.cache = json.load(f)
                print(f"[ExternSourceFilter] 已加载外部函数Source缓存: {len(self.cache)} 条记录")
            except Exception as e:
                print(f"[ExternSourceFilter] 警告: 加载缓存失败 ({e})，将使用空缓存")
                self.cache = {}
        else:
            print(f"[ExternSourceFilter] 缓存文件不存在，将在首次SubAgent判断后创建: {self.cache_path}")
            self.cache = {}

    def _save_cache(self):
        """将当前缓存写入持久化文件。"""
        os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
        with open(self.cache_path, "w", encoding="utf-8") as f:
            json.dump(self.cache, f, indent=4, ensure_ascii=False)

    # ── 核心过滤逻辑 ─────────────────────────────────────────

    def filter_source_funcs(self, extern_funcs: list[str]) -> tuple[list[str], list[str]]:
        """
        过滤外部函数列表。

        优先从缓存获取结果（命中缓存的Source函数直接返回），
        未命中缓存的函数返回供 SubAgent 判断。

        :param extern_funcs: 外部导入函数名称列表
        :return: (cached_source_funcs, uncached_funcs)
                 - cached_source_funcs: 缓存命中且判定为Source的函数列表
                 - uncached_funcs: 缓存未命中、需要SubAgent判断的函数列表
        """
        cached_source_funcs = []
        uncached_funcs = []

        for func in extern_funcs:
            if func in self.cache:
                if self.cache[func].get("is_source", False):
                    cached_source_funcs.append(func)
                # else: 缓存判定为非Source，直接跳过
            else:
                uncached_funcs.append(func)

        cache_hit_source = len(cached_source_funcs)
        cache_hit_non_source = len(extern_funcs) - cache_hit_source - len(uncached_funcs)

        print(f"[ExternSourceFilter] 外部函数Source判断统计:")
        print(f"  总计外部函数: {len(extern_funcs)} 个")
        print(f"  缓存命中 - 是Source (直接加入): {cache_hit_source} 个")
        print(f"  缓存命中 - 非Source (已排除):   {cache_hit_non_source} 个")
        print(f"  待SubAgent判断:                 {len(uncached_funcs)} 个")

        return cached_source_funcs, uncached_funcs


# ── 待判断文件读写（供 SubAgent 使用）────────────────────────

def write_pending_judge_file(uncached_funcs: list[str], output_dir: str) -> str:
    """
    将缓存未命中的函数写入待判断文件，供 SubAgent 读取并判断。

    :param uncached_funcs: 需要SubAgent判断的函数名列表
    :param output_dir: 输出目录（如 {output_name}/origin/）
    :return: 待判断文件的完整路径
    """
    os.makedirs(output_dir, exist_ok=True)
    pending_path = os.path.join(output_dir, PENDING_FILENAME)

    pending_data = {
        "description": (
            "以下是缓存未命中的外部导入函数列表。"
            "请 SubAgent 逐个判断每个函数是否为 Source 函数（能够从外部接收用户/攻击者控制的数据的函数）。"
            "判断标准：\n"
            "1. 如果判定为 Source：必须给出理由（reason 字段）。\n"
            "   - 标准库函数：引用所属标准库/API（如 fopen 是 C标准库 stdio.h 的文件读取函数）\n"
            "   - 非标准库函数：给出强证据说明为什么能接收外部控制数据\n"
            "2. 如果判定为非 Source：不需要给出理由。\n"
            "判断完成后，使用 apply_subagent_results() 将结果（含 reason）写入缓存。\n"
            "调用格式：apply_subagent_results({\"func1\": {\"is_source\": True, \"reason\": \"...\"}, \"func2\": {\"is_source\": False}})"
        ),
        "cache_file_path": os.path.abspath(
            os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "caches_data", CACHE_FILENAME)
        ),
        "functions": uncached_funcs,
    }

    with open(pending_path, "w", encoding="utf-8") as f:
        json.dump(pending_data, f, indent=4, ensure_ascii=False)

    print(f"[ExternSourceFilter] 待判断文件已写入: {pending_path}")
    print(f"  共 {len(uncached_funcs)} 个函数需要 SubAgent 判断")
    return pending_path


def read_pending_judge_file(pending_path: str) -> dict:
    """
    读取待判断文件（供 SubAgent 调用方使用，便于了解需要判断哪些函数）。

    :param pending_path: 待判断文件路径
    :return: 文件内容字典
    """
    with open(pending_path, "r", encoding="utf-8") as f:
        return json.load(f)


def apply_subagent_results(results: dict, cache_dir: str = None) -> int:
    """
    SubAgent 判断完成后，将结果写入缓存。

    此函数可由 SubAgent 或调用方调用，将判断结果持久化到缓存文件。

    :param results:
        - 新格式: {函数名: {"is_source": bool, "reason": str}} 字典
          is_source=True 时，reason 应给出判断理由（标准库引用或强证据）。
          is_source=False 时，reason 可为空字符串或省略。
        - 旧格式: {函数名: bool} 字典（向后兼容，reason 默认为空）
    :param cache_dir: 缓存目录路径，默认为 caches_data/
    :return: 新增缓存条数
    """
    if cache_dir is None:
        cache_dir = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "caches_data"
        )
    cache_path = os.path.join(cache_dir, CACHE_FILENAME)

    # 加载现有缓存
    cache = {}
    if os.path.exists(cache_path):
        try:
            with open(cache_path, "r", encoding="utf-8") as f:
                cache = json.load(f)
        except Exception:
            cache = {}

    new_count = 0
    for func_name, value in results.items():
        if isinstance(value, bool):
            # 向后兼容旧格式 {func_name: bool}
            is_source = value
            reason = ""
        elif isinstance(value, dict):
            is_source = value.get("is_source", False)
            # 只有判定为 Source 时才需要理由
            reason = value.get("reason", "") if is_source else ""
        else:
            print(f"[ExternSourceFilter] 警告: 跳过无效格式的函数 {func_name}: {type(value)}")
            continue

        cache[func_name] = {
            "is_source": bool(is_source),
            "reason": reason,
            "timestamp": datetime.now().isoformat()
        }
        new_count += 1

    os.makedirs(os.path.dirname(cache_path), exist_ok=True)
    with open(cache_path, "w", encoding="utf-8") as f:
        json.dump(cache, f, indent=4, ensure_ascii=False)

    print(f"[ExternSourceFilter] 已更新缓存: 新增 {new_count} 条记录 -> {cache_path}")
    return new_count
