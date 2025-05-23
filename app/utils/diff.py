from deepdiff import DeepDiff
import json 

def diff_versions(old_data: dict, new_data: dict):
    diff_obj = DeepDiff(old_data, new_data, ignore_order=True)
    diff = json.loads(diff_obj.to_json())
    return diff
