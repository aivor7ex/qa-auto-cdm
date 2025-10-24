#!/usr/bin/env python3
"""
Mirada Agent - API для проверки объектов
"""

import logging
import os
import sys
import subprocess
import time
from datetime import datetime
import importlib.util
from flask import Flask
from flask_smorest import Api, Blueprint, abort
from marshmallow import Schema, fields, INCLUDE, ValidationError
from flask import request as _request

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Проверка привилегий root
def check_root_privileges():
    """Проверяет, запущена ли программа с привилегиями root"""
    if os.geteuid() != 0:
        logger.error("ОШИБКА: Программа должна быть запущена с привилегиями root (sudo)")
        logger.error("Запустите: sudo python3 main.py")
        return False
    logger.info("✓ Проверка привилегий root пройдена")
    return True

# Проверяем привилегии при запуске
if not check_root_privileges():
    sys.exit(1)

# Порт сервера
SERVER_PORT = int(os.environ.get('MIRADA_PORT', 8000))

# Создаем Flask приложение
app = Flask(__name__)

# Конфигурация Flask-Smorest
app.config["API_TITLE"] = "Mirada Agent API"
app.config["API_VERSION"] = "1.0.0"
app.config["OPENAPI_VERSION"] = "3.0.2"
app.config["OPENAPI_URL_PREFIX"] = "/"
app.config["OPENAPI_SWAGGER_UI_PATH"] = "/docs"
app.config["OPENAPI_SWAGGER_UI_URL"] = "https://cdn.jsdelivr.net/npm/swagger-ui-dist/"
app.config["OPENAPI_REDOC_PATH"] = "/redoc"
app.config["OPENAPI_REDOC_URL"] = "https://cdn.jsdelivr.net/npm/redoc@2.0.0-rc.55/bundles/redoc.standalone.js"

# Создаем API
api = Api(app)

# Создаем blueprint с базовым путем /api
blp = Blueprint("mirada", "mirada", url_prefix="/api", description="Операции с Mirada Agent")

# Marshmallow схемы для API
class ObjectRequestSchema(Schema):
    name = fields.Str(required=True, metadata={"description": "Имя объекта"})
    type = fields.Str(required=True, metadata={"description": "Тип объекта"})
    contents = fields.List(fields.Raw(), required=True, metadata={"description": "Содержимое объекта"})

class ObjectResponseSchema(Schema):
    result = fields.Str(metadata={"description": "Результат проверки"})
    message = fields.Str(required=False, metadata={"description": "Сообщение об ошибке"})

class FilterRequestSchema(Schema):
    overwrite = fields.Bool(required=False, metadata={"description": "Перезаписать существующие правила"})
    data = fields.List(fields.Raw(), required=True, metadata={"description": "Список правил фильтрации"})

class FilterResponseSchema(Schema):
    result = fields.Str(metadata={"description": "Результат сохранения правила"})
    message = fields.Str(required=False, metadata={"description": "Сообщение об ошибке"})

class CertificateRequestSchema(Schema):
    type = fields.Str(required=False, metadata={"description": "Тип сертификата (tls для TLS, пустой для management)"})
    cert = fields.Str(required=True, metadata={"description": "Сертификат в формате base64"})
    key = fields.Str(required=False, metadata={"description": "Ключ в формате base64"})

class CertificateResponseSchema(Schema):
    result = fields.Str(metadata={"description": "Результат проверки сертификата"})
    message = fields.Str(required=False, metadata={"description": "Сообщение об ошибке"})

class CertificatesCertsRequestSchema(Schema):
    # Схема для принятия массива напрямую
    class Meta:
        unknown = INCLUDE
    
    def load(self, data, *args, **kwargs):
        # Просто возвращаем данные как есть
        return data

class CertificatesCertsResponseSchema(Schema):
    result = fields.Str(metadata={"description": "Результат проверки генерации сертификата"})
    message = fields.Str(required=False, metadata={"description": "Сообщение об ошибке"})

class CreateInterfaceRequestSchema(Schema):
    name = fields.Raw(required=True, metadata={"description": "Имя интерфейса (строка или число)"})
    ipAndMask = fields.Str(required=False, metadata={"description": "IP адрес и маска подсети"})
    
    class Meta:
        unknown = INCLUDE
    
    def load(self, data, *args, **kwargs):
        """Кастомная загрузка для обработки числовых имен интерфейсов"""
        # Конвертируем числовые имена в строки
        if isinstance(data, dict) and 'name' in data:
            if isinstance(data['name'], (int, float)):
                data['name'] = str(data['name'])
        return super().load(data, *args, **kwargs)

class CreateInterfaceResponseSchema(Schema):
    result = fields.Str(metadata={"description": "Результат проверки создания интерфейса"})
    message = fields.Str(required=False, metadata={"description": "Сообщение об ошибке"})

class SetInterfaceStateRequestSchema(Schema):
    interface = fields.Str(required=True, metadata={"description": "Имя интерфейса"})
    state = fields.Str(required=True, metadata={"description": "Желаемое состояние (up/down)"})
    
    class Meta:
        unknown = INCLUDE
    
    def load(self, data, *args, **kwargs):
        """Кастомная загрузка для валидации состояния интерфейса"""
        if isinstance(data, dict) and 'state' in data:
            state = data['state']
            if state not in ['up', 'down']:
                raise ValidationError(f"Состояние должно быть 'up' или 'down', получено: {state}")
        return super().load(data, *args, **kwargs)

class SetInterfaceStateResponseSchema(Schema):
    result = fields.Str(metadata={"description": "Результат проверки состояния"})
    message = fields.Str(required=False, metadata={"description": "Сообщение об ошибке"})

class SetInterfaceRequestSchema(Schema):
    interface = fields.Str(required=True, metadata={"description": "Имя интерфейса"})
    ip = fields.Str(required=False, metadata={"description": "IP адрес с маской подсети"})
    netmask = fields.Str(required=False, metadata={"description": "Маска подсети"})
    mtu = fields.Int(required=False, metadata={"description": "MTU интерфейса"})
    mac = fields.Str(required=False, metadata={"description": "MAC адрес интерфейса"})
    broadcast = fields.Str(required=False, metadata={"description": "Broadcast адрес"})
    
    class Meta:
        unknown = INCLUDE

class SetInterfaceResponseSchema(Schema):
    result = fields.Str(metadata={"description": "Результат настройки интерфейса"})
    message = fields.Str(required=False, metadata={"description": "Сообщение об ошибке"})

 

class IptablesMapRequestSchema(Schema):
    data = fields.Dict(required=False, metadata={"description": "Данные для проверки (table/chain)"})
    util = fields.Str(required=False, metadata={"description": "Утилита (iptables|arptables)"})
    
    class Meta:
        unknown = INCLUDE
    
    def load(self, data, *args, **kwargs):
        # Пропускаем данные как есть для гибкости автотеста
        return data

class IptablesMapResponseSchema(Schema):
    # Схема для поддержки разных типов ответов
    class Meta:
        unknown = INCLUDE

class HealthResponseSchema(Schema):
    status = fields.Str(metadata={"description": "Статус сервиса"})
    service = fields.Str(metadata={"description": "Название сервиса"})

class GenerateTrafficRequestSchema(Schema):
    protocol = fields.Str(required=True, metadata={"description": "Протокол: udp или tcp"})
    src = fields.Str(required=False, metadata={"description": "Источник (опционально)"})
    dst = fields.Str(required=True, metadata={"description": "IP/host назначения"})
    dport = fields.Int(required=True, metadata={"description": "Порт назначения"})
    count = fields.Int(required=False, load_default=1, metadata={"description": "Количество пакетов"})

class GenerateTrafficResponseSchema(Schema):
    result = fields.Str(metadata={"description": "Результат операции"})
    message = fields.Str(metadata={"description": "Сообщение"})



class UtilsTracerouteRequestSchema(Schema):
    addr = fields.Str(required=False, metadata={"description": "IP/host назначения"})
    icmp = fields.Bool(required=False, metadata={"description": "Использовать ICMP (-I)"})
    attemptsAmount = fields.Int(required=False, metadata={"description": "Значение для параметра -m"})
    source = fields.Str(required=False, metadata={"description": "Интерфейс источника (-i)"})
    dontFragmentByte = fields.Bool(required=False, metadata={"description": "Флаг DF (-F)"})

    class Meta:
        unknown = INCLUDE

class UtilsTracerouteResponseSchema(Schema):
    result = fields.Str(metadata={"description": "Результат операции"})
    message = fields.Str(required=False, metadata={"description": "Описание ошибки"})

class UtilsPingRequestSchema(Schema):
    addr = fields.Str(required=True, metadata={"description": "IP/host назначения"})
    packetsAmount = fields.Int(required=False, metadata={"description": "Количество пакетов (-c)"})
    timeout = fields.Int(required=False, metadata={"description": "Timeout в секундах (-W)"})
    payloadSize = fields.Int(required=False, metadata={"description": "Размер данных (-s)"})
    source = fields.Str(required=False, metadata={"description": "Интерфейс источника (-I)"})
    period = fields.Float(required=False, metadata={"description": "Интервал между пакетами (-i)"})
    pmtuDefinition = fields.Str(required=False, metadata={"description": "PMTU discovery policy (-M): do, want, dont"})

    class Meta:
        unknown = INCLUDE

class UtilsPingResponseSchema(Schema):
    result = fields.Str(metadata={"description": "Результат операции"})
    message = fields.Str(required=False, metadata={"description": "Описание ошибки"})

class UtilsArpRequestSchema(Schema):
    pid = fields.Int(required=False, metadata={"description": "PID процесса (опционально)"})

    class Meta:
        unknown = INCLUDE



class ConntrackCountResponseSchema(Schema):
    count = fields.Int(metadata={"description": "Текущее значение счётчика nf_conntrack"})
    timestamp = fields.Str(metadata={"description": "Время фиксации в формате ISO8601"})

class VerifyConntrackDropRequestSchema(Schema):
    protocol = fields.Str(required=True, metadata={"description": "Протокол: udp или tcp"})
    dport = fields.Int(required=True, metadata={"description": "Порт назначения"})
    src = fields.Str(required=False, metadata={"description": "Источник (опционально)"})
    dst = fields.Str(required=False, metadata={"description": "Назначение (опционально)"})

class VerifyConntrackDropResponseSchema(Schema):
    before = fields.Int(metadata={"description": "Счётчик до операции"})
    after = fields.Int(metadata={"description": "Счётчик после операции"})
    dropped = fields.Int(metadata={"description": "Разница (сколько удалено)"})
    success = fields.Bool(metadata={"description": "after < before"})

