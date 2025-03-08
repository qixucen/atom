import asyncio
import os
import time
import argparse
from dataclasses import dataclass
from typing import Dict, List, Any, Tuple
from tqdm.asyncio import tqdm

from experiment.dataset import load_data
from experiment.module import (
    set_module,
    atom,
    plugin,
    cot,
    sf,
    cot_sc,
    ar
)
from experiment.utils import (
    duration_formatter,
    load_json,
    save_json,
    get_next_log_file,
    get_file_count,
)
from llm import get_token, get_call_count, set_model

# 配置常量
LOG_DIR = "log/{dataset}/{size}"

# 数据集配置
@dataclass
class DatasetConfig:
    question_key: str
    answer_key: str
    module_type: str
    scoring_function: str
    
    def requires_context(self) -> bool:
        return self.module_type == "multi-hop"

# 数据集配置映射
DATASET_CONFIGS = {
    "gsm8k": DatasetConfig(question_key="question", answer_key="answer", 
                          module_type="math", scoring_function="score_math"),
    "math": DatasetConfig(question_key="problem", answer_key="solution", 
                         module_type="math", scoring_function="score_math"),
    "bbh": DatasetConfig(question_key="input", answer_key="target", 
                        module_type="multi-choice", scoring_function="score_mc"),
    "mmlu": DatasetConfig(question_key=["Question", "A", "B", "C", "D"], answer_key="Answer", 
                         module_type="multi-choice", scoring_function="score_mc"),
    "hotpotqa": DatasetConfig(question_key="question", answer_key="answer", 
                             module_type="multi-hop", scoring_function="score_mh"),
    "longbench": DatasetConfig(question_key="input", answer_key="answers", 
                              module_type="multi-hop", scoring_function="score_mh"),
}


