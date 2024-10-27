import typing
from io import BytesIO, SEEK_CUR, SEEK_SET
from pathlib import Path
from struct import unpack

# Unity asset directory file
# See https://github.com/Perfare/AssetStudio


MONO_BEHAVIOUR = 114


def str_to_nul(f: typing.BinaryIO) -> str:
    s = BytesIO()
    while True:
        b = f.read(1)
        if not b[0]:
            break
        s.write(b)
    return s.getvalue().decode('utf-8')


def align4(f: typing.BinaryIO) -> None:
    p = f.tell() & 3
    if p:
        f.seek(4 - p, SEEK_CUR)


def f_int(f: typing.BinaryIO) -> int:
    return unpack('I', f.read(4))[0]


def get_classes(f: typing.BinaryIO, base_count: int) -> list[tuple[int, int]]:
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


def get_preload_table(
    f: typing.BinaryIO,
    class_ids: list[tuple[int, int]],
    paths_to_search: typing.Collection[int],
    data_offset: int,
) -> dict[int, dict[str, int]]:
    asset_count = f_int(f)
    preload_table = {}
    for _ in range(asset_count):
        align4(f)
        path_id, offset, size, index = unpack('QIII', f.read(20))
        type1, type2 = class_ids[index]

        # if path_id in paths_to_search:
        preload_table[path_id] = {'offset': offset + data_offset,
                                  'size': size, 'type1': type1, 'type2': type2}
    return preload_table


def consume_prio_preload(f: typing.BinaryIO) -> None:
    some_count = f_int(f)
    for _ in range(some_count):
        f.seek(4, SEEK_CUR)
        align4(f)
        f.seek(8, SEEK_CUR)


def get_shared_assets(f: typing.BinaryIO) -> list[dict[str, str]]:
    shared_file_count = f_int(f)
    shared_assets = []
    for _ in range(shared_file_count):
        aname = str_to_nul(f)
        f.seek(20, SEEK_CUR)
        shared_assets.append({'aname': aname,
                              'file_name': str_to_nul(f)})
    return shared_assets


def get_shared(
    f: typing.BinaryIO,
    shared_assets: list[dict[str, str]],
) -> dict[str, int | dict[str, str]]:
    file_id, path_id = unpack('<IQ', f.read(12))
    if 0 <= file_id < len(shared_assets):
        shared = shared_assets[file_id]
    else:
        shared = None
    return {'file_id': file_id, 'path_id': path_id, 'shared': shared}


def load_mono_behaviour(
    f: typing.BinaryIO,
    preload_table: dict[int, dict[str, int]],
    shared_assets: list[dict[str, str]],
) -> None:
    for path_id, asset in preload_table.items():
        try:
            assert (asset['type2'] == MONO_BEHAVIOUR)  # Only type supported here
            f.seek(asset['offset'], SEEK_SET)

            game_obj = get_shared(f, shared_assets)
            enabled = bool(f.read(1)[0])
            assert enabled
            align4(f)
            script = get_shared(f, shared_assets)
            name = f.read(f_int(f)).decode('utf-8')
            align4(f)
            main_size = asset['size'] - (f.tell() - asset['offset'])

            asset.update({'name': name, 'game_obj': game_obj, 'script': script,
                          'data': f.read(main_size)})
        except AssertionError:
            continue


def search_asset_file(
    fn: Path,
    paths_to_search: typing.Collection[int],
) -> dict[int, dict[str, typing.Any]]:
    with fn.open('rb') as f:
        table_size, data_end, file_gen, data_offset = unpack('>IIIIxxxx', f.read(20))
        assert(file_gen == 17)  # Unity 5.5.0+

        ver = str_to_nul(f)
        assert(ver == '5.6.2f1')

        platform, base_definitions, base_count = unpack('<I?I', f.read(9))

        # assert(platform == 5)  # StandaloneWindows
        assert platform == 19    # StandaloneWindows64

        assert(not base_definitions)  # not supported

        class_ids = get_classes(f, base_count)
        preload_table = get_preload_table(f, class_ids, paths_to_search, data_offset)
        consume_prio_preload(f)
        shared_assets = get_shared_assets(f)
        load_mono_behaviour(f, preload_table, shared_assets)

    return preload_table


def get_dbs(steam_prefix: Path) -> tuple[
    dict[str, typing.Any],
    dict[str, typing.Any],
]:
    print('Loading game databases...', end=' ')

    # block_id, resource_id = 21228, 21231  # in old version
    block_id, resource_id = 21222, 21225  # in 64-bit version

    directory = steam_prefix / r'steamapps\common\Blockhood\BLOCKHOOD v0_40_08_Data'
    block_db = None
    resource_db = None

    for fn in directory.glob('*.assets'):
        dbs = search_asset_file(fn, (block_id, resource_id))
        by_name = {
            v['name']: v
            for v in dbs.values()
            if 'name' in v
        }
        block_db = by_name.get('blockDB_current', block_db)
        resource_db = by_name.get('resourceDB', resource_db)
        if block_db and resource_db:
            break

    print('Loaded %s %dkiB, %s %dkiB.' % (block_db['name'], block_db['size']/1024,
                                          resource_db['name'], resource_db['size']/1024))
    return block_db, resource_db