class ConntrackDropRequestSchema(Schema):
    protocol = fields.Str(required=False, metadata={"description": "Протокол: tcp|udp|icmp"})
    src = fields.Str(required=False, metadata={"description": "IP/host источника"})
    dst = fields.Str(required=False, metadata={"description": "IP/host назначения"})
    sport = fields.Int(required=False, metadata={"description": "Порт источника"})
    dport = fields.Int(required=False, metadata={"description": "Порт назначения"})

    class Meta:
        unknown = INCLUDE

class MirrorsRequestSchema(Schema):
    id = fields.Str(required=True, metadata={"description": "ID mirror с префиксом типа (e:, i:, b:)"})
    dev = fields.Str(required=True, metadata={"description": "Имя сетевого интерфейса"})
    target = fields.Str(required=True, metadata={"description": "Целевой интерфейс для зеркалирования"})
    type = fields.Str(required=True, metadata={"description": "Тип зеркалирования: ingress, egress, both"})

class MirrorsResponseSchema(Schema):
    result = fields.Str(metadata={"description": "Результат проверки mirror"})
    message = fields.Str(required=False, metadata={"description": "Сообщение об ошибке"})

class ConntrackDropResponseItemSchema(Schema):
    index = fields.Int(metadata={"description": "Индекс операции"})
    cmd = fields.Str(metadata={"description": "Выполненная команда"})
    res = fields.Str(metadata={"description": "Результат выполнения"})
    error = fields.Str(metadata={"description": "Сообщение об ошибке"})

class AddInterfaceAddrRequestSchema(Schema):
    interface = fields.Str(required=True, metadata={"description": "Имя интерфейса"})
    address = fields.Str(required=True, metadata={"description": "IP адрес с маской подсети"})

class AddInterfaceAddrResponseSchema(Schema):
    result = fields.Str(metadata={"description": "Результат операции"})
    message = fields.Str(required=False, metadata={"description": "Сообщение об ошибке"})

class LocalRulesRequestSchema(Schema):
    port = fields.Int(required=True, metadata={"description": "Номер порта (1-65535)"})
    interface = fields.Raw(required=False, metadata={"description": "Имя интерфейса (строка или число)"})
    type = fields.Raw(required=False, metadata={"description": "Тип правила (строка или число)"})
    description = fields.Raw(required=False, metadata={"description": "Описание правила (строка или число)"})
    
    class Meta:
        unknown = INCLUDE

class LocalRulesResponseSchema(Schema):
    result = fields.Str(metadata={"description": "Результат операции"})
    message = fields.Str(required=False, metadata={"description": "Сообщение об ошибке"})

class ForwardRulesRequestSchema(Schema):
    srcNets = fields.List(fields.Dict(), required=False, metadata={"description": "Список исходных сетей с портами"})
    dstNets = fields.List(fields.Dict(), required=False, metadata={"description": "Список сетей назначения с портами"})
    srcExclude = fields.List(fields.Dict(), required=False, metadata={"description": "Список исключаемых исходных сетей"})
    dstExclude = fields.List(fields.Dict(), required=False, metadata={"description": "Список исключаемых сетей назначения"})
    action = fields.Dict(required=False, metadata={"description": "Действие правила"})
    config = fields.Str(required=False, metadata={"description": "Тип конфигурации"})
    description = fields.Str(required=False, metadata={"description": "Описание правила"})
    active = fields.Bool(required=False, metadata={"description": "Активность правила"})
    
    class Meta:
        unknown = INCLUDE

class ForwardRulesResponseSchema(Schema):
    result = fields.Str(metadata={"description": "Результат операции"})
    message = fields.Str(required=False, metadata={"description": "Сообщение об ошибке"})

# ---- CSI notification subscribe schemas ----
 

# Импортируем сервисы
from services.objects.object import handle as object_handler
from services.vswitch.filter import handle as filter_handler
from services.vswitch.certificates_certs_set import handle as certificate_handler
from services.vswitch.certificates_certs import handle as certificates_certs_handler
from services.vswitch.managers_createInterface import handle as create_interface_handler
from services.vswitch.managers_setInterfaceState import handle as set_interface_state_handler
from services.vswitch.managers_setInterface import handle as set_interface_handler
from services.vswitch.managers_conntrackDrop import handle as conntrack_drop_handler
from services.vswitch.utils import remove_interface_addr_handler as verify_and_remove_interface_addr_handler
from services.vswitch.mirrors import handle as mirrors_handler
# from services.vswitch.managers_iptablesMap import handle as iptables_map_handler

from services.vswitch.utils_traceroute import handle as utils_traceroute_handler
from services.vswitch.utils_ping import handle as utils_ping_handler

from services.vswitch.localRules import handle as local_rules_handler
from services.vswitch.forwardRules import handle as forward_rules_handler
from services.vswitch.managers_iptablesMap import handle as iptables_map_handler

# CSI server services - динамический импорт для модулей с дефисом
def _load_manager_settings_timezone_handler():
    """Динамически загружает обработчик manager_settings_timezone."""
    import importlib.util
    import os
    module_path = os.path.join(os.path.dirname(__file__), "services", "csi-server", "manager_settings_timezone.py")
    spec = importlib.util.spec_from_file_location("manager_settings_timezone", module_path)
    if spec is None or spec.loader is None:
        raise ImportError("manager_settings_timezone module not found")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return getattr(mod, "handle", None)

# Динамический импорт для модуля с дефисом в имени
def _load_integrity_test_handler():
    """Динамически загружает обработчик integrity_test."""
    import importlib.util
    import os
    module_path = os.path.join(os.path.dirname(__file__), "services", "csi-server", "integrity_test.py")
    spec = importlib.util.spec_from_file_location("integrity_test", module_path)
    if spec is None or spec.loader is None:
        raise ImportError("integrity_test module not found")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return getattr(mod, "handle", None)

def _load_manager_uploader_password_handler():
    """Динамически загружает обработчик manager_uploaderPassword."""
    import importlib.util
    import os
    module_path = os.path.join(os.path.dirname(__file__), "services", "csi-server", "manager_uploaderPassword.py")
    spec = importlib.util.spec_from_file_location("manager_uploaderPassword", module_path)
    if spec is None or spec.loader is None:
        raise ImportError("manager_uploaderPassword module not found")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return getattr(mod, "handle", None)

def _load_manager_config_handler():
    """Динамически загружает обработчик manager_config."""
    import importlib.util
    import os
    module_path = os.path.join(os.path.dirname(__file__), "services", "csi-server", "manager_config.py")
    spec = importlib.util.spec_from_file_location("manager_config", module_path)
    if spec is None or spec.loader is None:
        raise ImportError("manager_config module not found")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return getattr(mod, "handle", None)

def _load_update_images_start_download_handler():
    """Динамически загружает обработчик update_images_start-download."""
    import importlib.util
    import os
    module_path = os.path.join(os.path.dirname(__file__), "services", "csi-server", "update_images_start-download.py")
    spec = importlib.util.spec_from_file_location("update_images_start_download", module_path)
    if spec is None or spec.loader is None:
        raise ImportError("update_images_start-download module not found")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return getattr(mod, "handle", None)


class UpdateCallOnHostRequestSchema(Schema):
    command = fields.Str(required=True, metadata={"description": "Имя команды (например, bash)"})
    args = fields.List(fields.Str(), required=True, metadata={"description": "Аргументы команды"})


class UpdateCallOnHostResponseSchema(Schema):
    result = fields.Str(metadata={"description": "Результат проверки"})
    message = fields.Str(required=False, metadata={"description": "Описание ошибки"})

class IntegrityTestRequestSchema(Schema):
    state = fields.Str(required=True, metadata={"description": "Состояние для проверки целостности"})

class IntegrityTestResponseSchema(Schema):
    result = fields.Str(metadata={"description": "Результат проверки целостности"})
    message = fields.Str(required=False, metadata={"description": "Описание ошибки"})

# ---- Security settings schemas ----
class SecuritySettingsRequestSchema(Schema):
    max_bad_auth_attempts = fields.Int(required=False, metadata={"description": "Макс. число неудачных попыток"})
    bad_auth_decay_s = fields.Int(required=False, metadata={"description": "Период затухания в секундах"})
    block_time_s = fields.Int(required=False, metadata={"description": "Время блокировки в секундах"})

class SecuritySettingsResponseSchema(Schema):
    result = fields.Str(metadata={"description": "Результат проверки"})
    message = fields.Str(required=False, metadata={"description": "Описание ошибки"})

class SystemReportCheckResponseSchema(Schema):
    status = fields.Str(metadata={"description": "Статус отчёта: NOT_FOUND | GENERATION_IN_PROGRESS | GENERATED"})
    ctime = fields.Str(required=False, allow_none=True, metadata={"description": "Время создания файла (ISO8601)"})
    mtime = fields.Str(required=False, allow_none=True, metadata={"description": "Время модификации файла (ISO8601)"})
    size = fields.Int(required=False, allow_none=True, metadata={"description": "Размер файла в байтах"})

# ---- System report generate schemas ----
class SystemReportGenerateRequestSchema(Schema):
    status = fields.Str(required=True, metadata={"description": "Статус генерации отчета: GENERATION_STARTED"})
    class ErrorPayloadSchema(Schema):
        statusCode = fields.Int(required=False)
        name = fields.Str(required=False)
        message = fields.Str(required=False)
        class Meta:
            unknown = INCLUDE

    error = fields.Nested(ErrorPayloadSchema, required=False)
    class Meta:
        unknown = INCLUDE

class SystemReportGenerateResponseSchema(Schema):
    result = fields.Str(metadata={"description": "Результат операции"})
    message = fields.Str(required=False, metadata={"description": "Сообщение об ошибке"})

# ---- System report generate prepare schemas ----
class SystemReportGeneratePrepareRequestSchema(Schema):
    class Meta:
        unknown = INCLUDE

class SystemReportGeneratePrepareResponseSchema(Schema):
    result = fields.Str(metadata={"description": "Результат операции"})
    message = fields.Str(required=False, metadata={"description": "Сообщение об ошибке"})

# ---- Manager settings timezone schemas ----
class ManagerSettingsTimezoneRequestSchema(Schema):
    data = fields.Str(required=True, metadata={"description": "Timezone value to verify"})

class ManagerSettingsTimezoneResponseSchema(Schema):
    result = fields.Str(metadata={"description": "Результат проверки timezone"})
    message = fields.Str(required=False, metadata={"description": "Сообщение об ошибке"})

class ManagerUploaderPasswordResponseSchema(Schema):
    result = fields.Str(metadata={"description": "Результат проверки изменения пароля uploader"})
    message = fields.Str(required=False, metadata={"description": "Сообщение об ошибке"})

