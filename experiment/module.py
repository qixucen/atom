from functools import wraps
from experiment.utils import (
    extract_json,
    extract_xml,
    calculate_depth,
    score_math,
    score_mc,
    score_mh,
)
from llm import gen
from experiment.prompter import math, multichoice, multihop
from contextlib import contextmanager
import asyncio

count = 0
MAX_RETRIES = 5
LABEL_RETRIES = 3
ATOM_DEPTH = 3
score = None

module = None
prompter = None
def set_module(module_name):  # math, multi-choice, multi-hop
    global module, prompter, score
    module = module_name
    if module == "math":
        prompter = math
        score = score_math
    elif module == "multi-choice":
        prompter = multichoice
        score = score_mc
    elif module == "multi-hop":
        prompter = multihop
        score = score_mh

def retry(func_name):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            global MAX_RETRIES
            retries = MAX_RETRIES
            while retries >= 0:
                prompt = getattr(prompter, func_name)(*args, **kwargs)
                
                if module == "multi-hop" and func_name != "contract":
                    response = await gen(prompt, response_format="json_object")
                    result = extract_json(response)
                    result["response"] = response
                else:
                    if func_name == "label":
                        response = await gen(prompt, response_format="json_object")
                        result = extract_json(response)
                    else:
                        response = await gen(prompt, response_format="text")
                        result = extract_xml(response)
                        if isinstance(result, dict):
                            result["response"] = response
                
                if prompter.check(func_name, result):
                    return result
                retries -= 1
            
            global count
            if MAX_RETRIES > 1:
                count += 1
            if count > 300:
                raise Exception("Too many failures")
            return result if isinstance(result, dict) else {}
        return wrapper
    return decorator

async def decompose(question: str, **kwargs):
    retries = LABEL_RETRIES
    if module == "multi-hop":
        if "contexts" not in kwargs:
            raise Exception("Multi-hop must have contexts")
        contexts = kwargs["contexts"]
        multistep_result = await multistep(question, contexts)
        while retries > 0:
            label_result = await label(question, multistep_result)
            try:
                if len(label_result["sub-questions"]) != len(multistep_result["sub-questions"]):
                    retries -= 1
                    continue
                calculate_depth(label_result["sub-questions"])
                break
            except:
                retries -= 1
                continue
        for step, note in zip(multistep_result["sub-questions"], label_result["sub-questions"]):
            step["depend"] = note["depend"]
        return multistep_result
    else:
        multistep_result = await multistep(question)
        while retries > 0:
            result = await label(question, multistep_result["response"], multistep_result["answer"])
            try:
                calculate_depth(result["sub-questions"])
                result["response"] = multistep_result["response"]
                break
            except:
                retries -= 1
                continue
        return result

async def merging(question: str, decompose_result: dict, independent_subqs: list, dependent_subqs: list, **kwargs):
    contract_args = (
        (question, decompose_result, independent_subqs, dependent_subqs, kwargs["contexts"])
        if module == "multi-hop"
        else (question, decompose_result, independent_subqs, dependent_subqs)
    )
    contractd_result = await contract(*contract_args)
    
    # Extract thought process and optimized question
    contractd_thought = contractd_result.get("response", "")
    contractd_question = contractd_result.get("question", "")
    
    # Solve the optimized question
    direct_args = (
        (contractd_question, contractd_result.get("context", kwargs.get("contexts")))
        if module == "multi-hop"
        else (contractd_question,)
    )
    contraction_result = await direct(*direct_args)
    
    return contractd_thought, contractd_question, contraction_result

async def atom(question: str, contexts: str=None, direct_result=None, decompose_result=None, depth=None, log=None):
    # Initialize logging
    log = log if log else {}
    index = len(log)
    if depth == 0:
        return None, log
    log[index] = {}
    
    # Get results from different approaches
    direct_args = (question, contexts) if module == "multi-hop" else (question,)
    direct_result = direct_result if direct_result else await direct(*direct_args)
    
    decompose_args = {"contexts": contexts} if module == "multi-hop" else {}
    decompose_result = decompose_result if decompose_result else await decompose(question, **decompose_args)
    
    # Set recursion depth
    depth = depth if depth else min(ATOM_DEPTH, calculate_depth(decompose_result["sub-questions"]))
    
    # Separate independent and dependent sub-questions
    independent_subqs = [sub_q for sub_q in decompose_result["sub-questions"] if len(sub_q["depend"]) == 0]
    dependent_subqs = [sub_q for sub_q in decompose_result["sub-questions"] if sub_q not in independent_subqs]
    
    # Get contraction result
    merging_args = {
        "question": question,
        "decompose_result": decompose_result,
        "independent_subqs": independent_subqs,
        "dependent_subqs": dependent_subqs
    }
    if module == "multi-hop":
        merging_args["contexts"] = contexts
        
    contractd_thought, contractd_question, contraction_result = await merging(**merging_args)
    
    # Update contraction result with additional information
    contraction_result["contraction_thought"] = contractd_thought
    contraction_result["sub-questions"] = independent_subqs + [{
        "description": contractd_question,
        "response": contraction_result.get("response", ""),
        "answer": contraction_result.get("answer", ""),
        "depend": []
    }]
    
    # Get ensemble result
    ensemble_args = [question]
    ensemble_args.append([direct_result["response"], decompose_result["response"], contraction_result["response"]])
    if module == "multi-hop":
        ensemble_args.append(contexts)
    
    ensemble_result = await ensemble(*ensemble_args)
    ensemble_answer = ensemble_result.get("answer", "")
    
    # Calculate scores
    scores = []
    if all(result["answer"] == ensemble_answer for result in [direct_result, decompose_result, contraction_result]):
        scores = [1, 1, 1]
    else:
        for result in [direct_result, decompose_result, contraction_result]:
            scores.append(score(result["answer"], ensemble_answer))
    
    # Update log with results
    log[index].update({
        "scores": scores,
        "direct": direct_result,
        "decompose": decompose_result,
        "contract": contraction_result
    })
    
    # Select best method based on scores
    methods = {
        2: ("contract", contraction_result),
        0: ("direct", direct_result),
        1: ("decompose", decompose_result),
        -1: ("ensemble", ensemble_result)
    }
    
    max_score_index = scores.index(max(scores))
    method, result = methods.get(max_score_index, methods[-1])
    
    log[index]["method"] = method
    
    # Return appropriate result format
    if index == 0:
        return {
            "method": method,
            "response": result.get("response"),
            "answer": result.get("answer"),
        }, log
    return result, log

