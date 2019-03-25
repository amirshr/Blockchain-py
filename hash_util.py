import json
import hashlib as hl


def hash_block(block):
    return hl.sha256(json.dumps(block, sort_keys=True).encode()).hexdigest()


def hash_string_256(string):
    return hl.sha256(string).hexdigest()