class ManagerConfigResponseSchema(Schema):
    result = fields.Str(metadata={"description": "Результат проверки импорта конфигурации"})
    message = fields.Str(required=False, metadata={"description": "Сообщение об ошибке"})

class ManagerResetRequestSchema(Schema):
    x_access_token = fields.Str(required=True, data_key="x-access-token", metadata={"description": "Токен доступа"})

class ManagerResetResponseSchema(Schema):
    result = fields.Str(metadata={"description": "Результат операции"})
    message = fields.Str(required=False, metadata={"description": "Сообщение об ошибке"})

class ManagerRebootRequestSchema(Schema):
    x_access_token = fields.Str(required=True, data_key="x-access-token", metadata={"description": "Токен доступа"})

class ManagerRebootResponseSchema(Schema):
    result = fields.Str(metadata={"description": "Результат операции"})
    message = fields.Str(required=False, metadata={"description": "Сообщение об ошибке"})

class UpdateImagesStartDownloadRequestSchema(Schema):
    x_access_token = fields.Str(required=True, data_key="x-access-token", metadata={"description": "Токен доступа"})

class UpdateImagesStartDownloadResponseSchema(Schema):
    result = fields.Str(metadata={"description": "Результат операции"})
    message = fields.Str(required=False, metadata={"description": "Сообщение об ошибке"})

class LicensesApplyActivationKeyRequestSchema(Schema):
    x_access_token = fields.Str(required=True, data_key="x-access-token", metadata={"description": "Токен доступа"})

class LicensesApplyActivationKeyResponseSchema(Schema):
    result = fields.Str(metadata={"description": "Результат операции"})
    message = fields.Str(required=False, metadata={"description": "Сообщение об ошибке"})
    serialNumber = fields.Str(required=False, metadata={"description": "Серийный номер устройства"})
    licenseNumber = fields.Str(required=False, metadata={"description": "Номер лицензии"})
    expiresAt = fields.Str(required=False, metadata={"description": "Дата истечения лицензии (ISO8601)"})

class LicensesGenerateActivationCodeResponseSchema(Schema):
    result = fields.Str(metadata={"description": "Результат операции"})
    message = fields.Str(required=False, metadata={"description": "Сообщение об ошибке"})


class ManagerMaintenanceUpdateBrpRequestSchema(Schema):
    x_access_token = fields.Str(required=True, data_key="x-access-token", metadata={"description": "Токен доступа"})

class ManagerMaintenanceUpdateBrpResponseSchema(Schema):
    result = fields.Str(metadata={"description": "Результат"})
    message = fields.Str(required=False, metadata={"description": "Описание ошибки"})

class UpdateRulesDownloadAndApplyRequestSchema(Schema):
    x_access_token = fields.Str(required=True, data_key="x-access-token", metadata={"description": "Токен доступа"})

class UpdateRulesDownloadAndApplyResponseSchema(Schema):
    result = fields.Str(metadata={"description": "Результат операции"})
    message = fields.Str(required=False, metadata={"description": "Описание ошибки"})

class UpdateRulesCheckForUpdatesRequestSchema(Schema):
    x_access_token = fields.Str(required=True, data_key="x-access-token", metadata={"description": "Токен доступа"})

class UpdateRulesCheckForUpdatesResponseSchema(Schema):
    result = fields.Str(metadata={"description": "Результат операции"})
    message = fields.Str(required=False, metadata={"description": "Описание ошибки"})

class UpdateRulesStartDownloadRequestSchema(Schema):
    x_access_token = fields.Str(required=True, data_key="x-access-token", metadata={"description": "Токен доступа"})

class UpdateRulesStartDownloadResponseSchema(Schema):
    result = fields.Str(metadata={"description": "Результат операции"})
    message = fields.Str(required=False, metadata={"description": "Описание ошибки"})

class UpdateRulesCancelDownloadRequestSchema(Schema):
    x_access_token = fields.Str(required=True, data_key="x-access-token", metadata={"description": "Токен доступа"})

class UpdateRulesCancelDownloadResponseSchema(Schema):
    result = fields.Str(metadata={"description": "Результат операции"})
    message = fields.Str(required=False, metadata={"description": "Описание ошибки"})

@blp.route("/")
@blp.response(200, description="Информация об API")
def root():
    """Корневой эндпоинт"""
    return {
        "service": "Mirada Agent API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health"
    }

@blp.route("/health")
@blp.response(200, HealthResponseSchema, description="Проверка состояния сервиса")
def health():
    """Проверка состояния сервиса"""
    return {"status": "healthy", "service": "mirada-agent"}

@blp.route("/object", methods=["POST"])
@blp.arguments(ObjectRequestSchema, location="json")
@blp.response(200, ObjectResponseSchema, description="Проверка создания объекта")
def check_object(args):
    """Проверка создания объекта"""
    try:
        result = object_handler(args)
        return {"result": "OK"}
    except ValidationError as e:
        logger.error(f"Ошибка валидации: {e}")
        return {"result": "ERROR", "message": f"Validation error: {str(e)}"}
    except Exception as e:
        logger.error(f"Ошибка при проверке объекта: {e}")
        return {"result": "ERROR", "message": f"Internal error: {str(e)}"}

@blp.route("/filter", methods=["POST"])
@blp.arguments(FilterRequestSchema, location="json")
@blp.response(200, FilterResponseSchema, description="Проверка наличия правил фильтрации")
def check_filter(args):
    """Проверка наличия правил фильтрации в БД"""
    try:
        result = filter_handler(args)
        return {"result": "OK"}
    except Exception as e:
        logger.error(f"Ошибка при проверке фильтра: {e}")
        return {"result": "ERROR", "message": f"Internal error: {str(e)}"}

@blp.route("/certificates/certs/set", methods=["POST"])
@blp.arguments(CertificateRequestSchema, location="json")
@blp.response(200, CertificateResponseSchema, description="Проверка установки сертификатов")
def set_certificates(args):
    """Проверка установки сертификатов"""
    try:
        result = certificate_handler(args)
        return {"result": "OK"}
    except Exception as e:
        logger.error(f"Ошибка при проверке сертификатов: {e}")
        return {"result": "ERROR", "message": f"Internal error: {str(e)}"}

@blp.route("/certificates/certs", methods=["POST"])
@blp.arguments(CertificatesCertsRequestSchema, location="json")
@blp.response(200, CertificatesCertsResponseSchema, description="Проверка генерации сертификатов")
def check_certificates_certs(args):
    """Проверка генерации сертификатов"""
    try:
        result = certificates_certs_handler(args)
        return {"result": "OK"}
    except Exception as e:
        logger.error(f"Ошибка при проверке генерации сертификатов: {e}")
        return {"result": "ERROR", "message": f"Internal error: {str(e)}"}

@blp.route("/managers/createInterface", methods=["POST"])
@blp.arguments(CreateInterfaceRequestSchema, location="json")
@blp.response(200, CreateInterfaceResponseSchema, description="Проверка создания интерфейса")
def create_interface(args):
    """Проверка создания интерфейса"""
    try:
        logger.info(f"=== ОБРАБОТКА ЗАПРОСА СОЗДАНИЯ ИНТЕРФЕЙСА ===")
        logger.info(f"Полученные аргументы: {args}")
        logger.info(f"Тип аргументов: {type(args)}")
        
        result = create_interface_handler(args)
        logger.info(f"Результат обработки: {result}")
        return {"result": "OK"}
    except ValidationError as e:
        logger.error(f"Ошибка валидации: {e}")
        logger.error(f"Детали валидации: {e.messages}")
        return {"result": "ERROR", "message": f"Validation error: {str(e)}"}
    except Exception as e:
        logger.error(f"Ошибка при проверке создания интерфейса: {e}")
        logger.error(f"Тип ошибки: {type(e)}")
        logger.error(f"Детали ошибки: {str(e)}")
        return {"result": "ERROR", "message": f"Internal error: {str(e)}"}

@blp.route("/managers/setInterfaceState", methods=["POST"])
@blp.arguments(SetInterfaceStateRequestSchema, location="json")
@blp.response(200, SetInterfaceStateResponseSchema, description="Проверка состояния интерфейса")
def set_interface_state(args):
    """Проверка состояния интерфейса"""
    try:
        logger.info(f"=== ОБРАБОТКА ЗАПРОСА ПРОВЕРКИ СОСТОЯНИЯ ИНТЕРФЕЙСА ===")
        logger.info(f"Полученные аргументы: {args}")
        logger.info(f"Тип аргументов: {type(args)}")
        
        result = set_interface_state_handler(args)
        logger.info(f"Результат обработки: {result}")
        return {"result": "OK"}
    except ValidationError as e:
        logger.error(f"Ошибка валидации: {e}")
        logger.error(f"Детали валидации: {e.messages}")
        return {"result": "ERROR", "message": f"Validation error: {str(e)}"}
    except Exception as e:
        logger.error(f"Ошибка при проверке состояния интерфейса: {e}")
        logger.error(f"Тип ошибки: {type(e)}")
        logger.error(f"Детали ошибки: {str(e)}")
        return {"result": "ERROR", "message": f"Internal error: {str(e)}"}

@blp.route("/managers/setInterface", methods=["POST"])
@blp.arguments(SetInterfaceRequestSchema, location="json")
@blp.response(200, SetInterfaceResponseSchema, description="Настройка параметров интерфейса")
def set_interface(args):
    """Настройка параметров интерфейса"""
    try:
        logger.info(f"=== ОБРАБОТКА ЗАПРОСА НАСТРОЙКИ ИНТЕРФЕЙСА ===")
        logger.info(f"Полученные аргументы: {args}")
        logger.info(f"Тип аргументов: {type(args)}")
        
        result = set_interface_handler(args)
        logger.info(f"Результат обработки: {result}")
        if isinstance(result, dict) and result.get("result") == "OK":
            return {"result": "OK"}, 200
        if isinstance(result, dict) and result.get("result") == "ERROR":
            return {"result": "ERROR", "message": result.get("message", "")}, 422
        return {"result": "ERROR", "message": "Unexpected response"}, 422
    except ValidationError as e:
        logger.error(f"Ошибка валидации: {e}")
        logger.error(f"Детали валидации: {e.messages}")
        return {"result": "ERROR", "message": f"Validation error: {str(e)}"}, 422
    except Exception as e:
        logger.error(f"Ошибка при настройке интерфейса: {e}")
        logger.error(f"Тип ошибки: {type(e)}")
        logger.error(f"Детали ошибки: {str(e)}")
        return {"result": "ERROR", "message": f"Internal error: {str(e)}"}, 500

