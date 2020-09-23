import math

def hx(a):
    return hex(a)[2:]
    
def hb(a):
    str = hex(a)[2:]
    if (len(str) < 2):
         str = "0" + str
    return str

def hw(a):
    str = hex(a)[2:]
    while (len(str) < 4):
         str = "0" + str
    return str
    
def HX(a):
    return hx(a).upper()
    
def HB(a):
    return hb(a).upper()
    
def HW(a):
    return hw(a).upper()
    
def json_list(list, map):
    str = "["
    is_first = True
    for l in list:
        if not is_first:
            str += ", "
        if type(l) == type([]):
            str += json_list(l, map)
        else:
            str += map(l)
        is_first = False
    return str + "]"

def floor_to(x, to=1):
    return to * math.floor(x / to)

def ceil_to(x, to=1):
    return to * math.ceil(x / to)

def rotated(list, idx):
    idx = ((idx % len(list)) + len(list)) % len(list)
    newlist = []
    for i in range(len(list)):
        j = (idx + i) % len(list)
        newlist.append(list[j])
    return newlist
    
def stat_out(file, *args):
    first = True
    for arg in args:
        if not first:
            file.write(" ")
        else:
            first = False
        file.write(str(arg))
    file.write("\n")
    
# clamps x to be an int in the range [a, b)
# ("clamp half-open-integer")
def clamp_hoi(x, a, b):
    assert(a <= b - 1)
    return int(max(a, min(x, b - 1)))
    
def common_prefix_length(a, b, maxlen):
    i = 0
    while i < maxlen and a[i] == b[i]:
        i += 1
    return i