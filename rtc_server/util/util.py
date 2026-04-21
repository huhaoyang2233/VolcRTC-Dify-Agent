import os
import json

def read_files(folder, ext=".json"):
    data = {}
    for file in os.listdir(folder):
        if file.endswith(ext):
            with open(os.path.join(folder, file), "r", encoding="utf-8") as f:
                data[file.replace(ext, "")] = json.load(f)
    return data

def assert_true(cond, msg):
    if not cond:
        raise ValueError(msg)