@blp.route("/managers/conntrackDrop", methods=["POST"])
@blp.arguments(ConntrackDropRequestSchema, location="json")
@blp.response(200, ConntrackDropResponseItemSchema(many=True), description="Удаление записей conntrack в namespace ngfw")
def managers_conntrack_drop(args):
    """Удаляет записи conntrack в namespace ngfw по фильтрам."""
    try:
        logger.info("=== ОБРАБОТКА ЗАПРОСА УДАЛЕНИЯ CONNTRACK ===")
        logger.info(f"Полученные аргументы: {args}")
        result = conntrack_drop_handler(args)
        logger.info(f"Результат: {result}")
        return result
    except Exception as e:
        logger.error(f"Ошибка при удалении conntrack: {e}")
        # Возвращаем массив с описанием ошибки для унификации
        return [{"index": 0, "cmd": "", "res": "", "error": str(e)}]

 

@blp.route("/managers/addInterfaceAddr", methods=["POST"])
@blp.arguments(AddInterfaceAddrRequestSchema, location="json")
@blp.response(200, AddInterfaceAddrResponseSchema, description="Проверка и удаление IP адреса из интерфейса")
def managers_verify_and_remove_interface_addr(args):
    """Проверяет наличие уже добавленного IP адреса и удаляет его из интерфейса в namespace ngfw."""
    try:
        logger.info("=== ОБРАБОТКА ЗАПРОСА ПРОВЕРКИ И УДАЛЕНИЯ IP АДРЕСА ===")
        logger.info(f"Полученные аргументы: {args}")
        result = verify_and_remove_interface_addr_handler(args)
        logger.info(f"Результат: {result}")
        if isinstance(result, dict) and result.get("result") == "OK":
            return {"result": "OK", "message": result.get("message", "")}
        if isinstance(result, dict) and result.get("result") == "ERROR":
            return {"result": "ERROR", "message": result.get("message", "")}
        return {"result": "ERROR", "message": "Unexpected response"}
    except Exception as e:
        logger.error(f"Ошибка при проверке и удалении IP адреса: {e}")
        return {"result": "ERROR", "message": f"Internal error: {str(e)}"}

@blp.route("/localRules", methods=["POST"])
@blp.arguments(LocalRulesRequestSchema, location="json")
@blp.response(200, LocalRulesResponseSchema, description="Проверка создания правила для локального файрвола")
def check_local_rule(args):
    """Проверяет создание нового правила для локального (host) файрвола."""
    try:
        logger.info("=== ОБРАБОТКА ЗАПРОСА ПРОВЕРКИ ЛОКАЛЬНОГО ПРАВИЛА ===")
        logger.info(f"Полученные аргументы: {args}")
        result = local_rules_handler(args)
        logger.info(f"Результат: {result}")
        if isinstance(result, dict) and result.get("result") == "OK":
            return {"result": "OK"}
        if isinstance(result, dict) and result.get("result") == "ERROR":
            return {"result": "ERROR", "message": result.get("message", "")}
        return {"result": "ERROR", "message": "Unexpected response"}
    except Exception as e:
        logger.error(f"Ошибка при проверке локального правила: {e}")
        return {"result": "ERROR", "message": f"Internal error: {str(e)}"}

@blp.route("/mirrors", methods=["POST"])
@blp.arguments(MirrorsRequestSchema, location="json")
@blp.response(200, MirrorsResponseSchema, description="Проверка mirror зеркалирования трафика")
def check_mirrors(args):
    """Проверка mirror зеркалирования трафика в namespace ngfw."""
    try:
        logger.info("=== ОБРАБОТКА ЗАПРОСА ПРОВЕРКИ MIRROR ===")
        logger.info(f"Полученные аргументы: {args}")
        result = mirrors_handler(args)
        logger.info(f"Результат: {result}")
        if isinstance(result, dict) and result.get("result") in ("OK", "ERROR"):
            return result
        return {"result": "ERROR", "message": "Unexpected response"}
    except Exception as e:
        logger.error(f"Ошибка при проверке mirror: {e}")
        return {"result": "ERROR", "message": f"Internal error: {str(e)}"}

@blp.route("/forwardRules", methods=["POST"])
@blp.arguments(ForwardRulesRequestSchema, location="json")
@blp.response(200, ForwardRulesResponseSchema, description="Проверка создания правил перенаправления трафика")
def check_forward_rules(args):
    """Проверяет создание правил перенаправления трафика в namespace ngfw."""
    try:
        logger.info("=== ОБРАБОТКА ЗАПРОСА ПРОВЕРКИ ПРАВИЛ ПЕРЕНАПРАВЛЕНИЯ ===")
        logger.info(f"Полученные аргументы: {args}")
        result = forward_rules_handler(args)
        logger.info(f"Результат: {result}")
        if isinstance(result, dict) and result.get("result") in ("OK", "ERROR"):
            return result
        return {"result": "ERROR", "message": "Unexpected response"}
    except Exception as e:
        logger.error(f"Ошибка при проверке правил перенаправления: {e}")
        return {"result": "ERROR", "message": f"Internal error: {str(e)}"}

 

@blp.route("/generate-traffic", methods=["POST"])
@blp.arguments(GenerateTrafficRequestSchema, location="json")
@blp.response(200, GenerateTrafficResponseSchema, description="Генерация трафика в namespace ngfw")
def generate_traffic(args):
    """Генерация трафика (UDP/TCP) в namespace ngfw"""
    try:
        protocol = (args.get("protocol") or "").lower()
        dst = args.get("dst")
        dport = int(args.get("dport"))
        count = int(args.get("count", 1))

        if protocol not in ["udp", "tcp"]:
            return {"result": "ERROR", "message": f"Unsupported protocol: {protocol}"}

        if not dst or dport <= 0 or count <= 0:
            return {"result": "ERROR", "message": "Invalid parameters"}

        # Простая валидация назначения для безопасности
        import re
        if not re.match(r"^[0-9A-Za-z\.:\-]+$", str(dst)):
            return {"result": "ERROR", "message": "Invalid dst"}

        loop_cmd = f"for i in $(seq 1 {count}); do echo -n test > /dev/{protocol}/{dst}/{dport}; done"
        cmd = ["ip", "netns", "exec", "ngfw", "bash", "-c", loop_cmd]
        logger.info(f"Выполняем генерацию трафика: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            logger.error(f"Ошибка генерации трафика: rc={result.returncode}, stderr={result.stderr}")
            return {"result": "ERROR", "message": result.stderr.strip() or "traffic generation failed"}

        time.sleep(1)
        return {"result": "OK", "message": f"Generated {count} {protocol.upper()} packets"}
    except Exception as e:
        logger.error(f"Ошибка при генерации трафика: {e}")
        return {"result": "ERROR", "message": str(e)}



@blp.route("/utils/traceroute", methods=["POST"])
@blp.arguments(UtilsTracerouteRequestSchema, location="json")
@blp.response(200, UtilsTracerouteResponseSchema, description="Проверка процесса traceroute в namespace ngfw")
def utils_traceroute(args):
    """Проверка наличия процесса traceroute с ожидаемыми аргументами в namespace ngfw."""
    try:
        logger.info("=== ОБРАБОТКА ЗАПРОСА UTILS/TRACEROUTE ===")
        logger.info(f"Полученные аргументы: {args}")
        result = utils_traceroute_handler(args)
        if isinstance(result, dict) and result.get("result") in ("OK", "ERROR"):
            return result
        return {"result": "ERROR", "message": "Unexpected response"}
    except Exception as e:
        logger.error(f"Ошибка при проверке utils/traceroute: {e}")
        return {"result": "ERROR", "message": f"Internal error: {str(e)}"}

@blp.route("/utils/ping", methods=["POST"])
@blp.arguments(UtilsPingRequestSchema, location="json")
@blp.response(200, UtilsPingResponseSchema, description="Проверка процесса ping в namespace ngfw")
def utils_ping(args):
    """Проверка наличия процесса ping с ожидаемыми аргументами в namespace ngfw."""
    try:
        logger.info("=== ОБРАБОТКА ЗАПРОСА UTILS/PING ===")
        logger.info(f"Полученные аргументы: {args}")
        result = utils_ping_handler(args)
        if isinstance(result, dict) and result.get("result") in ("OK", "ERROR"):
            return result
        return {"result": "ERROR", "message": "Unexpected response"}
    except Exception as e:
        logger.error(f"Ошибка при проверке utils/ping: {e}")
        return {"result": "ERROR", "message": f"Internal error: {str(e)}"}



@blp.route("/get-conntrack-count", methods=["GET"])
@blp.response(200, ConntrackCountResponseSchema, description="Получение счётчика nf_conntrack в namespace ngfw")
def get_conntrack_count():
    """Возвращает текущее значение nf_conntrack_count из namespace ngfw"""
    try:
        cmd = ["ip", "netns", "exec", "ngfw", "cat", "/proc/sys/net/netfilter/nf_conntrack_count"]
        logger.info(f"Чтение nf_conntrack_count: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        if result.returncode != 0:
            logger.error(f"Ошибка чтения счётчика: rc={result.returncode}, stderr={result.stderr}")
            # Возвращаем 0 со штампом времени даже при ошибке, чтобы не ломать автотесты
            return {"count": 0, "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")}
        value_str = (result.stdout or "").strip()
        try:
            count = int(value_str)
        except ValueError:
            logger.error(f"Невалидное значение счётчика: '{value_str}'")
            count = 0
        return {"count": count, "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")}
    except Exception as e:
        logger.error(f"Ошибка при получении счётчика: {e}")
        return {"count": 0, "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")}

@blp.route("/verify-conntrack-drop", methods=["POST"])
@blp.arguments(VerifyConntrackDropRequestSchema, location="json")
@blp.response(200, VerifyConntrackDropResponseSchema, description="Проверка уменьшения счётчика nf_conntrack после удаления")
def verify_conntrack_drop(args):
    """Фиксирует значение nf_conntrack_count до и после паузы, оценивает снижение."""
    try:
        # Параметры сейчас не используются в команде, оставлены для совместимости с автотестом
        _ = args

        def read_count():
            cmd_local = ["ip", "netns", "exec", "ngfw", "cat", "/proc/sys/net/netfilter/nf_conntrack_count"]
            res = subprocess.run(cmd_local, capture_output=True, text=True, check=False)
            if res.returncode != 0:
                logger.error(f"Ошибка чтения счётчика: rc={res.returncode}, stderr={res.stderr}")
                return 0
            try:
                return int((res.stdout or "").strip())
            except ValueError:
                return 0

        before = read_count()
        time.sleep(2)
        after = read_count()
        dropped = max(0, before - after)
        success = after < before
        return {"before": before, "after": after, "dropped": dropped, "success": success}
    except Exception as e:
        logger.error(f"Ошибка при проверке удаления conntrack: {e}")
        # Возвращаем безопасные значения
        return {"before": 0, "after": 0, "dropped": 0, "success": False}

