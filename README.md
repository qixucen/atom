# Atom of Thoughts (AoT)

This is the official implementation of the paper [Atom of Thoughts for Markov LLM Test-Time Scaling](https://arxiv.org/abs/xxx.xxxx).

## Overview

AoT is a novel reasoning framework that progressively decomposes complex problems into atomic units while maintaining Markov property. The key features include:

- **Markov Property**: Each state transition depends only on the current state, eliminating the need to maintain historical information
- **Plug-in Enhancement**: Can be integrated with existing test-time scaling methods to improve their performance
- **Resource Efficiency**: Focuses computational resources on effective reasoning rather than processing historical information

## Quick Start

Run experiments on different datasets:

```bash
python main.py --dataset math --start 0 --end 10 --model gpt-4o-mini
```

Supported datasets:

- MATH
- GSM8K  
- BBH
- MMLU
- HotpotQA
- LongBench

## API Configuration Setup

Before using the Atom of Thoughts (AoT) framework, you need to set up your API key and URL:

1. Create an `apikey.py` file in the project root directory with the following format:

```
url = "https://api.openai.com/v1"  # Replace with your API endpoint
api_key = [
    "your-api-key-here",  # Replace with your actual API key
    # You can add multiple API keys as backups
]
```

## Citation

```bibtex
@article{teng2024atom,
  title={Atom of Thoughts for Markov LLM Test-Time Scaling},
  author={Teng, Fengwei and Yu, Zhaoyang and Shi, Quan and Zhang, Jiayi and Wu, Chenglin and Luo, Yuyu},
  journal={arXiv preprint arXiv:2502.12018},
  year={2025}
}
```
