import os
import functools

ascii = bytes((0x50, 0x41, 0x54, 0x43, 0x48))
eof = bytes((0x45, 0x4f, 0x46))
eofint = 0x454f46

filemax = 0x1000000

# writes the end of the hunk
def endhunk(out, hunk):
    size = bytearray(2)
    for i in range(2):
        size[i] = (len(hunk) >> (8 if i == 0 else 0)) & 0xff
    out(size)
    out(hunk)

# creates an org -> mod patch, saves it in the given file.
# returns True on success.
def create_patch(org, mod, file):
    assert(len(org) == len(mod))
    assert(len(mod) < filemax)
    
    with open(file, "wb") as f:
        out = functools.partial(f.write)
        out(ascii)
        write = False
        for i in range(len(mod)):
            if not write:
                if org[i] != mod[i]:
                    hunk = bytearray()
                    
                    # hacky fix for the eof-int problem
                    if i == eofint:
                        hunk.append(mod[i-1])
                    
                    hunk.append(mod[i])
                    
                    # write starting position of chunk
                    position = bytearray(3)
                    for j in range(3):
                        position[j] = (i >> (0x10 - j * 8)) & 0xff
                    
                    write = True
                    
                    out(position)
            else:
                # check the next 5 bytes for differences.
                # if any are different, append *this* byte.
                """for j in reversed(range(5)):
                    if i + j >= len(mod):
                        continue
                    if org[i + j] != mod[i + j]:
                        hunk.append(mod[i])
                        break
                    if j == 0:
                        write = False
                        endhunk(f, hunk)
                        break"""
                if org[i] != mod[i]:
                    hunk.append(mod[i])
                else:
                    write = False
                    endhunk(out, hunk)
                    
            # end of mod reached.
            if write and i == len(mod) - 1:
                endhunk(out, hunk)
        
        out(eof)
        return True
    
    return False