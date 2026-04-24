# LLMChainAnalyzer 输出json各字段说明
# 0. 函数链名称(chain_name)： str
# 1. 大模型认为提供信息是否充足(info_enough)： bool
# 2. 输入点函数(input_func)：tuple(bool, list[tuple(str, list(str))])， bool： 是否找到了输入点函数， str： 函数链中函数名称（输入点名称） Sample: ("parse_input", ["funcA", "funcB"])
# 3. 详细报告内容(repo_detail)： str
# 4. 输入示例（payload）： list[tuple(str, str)]， (str: 输入描述, str: 输入内容)
# 若发生错误，返回字段如下：
# Error: str， 错误描述

# LLMStringAnalyzer 输出json各字段说明
# 1. 字符串值(str)： 风险评分(float)， 范围0-1，0表示无风险，1表示高风险
# Sample: {"admin": 0.8, "password": 0.9, "hello": 0.0}

import requests
import json
import sys
import os
import glob
from tqdm import tqdm
import json_repair

# === 0day 智能体 LLM 全局配置（便于统一修改） ===
ZERO_DAY_LLM_BASE_URL = os.environ.get("ZERO_DAY_LLM_BASE_URL").rstrip("/")
ZERO_DAY_LLM_API_KEY = os.environ.get("ZERO_DAY_LLM_API_KEY")
ZERO_DAY_LLM_MODEL = os.environ.get("ZERO_DAY_LLM_MODEL")
ZERO_DAY_LLM_TEMPERATURE = float(os.environ.get("ZERO_DAY_LLM_TEMPERATURE", "0.05"))
ZERO_DAY_LLM_MAX_TOKENS = int(os.environ.get("ZERO_DAY_LLM_MAX_TOKENS", "8192"))
ZERO_DAY_LLM_TIMEOUT_SECONDS = int(os.environ.get("ZERO_DAY_LLM_TIMEOUT_SECONDS", "600"))


def load_llm_runtime_config(base_url: str | None = None, api_key: str | None = None, config_path: str | None = None) -> dict[str, str]:
    resolved_base_url = (base_url or "").strip()
    resolved_api_key = (api_key or "").strip()
    candidate_config_path = (config_path or os.environ.get("ZERO_DAY_AGENT_LLM_CONFIG_PATH") or "").strip()

    if candidate_config_path and os.path.isfile(candidate_config_path):
        try:
            with open(candidate_config_path, "r", encoding="utf-8") as f:
                data = json.load(f) or {}
            if not resolved_base_url:
                resolved_base_url = str(data.get("ZERO_DAY_AGENT_TOOL_LLM_BASE_URL") or "").strip()
            if not resolved_api_key:
                resolved_api_key = str(data.get("ZERO_DAY_AGENT_TOOL_LLM_API_KEY") or "").strip()
        except Exception:
            pass

    if not resolved_base_url:
        resolved_base_url = ZERO_DAY_LLM_BASE_URL
    if not resolved_api_key:
        resolved_api_key = ZERO_DAY_LLM_API_KEY

    return {
        "base_url": resolved_base_url.rstrip("/"),
        "api_key": resolved_api_key,
    }

DEBUG = 5  # 设置为大于0的整数以启用测试模式，仅分析最后N个文件夹

class LLMClient:
    def __init__(self, base_url: str, api_key: str, 
                 temperature: float=ZERO_DAY_LLM_TEMPERATURE, max_tokens: int=ZERO_DAY_LLM_MAX_TOKENS, thinking: bool=True, timeout: int=ZERO_DAY_LLM_TIMEOUT_SECONDS,
                 model: str=ZERO_DAY_LLM_MODEL):
        self.base_url = base_url
        self.api_key = api_key
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.thinking = thinking
        self.timeout = timeout
        self.model = model

    def ask_question(self, question: str) -> str:
        """调用DeepSeek模型回答问题"""
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": question
                }
            ],
            "temperature": self.temperature,  # 低温度——更确定性的回答
            "max_tokens": self.max_tokens,
            "chat_template_kwargs": {"thinking": self.thinking}
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",  # OpenAI兼容接口
                headers=headers,
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            
            result = response.json()
            content = result['choices'][0]['message']['content']
            
            # 如果包含思考过程，只保留思考后的内容
            if "</think>" in content:
                content = content.split("</think>")[-1].strip()
                
            return content
            
        except Exception as e:
            error_msg = f'错误: 模型调用失败 - {str(e)}'
            if 'response' in locals() and hasattr(response, 'text'):
                error_msg += f'\n服务器返回详情: {response.text}'
                error_msg = '{"Error": "' + error_msg.replace('"', '\\"') + '"}'
            return error_msg