async def plugin(question: str, contexts: str=None, sample_num: int=3):
    # Create tasks for parallel execution
    async def process_sample():
        # Get decompose result
        decompose_args = {"contexts": contexts} if module == "multi-hop" else {}
        decompose_result = await decompose(question, **decompose_args)
        
        # Separate independent and dependent sub-questions
        independent_subqs = [sub_q for sub_q in decompose_result["sub-questions"] if len(sub_q["depend"]) == 0]
        dependent_subqs = [sub_q for sub_q in decompose_result["sub-questions"] if sub_q not in independent_subqs]
        
        # Get contraction result
        merging_args = {
            "question": question,
            "decompose_result": decompose_result,
            "independent_subqs": independent_subqs,
            "dependent_subqs": dependent_subqs
        }
        if module == "multi-hop":
            merging_args["contexts"] = contexts
            
        contractd_thought, contractd_question, contraction_result = await merging(**merging_args)
        
        return {
            "decompose_result": decompose_result,
            "contractd_thought": contractd_thought,
            "contractd_question": contractd_question,
            "contraction_result": contraction_result
        }
    
    # Execute all samples in parallel
    tasks = [process_sample() for _ in range(sample_num)]
    all_results = await asyncio.gather(*tasks)
    
    # Get direct result for original question
    direct_args = (question, contexts) if module == "multi-hop" else (question,)
    direct_result = await direct(*direct_args)
    
    # Get ensemble result from all contracted results plus direct result
    all_responses = [direct_result["response"]] + [r["contraction_result"]["response"] for r in all_results]
    ensemble_args = [question, all_responses]
    if module == "multi-hop":
        ensemble_args.append(contexts)
    
    ensemble_result = await ensemble(*ensemble_args)
    ensemble_answer = ensemble_result.get("answer", "")
    
    # Calculate scores for each contracted result
    scores = []
    token_counts = []
    
    for result in all_results:
        contraction_result = result["contraction_result"]
        # Calculate score compared to ensemble answer
        scores.append(score(contraction_result["answer"], ensemble_answer))
        
        # Estimate token count for the response
        token_counts.append(len(contraction_result.get("response", "").split()))
    
    # Find the best result(s) - those with the highest score
    max_score = max(scores)
    best_indices = [i for i, s in enumerate(scores) if s == max_score]
    
    # Among the best results, find the one with the lowest token count
    best_index = min(best_indices, key=lambda i: token_counts[i])
    
    # Return the best result
    best_result = all_results[best_index]
    return best_result["contractd_question"]

async def sf(question: str, contexts: str=None):
    cot_trajectory = await cot(question, contexts)
    return await sf_(question, cot_trajectory)

async def cot_sc(question: str, contexts: str=None, n: int=5):
    cot_trajectorise = await asyncio.gather(
        *[cot(question, contexts) for _ in range(n)]
    )
    return await sc(question, cot_trajectorise)

@retry("direct")
async def direct(question: str, contexts: str=None):
    if isinstance(question, (list, tuple)):
        question = ''.join(map(str, question))
    pass

@retry("multistep")
async def multistep(question: str, contexts: str=None):
    pass

@retry("label")
async def label(question: str, sub_questions: str, answer: str=None):
    pass

@retry("contract")
async def contract(question: str, sub_result: dict, independent_subqs: list, dependent_subqs: list, contexts: str=None):
    pass

@retry("ensemble")
async def ensemble(question: str, results: list, contexts: str=None):
    pass

@retry("cot")
async def cot(question: str, contexts: str=None):
    pass

@retry("ar")
async def ar(question: str, contexts: str=None):
    pass

@retry("sc")
async def sc(question: str, contexts: str=None):
    pass

@retry("sf")
async def sf_(question: str, contexts: str=None):
    pass

@contextmanager
def temporary_retries(value):
    global MAX_RETRIES
    original = MAX_RETRIES
    MAX_RETRIES = value
    try:
        yield
    finally:
        MAX_RETRIES = original