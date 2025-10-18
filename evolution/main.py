import os
import re
import asyncio
import random
import uuid
from typing import Tuple, Optional, Union
from concurrent.futures import ThreadPoolExecutor
from core.base import TaskPlugin, TaskEvaluator
from evolution.config import CoreConfig
from api import (
    LLMInterface,
    AsyncOpenAILLM, OpenAIConfig,
    AsyncAnthropicLLM, AnthropicConfig,
    AsyncLiteLLM, LiteLLMConfig
)
from evolution.agent import ClaudeAgent, ClaudeCodeConfig
from evolution.program_library import ProgramLibrary, Program
from evolution.client import RemoteEvaluatorServerManager
from utils.cache_manager import SimpleCacheManager

class EvolutionEngine:
    core_config: CoreConfig
    task_plugin: TaskPlugin
    evaluator: TaskEvaluator
    llm: Union[LLMInterface, ClaudeAgent]
    client: RemoteEvaluatorServerManager

    llm_cache: Optional[SimpleCacheManager]
    evaluator_cache: Optional[SimpleCacheManager]

    def __init__(self, task_plugin: TaskPlugin, core_config: CoreConfig):
        self.core_config = core_config
        self.task_plugin = task_plugin
        self.evaluator = task_plugin.create_evaluator()
        
        # 根据配置类型创建对应的 LLM 实例或 ClaudeAgent
        if isinstance(core_config.llm, OpenAIConfig):
            self.llm = AsyncOpenAILLM(
                core_config.llm,
                os.getenv("OPENAI_BASE_URL"),
                os.getenv("OPENAI_API_KEY")
            )
        elif isinstance(core_config.llm, AnthropicConfig):
            self.llm = AsyncAnthropicLLM(
                core_config.llm,
                os.getenv("ANTHROPIC_BASE_URL"),
                os.getenv("ANTHROPIC_API_KEY")
            )
        elif isinstance(core_config.llm, LiteLLMConfig):
            self.llm = AsyncLiteLLM(
                core_config.llm,
                os.getenv("LITELLM_BASE_URL"),  # LiteLLM 可以使用自定义 base_url
                os.getenv("LITELLM_API_KEY")     # 或从环境变量中读取
            )
        elif isinstance(core_config.llm, ClaudeCodeConfig):
            self.llm = ClaudeAgent(core_config.llm)
        else:
            raise ValueError(f"Unsupported LLM config type: {type(core_config.llm)}")

        # 初始化随机种子
        if core_config.seed is not None:
            random.seed(core_config.seed)

        # 初始化缓存
        if core_config.cache.enabled:
            self.llm_cache = SimpleCacheManager(core_config.cache, core_config.task_name + '.llm')
            self.evaluator_cache = SimpleCacheManager(core_config.cache, core_config.task_name + '.evaluator')
        else:
            self.llm_cache = None
            self.evaluator_cache = None

        hostname_list = os.environ.get('HOSTNAME_LIST', '')
        ip_pool = [ip.strip() for ip in hostname_list.split(';') if ip.strip()]
        self.client = RemoteEvaluatorServerManager(
            source_dir = task_plugin.task_path,
            output_dir = os.path.join("tmp", core_config.task_name),
            ip_pool = ip_pool,
            key_path = "~/.ssh/id_rsa",
            port = 22,
            cache = self.evaluator_cache,
            evaluation_config = self.task_plugin.get_evaluation_config()
        )

    async def create_generation(self, program_library: ProgramLibrary, generation: int, task_dir: str, evaluator_client: RemoteEvaluatorServerManager):
        program_pool_size = self.core_config.evolution_setting.program_pool_size
        
        # 生成程序
        if generation == 0:
            print("正在生成初始种群...")
            prompt = self.task_plugin.get_initial_prompt()
            tasks = [self.gen_program(prompt, extra_cache_param=i) for i in range(program_pool_size)]
            program_list = await asyncio.gather(*tasks)
            parent_ids_list = [None] * len(program_list)
            creation_method = "initial"
        else:
            print(f"将采样 {program_pool_size} 对 parent 和 inspiration 程序...")
            samples = program_library.sample_parent_inspiration_pairs(program_pool_size, program_pool_size)
            
            prompts = [
                self.task_plugin.get_mutation_prompt(parent.content, inspiration.content, parent.metadata, inspiration.metadata)
                for parent, inspiration in samples
            ]
            tasks = [self.gen_program(prompt) for prompt in prompts]
            program_list = await asyncio.gather(*tasks)
            parent_ids_list = [[parent.id, inspiration.id] for parent, inspiration in samples]
            creation_method = "mutation"
        
        print(f"评估产生的 {len(program_list)} 个程序...")
        
        # 并发评估所有程序
        loop = asyncio.get_event_loop()
        with ThreadPoolExecutor() as executor:
            tasks = [
                loop.run_in_executor(
                    executor,
                    evaluator_client.execute_evaluation_auto,
                    code, self.core_config.evaluation_timeout_sec
                )
                for code in program_list
            ]
            eval_results = await asyncio.gather(*tasks)
        
        # 将评估结果添加到程序库
        success_count = 0
        for i, (code, eval_result, parent_ids) in enumerate(zip(program_list, eval_results, parent_ids_list)):
            if eval_result['success'] and eval_result['result']:
                metrics = eval_result['result']
                metadata = eval_result.get('metadata', {})
                
                program = program_library.add_program(
                    content=code,
                    metrics=metrics,
                    parent_ids=parent_ids,
                    creation_method=creation_method,
                    metadata=metadata
                )
                success_count += 1
                print(f"程序 {i+1}/{len(program_list)}: 成功 (combined_score={program.metrics.get('combined_score', 0):.4f})")
            else:
                error_msg = eval_result.get('error', 'Unknown error')
                print(f"程序 {i+1}/{len(program_list)}: 失败 - {error_msg}")
        
        print(f"成功评估 {success_count}/{len(program_list)} 个程序")
        
        # 保存当前代的程序库
        save_path = program_library.save()
        print(f"已保存程序库到: {save_path}")

    async def run_evolution(self, task_dir: str, save_dir: str) -> ProgramLibrary:
        print(f"输出目录: {os.path.abspath(save_dir)}")
        lib = ProgramLibrary(save_dir)

        with self.client as manager:
            print('-' * 20)
            print(manager.get_resource_status())
            print('-' * 20)
            await self.create_generation(lib, 0, task_dir, manager)
            for gen_id in range(1, self.core_config.evolution_setting.max_iterations + 1):
                print(f"\n=== 第 {gen_id}/{self.core_config.evolution_setting.max_iterations} 代 ===")
                await self.create_generation(lib, gen_id, task_dir, manager)

        return lib

    async def gen_program(self, prompt: str, extra_cache_param: Optional[int] = None) -> str:
        # 根据 self.llm 类型使用不同的缓存参数
        if isinstance(self.llm, ClaudeAgent):
            config_dict = self.llm.config.to_json()
        else:
            config_dict = self.llm.config.to_json()
        
        if self.llm_cache is not None:
            cache_params = { "llm.config": config_dict, "prompt": prompt }
            if extra_cache_param is not None:
                cache_params["extra_cache_param"] = extra_cache_param
            cached_response = self.llm_cache.get_cached_response(**cache_params)
            if cached_response:
                return cached_response

        # 根据 self.llm 类型调用不同的生成方法
        if isinstance(self.llm, ClaudeAgent):
            # 使用 ClaudeAgent
            task_uid = str(uuid.uuid4())[:8]  # 生成短的唯一标识符
            program_code = await self.llm.run(
                prompt=prompt,
                task_uid=task_uid,
                target_file="program.py"
            )
            # ClaudeAgent 已经返回纯代码，不需要额外提取
        else:
            # 使用传统 LLMInterface
            original_code = await self.llm.generate(prompt)
            program_code = EvolutionEngine.extract_code(original_code)
            if "```" in program_code:
                print("Warning! extract failed.")
                with open("debug.log", "w") as f:
                    f.write(original_code)
                raise

        if self.llm_cache:
            self.llm_cache.cache_response(response=program_code, **cache_params)
        return program_code

    @staticmethod
    def extract_code(text: str) -> str:
        """Extract code from LLM output"""
        pattern = r'```(?:python)?\n(.*?)```'
        matches = re.findall(pattern, text, re.DOTALL)
        
        if matches:
            return '\n'.join(match.strip() for match in matches)
        else:
            return text