class LLMChainAnalyzer:
    """分析函数链以生成输入示例的类"""
    def __init__(self,
                 client: LLMClient,
                 data_dir: str="../test/output",
                 output_dir: str="../test/LLM_result",
                 need_repo_detail: bool=True):
        self.client = client
        self.output_dir = output_dir
        self.data_dir = data_dir
        self.output_dir = output_dir
        self.need_repo_detail = need_repo_detail
        
    def analyze_function_chain(self, chain_folder_name: str):
        """分析单个函数链文件夹"""
        tqdm.write(f"正在分析: {chain_folder_name}")
        
        # 读取文件夹下的所有.c文件
        c_files = glob.glob(os.path.join(self.data_dir, chain_folder_name, "*.c"))
        if not c_files:
            tqdm.write(f"  警告: {chain_folder_name} 中没有找到 .c 文件")
            return

        code_content = ""
        for c_file in c_files:
            func_name = os.path.basename(c_file).replace(".c", "")
            try:
                with open(c_file, "r", encoding="utf-8") as f:
                    content = f.read()
                    code_content += f"\n--- Function: {func_name} ---\n{content}\n"
            except Exception as e:
                tqdm.write(f"  读取文件失败 {c_file}: {e}")
        
        repo_detail = None
        if self.need_repo_detail:
            # 构建提示词1
            prompt_repo = f"""
    你是一个安全研究专家。我有一组相关的C语言反编译伪代码，它们构成了一个调用链。
    文件夹名称为 "{chain_folder_name}"，格式通常为 "输入解析函数-调用者[-调用者]"。

    代码内容如下：
    {code_content}

    任务目标：
    请分析上述代码，特别是输入解析函数的逻辑。
    请推断什么样的输入（Input）可以成功通过输入解析函数的检查（Parsing Logic），或者触发特定的解析路径。
    请只关注提供的这几个函数内部的逻辑，不要发散到未提供的函数。

    请回答：
    1. 输入解析函数的主要逻辑是什么？
    2. 需要什么样的输入数据（例如：特定的字符串格式、魔数、长度限制、JSON结构等）才能通过检查？
    """

            # 调用模型
            repo_detail = self.client.ask_question(prompt_repo)
        
        # 构建提示词2
        prompt_json = f"""
你是一个安全研究专家。我有一组相关的C语言反编译伪代码，它们构成了一个调用链。
文件夹名称为 "{chain_folder_name}"，格式通常为 "输入解析函数-调用者[-调用者]"。

代码内容如下：
{code_content}

任务目标：
请分析上述代码，特别是输入解析函数的逻辑。
请推断什么样的输入（Input）可以成功通过输入解析函数的检查（Parsing Logic），或者触发特定的解析路径。
请只关注提供的这几个函数内部的逻辑，不要发散到未提供的函数。

请严格按照以下 JSON 格式输出分析结果，不要包含 Markdown 代码块标记（如 ```json ... ```），直接返回 JSON 字符串。
{{
    "chain_name": "{chain_folder_name}",
    "info_enough": true, // bool, 大模型认为提供信息是否充足
    // tuple(bool, list[tuple(str, list(str))])
    "input_func": [
        true, // bool, 是否找到了输入点函数
        [
            ["函数名", ["函数1", "函数2", ...]] // list[tuple(str, list(str))], 识别到的输入点函数信息，其中函数名为链中函数名称，子列表为该函数可能的输入点函数名称（比如'recv'之类的）
        ]
    ],
    "repo_detail": "详细的分析报告内容，包括输入解析函数的主要逻辑、通过检查需要的输入数据特征等",
    // list[tuple(str, str)]
    "payload": [
        ["输入描述1", "输入内容1"],
        ["输入描述2", "输入内容2"]
    ]
}}
"""

        # 调用模型
        answer = self.client.ask_question(prompt_json)
        # test output raw answer
        # with open(os.path.join(self.output_dir, f"{chain_folder_name}.md"), "w", encoding="utf-8") as f:
        #    f.write(answer)
        
        # 保存结果
        try:
            # 尝试清理可能存在的 Markdown 标记
            json_content = answer.strip()
            # 寻找第一个 { 和最后一个 }
            start_idx = json_content.find('{')
            end_idx = json_content.rfind('}')
            
            if start_idx != -1 and end_idx != -1:
                json_content = json_content[start_idx:end_idx+1]
            else:
                # 如果找不到大括号，可能格式完全不对，但还是尝试清理markdown标记作为备选
                if json_content.startswith("```json"):
                    json_content = json_content[7:]
                if json_content.startswith("```"):
                    json_content = json_content[3:]
                if json_content.endswith("```"):
                    json_content = json_content[:-3]
                json_content = json_content.strip()

            # 验证是否为有效JSON
            try:
                parsed_json = json.loads(json_content)
                if repo_detail is not None and "repo_detail" in parsed_json:
                    tqdm.write(f"  注意: 已包含 repo_detail，跳过模型返回的内容")
                    # 强制覆盖 repo_detail 字段
                    parsed_json["repo_detail"] = repo_detail
                # 重新序列化以确保格式统一
                json_content = json.dumps(parsed_json, indent=4, ensure_ascii=False)
            except json.JSONDecodeError as e:
                try:
                    # 尝试使用 json_repair 修复
                    parsed_json = json_repair.loads(json_content)
                    
                    # 针对 input_func 结构错误的特定修复逻辑
                    # 问题描述：json_repair 可能会把 repo_detail 和 payload 误判为 input_func 列表的第三个元素
                    if isinstance(parsed_json, dict) and "input_func" in parsed_json:
                        input_func = parsed_json["input_func"]
                        if isinstance(input_func, list) and len(input_func) > 2:
                            last_item = input_func[-1]
                            # 如果最后一个元素是字典，且包含 repo_detail 或 payload，说明结构错乱
                            if isinstance(last_item, dict) and ("repo_detail" in last_item or "payload" in last_item):
                                tqdm.write(f"  注意: 检测到 input_func 包含额外字段，正在重构 JSON 结构...")
                                # 将误入的字段移回根节点
                                for key, value in last_item.items():
                                    if key in ["repo_detail", "payload"]:
                                        parsed_json[key] = value
                                # 修正 input_func，只保留前两个元素 [bool, list]
                                parsed_json["input_func"] = input_func[:2]

                    if repo_detail is not None and "repo_detail" in parsed_json:
                        tqdm.write(f"  注意: 已包含 repo_detail，跳过模型返回的内容")
                        # 强制覆盖 repo_detail 字段
                        parsed_json["repo_detail"] = repo_detail
                    # 修复后重新序列化
                    json_content = json.dumps(parsed_json, indent=4, ensure_ascii=False)
                    tqdm.write(f"  注意: 检测到JSON格式错误，已使用 json_repair 自动修复")
                except Exception as repair_e:
                    tqdm.write(f"  JSON修复失败: {repair_e} - 内容片段: {json_content[:50]}...")
                    with open(os.path.join(self.output_dir, f"{chain_folder_name}_json_parse_error.md"), "w", encoding="utf-8") as f:
                        f.write(answer)
                    return

            output_path = os.path.join(self.output_dir, f"{chain_folder_name}.json")
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(json_content)
            tqdm.write(f"  结果已保存至: {output_path}")
        except Exception as e:
            tqdm.write(f"  保存结果失败: {e}")
            
    def analyze_chains(self):
        """遍历所有函数链文件夹进行分析"""
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        
        items = os.listdir(self.data_dir)
        folders = [item for item in items if os.path.isdir(os.path.join(self.data_dir, item))]
        
        print(f"找到 {len(folders)} 个待分析的函数链文件夹。")
        
        # test 只分析后DEBUG个文件夹，为0则非测试
        if DEBUG:
            folders = folders[-DEBUG:]
        # end test
        
        for folder in tqdm(folders, desc="分析进度", colour="green"):
            self.analyze_function_chain(folder)

