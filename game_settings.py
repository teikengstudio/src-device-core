import hashlib
import json
import os
from copy import deepcopy
from pathlib import Path

from deploy.Windows.atomic import atomic_read_text, atomic_write
from filelock import FileLock


MAX_GAME_DATA_BYTES = 4 * 1024 * 1024


def validate_game_data(value):
    if not isinstance(value, dict) or len(value) > 4096:
        raise ValueError('Game settings must be an object with at most 4096 keys')
    if any(not isinstance(key, str) or not key or len(key) > 256 for key in value):
        raise ValueError('Invalid game settings key')
    encoded = json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(',', ':'))
    if len(encoded.encode('utf-8')) > MAX_GAME_DATA_BYTES:
        raise ValueError('Game settings exceed 4 MiB')
    return encoded


def enable_auto_battle(data):
    updated = deepcopy(data)
    raw = updated.get('RPGCloudSave') or '{}'
    if not isinstance(raw, str):
        raise ValueError('RPGCloudSave must be a JSON string')
    save = json.loads(raw)
    if not isinstance(save, dict):
        raise ValueError('RPGCloudSave must contain an object')
    values = save.setdefault('IntDicts', {})
    if not isinstance(values, dict):
        raise ValueError('RPGCloudSave.IntDicts must contain an object')
    values['OtherSettings_AutoBattleOpen'] = 1
    values['OtherSettings_IsSaveBattleSpeed'] = 1
    uid = values.get('App_LastUserID')
    has_uid = type(uid) is int and uid > 0 or isinstance(uid, str) and uid.isascii() and uid.isdecimal() and int(uid) > 0
    if has_uid:
        values[f'User_{uid}_SpeedUpOpen'] = 1
    updated['RPGCloudSave'] = json.dumps(save, ensure_ascii=False, allow_nan=False, separators=(',', ':'))
    validate_game_data(updated)
    return updated, bool(has_uid)


class GameSettingsStore:
    def __init__(self, directory, account_id):
        if not isinstance(account_id, str) or not account_id or len(account_id) > 256:
            raise ValueError('Missing game settings account identity')
        directory = Path(directory)
        directory.mkdir(parents=True, exist_ok=True, mode=0o700)
        if os.name != 'nt':
            os.chmod(directory, 0o700)
        identity = hashlib.sha256(account_id.encode('utf-8')).hexdigest()
        self.path = directory / (identity + '.json')
        self._lock = FileLock(str(self.path) + '.lock', timeout=2)

    def load(self):
        with self._lock:
            if not self.path.exists():
                return {}
            if self.path.stat().st_size > MAX_GAME_DATA_BYTES + 64:
                raise ValueError('Saved game settings exceed 4 MiB')
            document = json.loads(atomic_read_text(str(self.path)))
            if not isinstance(document, dict) or not isinstance(document.get('value'), dict):
                raise ValueError('Invalid saved game settings')
            validate_game_data(document['value'])
            return document['value']

    def save(self, data):
        validate_game_data(data)
        encoded = json.dumps({'value': data}, ensure_ascii=False, allow_nan=False, separators=(',', ':'))
        with self._lock:
            atomic_write(str(self.path), encoded + '\n')
            if os.name != 'nt':
                os.chmod(self.path, 0o600)
