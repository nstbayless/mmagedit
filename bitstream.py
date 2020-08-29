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
        
    def write_bit(self, bit):
        mask = 1 << (7 - self.bitoffset)
        self.bin[self.offset] = (self.bin[self.offset] & ~mask) | (mask if bit else 0)
        self.bitoffset += 1
        if self.bitoffset >= 8:
            self.bitoffset = 0
            self.offset += 1
    
    def write_bits(self, data, n):
        for i in range(n):
            self.write_bit((data >> (n - i - 1)) & 1)
    
    def write_bits_list(self, bits):
        for bit in bits:
            self.write_bit(bit)