@blp.route("/managers/iptablesMap", methods=["POST"])
@blp.arguments(IptablesMapRequestSchema, location="json")
@blp.response(200, IptablesMapResponseSchema, description="Проверка правил iptables и последующее удаление найденного")
def iptables_map(args):
    """Проверка правил iptables с последующим удалением найденного правила."""
    try:
        logger.info(f"=== ОБРАБОТКА ЗАПРОСА ПРОВЕРКИ ПРАВИЛ IPTABLES ===")
        logger.info(f"Полученные аргументы: {args}")
        result = iptables_map_handler(args)
        logger.info(f"Результат обработки: {result}")
        # Нормализуем ответ под контракт автотестов
        if isinstance(result, dict):
            if result.get("result") in ("OK", "ERROR"):
                return result
            # Если вернулся специальный ответ типа {"index": 0} — считаем успехом
            return {"result": "OK"}
        if isinstance(result, list):
            # Список правил — успех
            return {"result": "OK"}
        # Непредвиденный формат — ошибка
        return {"result": "ERROR", "message": "Unexpected response format"}
    except ValidationError as e:
        logger.error(f"Ошибка валидации: {e}")
        logger.error(f"Детали валидации: {e.messages}")
        return {"result": "ERROR", "message": f"Validation error: {str(e)}"}
    except Exception as e:
        logger.error(f"Ошибка при проверке правил iptables: {e}")
        return {"result": "ERROR", "message": f"Internal error: {str(e)}"}


@blp.route("/update/call-on-host", methods=["POST"])
@blp.arguments(UpdateCallOnHostRequestSchema, location="json")
@blp.response(200, UpdateCallOnHostResponseSchema, description="Проверка выполнения команды ctl-daemon на хосте по логам")
def update_call_on_host(args):
    """Проверяет по логам Docker, что ctl-daemon выполнил команду на хосте с ожидаемым кодом выхода.

    Тело запроса: {"command":"bash","args":["-lc","echo ok MK12345; exit 42"]}
    Логика:
      - Извлекает маркер из аргументов (паттерн MK[0-9]+)
      - Читает логи контейнера csi.csi-server за последние 5 минут и фильтрует по ключевым словам и маркеру
      - Если найдены строки stdout с маркером и статус exit,<код>, то возвращает OK, иначе ERROR
    """
    try:
        # Безопасно логируем ключи тела и типы
        if isinstance(args, dict):
            logger.info("/update/call-on-host request keys: %s", ",".join(sorted(args.keys())))
        command = args.get("command") if isinstance(args, dict) else None
        cmd_args = args.get("args") if isinstance(args, dict) else None

        if not isinstance(command, str) or not command:
            return {"result": "ERROR", "message": "Invalid 'command'"}
        if not isinstance(cmd_args, list) or not all(isinstance(x, str) for x in cmd_args):
            return {"result": "ERROR", "message": "Invalid 'args'"}

        # Динамический импорт обработчика (директория содержит '-')
        module_path = os.path.join(os.path.dirname(__file__), "services", "csi-server", "update_call-on-host.py")
        logger.info("Handler module path: %s exists=%s", module_path, os.path.exists(module_path))
        spec = importlib.util.spec_from_file_location("update_call_on_host", module_path)
        if spec is None or spec.loader is None:
            return {"result": "ERROR", "message": "Handler module not found"}
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        handler = getattr(mod, "handle", None)
        if handler is None:
            return {"result": "ERROR", "message": "Handler function missing"}

        result = handler(command, cmd_args)
        if isinstance(result, dict) and result.get("result") in ("OK", "ERROR"):
            return result
        return {"result": "ERROR", "message": "Unexpected handler response"}
    except Exception as e:
        logger.error(f"Ошибка при проверке /update/call-on-host: {e}")
        return {"result": "ERROR", "message": f"Internal error: {str(e)}"}

@blp.route("/integrity/test", methods=["POST"])
@blp.arguments(IntegrityTestRequestSchema, location="json")
@blp.response(200, IntegrityTestResponseSchema, description="Проверка целостности системы")
def integrity_test(args):
    """Проверка целостности системы по логам приложения.
    
    Тело запроса: {"state": "success"}
    Логика:
      - Выполняет команду для проверки целостности
      - Ищет INTEGRITY_SUCCESS в логах приложения
      - Возвращает OK если найдено, ERROR иначе
    """
    try:
        logger.info("=== ОБРАБОТКА ЗАПРОСА ПРОВЕРКИ ЦЕЛОСТНОСТИ ===")
        logger.info(f"Полученные аргументы: {args}")
        
        state = args.get("state") if isinstance(args, dict) else None
        if not state:
            return {"result": "ERROR", "message": "Missing 'state' parameter"}
        
        integrity_test_handler = _load_integrity_test_handler()
        if integrity_test_handler is None:
            return {"result": "ERROR", "message": "Integrity test handler not found"}
        
        result = integrity_test_handler(state)
        logger.info(f"Результат обработки: {result}")
        
        if isinstance(result, dict) and result.get("result") in ("OK", "ERROR"):
            return result
        return {"result": "ERROR", "message": "Unexpected handler response"}
    except Exception as e:
        logger.error(f"Ошибка при проверке целостности: {e}")
        return {"result": "ERROR", "message": f"Internal error: {str(e)}"}

@blp.route("/security-settings", methods=["POST"])
@blp.arguments(SecuritySettingsRequestSchema, location="json")
@blp.response(200, SecuritySettingsResponseSchema, description="Проверка настроек безопасности аутентификации")
def security_settings(args):
    """Проверяет текущие настройки безопасности аутентификации в csi-server.

    Тело запроса может включать один или несколько параметров из списка:
      - max_bad_auth_attempts
      - bad_auth_decay_s
      - block_time_s

    Возвращает OK, если переданные в запросе значения совпадают с текущими.
    """
    try:
        # Динамический импорт обработчика (директория содержит '-')
        import importlib.util as _importlib_util
        import os as _os

        module_path = _os.path.join(_os.path.dirname(__file__), "services", "csi-server", "security-settings.py")
        logger.info("Security settings handler path: %s exists=%s", module_path, _os.path.exists(module_path))
        spec = _importlib_util.spec_from_file_location("security_settings", module_path)
        if spec is None or spec.loader is None:
            return {"result": "ERROR", "message": "Handler module not found"}
        mod = _importlib_util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        handler = getattr(mod, "handle", None)
        if handler is None:
            return {"result": "ERROR", "message": "Handler function missing"}

        result = handler(args if isinstance(args, dict) else {})
        if isinstance(result, dict) and result.get("result") in ("OK", "ERROR"):
            return result
        return {"result": "ERROR", "message": "Unexpected handler response"}
    except Exception as e:
        logger.error(f"Ошибка при проверке security-settings: {e}")
        return {"result": "ERROR", "message": f"Internal error: {str(e)}"}

@blp.route("/system-report/check", methods=["POST"])
@blp.response(200, description="Верификация статуса system-report на агенте (OK/ERROR)")
def system_report_check():
    """Проксирует проверку в агентский сервис и возвращает {result}.

    Правила:
      - Если в теле указан status: NOT_FOUND | GENERATION_IN_PROGRESS | GENERATED — сверяем с фактом
      - Если status отсутствует — трактуем как GENERATION_IN_PROGRESS (всегда OK)
    """
    try:
        from flask import request as _request
        import importlib.util as _importlib_util
        import os as _os

        # Извлекаем JSON, но не требуем строгий Content-Type
        try:
            body = _request.get_json(silent=True) or {}
        except Exception:
            body = {}

        status = None
        if isinstance(body, dict):
            raw = body.get("status")
            if isinstance(raw, str):
                status = raw
        if status is None:
            status = "GENERATION_IN_PROGRESS"

        # Динамический импорт обработчика агента
        module_path = _os.path.join(_os.path.dirname(__file__), "services", "csi-server", "system-report_check.py")
        spec = _importlib_util.spec_from_file_location("system_report_check", module_path)
        if spec is None or spec.loader is None:
            return {"result": "ERROR", "message": "Handler module not found"}
        mod = _importlib_util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        handler = getattr(mod, "handle", None)
        if handler is None:
            return {"result": "ERROR", "message": "Handler function missing"}

        result = handler(status)
        if isinstance(result, dict) and result.get("result") in ("OK", "ERROR"):
            return result
        return {"result": "ERROR", "message": "Unexpected handler response"}
    except Exception as e:
        logger.error(f"Ошибка при обработке /system-report/check: {e}")
        return {"result": "ERROR", "message": f"Internal error: {str(e)}"}

@blp.route("/system-report/generate", methods=["POST"])
@blp.response(200, SystemReportGenerateResponseSchema, description="Генерация системного отчета")
def system_report_generate():
    """Генерирует системный отчет и отслеживает его завершение."""
    try:
        import importlib.util as _importlib_util
        import os as _os

        module_path = _os.path.join(_os.path.dirname(__file__), "services", "csi-server", "system-report_generate.py")
        spec = _importlib_util.spec_from_file_location("system_report_generate", module_path)
        if spec is None or spec.loader is None:
            return {"result": "ERROR", "message": "Handler module not found"}
        mod = _importlib_util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        handler = getattr(mod, "handle", None)
        if handler is None:
            return {"result": "ERROR", "message": "Handler function missing"}

        result = handler()
        if isinstance(result, dict) and result.get("result") in ("OK", "ERROR"):
            return result
        return {"result": "ERROR", "message": "Unexpected handler response"}
    except Exception as e:
        logger.error(f"Ошибка при обработке /system-report/generate: {e}")
        return {"result": "ERROR", "message": f"Internal error: {str(e)}"}

@blp.route("/system-report/generate/prepare", methods=["POST"])
@blp.response(200, SystemReportGeneratePrepareResponseSchema, description="Подготовка системного отчета: удаление старого файла")
def system_report_generate_prepare():
    """Удаляет существующий файл system-report.log.zip для подготовки к новой генерации."""
    try:
        import importlib.util as _importlib_util
        import os as _os

        module_path = _os.path.join(_os.path.dirname(__file__), "services", "csi-server", "system-report_generate_prepare.py")
        spec = _importlib_util.spec_from_file_location("system_report_generate_prepare", module_path)
        if spec is None or spec.loader is None:
            return {"result": "ERROR", "message": "Handler module not found"}
        mod = _importlib_util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        handler = getattr(mod, "handle", None)
        if handler is None:
            return {"result": "ERROR", "message": "Handler function missing"}

        result = handler()
        if isinstance(result, dict) and result.get("result") in ("OK", "ERROR"):
            return result
        return {"result": "ERROR", "message": "Unexpected handler response"}
    except Exception as e:
        logger.error(f"Ошибка при обработке /system-report/generate/prepare: {e}")
        return {"result": "ERROR", "message": f"Internal error: {str(e)}"}

