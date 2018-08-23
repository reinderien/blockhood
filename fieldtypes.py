from io import SEEK_CUR
from struct import unpack


def _read(f, n):
    data = f.read(n)
    if not len(data):
        raise EOFError()
    return data


def _read_int(f):
    return unpack('i', _read(f, 4))[0]


class FieldType:
    def read(self, f):
        raise NotImplementedError()


class Int(FieldType):
    names = ('int',)
    size = 4
    fixed = True

    def read(self, f):
        return _read_int(f)


class Float(FieldType):
    names = ('float',)
    size = 4
    fixed = True

    def read(self, f):
        return unpack('f', _read(f, Float.size))[0]


class Bool(FieldType):
    names = ('bool',)
    size = 4
    fixed = True

    def read(self, f):
        b = _read_int(f)
        if b not in (0, 1):
            raise ValueError('Bad boolean %d' % b)
        return bool(b)


class String(FieldType):
    names = ('string',)
    size = 4
    fixed = False

    def read(self, f):
        str_len = _read_int(f)
        if not str_len:
            return ''
        val = _read(f, str_len).decode('utf-8')

        # 4-byte alignment
        str_len &= 3
        if str_len > 0:
            f.seek(4 - str_len, SEEK_CUR)
        return val


class AssetRef(FieldType):
    names = ('Sprite', 'Texture', 'Block', 'AudioClip', 'Material')
    size = 12
    fixed = True

    def read(self, f):
        return unpack('III', _read(f, AssetRef.size))


class GameObject(FieldType):
    names = ('GameObject',)
    size = 20
    fixed = True

    def read(self, f):
        return unpack('IIIII', _read(f, GameObject.size))


class Enum(FieldType):
    size = 4
    fixed = True

    def __init__(self, vals):
        self.vals = vals

    def read(self, f):
        raw = _read_int(f)
        return self.vals[raw]


class Vector3(FieldType):
    names = ('Vector3',)
    size = 12  # ?? Not seen in the wild yet
    fixed = True

    def read(self, f):
        return unpack('fff', _read(f, Vector3))


class List(FieldType):
    size = 4
    fixed = False

    def __init__(self, inner):
        self.inner = inner

    def read(self, f):
        list_len = _read_int(f)
        if list_len > 100:
            raise ValueError('Suspicious list length of %d' % list_len)
        return tuple(self.inner.read(f) for _ in range(list_len))
