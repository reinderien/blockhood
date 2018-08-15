import re
from io import SEEK_CUR
from struct import unpack


def _read(f, n):
    data = f.read(n)
    if not len(data):
        raise EOFError()
    return data


def _read_int(f):
    return unpack('I', _read(f, 4))[0]


class FieldType:
    def __init__(self, pat):
        self.pat = re.compile(pat)

    def read(self, f):
        raise NotImplementedError()


class Int(FieldType):
    def __init__(self):
        super().__init__('int')

    def read(self, f):
        return _read_int(f)


class Float(FieldType):
    def __init__(self):
        super().__init__('float')

    def read(self, f):
        return unpack('f', _read(f, 4))[0]


class Bool(FieldType):
    def __init__(self):
        super().__init__('bool')

    def read(self, f):
        b = _read_int(f)
        return b != 0


class String(FieldType):
    def __init__(self):
        super().__init__('string')

    def read(self, f):
        str_len = _read_int(f)
        val = _read(f, str_len).decode('utf-8')

        # 4-byte alignment
        str_len &= 3
        if str_len > 0:
            f.seek(4 - str_len, SEEK_CUR)
        return val


class AssetRef(FieldType):
    def __init__(self):
        super().__init__('Sprite|GameObject|Texture|Block|AudioClip|Material')

    def read(self, f):
        return unpack('III', _read(f, 12))


class Enum(FieldType):
    def __init__(self, name, vals):
        super().__init__(name)
        self.vals = vals

    def read(self, f):
        raw = _read_int(f)
        return self.vals[raw]