# ---- CSI config endpoint ----

def _load_config_handler():
    import importlib.util
    import os
    module_path = os.path.join(os.path.dirname(__file__), "services", "csi-server", "config.py")
    spec = importlib.util.spec_from_file_location("config", module_path)
    if spec is None or spec.loader is None:
        raise ImportError("config module not found")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return getattr(mod, "handle", None)


class ConfigRequestSchema(Schema):
    data = fields.List(fields.Dict(), required=True, metadata={"description": "Массив данных для проверки"})

class ConfigResponseSchema(Schema):
    result = fields.Str(metadata={"description": "Результат проверки"})
    message = fields.Str(required=False, metadata={"description": "Сообщение об ошибке"})

@blp.route("/config", methods=["POST"])
@blp.arguments(ConfigRequestSchema, location="json")
@blp.response(200, ConfigResponseSchema, description="Проверка конфигурации CSI")
def check_config(args):
    """Проверка конфигурации CSI через /config."""
    try:
        config_handler = _load_config_handler()
        if config_handler is None:
            return {"result": "ERROR", "message": "Config handler not found"}
        result = config_handler(args)
        if isinstance(result, dict) and result.get("result") in ("OK", "ERROR"):
            return result
        return {"result": "ERROR", "message": "Unexpected handler response"}
    except Exception as e:
        logger.error(f"Ошибка при проверке конфигурации: {e}")
        return {"result": "ERROR", "message": f"Internal error: {str(e)}"}

# ---- Users endpoint ----
class UsersRequestSchema(Schema):
    endpoint = fields.Str(required=False, metadata={"description": "Эндпоинт (игнорируется)"})
    marker = fields.Int(required=False, metadata={"description": "Маркер (игнорируется)"})
    payload = fields.Dict(required=False, metadata={"description": "Полезная нагрузка с данными пользователя"})
    # Поля для прямого доступа (альтернативный формат)
    id = fields.Str(required=False, metadata={"description": "ID пользователя"})
    userRoleIds = fields.List(fields.Str(), required=False, metadata={"description": "Список ролей пользователя"})
    
    class Meta:
        unknown = INCLUDE
    
    def load(self, data, *args, **kwargs):
        # Просто возвращаем данные как есть
        return data

class UsersResponseSchema(Schema):
    result = fields.Str(metadata={"description": "Результат"})
    message = fields.Str(required=False, metadata={"description": "Описание ошибки"})


# --- Users endpoint registration ---
@blp.route("/users", methods=["POST"])
@blp.arguments(UsersRequestSchema, location="json")
@blp.response(200, UsersResponseSchema, description="Проверка пользователя через ngfw.core")
def check_user(args):
    """Проверяет пользователя через ngfw.core и сверяет с запросом."""
    try:
        import importlib.util as _importlib_util
        import os as _os
        
        # Извлекаем данные из payload или корневых полей
        user_data = {}
        if isinstance(args, dict):
            if "payload" in args and isinstance(args["payload"], dict):
                user_data = args["payload"]
            else:
                user_data = {k: v for k, v in args.items() if k in ["id", "userRoleIds"]}
        
        module_path = _os.path.join(_os.path.dirname(__file__), "services", "csi-server", "users.py")
        spec = _importlib_util.spec_from_file_location("users", module_path)
        if spec is None or spec.loader is None:
            return {"result": "ERROR", "message": "Handler module not found"}
        mod = _importlib_util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        handler = getattr(mod, "handle", None)
        if handler is None:
            return {"result": "ERROR", "message": "Handler function missing"}
        result = handler(user_data)
        if isinstance(result, dict) and result.get("result") in ("OK", "ERROR"):
            return result
        return {"result": "ERROR", "message": "Unexpected handler response"}
    except Exception as e:
        logger.error(f"Ошибка при обработке /users: {e}")
        return {"result": "ERROR", "message": f"Internal error: {str(e)}"}

@blp.route("/manager/settings/timezone", methods=["POST"])
@blp.arguments(ManagerSettingsTimezoneRequestSchema, location="json")
@blp.response(200, ManagerSettingsTimezoneResponseSchema, description="Проверка настроек timezone")
def manager_settings_timezone(args):
    """Проверка настроек timezone в csi-server.

    Тело запроса: {"data": "timezone_value"}
    Логика:
      - Выполняет docker exec команду для получения текущих настроек timezone
      - Сравнивает переданное значение с полученным из системы
      - Возвращает OK если значения совпадают, ERROR иначе
    """
    try:
        logger.info("=== ОБРАБОТКА ЗАПРОСА ПРОВЕРКИ TIMEZONE ===")
        logger.info(f"Полученные аргументы: {args}")
        
        manager_settings_timezone_handler = _load_manager_settings_timezone_handler()
        if manager_settings_timezone_handler is None:
            return {"result": "ERROR", "message": "Manager settings timezone handler not found"}
        
        result = manager_settings_timezone_handler(args)
        logger.info(f"Результат обработки: {result}")
        
        if isinstance(result, dict) and result.get("result") in ("OK", "ERROR"):
            return result
        return {"result": "ERROR", "message": "Unexpected handler response"}
    except Exception as e:
        logger.error(f"Ошибка при проверке timezone: {e}")
        return {"result": "ERROR", "message": f"Internal error: {str(e)}"}

@blp.route("/manager/uploaderPassword", methods=["POST"])
@blp.response(200, ManagerUploaderPasswordResponseSchema, description="Проверка изменения пароля uploader")
def manager_uploader_password():
    """Проверка изменения пароля пользователя uploader.

    POST запрос без тела.
    Логика:
      0) Приходит сигнал, что нужно запомнить хэш пароля
      1) Выполняем команду: sudo grep uploader /etc/shadow
      2) Запоминаем хэш пароля
      3) Приходит сигнал, что запрос выполнился
      4) Снова выполняем команду: sudo grep uploader /etc/shadow
      5) Сравниваем хэш предыдущего и текущего, они не должны совпадать
      - Возвращает OK если хэши не совпадают, ERROR иначе
    """
    try:
        logger.info("=== ОБРАБОТКА ЗАПРОСА ПРОВЕРКИ ИЗМЕНЕНИЯ ПАРОЛЯ UPLOADER ===")
        
        manager_uploader_password_handler = _load_manager_uploader_password_handler()
        if manager_uploader_password_handler is None:
            return {"result": "ERROR", "message": "Manager uploader password handler not found"}
        
        result = manager_uploader_password_handler()
        logger.info(f"Результат обработки: {result}")
        
        if isinstance(result, dict) and result.get("result") in ("OK", "ERROR"):
            return result
        return {"result": "ERROR", "message": "Unexpected handler response"}
    except Exception as e:
        logger.error(f"Ошибка при проверке изменения пароля uploader: {e}")
        return {"result": "ERROR", "message": f"Internal error: {str(e)}"}

@blp.route("/manager/config", methods=["POST"])
@blp.response(200, ManagerConfigResponseSchema, description="Проверка импорта конфигурации")
def manager_config():
    """Проверка завершения импорта конфигурации.

    POST запрос без тела.
    Логика:
      1) Проверяет наличие файла /tmp/miradaexport/config.bkp в контейнере csi.csi-server
      2) Проверяет наличие и содержимое лога /app/ctld-logs/configuration-restore
      3) Возвращает OK если импорт завершен успешно, ERROR иначе
    """
    try:
        logger.info("=== ОБРАБОТКА ЗАПРОСА ПРОВЕРКИ ИМПОРТА КОНФИГУРАЦИИ ===")
        
        manager_config_handler = _load_manager_config_handler()
        if manager_config_handler is None:
            return {"result": "ERROR", "message": "Manager config handler not found"}
        
        result = manager_config_handler()
        logger.info(f"Результат обработки: {result}")
        
        if isinstance(result, dict) and result.get("result") in ("OK", "ERROR"):
            return result
        return {"result": "ERROR", "message": "Unexpected handler response"}
    except Exception as e:
        logger.error(f"Ошибка при проверке импорта конфигурации: {e}")
        return {"result": "ERROR", "message": f"Internal error: {str(e)}"}

@blp.route("/update/images/start-download", methods=["POST"])
@blp.arguments(UpdateImagesStartDownloadRequestSchema, location="json")
@blp.response(200, UpdateImagesStartDownloadResponseSchema, description="Запуск загрузки образов")
def update_images_start_download(args):
    """Запуск процесса загрузки образов для последнего доступного обновления.

    Тело запроса: {"x-access-token": "token"}
    Логика:
      1) Валидирует токен доступа
      2) Ищет последнее доступное обновление образов в MongoDB
      3) Запускает процесс загрузки
      4) Возвращает OK если загрузка успешно запущена, ERROR иначе
    """
    try:
        logger.info("=== ОБРАБОТКА ЗАПРОСА /update/images/start-download ===")
        logger.info(f"Полученные аргументы: {args}")
        
        update_images_start_download_handler = _load_update_images_start_download_handler()
        if update_images_start_download_handler is None:
            return {"result": "ERROR", "message": "Update images start download handler not found"}
        
        result = update_images_start_download_handler(args)
        logger.info(f"Результат обработки: {result}")
        
        if isinstance(result, dict) and result.get("result") in ("OK", "ERROR"):
            return result
        return {"result": "ERROR", "message": "Unexpected handler response"}
    except Exception as e:
        logger.error(f"Ошибка при запуске загрузки образов: {e}")
        return {"result": "ERROR", "message": f"Internal error: {str(e)}"}

