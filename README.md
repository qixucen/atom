# Atom of Thoughts (AoT)

This is the official implementation of the paper [Atom of Thoughts for Markov LLM Test-Time Scaling](https://arxiv.org/abs/2502.12018).

## Overview

Atom of Thoughts (AoT) is a revolutionary reasoning framework that progressively decomposes complex problems into atomic units while maintaining Markov property. This approach significantly enhances large language models' performance on reasoning tasks while reducing computational waste.

**Key Features:**

- **Markov Property**: Each state transition depends only on the current state, eliminating the need to maintain historical information
- **Plug-in Enhancement**: Can be integrated with existing test-time scaling methods to improve their performance
- **Resource Efficiency**: Focuses computational resources on effective reasoning rather than processing historical information
- **Superior Performance**: Outperforms existing methods across multiple benchmarks, enabling gpt-4o-mini to surpass o3-mini by 3.4% and DeepSeek-R1 by 10.6% on HotpotQA

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
