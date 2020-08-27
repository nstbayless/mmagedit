class BitStream:
    def __init__(self, bin, offset):
        self.bin = bin
        self.offset = offset
        self.bitoffset = 0
    
    def read_bit(self):
        byte = self.bin[self.offset] & (1 << (7 - self.bitoffset))
        self.bitoffset += 1
        if self.bitoffset >= 8:
            self.bitoffset = 0
            self.offset += 1
        if byte:
            return 1
        return 0
        
    def read_bits(self, n):
        c = 0
        for i in range(n):
            c *= 2
            c = c | self.read_bit()
        return c