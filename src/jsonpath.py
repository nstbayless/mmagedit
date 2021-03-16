import json
import re

rematchdict = re.compile("\.([^\.\n \[\]\"']+)")
rematchdictstr = re.compile("\.\"([^\"]*)\"")
rematcharr = re.compile("\[([0-9]+)\]")
rematcharrspan = re.compile("\[([0-9]+):([0-9]+)\]")

class jsonpath_token:
    def __init__(self, type, value=""):
        self.type = type
        self.value = value

def split_next_path_token(jsonpath):
    if len(jsonpath) == 0:
        return jsonpath_token("end"), ""
    for match in [rematchdict.match(jsonpath), rematchdictstr.match(jsonpath)]:
        if match:
            return jsonpath_token("dict", match.group(1)), jsonpath[match.span()[1]:]
    match = rematcharr.match(jsonpath)
    if match:
        return jsonpath_token("array", int(match.group(1))), jsonpath[match.span()[1]:]
    match = rematcharrspan.match(jsonpath)
    if match:
        return jsonpath_token("span", (int(match.group(1)), int(match.group(2)))), jsonpath[match.span()[1]:]
    return jsonpath_token("error"), jsonpath

def extract_json(json, jsonpath):
    while True:
        token, jsonpath = split_next_path_token(jsonpath)
        if token.type == "error":
            return None
        if token.type == "end":
            return json
        if token.type == "dict":
            if type(json) == dict:
                json = json[token.value]
            else:
                 return None
        if token.type == "span":
            if type(json) == list:
                if jsonpath != "":
                    # : must be last entry.
                    return None
                json = json[token.value[0]:token.value[1]]
            else:
                 return None
        if token.type == "array":
            if type(json) == list:
                json = json[token.value]
            else:
                return None