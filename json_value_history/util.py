import json


def pprint(o):
    print(json.dumps(o, sort_keys=True, indent=2, ensure_ascii=False))
