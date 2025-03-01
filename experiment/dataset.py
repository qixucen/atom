import json
import os
from functools import lru_cache

@lru_cache(maxsize=None)
def load_data(data_name, split="test"):
    # Determine file path
    file_path = f"experiment/data/{data_name}/{split}.json"
    
    # Load data from JSON file
    if os.path.exists(file_path):
        print(file_path)
        with open(file_path, 'r') as f:
            data = json.load(f)
    else:
        raise FileNotFoundError(f"Could not load {data_name} {split} locally")
    
    return data