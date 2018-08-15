import re
from collections import namedtuple
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
    def read(self, f):
        raise NotImplementedError()


class Int(FieldType):
    names = ('int',)

    def read(self, f):
        return _read_int(f)


class Float(FieldType):
    names = ('float',)

    def read(self, f):
        return unpack('f', _read(f, 4))[0]


class Bool(FieldType):
    names = ('bool',)

    def read(self, f):
        b = _read_int(f)
        if b not in (0, 1):
            raise ValueError('Bad boolean %d' % b)
        return bool(b)


class String(FieldType):
    names = ('string',)

    def read(self, f):
        str_len = _read_int(f)
        val = _read(f, str_len).decode('utf-8')

        # 4-byte alignment
        str_len &= 3
        if str_len > 0:
            f.seek(4 - str_len, SEEK_CUR)
        return val


class AssetRef(FieldType):
    names = ('Sprite', 'Texture', 'Block', 'AudioClip', 'Material')

    def read(self, f):
        return unpack('III', _read(f, 12))


class GameObject(FieldType):
    names = ('GameObject',)

    def read(self, f):
        return unpack('IIIII', _read(f, 20))


class Enum(FieldType):
    def __init__(self, vals):
        self.vals = vals

    def read(self, f):
        raw = _read_int(f)
        return self.vals[raw]


class Vector3(FieldType):
    names = ('Vector3',)

    def read(self, f):
        return unpack('fff', _read(f, 12))


class List(FieldType):
    def __init__(self, inner):
        self.inner = inner

    def read(self, f):
        list_len = _read_int(f)
        return tuple(self.inner.read(f) for _ in range(list_len))


Member = namedtuple('MemberType', ('field_index', 'access', 'type_name', 'field_name', 'field_type'))


def get_types(src):
    types = {n: t()
             for t in (Int, Float, Bool, String, AssetRef, GameObject, Vector3)
             for n in t.names}

    enum_re = re.compile(r'\s*public enum (\S+)$', re.M)
    for tm in enum_re.finditer(src):
        type_name = tm.group(1)
        start = tm.start(1)
        end = src.index('}', start)
        val_src = src[start:end]
        vals = tuple(m[1] for m in
                     re.finditer(r'\s*(\S+),$', val_src, re.M))
        types[type_name] = Enum(vals)

    list_re = re.compile(r'(List<([^<>]+)>)|'
                         r'(\S+)\[\]', re.M)
    for tm in list_re.finditer(src):
        inner = types[tm[2] or tm[3]]
        types[tm[0]] = List(inner)

    return types


def get_members(src):
    types = get_types(src)

    mbr_re = re.compile(r'^\s*(public|private)'
                        r'\s+(\S+)' 
                        r'\s+(\S+)(;| =)', re.M)
    for field_index, m in enumerate(mbr_re.finditer(src, re.M)):
        access, type_name, field_name = m.groups()[:3]
        field_type = types[type_name]
        yield Member(field_index, access, type_name, field_name, field_type)
