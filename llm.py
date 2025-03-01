import random
import asyncio
import openai
import httpx
from apikey import url, api_key
from functools import lru_cache

transport = httpx.AsyncHTTPTransport(local_address="192.168.1.2")
direct_client = httpx.AsyncClient(
    transport=transport,
    proxies=None,
    verify=False
)
model_name = None

class DirectHttpClient(openai.AsyncClient):
    def __init__(self, **kwargs):
        kwargs['http_client'] = direct_client
        super().__init__(**kwargs)

if isinstance(api_key, list):
    clients = [openai.AsyncClient(base_url=url, api_key=key) for key in api_key]
else:
    clients = [openai.AsyncClient(base_url=url, api_key=api_key)]

MAX_RETRIES = 3
total_prompt_tokens, total_completion_tokens, call_count, cost = 0, 0, 0, 0
current_prompt_tokens, current_completion_tokens = 0, 0

def set_model(model):
    global model_name
    model_name = model

async def gen(msg, model=None, temperature=None, response_format="json_object"):
    global call_count, cost, current_prompt_tokens, current_completion_tokens, model_name
    if not model:
        model = model_name
    client = random.choice(clients)
    errors = []
    call_count += 1

    DEFAULT_RETRY_AFTER = random.uniform(0.1, 2)
    for retry in range(MAX_RETRIES):
        try:
            async with asyncio.timeout(120 * 2):
                if model == "o3-mini":
                    response = await client.chat.completions.create(
                        model=model,
                        messages=[
                            {"role": "user", "content": msg},
                        ],
                        # temperature=temperature,
                        stop=None,
                        # max_tokens=8192,
                        response_format={"type": response_format}
                    )
                else:
                    response = await client.chat.completions.create(
                        model=model,
                        messages=[
                            {"role": "user", "content": msg},
                        ],
                        temperature=temperature,
                        stop=None,
                        max_tokens=8192,
                        response_format={"type": response_format}
                    )
                content = response.choices[0].message.content
                
                usage = response.usage
                current_prompt_tokens = usage.prompt_tokens
                current_completion_tokens = usage.completion_tokens
                update_token()
                
                return content
        except asyncio.TimeoutError:
            errors.append("Request timeout")
        except openai.RateLimitError:
            errors.append("Rate limit error")
        except openai.APIError as e:
            errors.append(f"API error: {str(e)}")
        except Exception as e:
            errors.append(f"Error: {type(e).__name__}, {str(e)}")
        
        await asyncio.sleep(DEFAULT_RETRY_AFTER * (2 ** retry))

    print(f"Error log: {errors}")

# 其他辅助函数保持不变
@lru_cache(maxsize=None)
def get_session_cost(model_name, prompt_tokens, completion_tokens):
    cost_map = {
        "gpt-3.5-turbo": (0.5, 1.5),
        "gpt-4o": (10, 30),
        "gpt-4o-mini": (0.15, 0.6),
        "o1": (15, 60),
        "claude-3-5-sonnet": (3, 15),
        "claude-3-haiku": (0.25, 1.25),
        "llama-3.1-8b": (2, 2),
    }

    for key, (prompt_cost, completion_cost) in cost_map.items():
        if key in model_name:
            cost = (prompt_tokens * prompt_cost + completion_tokens * completion_cost) / 1e6
            return cost if "gpt" not in key else cost * 2.5

    return -1

def get_cost():
    return cost

def update_token():
    global total_prompt_tokens, total_completion_tokens, current_completion_tokens, current_prompt_tokens
    total_prompt_tokens += current_prompt_tokens
    total_completion_tokens += current_completion_tokens

def reset_token():
    global total_prompt_tokens, total_completion_tokens, call_count
    total_prompt_tokens = 0
    total_completion_tokens = 0
    call_count = 0

def get_token():
    return total_prompt_tokens, total_completion_tokens

def get_call_count():
    return call_count