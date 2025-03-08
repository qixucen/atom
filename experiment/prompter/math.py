from experiment.utils import check_json

def direct(question: str):
    instruction = """
        You are a precise math problem solver. Solve the given math problem step by step:

        QUESTION: {question}
        
        Please extend your chain of thought as much as possible; the longer the chain of thought, the better.
        
        You can freely reason in your response, but please enclose the final answer within <answer></answer> tags (pure number without units and explanations)
    """
    prompt = instruction.format(question=question)
    return prompt

def multistep(question: str):
    instruction = """
        You are a precise math problem solver. Solve the given math problem step by step:

        QUESTION: {question}
        
        Please extend your chain of thought as much as possible; the longer the chain of thought, the better.
        
        You can freely reason in your response, but please enclose the final answer within <answer></answer> tags (pure number without units and explanations)
    """
    prompt = instruction.format(question=question)
    return prompt

def label(question: str, trajectory: str, answer: str):
    instruction = """
        You are tasked with breaking down a math problem reasoning process into sub-questions.

        Original Question: {question}
        Complete Reasoning Process: {trajectory}

        Instructions:
        1. Break down the reasoning process into a series of sub-questions
        2. Each sub-question should:
           - Be written in interrogative form
           - Have a clear numerical answer
           - List its other sub-questions' indexes it depends (0-based, can be an empty list)
        3. Dependencies are defined as information needed to answer the current sub-question that:
           - Does NOT come directly from the original question
           - MUST come from the answers of previous sub-questions
    """
    formatter = """
        Format your response as the following JSON object:
        {{
            "sub-questions": [
                {{
                    "description": "<clear interrogative question>",
                    "answer": <numerical value without units>,
                    "depend": [<indices of prerequisite sub-questions>]
                }},
                ...
            ],
            "answer": {answer}
        }}
    """
    return (instruction + formatter).format(question=question, trajectory=trajectory, answer=answer)

def contract(question: str, decompose_result: dict, independent=None, dependent=None):
    instruction = """
        You are a math problem solver specializing in optimizing step-by-step reasoning processes. Your task is to optimize the existing reasoning trajectory into a more efficient, single self-contained question.
        
        For the original question: {question}
        
        Here are step-by-step reasoning process:
        {response}
        
        {sub_questions}
        
        Here are explanations of key concepts:
        1. self-contained: The optimized question must be solvable independently, without relying on any external information
        2. efficient: The optimized question must be simpler than the original, requiring fewer reasoning steps (these steps are reduced because some solved independent sub-problems become known conditions in the optimized question or are excluded as incorrect explorations)
        
        You can freely reason in your response, but please enclose the your optimized question within <question></question> tags
    """
    independent_sub_questions = """
        The following sub-questions and their answers can serve as known conditions:
        {independent}
    """
    dependent_sub_questions = """
        The descriptions of the following questions can be used to form the description of the optimized problem:
        {dependent}    
    """
    answer = decompose_result["answer"]
    
    if independent not in [None, []]:
        for sub_q in independent:
            sub_q.pop("depend", None)
    if dependent is not None:
        for sub_q in dependent:
            sub_q.pop("depend", None)
    
    if independent not in [None, []]:
        sub_questions = independent_sub_questions.format(independent=independent) + dependent_sub_questions.format(dependent=dependent)
    elif independent is not None:
        sub_questions = independent_sub_questions.format(independent=independent)
    else:
        sub_questions = ""
    return instruction.format(question=question, answer=answer, response=decompose_result["response"], sub_questions=sub_questions)

def ensemble(question: str, solutions: list):
    instruction = """
        You are a precise math problem solver. Compare then synthesize the best answer from multiple solutions to solve the following question.

        QUESTION: {question}

        SOLUTIONS:
        {solutions}

        Please extend your chain of thought as much as possible; the longer the chain of thought, the better.

        You can freely reason in your response, but please enclose the final answer within <answer></answer> tags (pure number without units and explanations)
    """
    
    solutions_str = ""
    for i, solution in enumerate(solutions):
        solutions_str += f"solution {i}: {solution}\n"
    prompt = instruction.format(question=question, solutions=solutions_str)
    return prompt

def cot(question: str):
    instruction = """
        Let's think step by step:
        {question}
        
        Enclose the final answer within <answer></answer> tags (pure number without units and explanations)
    """
    prompt = instruction.format(question=question)
    return prompt

def sf(question: str, trajectory: dict):
    instruction = """
        Let': think step by step:
        {question}
        
        Here is the reasoning process of this question:
        {trajectory}
        You can keep the same answer as the reasoning process, or you can improve the reasoning process to get a better answer.
        
        You can freely reason in your response, but please enclose the final answer within <answer></answer> tags (pure number without units and explanations)
    """
    prompt = instruction.format(question=question, trajectory=trajectory)
    return prompt

def sc(question: str, answers: list):
    instruction = """
        You are a precise math problem solver. Marginalize the final answer from the following answers.

        QUESTION: {question}

        ANSWERS:
        {answers}

        You can freely reason in your response, but please mark the final answer with <answer></answer> tags (pure number without units and explanations)
    """
    answers_str = ""
    for i, answer in enumerate(answers):
        answers_str += f"answer {i}: {answer}\n"
    prompt = instruction.format(question=question, answers=answers_str)
    return prompt

def ar(question: str):
    instruction = """
        Let's think step by step:
        {question}
        
        Recall three examples of math problems that are relevant to the initial problem. Note that your problems should be distinct from each other and from the initial problem (e.g., involving different numbers and names). For each problem:
        - After "Q: ", describe the problem
        - After "A: ", explain the solution give the answer (pure number without units and explanations)
        
        Solve the Initial Problem, say "Let's solve the following math problem." Then enclose the final answer within <answer></answer> tags (pure number without units and explanations)
    """
    prompt = instruction.format(question=question)
    return prompt

# utilization
def check(name: str, result, *args):
    def is_number(x):
        try:
            float(x)
            return True
        except:
            return False
    
    if not isinstance(result, dict):
        return False

    if name in ["cot", "direct", "multistep", "ensemble", "sf", "sc", "ar"]:
        if not check_json(result, ["answer"]):
            return False
        if not isinstance(result["answer"], (str, int, float)):
            return False
        if not is_number(result["answer"]):
            return False
    elif name == "label":
        if not check_json(result, ["sub-questions", "answer"]):
            return False
        if not is_number(result["answer"]):
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
