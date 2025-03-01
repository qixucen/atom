from experiment.utils import check_json

def cot(question: str, contexts: str = None):
    instruction = """
        Please solve the multi-hop question below based on the following contexts step by step:

        QUESTION: 
        {question}

        CONTEXTS: 
        {contexts}
    """
    formatter = """
        
        Provide your response in this JSON format:
        {{
            "thought": "Give your step-by-step reasoning process",
            "answer": "Your precise answer"
        }}
    """
    prompt = (instruction + formatter).format(question=question, contexts=contexts)
    return prompt

def direct(question: str, contexts: str = None):
    instruction = """
        You are a precise question-answering solver. Answer the following question using only the provided contexts:

        QUESTION: 
        {question}

        CONTEXTS: 
        {contexts}

        INSTRUCTIONS:
        1. Answer Selection Rules:
           a) Use ONLY information from the given contexts
           b) For yes/no questions: Answer with exactly "yes" or "no"
           c) For other questions: Extract a precise answer that is:
              - CONTINUOUS: Must be an unbroken segment from the text
              - EXACT: Use the original text without modifications
              - MINIMAL: Include only the essential information

        2. Supporting Evidence:
           - Select ALL relevant sentences that lead to your answer
           - Include complete context when needed
           - You may use ellipsis (...) to connect relevant parts of long sentences
           
           EXAMPLE:
           Question: "Where was the rock band Letters to Cleo formed?"
           Supporting Sentences: 
           ✓ Good: "Letters to Cleo are an alternative rock band from Boston, Massachusetts..."
           × Bad: "The band was formed in Boston, Massachusetts" (lacks subject reference)

        3. Answer Extraction Guidelines:
           a) CONTINUOUS text only:
              Question: "Where is BTS from?"
              Context: "BTS is a South Korean boy band formed in Seoul"
              ✓ CORRECT: "Seoul"
              × WRONG: "Seoul, South Korea" (combining segments)

           b) EXACT text:
              Question: "When was Nixon president?"
              Context: "Nixon was president from 1969 until 1974"
              ✓ CORRECT: "1969 until 1974"
              × WRONG: "1969-1974" (modified text)

           c) MINIMAL answer:
              Question: "What was Tesla's profession?"
              Context: "Nikola Tesla was a brilliant Serbian-American inventor"
              ✓ CORRECT: "inventor"
              × WRONG: "brilliant Serbian-American inventor" (includes unnecessary details)

        4. Important:
           - Handle unclear questions by focusing on the main intent
           - Avoid common pitfalls like combining disconnected information
           - Prioritize precision over completeness
        
        5. Robustness:
            Sometimes the question may have some errors, leading to a situation where there is actually no answer in the context. I hope you can infer what the questioner is actually asking and then respond according to the above process.
    """
    
    formatter = """
    Provide your response in this JSON format:
    {{
        "question": {question},
        "thought": "give your step by step thought process here",
        "supporting_sentences": [
            "Include ALL sentences needed to justify your answer",
            "Use ... for long sentences when appropriate"
        ],
        "answer": "Your precise answer following the instructions above" or "none" if no answer can be found
    }}
    """
    prompt = (instruction + formatter).format(question=question, contexts=contexts)
    return prompt

