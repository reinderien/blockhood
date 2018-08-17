from io import BytesIO, SEEK_CUR
from struct import unpack

# Unity asset directory file
# See https://github.com/Perfare/AssetStudio/blob/master/AssetStudio/StudioClasses/AssetsFile.cs


MONO_BEHAVIOUR = 114


def str_to_nul(f):
    s = BytesIO()
    while True:
        b = f.read(1)
        if not b[0]:
            break
        s.write(b)
    return s.getvalue().decode('utf-8')


def align4(f):
    p = f.tell() & 3
    if p:
        f.seek(4 - p, SEEK_CUR)


def f_int(f):
    return unpack('I', f.read(4))[0]


def get_classes(f, base_count):
    class_ids = []
    for _ in range(base_count):
        class_id, type1 = unpack('<Ixh', f.read(7))
        if type1 >= 0:
            type1 = -1 - type1
        else:
            type1 = class_id
        class_ids.append((type1, class_id))
        if class_id == MONO_BEHAVIOUR:
            f.seek(16, SEEK_CUR)
        f.seek(16, SEEK_CUR)

    return class_ids


def get_preload_table(f, class_ids, paths_to_search, data_offset):
    asset_count = f_int(f)
    preload_table = {}
    for _ in range(asset_count):
        align4(f)
        path_id, offset, size, index = unpack('QIII', f.read(20))
        type1, type2 = class_ids[index]

        if path_id in paths_to_search:
            preload_table[path_id] = {'offset': offset + data_offset,
                                      'size': size,
                                      'type1': type1,
                                      'type2': type2}
    return preload_table


def consume_prio_preload(f):
    some_count = f_int(f)
    for _ in range(some_count):
        f.seek(4, SEEK_CUR)
        align4(f)
        f.seek(8, SEEK_CUR)


def get_shared_assets(f):
    shared_file_count = unpack('I', f.read(4))[0]
    shared_assets = []
    for _ in range(shared_file_count):
        aname = str_to_nul(f)
        f.seek(20, SEEK_CUR)
        shared_assets.append({'aname': aname,
                              'file_name': str_to_nul(f)})
    return shared_assets


def search_asset_file(fn, paths_to_search):
    with open(fn, 'rb') as f:
        table_size, data_end, file_gen, data_offset = unpack('>IIIIxxxx', f.read(20))
        assert(file_gen == 17)  # Unity 5.5.0+

        ver = str_to_nul(f)
        assert(ver == '5.6.2f1')

        platform, base_definitions, base_count = unpack('<I?I', f.read(9))
        assert(platform == 5)         # StandaloneWindows
        assert(not base_definitions)  # not supported

        class_ids = get_classes(f, base_count)
        preload_table = get_preload_table(f, class_ids, paths_to_search, data_offset)
        consume_prio_preload(f)
        shared_assets = get_shared_assets(f)

    return preload_table