class ExperimentRunner:
    def __init__(self, dataset: str, model: str, start: int = 0, end: int = -1, mode: str = "atom"):
        """初始化实验运行器"""
        self.dataset = dataset
        self.start = start
        self.end = None if end == -1 else end
        self.interval = "full" if self.end is None else f"{start}-{end}"
        self.timestamp = time.time()
        self.mode = mode
        # 验证数据集是否支持
        if dataset not in DATASET_CONFIGS:
            raise ValueError(f"Unsupported dataset: {dataset}")
            
        self.config = DATASET_CONFIGS[dataset]
        set_model(model)
    
    async def gather_results(self, testset: List[Dict[str, Any]]) -> List[Any]:
        """收集实验结果"""
        set_module(self.config.module_type)
        
        question_key = self.config.question_key
        tasks = []
        
        if self.mode == "atom":
            if self.config.requires_context():
                from experiment.prompter.multihop import contexts
                # 处理question_key为列表的情况
                if isinstance(question_key, list):
                    formatted_questions = [self._format_question_from_keys(item, question_key) for item in testset]
                    tasks = [atom(question, contexts(item, self.dataset)) 
                            for question, item in zip(formatted_questions, testset)]
                else:
                    tasks = [atom(item[question_key], contexts(item, self.dataset)) for item in testset]
            else:
                # 处理question_key为列表的情况
                if isinstance(question_key, list):
                    tasks = [atom(self._format_question_from_keys(item, question_key)) for item in testset]
                else:
                    tasks = [atom(item[question_key]) for item in testset]
        else:
            # baselines
            func_map = {
                "cot": cot,
                "sf": sf,
                "cot_sc": cot_sc,
                "ar": ar,
            }
            func = func_map[self.mode]
            if self.config.requires_context():
                from experiment.prompter.multihop import contexts
                if isinstance(question_key, list):
                    formatted_questions = [self._format_question_from_keys(item, question_key) for item in testset]
                    tasks = [func(question, contexts=contexts(item, self.dataset)) 
                            for question, item in zip(formatted_questions, testset)]
                else:
                    tasks = [func(item[question_key], contexts=contexts(item, self.dataset)) for item in testset]
            else:
                if isinstance(question_key, list):
                    tasks = [func(self._format_question_from_keys(item, question_key)) for item in testset]
                else:
                    tasks = [func(item[question_key]) for item in testset]

        return await tqdm.gather(*tasks, desc=f"Processing {self.dataset} tasks by {self.mode}")
    
    def _format_question_from_keys(self, item: Dict[str, Any], keys: List[str]) -> str:
        """当question_key是列表时，将多个键对应的值拼接成一个问题"""
        parts = []
        for key in keys:
            if key in item:
                parts.append(f"{key}: {item[key]}")
        return "\n".join(parts)
    
    def construct_entry(self, result: Tuple[Dict[str, Any], Any], data: Dict[str, Any]) -> Dict[str, Any]:
        """构建结果条目"""
        result_data, log = result
        question_key = self.config.question_key
        answer_key = self.config.answer_key
        
        # 处理question_key为列表的情况
        if isinstance(question_key, list):
            question = self._format_question_from_keys(data, question_key)
        else:
            question = data[question_key]
            
        groundtruth = data[answer_key]
        
        entry = {
            "problem": question,
            "groundtruth": groundtruth,
            "response": result_data.get("response"),
            "answer": result_data.get("answer"),
            "log": log
        }
        
        # 动态导入评分函数
        scoring_function = getattr(__import__(f"experiment.utils", fromlist=[self.config.scoring_function]), 
                                  self.config.scoring_function)
        
        # 根据评分函数的不同传递不同数量的参数
        if self.config.scoring_function == "score_math":
            entry["score"] = scoring_function(entry["answer"], groundtruth, self.dataset)
        else:
            entry["score"] = scoring_function(entry["answer"], groundtruth)
        return entry
    
    def construct_entry_baseline(self, result: Dict[str, Any], data: Dict[str, Any]) -> Dict[str, Any]:
        question_key = self.config.question_key
        answer_key = self.config.answer_key
        if isinstance(question_key, list):
            question = self._format_question_from_keys(data, question_key)
        else:
            question = data[question_key]
        groundtruth = data[answer_key]
        entry = {
            "problem": question,
            "groundtruth": groundtruth,
        }
        if self.mode in ["cot", "sf", "cot_sc", "ar", "ap"]:
            entry["response"] = result.get("response")
            entry["answer"] = result.get("answer")
        
        scoring_function = getattr(__import__(f"experiment.utils", fromlist=[self.config.scoring_function]), 
                                  self.config.scoring_function)
        
        if self.config.scoring_function == "score_math":
            entry["score"] = scoring_function(entry["answer"], groundtruth, self.dataset)
        else:
            entry["score"] = scoring_function(entry["answer"], groundtruth)
        return entry
    
    def update_score_log(self, accuracy: float) -> None:
        """更新分数日志"""
        log_entry = {
            "start": self.start,
            "end": self.end,
            "mode": self.mode,
            "token": {"prompt": get_token()[0], "completion": get_token()[1]},
            "call_count": get_call_count(),
            "accuracy": accuracy,
        }
        
        score_log_file = LOG_DIR.format(dataset=self.dataset, size=self.interval) + "/score.json"
        existing_log = load_json(score_log_file) if os.path.exists(score_log_file) else {}
        count = get_file_count(LOG_DIR, self.interval, self.dataset, exclude_score=True)

        if self.dataset not in existing_log:
            existing_log[self.dataset] = {}
        existing_log[self.dataset][str(count)] = log_entry
        save_json(score_log_file, existing_log)
    
    async def run(self) -> float:
        """运行实验并返回准确率"""
        print(f"Running {self.mode} experiment on {self.dataset} dataset from index {self.start} to {self.end}")
        
        # 加载测试集
        testset = load_data(self.dataset, "test")[self.start:self.end]
        results = await self.gather_results(testset)

        # 构建结果
        if self.mode == "atom":
            json_obj = [self.construct_entry(result, data) for result, data in zip(results, testset)]
        else:
            json_obj = [self.construct_entry_baseline(result, data) for result, data in zip(results, testset)]
        accuracy = sum(entry["score"] for entry in json_obj) / len(json_obj)

        # 保存结果
        log_file = get_next_log_file(LOG_DIR, self.interval, self.dataset)
        save_json(log_file, json_obj)
        
        # 更新分数日志
        self.update_score_log(accuracy)

        # 打印结果摘要
        print(f"Unsolved: {round((1-accuracy) * len(json_obj))}")
        print(f"Accuracy: {accuracy:.4f}")
        print(f"Time taken: {duration_formatter(time.time() - self.timestamp)}")
        
        return accuracy