def multistep(question: str, contexts: str = None):
    instruction = """
        You are a precise question-answering solver. Breaks down multi-hop questions into single-hop sub-questions to answer the following question using only the provided contexts:

        QUESTION: 
        {question}

        CONTEXTS: 
        {contexts}

        INSTRUCTIONS:
        1. Answer Selection Rules:
           a) Use ONLY information from the given contexts
           b) For yes/no questions: Answer with exactly "yes" or "no"
           c) For other questions: Extract a precise answer that is:
              - CONTINUOUS: Must be an unbroken segment from the text
              - EXACT: Use the original text without modifications
              - MINIMAL: Include only the essential information

        2. Supporting Evidence:
           - Select ALL relevant sentences that lead to your answer
           - Include complete context when needed
           - You may use ellipsis (...) to connect relevant parts of long sentences
           
           EXAMPLE:
           Question: "Where was the rock band Letters to Cleo formed?"
           Supporting Sentences: 
           ✓ Good: "Letters to Cleo are an alternative rock band from Boston, Massachusetts..."
           × Bad: "The band was formed in Boston, Massachusetts" (lacks subject reference)

        3. Answer Extraction Guidelines:
           a) CONTINUOUS text only:
              Question: "Where is BTS from?"
              Context: "BTS is a South Korean boy band formed in Seoul"
              ✓ CORRECT: "Seoul"
              × WRONG: "Seoul, South Korea" (combining segments)

           b) EXACT text:
              Question: "When was Nixon president?"
              Context: "Nixon was president from 1969 until 1974"
              ✓ CORRECT: "1969 until 1974"
              × WRONG: "1969-1974" (modified text)

           c) MINIMAL answer:
              Question: "What was Tesla's profession?"
              Context: "Nikola Tesla was a brilliant Serbian-American inventor"
              ✓ CORRECT: "inventor"
              × WRONG: "brilliant Serbian-American inventor" (includes unnecessary details)

        4. Important:
           - Handle unclear questions by focusing on the main intent
           - Avoid common pitfalls like combining disconnected information
           - Prioritize precision over completeness
           
        5. Robustness:
            Sometimes the question may have some errors, leading to a situation where there is actually no answer in the context. I hope you can infer what the questioner is actually asking and then respond according to the above process.
    """
    
    formatter = """
    Provide your response in this JSON format:
    {{
        "question": {question},
        "thought": "give your step by step thought process here",
        "sub-questions": [
            {{
                "description": "the description of the sub-question",
                "supporting_sentences": [
                    "Include ALL sentences needed to justify your answer to this sub-question",
                    "Use ... for long sentences when appropriate"
                ],
                "answer": "Answer to this sub-question"
            }},
            ...more sub-questions as needed
        ],
        "conclusion": "Explain how the sub-answers combine to answer the main question",
        "answer": "Your precise answer to the main question" or "none" if no answer can be found
    }}
    """
    prompt = (instruction + formatter).format(question=question, contexts=contexts)
    return prompt

def label(question: str, result: dict):
    instruction = f"""
        For the original question: {question},
        We have broken it down into the following sub-questions:
        SUB-QUESTIONS:
        {result["sub-questions"]}
        And obtained a complete reasoning process for the original question:
        {result}
        We define the dependency relationship between sub-questions as: which information in the current sub-question description does not come directly from the original question and contexts, but from the results of other sub-questions.
        
        You are a question answering expert specializing in analyzing the dependency relationships between these sub-questions. Please return a JSON object that expresses a complete reasoning trajectory for the original question, including the question, answer, supporting evidence, and dependency relationships of each sub-question. The dependency relationships are represented by the indices of the dependent sub-questions in SUB-QUESTIONS, starting from zero.
    """
    
    formatter = '''
        Format your response as the following JSON object:
        {
            "thought": "Give your thought process here",
            "sub-questions": [
'''
    for i, sub_q in enumerate(result["sub-questions"]):
        formatter += f'''                {{"description": "{sub_q["description"]}", "answer": "{sub_q["answer"]}", "supporting_sentences": {sub_q["supporting_sentences"]}, "depend": [<indices of the dependent sub-questions>, ...]}}'''
        if i != len(result["sub-questions"]) - 1:
            formatter += ",\n"
        else:
            formatter += "\n            ]\n        }"
    
    return instruction + formatter

def contract(question: str, decompose_result: dict, independent: list, dependent: list, contexts: str = None):
    instruction = """
        You are a precise question-answering solver specializing in optimizing step-by-step reasoning processes. Your task is to optimize the existing reasoning trajectory into a more efficient, single-hop and self-contained question.
        
        For the original question: {question}
        
        Here are the contexts that can be used to answer the original question (but only some of them can be directly used to solve the question):
        {contexts}
        
        Here are step-by-step reasoning process:
        {response}
        
        {sub_questions}
        
        Here are explanations of key concepts:
        1. self-contained: The optimized question must be solvable independently, without relying on any external information
        2. efficient: The optimized question must be simpler than the original, requiring fewer reasoning steps and having a clearer reasoning process (these steps are reduced because some solved sub-problems become known conditions in the optimized question or are excluded as incorrect explorations)
        
        You can freely reason in your response, but please enclose the your optimized question within <question></question> tags, and enclose the complete context needed to answer the optimized question within <context></context> tags
    """
    sub_questions = """
        The following sub-questions and their answers can serve as known conditions:
        {independent}

        The descriptions of the following questions can be used to form the description of the optimized problem:
        {dependent}
        """
    for sub_q in independent:
        sub_q.pop("depend", None)
    for sub_q in dependent:
        sub_q.pop("depend", None)
        
    sub_questions = sub_questions.format(independent=independent, dependent=dependent)
    return instruction.format(question=question, contexts=contexts, response=decompose_result, sub_questions=sub_questions)

