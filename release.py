import configparser
import json
import logging
import random
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from module.logger import logger
from .log import emit_log_callback

VERSION = 6
REPOSITORY_URL = 'https://github.com/teikengstudio/src-device-core'
REPOSITORY_API = 'https://api.github.com/repos/teikengstudio/src-device-core'
VERSION_URL = 'https://teikengstudio.github.io/src-device-core/version.json'
RULES_PATH = Path(__file__).with_name('rules.ini')
DISCLAIMER = ('免责声明：本组件为非官方独立设备后端，不由游戏服务商提供或认可。'
              '使用者须遵守适用法律及服务条款，并自行评估账号、隐私和使用风险；'
              '该声明不免除任何依法应承担的责任。')
LYRICS = (
    ('文明寥落旧忆斑驳', '残响凝结无人诉说', '下个时代再相付托', '信守如日升月落', '守候你的方向'),
    ('梦中万年相随相看短暂', '记忆黯淡茫茫星海', '幻光定格孤影柔怀', '都有你的长情告白'),
    ('任命运 万般错 落红擦肩过', '你同我 篆新卷 提笔在此刻'),
    ('I will wait until', "Wait' til I see you", 'I will wait until'),
    ('梦中万年相随相看短暂', '前尘褪色星海茫然', '幻光定格孤影柔怀', '都有你的长情告白'),
    ('左手冰川右手荒漠', '汉谟拉比法典定夺', '回溯浩渺斗转蹉跎', '答案旧约中镌刻', '我在源点等待'),
    ('亘古的墨客 谱写着', '史册中又更迭几番因果', '爱游荡在时间长河', '潮起潮落'),
)


def _log(message, level, log_callback):
    logger.log(level, message)
    emit_log_callback(log_callback, message, level)


def _read_json(url):
    request = Request(url, headers={'User-Agent': 'src-device-core', 'Cache-Control': 'no-cache'})
    with urlopen(request, timeout=5) as response:
        content = response.read(65537)
    if len(content) > 65536:
        raise ValueError('Version response exceeds the size limit')
    return json.loads(content)


def check_update(log_callback=None):
    failures = []
    try:
        _read_json(REPOSITORY_API)
    except HTTPError as exc:
        if exc.code == 404:
            _log('设备后端仓库不存在，拒绝启动。', logging.ERROR, log_callback)
            raise RuntimeError('Unsupported device backend') from None
        failures.append(f'仓库检查 HTTP {exc.code}')
    except (OSError, URLError, ValueError) as exc:
        failures.append(f'仓库检查 {type(exc).__name__}')
    try:
        manifest = _read_json(VERSION_URL)
        remote = manifest.get('version') if isinstance(manifest, dict) else None
        if type(remote) is not int or remote < 0:
            raise ValueError('Invalid remote version')
    except (OSError, URLError, ValueError) as exc:
        failures.append(f'版本检查 {type(exc).__name__}')
    else:
        if remote == 0:
            _log('远程版本为 0，设备后端已停用，拒绝启动。', logging.ERROR, log_callback)
            raise RuntimeError('Unsupported device backend')
        if remote > VERSION:
            _log(f'设备后端有更新：本地 {VERSION}，远程 {remote}。请更新：{REPOSITORY_URL}', logging.WARNING, log_callback)
    if failures:
        _log('检查更新失败：' + '；'.join(failures), logging.WARNING, log_callback)


def require_acceptance(log_callback=None):
    _log(DISCLAIMER, logging.WARNING, log_callback)
    try:
        with RULES_PATH.open('x', encoding='utf-8') as file:
            file.write('[Rules]\nAccepted = False\n')
    except FileExistsError:
        pass
    parser = configparser.ConfigParser()
    try:
        with RULES_PATH.open(encoding='utf-8') as file:
            parser.read_file(file)
        accepted = parser.get('Rules', 'Accepted', fallback='False').strip() == 'True'
    except (OSError, configparser.Error):
        accepted = False
    if not accepted:
        _log(f'尚未确认使用规则。请阅读免责声明并手动将 {RULES_PATH} 中 Accepted = False 改为 Accepted = True。', logging.WARNING, log_callback)
    return accepted


def prepare_load(log_callback=None):
    accepted = require_acceptance(log_callback)
    check_update(log_callback)
    if not accepted:
        raise RuntimeError('Unsupported device backend')


def announce_load(log_callback=None):
    _log(f'设备后端版本：{VERSION}', logging.INFO, log_callback)
    _log('\n' + '\n'.join('♪' + line for line in random.choice(LYRICS)), logging.INFO, log_callback)