async def optimize_dataset(dataset: str, model: str, start: int = 0, end: int = -1):
    """优化数据集中的问题并保存到新文件"""
    print(f"Optimizing {dataset} dataset questions from index {start} to {end}")
    timestamp = time.time()
    
    # 设置模型和模块
    set_model(model)
    config = DATASET_CONFIGS[dataset]
    set_module(config.module_type)
    
    # 加载测试集
    testset = load_data(dataset, "test")[start:None if end == -1 else end]
    question_key = config.question_key
    if isinstance(question_key, list):
        question_key = question_key[0]
    
    # 创建任务
    async def process_item(item):
        try:
            if config.requires_context():
                from experiment.prompter.multihop import contexts
                optimized_question = await plugin(item[question_key], contexts(item, dataset))
            else:
                optimized_question = await plugin(item[question_key])
                
            # 创建新条目
            new_item = item.copy()
            new_item["original_question"] = item[question_key]
            new_item[question_key] = optimized_question
            return new_item
        except Exception as e:
            print(f"Error processing item: {e}")
            return item  # 出错时返回原始条目
    
    # 并行处理所有条目
    tasks = [process_item(item) for item in testset]
    optimized_data = await tqdm.gather(*tasks, desc=f"Optimizing {dataset} questions")
    
    # 确保输出目录存在
    os.makedirs(f"experiment/data/{dataset}", exist_ok=True)
    
    # 保存优化后的数据集
    output_path = f"experiment/data/{dataset}/contracted.json"
    save_json(output_path, optimized_data)
    
    elapsed_time = time.time() - timestamp
    print(f"Optimized dataset saved to {output_path}")
    print(f"Time taken: {duration_formatter(elapsed_time)}")
    
    return optimized_data

async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='Run experiments on various datasets')
    parser.add_argument('--dataset', type=str, default='mmlu', 
                        choices=list(DATASET_CONFIGS.keys()),
                        help='Dataset to run experiment on')
    parser.add_argument('--start', type=int, default=0, 
                        help='Start index of the dataset')
    parser.add_argument('--end', type=int, default=2, 
                        help='End index of the dataset (-1 for all)')
    parser.add_argument('--model', type=str, default='gpt-4o-mini',
                        help='Model to use for the experiment')
    parser.add_argument('--mode', type=str, default='atom',
                        help='Mode: atom (standard experiment) or plugin (generate contracted dataset) or baselines (cot, sf, cot_sc, ar)')
    
    args = parser.parse_args()
    
    if args.mode == 'plugin':
        # 运行插件流程
        await optimize_dataset(
            dataset=args.dataset,
            model=args.model,
            start=args.start,
            end=args.end
        )
    elif args.mode == 'atom':
        # 运行常规实验
        runner = ExperimentRunner(
            dataset=args.dataset,
            model=args.model,
            start=args.start,
            end=args.end,
            mode=args.mode
        )
        await runner.run()
    elif args.mode in ["cot", "sf", "ar", "cot_sc"]:
        # baselines
        runner = ExperimentRunner(
            dataset=args.dataset,
            model=args.model,
            start=args.start,
            end=args.end,
            mode=args.mode
        )
        await runner.run()
    else:
        raise ValueError(f"Invalid mode: {args.mode}")

if __name__ == "__main__":
    asyncio.run(main())
