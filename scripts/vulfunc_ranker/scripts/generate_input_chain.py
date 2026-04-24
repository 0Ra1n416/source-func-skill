import idapro
import idautils
import idc
import sys
import os
import idaapi
import ida_auto
import json
from typing import Callable, List, Dict, Set, Tuple, Any
# 从项目根目录导入
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# 该脚本用于提取输入解析函数与输入函数之间的切片  （B->A）
this_script_path = os.path.abspath(__file__)
THIS_FILE_DIR = os.path.dirname(this_script_path)
INPUT_FILE = os.path.join(THIS_FILE_DIR, "..", "..", "..", "caches_data", "rumpusd.exe")
RECOGNIZE_OUTPUT_BASE_DIR = os.path.join(THIS_FILE_DIR, "..", "..", "..", "caches_data")
OUTPUT_DIR = os.path.join(THIS_FILE_DIR, "..", "test", "output")


class InputParsingChainGenerator:
    """
    用于生成输入解析函数与输入函数之间调用关系链的类
    """
    def __init__(self,
                 input_bin: str=INPUT_FILE,
                 recognize_output_base_dir: str=RECOGNIZE_OUTPUT_BASE_DIR) -> None:
        """
        :param _input_bin: 输入二进制文件的路径
        :type _input_bin: str
        :param _recognize_output_base_dir: 缓存文件夹路径，与vulfunc_ranker.py的缓存文件夹应相同，其下包含./{bin_name}/recognize_output_{bin_name}.json文件
        :type _recognize_output_base_dir: str
        """
        self._input_bin = input_bin
        self._recognize_output_base_dir = recognize_output_base_dir

    @staticmethod
    def _decompile_function(func_ea) -> Dict | None:
        """
        反编译单个函数并返回结果
        
        :param func_ea: 函数地址
        :return: 反编译结果字典，包含"name"、"address"、"decompiled"字段；反编译失败返回None
        """
        if func_ea in (idc.BADADDR, None):
            print(f"[WARN] 无效函数地址: {func_ea}")
            return None
        try:
            dec = idaapi.decompile(func_ea)
            if dec is None:
                print(f"[WARN] 反编译失败: {hex(func_ea)}")
                return None
            return {
                "name": idc.get_func_name(func_ea),
                "address": hex(func_ea),
                "decompiled": str(dec).replace("\n", "\n    ")
            }
        except Exception as e:
            print(f"[CRASH] 反编译异常 {hex(func_ea)}: {str(e)}")
            return None

    @staticmethod
    def _get_func_caller(func_ea) -> Set[Tuple[int, ...]]:
        """
        通过调用IDA的API获取func的调用关系（主要是调用func的函数,往前找两层）

        :param func_ea: 函数地址
        :return chain_funcs: 从输入解析函数往前溯两层的函数集合（链上各个函数的地址组成的元组）
        """
        chain_funcs = set()
        # 获取调用该函数的所有函数
        for xref in idautils.XrefsTo(func_ea):
            l1_ea = xref.frm
            
            # 过滤l1_ea无效的情况
            if l1_ea == idc.BADADDR or l1_ea == "":
                continue
            
            # 获取l1函数名
            l1_func = idaapi.get_func(l1_ea)
            if not l1_func:
                continue
            l1_start = l1_func.start_ea
            
            has_l2 = False
            # 获取调用l1的所有函数
            for xref2 in idautils.XrefsTo(l1_start):
                l2_ea = xref2.frm
                
                # 过滤l2_ea无效的情况
                if l2_ea == idc.BADADDR or l2_ea == "":
                    continue
                
                l2_func = idaapi.get_func(l2_ea)
                if not l2_func:
                    continue
                l2_start = l2_func.start_ea
                
                has_l2 = True
                chain_funcs.add((l2_start, l1_start, func_ea))
                print(f"Found function chain: {hex(l2_start)} -> {hex(l1_start)} -> {hex(func_ea)}")
            
            if not has_l2:
                chain_funcs.add((l1_start, func_ea))
                print(f"Found function chain: {hex(l1_start)} -> {hex(func_ea)}")
            
        if not chain_funcs:
            chain_funcs.add((func_ea,))
            print(f"Found function chain: {hex(func_ea)}")

        return chain_funcs

    def _decompile_all_chain(self,funcs_list) -> List:
        """
        反编译所有输入解析函数可能的三层内调用函数关系链
        
        :param funcs_list: 输入解析函数名列表
        :return all_chain_funcs: 所有输入解析函数与输入函数之间的调用关系链列表
        """
        # 获取所有输入解析函数可能的三层内调用函数关系链
        all_chain_funcs = list()
        for func in funcs_list:
            # 获得函数名对应的地址
            func_ea = idc.get_name_ea_simple(func)
            if func_ea == idc.BADADDR:
                print(f"[WARN] 找不到函数: {func}")
                continue
            chain_funcs = self._get_func_caller(func_ea)
            
            for chain in chain_funcs:
                # 如果反编译失败，跳过
                if len(chain) == 1:
                    func1 = self._decompile_function(chain[0])
                    if func1:
                        all_chain_funcs.append([func1])
                    else:
                        print(f"Skipping function chain due to decompilation error: {hex(chain[0])}")
                elif len(chain) == 2:
                    func1 = self._decompile_function(chain[0])
                    func2 = self._decompile_function(chain[1])
                    if func1 and func2:
                        all_chain_funcs.append([func1, func2])
                    else:
                        print(f"Skipping function chain due to decompilation error: {hex(chain[0])} or {hex(chain[1])}")
                elif len(chain) == 3:
                    func1 = self._decompile_function(chain[0])
                    func2 = self._decompile_function(chain[1])
                    func3 = self._decompile_function(chain[2])
                    if func1 and func2 and func3:
                        all_chain_funcs.append([func1, func2, func3])
                    else:
                        print(f"Skipping function chain due to decompilation error: {hex(chain[0])} or {hex(chain[1])} or {hex(chain[2])}")
        
        return all_chain_funcs

    def _get_all_chain_names(self, funcs_list) -> List[List[str]]:
        """
        获取所有输入解析函数可能的三层内调用函数关系链（仅函数名）
        
        :param funcs_list: 输入解析函数名列表
        :return all_chain_names: 所有输入解析函数与输入函数之间的调用关系链列表（仅函数名）
        """
        # 获取所有输入解析函数可能的三层内调用函数关系链（仅函数名）
        all_chain_names = list()
        for func in funcs_list:
            # 获得函数名对应的地址
            func_ea = idc.get_name_ea_simple(func)
            if func_ea == idc.BADADDR:
                print(f"[WARN] 找不到函数: {func}")
                continue
            chain_funcs = self._get_func_caller(func_ea)
            for chain in chain_funcs:
                if len(chain) == 1:
                    all_chain_names.append([idc.get_func_name(chain[0])])
                elif len(chain) == 2:
                    all_chain_names.append([idc.get_func_name(chain[0]), idc.get_func_name(chain[1])])
                elif len(chain) == 3:
                    all_chain_names.append([idc.get_func_name(chain[0]), idc.get_func_name(chain[1]), idc.get_func_name(chain[2])])
        
        return all_chain_names

    def _find_all_input_chain(self, process_func :Callable[[List], List]) -> List[Any]:
        """
        寻找所有输入解析函数与输入函数之间的调用关系链，并使用process_func进行处理
        
        :param process_func: 处理函数，用于处理每个函数链
        :return all_chain_funcs: 所有输入解析函数与输入函数之间的调用关系链列表
        """
        # 打开数据库并自动分析
        idapro.open_database(self._input_bin, True)
        try:
            ida_auto.auto_wait()
            print("数据库打开并自动分析完成!")
            # 获取二进制文件名，用于定位recognize_output文件
            bin_name = os.path.splitext(os.path.basename(self._input_bin))[0]
            recognize_output_file = os.path.join(self._recognize_output_base_dir, bin_name, f"recognize_output_{bin_name}.json")
            if not os.path.isfile(recognize_output_file):
                raise FileNotFoundError(f"未找到识别结果文件: {recognize_output_file}，请检查缓存文件夹路径并确保漏洞函数识别模块已运行并生成该文件。")
            # 获取输入解析函数名列表
            funcs_list = []
            with open(recognize_output_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                for item in data:
                    funcs_list.append(item.get("name"))
            # 处理函数链
            all_chain_results = process_func(funcs_list)
            
        finally:
            # 关闭数据库
            idapro.close_database()

        return all_chain_results

    def output_input_chain(self,
                           output_dir: str=OUTPUT_DIR) -> None:
        """
        （测试）生成输入解析函数与输入函数之间的调用关系链，并将反编译结果写入文件
        
        :param output_dir: 输出文件夹路径
        """
        all_chain_funcs = self._find_all_input_chain(self._decompile_all_chain)
        print(f"Total function chains found: {len(all_chain_funcs)}")
        
        # 尝试在test文件夹下创建output文件夹
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
        for func_chain in all_chain_funcs:
            if(len(func_chain) == 1):
                output_dir_name = func_chain[0]['name']
            elif(len(func_chain) == 2):
                output_dir_name = func_chain[1]['name'] + "-" + func_chain[0]['name']

            elif(len(func_chain) == 3):
                output_dir_name = func_chain[2]['name'] + "-" + func_chain[1]['name'] + "-" + func_chain[0]['name']
            print(f"Creating files for function chain: {output_dir_name}")
                # 将结果写入文件,在output_path下创建三个文件，文件名为output_dir_name_1.c、output_dir_name_2.c、output_dir_name_3.c
            output_path = os.path.join(output_dir, output_dir_name)
                # 创建一个文件夹，名字为output_path的目录

            try:
                os.makedirs(output_path, exist_ok=True)
            except Exception as e:
                print(f"Failed to create directory {output_path}: {str(e)}")
            # 在对应output_path目录下创建文件
            if(len(func_chain) == 1):
                with open(os.path.join(output_path, f"{func_chain[0]['name']}.c"), "w", encoding="utf-8") as f:
                    f.write(func_chain[0]['decompiled'])
            elif(len(func_chain) == 2):
                with open(os.path.join(output_path, f"{func_chain[0]['name']}.c"), "w", encoding="utf-8") as f:
                    f.write(func_chain[0]['decompiled'])
                with open(os.path.join(output_path, f"{func_chain[1]['name']}.c"), "w", encoding="utf-8") as f:
                    f.write(func_chain[1]['decompiled'])
            elif(len(func_chain) == 3):
                with open(os.path.join(output_path, f"{func_chain[0]['name']}.c"), "w", encoding="utf-8") as f:
                    f.write(func_chain[0]['decompiled'])
                with open(os.path.join(output_path, f"{func_chain[1]['name']}.c"), "w", encoding="utf-8") as f:
                    f.write(func_chain[1]['decompiled'])
                with open(os.path.join(output_path, f"{func_chain[2]['name']}.c"), "w", encoding="utf-8") as f:
                    f.write(func_chain[2]['decompiled'])
        return
                    
    def extract_input_parsing_chains(self) -> List[List[Dict]]:
        """
        对外接口，提取所有输入解析函数与输入函数之间的调用关系链
        
        :return all_chain_funcs: 所有输入解析函数与输入函数之间的调用关系链列表，外层列表包含所有链的列表，内层列表（每个链的列表）包含链中每个函数的反编译结果字典（name、address、decompiled）
        """
        all_chain_funcs = self._find_all_input_chain(self._decompile_all_chain)
        return all_chain_funcs

    def extract_input_parsing_chain_names(self) -> List[List[str]]:
        """
        对外接口，获取所有输入解析函数与输入函数之间的调用关系链（仅函数名）
        
        :return all_chain_names: 所有输入解析函数与输入函数之间的调用关系链列表（仅函数名），外层列表包含所有链的列表，内层列表（每个链的列表）包含链中每个函数的函数名字符串
        """
        all_chain_names = self._find_all_input_chain(self._get_all_chain_names)
        return all_chain_names

if __name__ == "__main__":
    p = InputParsingChainGenerator()
    p.output_input_chain()