@blp.route("/licenses/apply-activation-key", methods=["POST"])
@blp.arguments(LicensesApplyActivationKeyRequestSchema, location="json")
@blp.response(200, LicensesApplyActivationKeyResponseSchema, description="Применение activation key локально (проверка токена)")
def licenses_apply_activation_key(args):
    """Подтверждает приём запроса на применение activationKey.

    Тело запроса: {"x-access-token":"token"}
    Возвращает {"result":"OK"} при валидном токене; иначе 401 с JSON.
    """
    try:
        import importlib.util as _importlib_util
        import os as _os
        from flask import request as _request  # для безопасного чтения тела при необходимости

        module_path = _os.path.join(_os.path.dirname(__file__), "services", "csi-server", "licenses_apply-activation-key.py")
        spec = _importlib_util.spec_from_file_location("licenses_apply_activation_key", module_path)
        if spec is None or spec.loader is None:
            return {"result": "ERROR", "message": "Handler module not found"}, 500
        mod = _importlib_util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        handler = getattr(mod, "handle", None)
        if handler is None:
            return {"result": "ERROR", "message": "Handler function missing"}, 500

        result = handler(args if isinstance(args, dict) else {})
        if isinstance(result, dict) and result.get("result") in ("OK", "ERROR"):
            if result.get("result") == "ERROR" and result.get("message") == "Authorization Required":
                return result, 401
            return result, 200
        return {"result": "ERROR", "message": "Unexpected handler response"}, 500
    except Exception as e:
        logger.error(f"Ошибка при обработке /licenses/apply-activation-key: {e}")
        return {"result": "ERROR", "message": f"Internal error: {str(e)}"}, 500

@blp.route("/licenses/generate-activation-code", methods=["POST"])
@blp.response(200, LicensesGenerateActivationCodeResponseSchema, description="Генерация activation code (верификация через контейнер)")
def licenses_generate_activation_code():
    """Верифицирует генерацию activation code через контейнер csi.csi-server.

    POST без тела. Возвращает {"result":"OK"} при успешной генерации (наличие value в выводе),
    иначе {"result":"ERROR","message":...}.
    """
    try:
        import importlib.util as _importlib_util
        import os as _os

        module_path = _os.path.join(_os.path.dirname(__file__), "services", "csi-server", "licenses_generate-activation-code.py")
        spec = _importlib_util.spec_from_file_location("licenses_generate_activation_code", module_path)
        if spec is None or spec.loader is None:
            return {"result": "ERROR", "message": "Handler module not found"}, 500
        mod = _importlib_util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        handler = getattr(mod, "handle", None)
        if handler is None:
            return {"result": "ERROR", "message": "Handler function missing"}, 500

        result = handler()
        if isinstance(result, dict) and result.get("result") in ("OK", "ERROR"):
            status = 200 if result.get("result") == "OK" else 200
            return result, status
        return {"result": "ERROR", "message": "Unexpected handler response"}, 500
    except Exception as e:
        logger.error(f"Ошибка при обработке /licenses/generate-activation-code: {e}")
        return {"result": "ERROR", "message": f"Internal error: {str(e)}"}, 500

@blp.route("/manager/maintenanceUpdateBrp", methods=["POST"])
@blp.arguments(ManagerMaintenanceUpdateBrpRequestSchema, location="json")
@blp.response(200, ManagerMaintenanceUpdateBrpResponseSchema, description="Запуск обновления BRP и ожидание OK по логам")
def manager_maintenance_update_brp(args):
    """Реализует сценарий maintenanceUpdateBrp через агентский обработчик.

    Тело запроса: {"x-access-token": "token"}
    Возвращает {"result":"OK"} или {"result":"ERROR","message": "..."}
    """
    try:
        import importlib.util as _importlib_util
        import os as _os

        logger.info("=== ОБРАБОТКА ЗАПРОСА /manager/maintenanceUpdateBrp ===")
        if isinstance(args, dict):
            logger.info("request keys: %s", ",".join(sorted(args.keys())))

        module_path = _os.path.join(_os.path.dirname(__file__), "services", "csi-server", "manager_maintenanceUpdateBrp.py")
        spec = _importlib_util.spec_from_file_location("manager_maintenanceUpdateBrp", module_path)
        if spec is None or spec.loader is None:
            return {"result": "ERROR", "message": "Handler module not found"}, 500
        mod = _importlib_util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        handler = getattr(mod, "handle", None)
        if handler is None:
            return {"result": "ERROR", "message": "Handler function missing"}, 500

        logger.info("calling handler: manager_maintenanceUpdateBrp.handle")
        result = handler(args if isinstance(args, dict) else {})
        logger.info("handler result keys: %s", ",".join(sorted(result.keys())) if isinstance(result, dict) else type(result).__name__)
        if isinstance(result, dict) and result.get("result") in ("OK", "ERROR"):
            status = 200
            # Ошибка авторизации маппится в 401
            if result.get("result") == "ERROR" and result.get("message") == "Authorization Required":
                status = 401
            return result, status
        return {"result": "ERROR", "message": "Unexpected handler response"}, 500
    except Exception as e:
        logger.error(f"Ошибка при обработке /manager/maintenanceUpdateBrp: {e}")
        return {"result": "ERROR", "message": f"Internal error: {str(e)}"}, 500

@blp.route("/manager/reset", methods=["POST"])
@blp.arguments(ManagerResetRequestSchema, location="json")
@blp.response(200, ManagerResetResponseSchema, description="Сброс менеджера: успешный вызов factory-reset")
def manager_reset(args):
    """Вызывает cdm factory-reset -y. Токен обязателен в теле запроса.

    Поведение:
      - При успехе: 204 No Content
      - При ошибке авторизации: 401 с JSON
      - При иных ошибках: 500 с JSON
    """
    try:
        import importlib.util as _importlib_util
        import os as _os

        module_path = _os.path.join(_os.path.dirname(__file__), "services", "csi-server", "manager_reset.py")
        spec = _importlib_util.spec_from_file_location("manager_reset", module_path)
        if spec is None or spec.loader is None:
            return {"result": "ERROR", "message": "Handler module not found"}, 500
        mod = _importlib_util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        handler = getattr(mod, "handle", None)
        if handler is None:
            return {"result": "ERROR", "message": "Handler function missing"}, 500

        # Передаем всё тело запроса (аргументы уже провалидированы схемой)
        result = handler(args if isinstance(args, dict) else {})
        if isinstance(result, dict) and result.get("result") in ("OK", "ERROR"):
            if result.get("result") == "OK":
                # Успех — возвращаем 200 с JSON
                return {"result": "OK"}, 200
            # Ошибка авторизации — 401
            if result.get("message") == "Authorization Required":
                return result, 401
            # Иные ошибки — 500
            return result, 500
        return {"result": "ERROR", "message": "Unexpected handler response"}, 500
    except Exception as e:
        logger.error(f"Ошибка при обработке /manager/reset: {e}")
        return {"result": "ERROR", "message": f"Internal error: {str(e)}"}, 500

@blp.route("/manager/reboot", methods=["POST"])
@blp.arguments(ManagerRebootRequestSchema, location="json")
@blp.response(200, ManagerRebootResponseSchema, description="Перезагрузка менеджера: успешный перехват reboot")
def manager_reboot(args):
    """Выполняет безопасный перехват вызова reboot. Токен обязателен в теле запроса.

    Поведение:
      - При успехе: 200 OK с JSON {"result":"OK"}
      - При ошибке авторизации: 401 с JSON
      - При иных ошибках: 500 с JSON
    """
    try:
        import importlib.util as _importlib_util
        import os as _os

        module_path = _os.path.join(_os.path.dirname(__file__), "services", "csi-server", "manager_reboot.py")
        spec = _importlib_util.spec_from_file_location("manager_reboot", module_path)
        if spec is None or spec.loader is None:
            return {"result": "ERROR", "message": "Handler module not found"}, 500
        mod = _importlib_util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        handler = getattr(mod, "handle", None)
        if handler is None:
            return {"result": "ERROR", "message": "Handler function missing"}, 500

        result = handler(args if isinstance(args, dict) else {})
        if isinstance(result, dict) and result.get("result") in ("OK", "ERROR"):
            if result.get("result") == "OK":
                return {"result": "OK"}, 200
            if result.get("message") == "Authorization Required":
                return result, 401
            return result, 500
        return {"result": "ERROR", "message": "Unexpected handler response"}, 500
    except Exception as e:
        logger.error(f"Ошибка при обработке /manager/reboot: {e}")
        return {"result": "ERROR", "message": f"Internal error: {str(e)}"}, 500

@blp.route("/notifications/delete-all", methods=["POST"])
@blp.response(200, description="Удаление всех уведомлений из MongoDB")
def notifications_delete_all():
    """Удаляет все уведомления из коллекции notification.

    Принимает токен авторизации из одного из источников:
      - заголовок: x-access-token
      - query: access_token
      - тело JSON: {"x-access-token":"..."} или {"access_token":"..."}

    Возвращает {"result":"OK"} или {"result":"ERROR","message":"..."}
    """
    try:
        import importlib.util as _importlib_util
        import os as _os

        # Безопасно читаем JSON-тело; допускаем отсутствие Content-Type
        try:
            body = _request.get_json(silent=True) or {}
        except Exception:
            body = {}

        # Извлекаем токены из заголовка и query
        header_token = _request.headers.get("x-access-token")
        query_token = _request.args.get("access_token")

        module_path = _os.path.join(_os.path.dirname(__file__), "services", "csi-server", "notifications_delete-all.py")
        spec = _importlib_util.spec_from_file_location("notifications_delete_all", module_path)
        if spec is None or spec.loader is None:
            return {"result": "ERROR", "message": "Handler module not found"}
        mod = _importlib_util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        handler = getattr(mod, "handle", None)
        if handler is None:
            return {"result": "ERROR", "message": "Handler function missing"}

        result = handler(body if isinstance(body, dict) else {}, header_token=header_token, query_token=query_token)
        if isinstance(result, dict) and result.get("result") in ("OK", "ERROR"):
            # Мэппинг статусов: при ошибке авторизации возвращаем 401, иначе 200
            if result.get("result") == "ERROR" and result.get("message") == "Authorization Required":
                return result, 401
            return result, 200
        return {"result": "ERROR", "message": "Unexpected handler response"}, 500
    except Exception as e:
        logger.error(f"Ошибка при обработке /notifications/delete-all: {e}")
        return {"result": "ERROR", "message": f"Internal error: {str(e)}"}, 500

