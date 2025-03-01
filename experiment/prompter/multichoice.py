from experiment.utils import check_json

def direct(question: str):
    instruction = """
        You are a precise multiple choice question solver. Select the most correct option for the given question:

        QUESTION: {question}
        
        Please extend your chain of thought as much as possible; the longer the chain of thought, the better.
        
        You can freely reason in your response, but please enclose your final option within <answer>single letter of your chosen option</answer> tags.
    """
    prompt = instruction.format(
        question=question,
    )
    return prompt

def multistep(question: str):
    instruction = """
        You are a precise multiple choice question solver. Break down complex questions into simpler sub-questions to select the most correct option:

        QUESTION: {question}
        
        Please extend your chain of thought as much as possible; the longer the chain of thought, the better.
        
        You can freely reason in your response, but please
        - Continuously raise sub-questions until the problem can be solved.
        - enclose your final option within <answer>single letter of your chosen option</answer> tags.
    """
    prompt = instruction.format(
        question=question,
    )
    return prompt

def label(question: str, trajectory: str, answer: str):
    instruction = """
        You are tasked with breaking down a multiple choice question reasoning process into sub-questions.

        Original Question: {question}
        Complete Reasoning Process: {trajectory}

        Instructions:
        1. Break down the reasoning process into a series of sub-questions
        2. Each sub-question should:
           - Be written in interrogative form
           - Have a clear answer
           - List its other sub-questions' indexes it depends (0-based, can be an empty list)
        3. Dependencies are defined as information needed to answer the current sub-question that:
           - Does NOT come directly from the original question
           - MUST come from the answers of previous sub-questions
    """
    formatter = """
        Format your response as the following JSON object:
        {{
            "thought": "<the thought process of how to step by step propose the sub-questions until the answer of the original question in the given reasoning process is obtained>",
            "sub-questions": [
                {{
                    "description": "<the description of the sub-question>", 
                    "answer": <the answer to the sub-question>,
                    "depend": [<indices of the dependent sub-questions>, ...]
                }}
            ],
            "answer": "{answer}"
        }}
    """
    return (instruction + formatter).format(question=question, trajectory=trajectory, answer=answer)

def contract(question: str, decompose_result: dict, independent: list, dependent: list):
    instruction = """
        You are a multiple choice question solver specializing in optimizing step-by-step reasoning processes. Your task is to optimize the existing reasoning trajectory into a more efficient, single self-contained question.
        
        For the original question: {question}
        
        Here are step-by-step reasoning process:
        {response}
        
        {sub_questions}
        
        Here are explanations of key concepts:
        1. self-contained: The optimized question must be solvable independently, without relying on any external information
        2. efficient: The optimized question must be simpler than the original, requiring fewer reasoning steps and having a clearer reasoning process (these steps are reduced because some solved sub-problems become known conditions in the optimized question or are excluded as incorrect explorations)
        
        Note: Since this is a multiple choice question, the optimized question must completely retain the options of the original question.
        
        You can freely reason in your response, but please enclose the your optimized question within <question></question> tags
    """
    sub_questions = """
        The following sub-questions and their answers can serve as known conditions:
        {independent}

        The descriptions of the following questions can be used to form the description of the optimized problem:
        {dependent}
        
        """
    answer = decompose_result["answer"]
    for sub_q in independent:
        sub_q.pop("depend", None)
    for sub_q in dependent:
        sub_q.pop("depend", None)
        
    sub_questions = sub_questions.format(independent=independent, dependent=dependent)
    return instruction.format(question=question, answer=answer, response=decompose_result["response"], sub_questions=sub_questions)

def ensemble(question: str, solutions: list):
    instruction = """
        You are a precise multiple choice question solver. Compare then synthesize the best answer from multiple solutions to select the most correct option:

        QUESTION: {question}

        SOLUTIONS:
        {solutions}
        
        Extend your chain of thought as much as possible; the longer the chain of thought, the better.

        You can freely reason in your response, even propose new reasoning to get a better answer than all solutions, but please mark the final option with <answer>single letter of your chosen option</answer> tags
    """
    
    solutions_str = ""
    for i, solution in enumerate(solutions):
        solutions_str += f"solution {i}: {solution}\n"
    prompt = instruction.format(question=question, solutions=solutions_str)
    return prompt

def check_answer(answer):
    if not isinstance(answer, str):
        return False
    if len(answer) == 1 and answer.isalpha():
        return True
    if len(answer) == 3 and answer.startswith('(') and answer.endswith(')'):
        return True
    return False

def check(name: str, result: dict, *args):
    if name in ["cot", "direct", "multistep", "ensemble"]:
        if not check_json(result, ["answer"]):
            return False
        if not check_answer(result["answer"]):
            return False
    elif name == "label":
        if not check_json(result, ["sub-questions", "answer"]):
            return False
        if not check_answer(result["answer"]):
            return False
        for sub_q in result["sub-questions"]:
            if not check_json(sub_q, ["description", "answer", "depend"]):
                return False
            if not isinstance(sub_q["depend"], list):
                return False
    elif name == "contract":
        if not check_json(result, ["question"]):
            return False
    return True