class LLMStringAnalyzer:
    """
    分析IDA字符串并得到其风险评分的类
    
    :param client: LLMClient实例，用于调用大模型
    :param string_info: 从IDA提取的字符串信息字典，格式为 {string_value: [calling_function_names]}
    :param batch_size: 每次分析的字符串数量，默认100
    """
    def __init__(self,
                 client: LLMClient,
                 string_info: dict[str, list[str]],
                 batch_size: int=100):
        self.string_info = string_info
        self.client = client
        self.batch_size = batch_size

    @staticmethod
    def _try_unescape_model_key(key: str) -> str:
        """将模型返回的可见转义形式尽量还原为原始字符串。"""
        try:
            return bytes(key, "utf-8").decode("unicode_escape")
        except Exception:
            return key

    def _analyze_string_batch(self, batch: list[str]) -> dict[str, float]:
        """
        分析一批字符串并获得风险评分
        
        :param batch: 字符串列表
        :return: 字符串风险评分字典，格式为 {string_value: risk_score}
        """
        prompt_json_base = f"""你是一个安全研究专家。我有一组从IDA中提取的字符串信息需要你进行分析。
我会在每一行提供一个字符串，请你分析每个字符串的潜在风险，主要关注那些可能处于输入解析流程中的字符串。
你需要为每个字符串生成一个评分，评价它的风险等级（0-1之间，0表示无风险，1表示高风险）。
请根据字符串的自然语义等因素综合评估风险。
另外，你需要注意，你应该将大部分风险评分集中在那些可能被输入解析函数调用的字符串上，而不是所有字符串都平均评分。并且，大部分字符串的评分应该为0，只有少数字符串可能具有较高的风险评分。


你的输出格式应该是一个JSON对象，格式如下：
{{
    "string_value1": risk_score1,
    "string_value2": risk_score2,
    ...
}}

现在请根据以下字符串信息进行分析：
"""
        prompt_json = prompt_json_base
        strings = []
        escaped_to_original = {}
        for string_value in batch:
            # 使用 JSON 字符串字面量保证换行/引号等字符不会破坏提示词结构。
            escaped = json.dumps(string_value, ensure_ascii=False)
            strings.append(f"{escaped}\n")
            escaped_to_original[escaped[1:-1]] = string_value

        prompt_json += "".join(strings)
        
        # 调用模型
        answer = self.client.ask_question(prompt_json)

        # 解析模型返回的JSON结果
        try:
            # 尝试清理可能存在的 Markdown 标记
            json_content = answer.strip()
            # 寻找第一个 { 和最后一个 }
            start_idx = json_content.find('{')
            end_idx = json_content.rfind('}')
            
            if start_idx != -1 and end_idx != -1:
                json_content = json_content[start_idx:end_idx+1]
            else:
                # 如果找不到大括号，可能格式完全不对，但还是尝试清理markdown标记作为备选
                if json_content.startswith("```json"):
                    json_content = json_content[7:]
                if json_content.startswith("```"):
                    json_content = json_content[3:]
                if json_content.endswith("```"):
                    json_content = json_content[:-3]
                json_content = json_content.strip()

            # 验证是否为有效JSON
            try:
                parsed_json = json.loads(json_content)
            except json.JSONDecodeError as e:
                try:
                    # 尝试使用 json_repair 修复
                    parsed_json = json_repair.loads(json_content)
                    tqdm.write(f"  注意: 检测到JSON格式错误，已使用 json_repair 自动修复")
                except Exception as repair_e:
                    tqdm.write(f"  JSON修复失败: {repair_e} - 内容片段: {json_content[:50]}...")
                    return {}

        except Exception as e:
            tqdm.write(f"  JSON解析失败: {e}")
            return {}

        normalized_scores = {}
        unmatched_keys = []
        for returned_key, score in parsed_json.items():
            original_key = None
            if returned_key in self.string_info:
                original_key = returned_key
            elif returned_key in escaped_to_original:
                original_key = escaped_to_original[returned_key]
            else:
                unescaped_key = self._try_unescape_model_key(returned_key)
                if unescaped_key in self.string_info:
                    original_key = unescaped_key

            if original_key is None:
                unmatched_keys.append(returned_key)
                continue

            try:
                normalized_scores[original_key] = float(score)
            except (TypeError, ValueError):
                continue

        if unmatched_keys:
            tqdm.write(f"  警告: 模型返回了 {len(unmatched_keys)} 个未匹配字符串 key")
            for idx, key in enumerate(unmatched_keys[:5], start=1):
                visible_key = key.encode("unicode_escape").decode("ascii", errors="replace")
                tqdm.write(f"    未匹配样例{idx}: {visible_key}")
            if len(unmatched_keys) > 5:
                tqdm.write(f"    ... 其余 {len(unmatched_keys) - 5} 个未展示")

        return normalized_scores
    
    def _string_is_in_cache(self, string: str) -> tuple[float, bool]:
        """
        检查字符串是否在缓存中，避免重复分析
        
        :param string: 待检查的字符串
        :return: (风险评分, 是否在缓存中)
        """
        # TODO: 实现缓存机制，当前版本不使用缓存，直接返回False
        # 实现缓存机制后，完善此函数，如果字符串在缓存中且评分有效，返回 (cached_score, True)，否则返回 (Any, False)
        return 0.0, False

    def analyze_strings(self) -> dict[str, tuple[float, bool]]:
        """
        分析字符串信息并获得评分结果
        
        :return: 字符串风险评分字典，格式为 {string_value: (risk_score, in_cache)}
        """
        string_scores = {}
        strings = list(self.string_info.keys())
        batches = []
        i = 0
        cache_hits = 0
        while i < len(strings):
            batch_strings_count = 0
            batch = []
            while i < len(strings) and batch_strings_count < self.batch_size:
                string = strings[i]
                cached_score, in_cache = self._string_is_in_cache(string)
                if in_cache:
                    # 如果在缓存中，直接使用缓存结果，不加入待分析批次
                    string_scores[string] = (cached_score, True)
                    i += 1
                    cache_hits += 1
                    continue
                batch.append(string)
                batch_strings_count += 1
                i += 1
            if batch:
                batches.append(batch)
        
        print(f"总字符串数量: {len(strings)}，批次数量: {len(batches)}，缓存命中数量: {cache_hits}")

        for batch in tqdm(batches, desc="分析字符串批次", colour="blue"):
            batch_result = self._analyze_string_batch(batch)
            if not batch_result:
                continue
            for string, score in batch_result.items():
                string_scores[string] = (score, False)

        return string_scores

def main():
    llm_cfg = load_llm_runtime_config()
    base_url = llm_cfg["base_url"]
    api_key = llm_cfg["api_key"]
    
    client = LLMClient(base_url, api_key)
    
    # 确定路径
    script_dir = os.path.dirname(os.path.abspath(__file__))
    test_dir = os.path.abspath(os.path.join(script_dir, "..", "test"))
    input_dir = os.path.join(test_dir, "output")
    result_dir = os.path.join(test_dir, "LLM_result")
    
    if not os.path.exists(input_dir):
        print(f"错误: 输入目录不存在: {input_dir}")
        return

    analyzer = LLMChainAnalyzer(client, data_dir=input_dir, output_dir=result_dir)
    analyzer.analyze_chains()

    print("\n" + "="*20 + " 所有分析完成 " + "="*20)

if __name__ == "__main__":
    main()