def ensemble(question: str, solutions: list, contexts: str = None):
    instruction = """
        You are a precise question answering expert. Compare then synthesize the best answer from multiple solutions to solve the following question.
        
        QUESTION:
        {question}

        CONTEXTS:
        {contexts}

        SOLUTIONS:
        {solutions}

        INSTRUCTIONS:
        1. Answer Selection Rules:
           a) Use ONLY information from the given contexts
           b) For yes/no questions: Answer with exactly "yes" or "no"
           c) For other questions: Extract a precise answer that is:
              - CONTINUOUS: Must be an unbroken segment from the text
              - EXACT: Use the original text without modifications
              - MINIMAL: Include only the essential information

        2. Supporting Evidence:
           - Select ALL relevant sentences that lead to your answer
           - Include complete context when needed
           - You may use ellipsis (...) to connect relevant parts of long sentences
           
           EXAMPLE:
           Question: "Where was the rock band Letters to Cleo formed?"
           Supporting Sentences: 
           ✓ Good: "Letters to Cleo are an alternative rock band from Boston, Massachusetts..."
           × Bad: "The band was formed in Boston, Massachusetts" (lacks subject reference)

        3. Answer Extraction Guidelines:
           a) CONTINUOUS text only:
              Question: "Where is BTS from?"
              Context: "BTS is a South Korean boy band formed in Seoul"
              ✓ CORRECT: "Seoul"
              × WRONG: "Seoul, South Korea" (combining segments)

           b) EXACT text:
              Question: "When was Nixon president?"
              Context: "Nixon was president from 1969 until 1974"
              ✓ CORRECT: "1969 until 1974"
              × WRONG: "1969-1974" (modified text)

           c) MINIMAL answer:
              Question: "What was Tesla's profession?"
              Context: "Nikola Tesla was a brilliant Serbian-American inventor"
              ✓ CORRECT: "inventor"
              × WRONG: "brilliant Serbian-American inventor" (includes unnecessary details)

        4. Important:
           - Handle unclear questions by focusing on the main intent
           - Avoid common pitfalls like combining disconnected information
           - Prioritize precision over completeness
        
        5. Robustness:
            Sometimes the question may have some errors, leading to a situation where there is actually no answer in the context. I hope you can infer what the questioner is actually asking and then respond according to the above process.
    """
    
    formatter = """
        Format your response as the following JSON object:
        {{
            "question": "{question}",
            "thought": "Explain your analysis of the different results and why you chose the final answer",
            "supporting_sentences": [
                "Include ALL sentences needed to justify your answer",
                "Use ... for long sentences when appropriate"
            ],
            "answer": "The most reliable answer following the answer instructions"
        }}
    """
    
    solutions_str = ""
    for i, solution in enumerate(solutions):
        solutions_str += f"solution {i}: {solution}\n"
    prompt = (instruction + formatter).format(question=question, contexts=contexts, solutions=solutions_str)
    return prompt

# utilization
def contexts(obj: dict, dataset: str):
    if dataset == "hotpotqa":
        context = []
        for i in range(len(obj["context"]["sentences"])):
            context.append(" ".join(obj["context"]["sentences"][i]))
        return context
        # return obj["context"]
    elif dataset == "longbench":
        return obj["context"]
    else:
        raise ValueError("Unknown dataset format: neither 'context' nor 'paragraphs' field found")

def check(name: str, result: dict, *args):
    if name == "cot":
        if not check_json(result, ["thought", "answer"]):
            return False
        if not isinstance(result["answer"], str) or result["answer"].lower() in ["null", "none", ""]:
            return False
    elif name == "direct":
        if not check_json(result, ["question", "thought", "supporting_sentences", "answer"]):
            return False
        if not isinstance(result["supporting_sentences"], list) or not all(isinstance(s, str) for s in result["supporting_sentences"]):
            return False
        if not isinstance(result["answer"], str) or result["answer"].lower() in ["null", "none", ""]:
            return False
    elif name == "contract":
        if not check_json(result, ["question", "context"]):
            return False
    return True
