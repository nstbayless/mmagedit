def hx(a):
    return hex(a)[2:]
    
def hb(a):
    str = hex(a)[2:]
    if (len(str) < 2):
         str = "0" + str
    return str
    
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
    
def rotated(list, idx):
    idx = ((idx % len(list)) + len(list)) % len(list)
    newlist = []
    for i in range(len(list)):
        j = (idx + i) % len(list)
        newlist.append(list[j])
    return newlist
    