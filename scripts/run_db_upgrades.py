"""Run database upgrades for selected plugins.

Usage:
  python scripts\run_db_upgrades.py songs
  python scripts\run_db_upgrades.py songs images bibles

If no plugin names are provided, this will run the `songs` upgrade by default.
"""
import sys
from openlp.core.db.helpers import get_db_path
from openlp.core.db.upgrades import upgrade_db

PLUGIN_UPGRADES = {
    'songs': 'openlp.plugins.songs.lib.upgrade',
    'images': 'openlp.plugins.images.lib.upgrade',
    'bibles': 'openlp.plugins.bibles.lib.upgrade',
    'songusage': 'openlp.plugins.songusage.lib.upgrade'
}

from importlib import import_module


def run_upgrade(plugin_name: str) -> None:
    module_path = PLUGIN_UPGRADES.get(plugin_name)
    if not module_path:
        print(f'No upgrade module known for plugin "{plugin_name}"')
        return
    upgrade_mod = import_module(module_path)
    db_url = get_db_path(plugin_name)
    print(f'Upgrading {plugin_name} DB at {db_url} using {module_path}...')
    updated_to_version, latest_version = upgrade_db(db_url, upgrade_mod)
    print(f'Finished: DB version {updated_to_version} / upgrade module {latest_version}')


if __name__ == '__main__':
    plugins = sys.argv[1:] if len(sys.argv) > 1 else ['songs']
    for plugin in plugins:
        run_upgrade(plugin)