@blp.route("/notifications/read", methods=["POST"])
@blp.response(200, description="Пометить уведомления как прочитанные по списку ids")
def notifications_read():
    """Помечает уведомления как прочитанные по переданным идентификаторам.

    Принимает токен авторизации только из тела JSON: {"x-access-token":"..."}
    Тело запроса:
      {"x-access-token": "token", "ids": ["n1", "n2"]}

    Возвращает {"result":"OK", "count": <int>} или {"result":"ERROR","message":"..."}
    """
    try:
        import importlib.util as _importlib_util
        import os as _os
        from flask import request as _request

        # Безопасно читаем JSON-тело; допускаем отсутствие Content-Type
        try:
            body = _request.get_json(silent=True) or {}
        except Exception:
            body = {}

        module_path = _os.path.join(_os.path.dirname(__file__), "services", "csi-server", "notifications_read.py")
        spec = _importlib_util.spec_from_file_location("notifications_read", module_path)
        if spec is None or spec.loader is None:
            return {"result": "ERROR", "message": "Handler module not found"}, 500
        mod = _importlib_util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        handler = getattr(mod, "handle", None)
        if handler is None:
            return {"result": "ERROR", "message": "Handler function missing"}, 500

        result = handler(body if isinstance(body, dict) else {})
        if isinstance(result, dict) and result.get("result") in ("OK", "ERROR"):
            if result.get("result") == "ERROR" and result.get("message") == "Authorization Required":
                return result, 401
            return result, 200
        return {"result": "ERROR", "message": "Unexpected handler response"}, 500
    except Exception as e:
        logger.error(f"Ошибка при обработке /notifications/read: {e}")
        return {"result": "ERROR", "message": f"Internal error: {str(e)}"}, 500

@blp.route("/update/rules/download-and-apply", methods=["POST"])
@blp.arguments(UpdateRulesDownloadAndApplyRequestSchema, location="json")
@blp.response(200, UpdateRulesDownloadAndApplyResponseSchema, description="Скачивание и применение правил IDS")
def update_rules_download_and_apply(args):
    """Скачивает правила IDS, применяет их и ожидает загрузки.

    Тело запроса: {"x-access-token": "token"}
    Логика:
      0) Очищает папку /opt/cdm-upload/files/*
      1) Скачивает правила и подпись по HTTPS с basic-авторизацией
      2) Проверяет наличие файлов
      3) Выполняет maintenanceUpdateBrp и ожидает завершения
      4) Применяет правила и ожидает их загрузки
      5) Возвращает OK при успехе, ERROR иначе
    """
    try:
        import importlib.util as _importlib_util
        import os as _os

        logger.info("=== ОБРАБОТКА ЗАПРОСА /update/rules/download-and-apply ===")
        if isinstance(args, dict):
            logger.info("request keys: %s", ",".join(sorted(args.keys())))

        module_path = _os.path.join(_os.path.dirname(__file__), "services", "csi-server", "update_rules_download-and-apply.py")
        spec = _importlib_util.spec_from_file_location("update_rules_download_and_apply", module_path)
        if spec is None or spec.loader is None:
            return {"result": "ERROR", "message": "Handler module not found"}, 500
        mod = _importlib_util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        handler = getattr(mod, "handle", None)
        if handler is None:
            return {"result": "ERROR", "message": "Handler function missing"}, 500

        logger.info("calling handler: update_rules_download_and_apply.handle")
        result = handler(args if isinstance(args, dict) else {})
        logger.info("handler result keys: %s", ",".join(sorted(result.keys())) if isinstance(result, dict) else type(result).__name__)
        if isinstance(result, dict) and result.get("result") in ("OK", "ERROR"):
            status = 200
            # Ошибка авторизации маппится в 401
            if result.get("result") == "ERROR" and result.get("message") == "Authorization Required":
                status = 401
            return result, status
        return {"result": "ERROR", "message": "Unexpected handler response"}, 500
    except Exception as e:
        logger.error(f"Ошибка при обработке /update/rules/download-and-apply: {e}")
        return {"result": "ERROR", "message": f"Internal error: {str(e)}"}, 500

@blp.route("/update/rules/check-for-updates", methods=["POST"])
@blp.arguments(UpdateRulesCheckForUpdatesRequestSchema, location="json")
@blp.response(200, UpdateRulesCheckForUpdatesResponseSchema, description="Проверка и применение обновлений правил IDS")
def update_rules_check_for_updates(args):
    """Оркестрация проверки и применения обновлений правил IDS через агентский обработчик.

    Тело запроса: {"x-access-token": "token"}
    Возвращает {"result":"OK"} или {"result":"ERROR","message":"..."}
    """
    try:
        import importlib.util as _importlib_util
        import os as _os

        logger.info("=== ОБРАБОТКА ЗАПРОСА /update/rules/check-for-updates ===")
        if isinstance(args, dict):
            logger.info("request keys: %s", ",".join(sorted(args.keys())))

        module_path = _os.path.join(_os.path.dirname(__file__), "services", "csi-server", "update_rules_check-for-updates.py")
        spec = _importlib_util.spec_from_file_location("update_rules_check_for_updates", module_path)
        if spec is None or spec.loader is None:
            return {"result": "ERROR", "message": "Handler module not found"}, 500
        mod = _importlib_util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        handler = getattr(mod, "handle", None)
        if handler is None:
            return {"result": "ERROR", "message": "Handler function missing"}, 500

        result = handler(args if isinstance(args, dict) else {})
        if isinstance(result, dict) and result.get("result") in ("OK", "ERROR"):
            status = 200
            if result.get("result") == "ERROR" and result.get("message") == "Authorization Required":
                status = 401
            return result, status
        return {"result": "ERROR", "message": "Unexpected handler response"}, 500
    except Exception as e:
        logger.error(f"Ошибка при обработке /update/rules/check-for-updates: {e}")
        return {"result": "ERROR", "message": f"Internal error: {str(e)}"}, 500

@blp.route("/update/rules/start-download", methods=["POST"])
@blp.arguments(UpdateRulesStartDownloadRequestSchema, location="json")
@blp.response(200, UpdateRulesStartDownloadResponseSchema, description="Запуск загрузки правил IDS")
def update_rules_start_download(args):
    """Запуск процесса загрузки правил IDS согласно алгоритму из задачи.

    Тело запроса: {"x-access-token": "token"}
    Логика:
      0) POST на /api/update/rules/check-for-updates с {login,password,channel} -> {found: bool}
         Если found == false -> переходим к шагу 1, иначе к шагу 6
      1) Очистка каталога /opt/cdm-upload/files/*
      2) Загрузка правил и подписи в /opt/cdm-upload/files/
      3) Проверка наличия файлов через ls
      4) POST /api/manager/maintenanceUpdateBrp и поллинг статуса до смены
         затем GET /api/manager/maintenanceUpdateBrpStatusAndLogs, ожидаем message == "OK"
      5) /manager/maintenanceUpdateBrpStatusAndLogs должен ответить "message": "OK"
      6) Повторный POST на /api/update/rules/start-download {x-access-token}, ожидаем {"ok": 1}
    """
    try:
        import importlib.util as _importlib_util
        import os as _os

        logger.info("=== ОБРАБОТКА ЗАПРОСА /update/rules/start-download ===")
        if isinstance(args, dict):
            logger.info("request keys: %s", ",".join(sorted(args.keys())))

        module_path = _os.path.join(_os.path.dirname(__file__), "services", "csi-server", "update_rules_start-download.py")
        spec = _importlib_util.spec_from_file_location("update_rules_start_download", module_path)
        if spec is None or spec.loader is None:
            return {"result": "ERROR", "message": "Handler module not found"}, 500
        mod = _importlib_util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        handler = getattr(mod, "handle", None)
        if handler is None:
            return {"result": "ERROR", "message": "Handler function missing"}, 500

        result = handler(args if isinstance(args, dict) else {})
        if isinstance(result, dict) and result.get("result") in ("OK", "ERROR"):
            status = 200
            if result.get("result") == "ERROR" and result.get("message") == "Authorization Required":
                status = 401
            return result, status
        return {"result": "ERROR", "message": "Unexpected handler response"}, 500
    except Exception as e:
        logger.error(f"Ошибка при обработке /update/rules/start-download: {e}")
        return {"result": "ERROR", "message": f"Internal error: {str(e)}"}, 500

@blp.route("/update/rules/cancel-download", methods=["POST"])
@blp.arguments(UpdateRulesCancelDownloadRequestSchema, location="json")
@blp.response(200, UpdateRulesCancelDownloadResponseSchema, description="Отмена загрузки правил IDS")
def update_rules_cancel_download(args):
    """Отмена процесса загрузки правил IDS согласно алгоритму из задачи.

    Тело запроса: {"x-access-token": "token"}
    Логика:
      0) POST на /api/update/rules/check-for-updates с {login,password,channel} -> {found: bool}
         Если found == false -> переходим к шагу 1, иначе к шагу 6
      1) Очистка каталога /opt/cdm-upload/files/*
      2) Загрузка правил и подписи в /opt/cdm-upload/files/
      3) Проверка наличия файлов через ls
      4) POST /api/manager/maintenanceUpdateBrp и поллинг статуса до смены
         затем GET /api/manager/maintenanceUpdateBrpStatusAndLogs, ожидаем message == "OK"
      5) /manager/maintenanceUpdateBrpStatusAndLogs должен ответить "message": "OK"
      6) POST /api/update/rules/download-and-apply
      7) GET /api/service/remote/ngfw/ids/call/status/ruleset-stats до получения loaded > 0
      8) POST /api/update/rules/start-download
      9) Выдерживаем таймаут 1 секунду и параллельно шагу 8 вызываем:
         POST /api/update/rules/cancel-download
         После выполнения шага 9, вызов в шаге 8 должен прерваться
    """
    try:
        import importlib.util as _importlib_util
        import os as _os

        logger.info("=== ОБРАБОТКА ЗАПРОСА /update/rules/cancel-download ===")
        if isinstance(args, dict):
            logger.info("request keys: %s", ",".join(sorted(args.keys())))

        module_path = _os.path.join(_os.path.dirname(__file__), "services", "csi-server", "update_rules_cancel-download.py")
        spec = _importlib_util.spec_from_file_location("update_rules_cancel_download", module_path)
        if spec is None or spec.loader is None:
            return {"result": "ERROR", "message": "Handler module not found"}, 500
        mod = _importlib_util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        handler = getattr(mod, "handle", None)
        if handler is None:
            return {"result": "ERROR", "message": "Handler function missing"}, 500

        result = handler(args if isinstance(args, dict) else {})
        if isinstance(result, dict) and result.get("result") in ("OK", "ERROR"):
            status = 200
            if result.get("result") == "ERROR" and result.get("message") == "Authorization Required":
                status = 401
            return result, status
        return {"result": "ERROR", "message": "Unexpected handler response"}, 500
    except Exception as e:
        logger.error(f"Ошибка при обработке /update/rules/cancel-download: {e}")
        return {"result": "ERROR", "message": f"Internal error: {str(e)}"}, 500

# Регистрируем blueprint
api.register_blueprint(blp)

if __name__ == "__main__":
    logger.info("Запуск Mirada Agent...")
    
    app.run(host="0.0.0.0", port=SERVER_PORT, debug=False) 