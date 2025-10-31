"""
===================================================================================
TUNNEL_MANAGER - Менеджер SSH туннелей для TCP port forwarding
===================================================================================

Предоставляет кросс-платформенный интерфейс для управления SSH туннелями,
используя subprocess для запуска OpenSSH клиента.

ФУНКЦИОНАЛЬНОСТЬ:
- Создание SSH туннелей с локальным port forwarding (ssh -L)
- Мониторинг состояния туннелей и портов
- Корректное закрытие SSH процессов
- Автоматический поиск SSH клиента в системе

ПЛАТФОРМЫ:
- Linux/Unix: Использование os.setsid для изоляции процессов
- Windows: CREATE_NEW_PROCESS_GROUP для управления процессами

ЗАВИСИМОСТИ:
- OpenSSH клиент (ssh executable)
- Настроенная SSH аутентификация (passwordless через ключи)

ИСПОЛЬЗОВАНИЕ:
    manager = SSHTunnelManager("192.168.1.100", username="user")
    manager.create_tunnel("service", local_port=8000, remote_port=8000)
    manager.close_tunnel("service", local_port=8000)
===================================================================================
"""
import subprocess
import socket
import logging
import platform
import os

logger = logging.getLogger(__name__)

IS_WINDOWS = platform.system() == "Windows"
IS_UNIX = not IS_WINDOWS


class SSHTunnelManager:
    """
    Менеджер для создания и управления SSH туннелями с локальным port forwarding.

    АТРИБУТЫ:
        mirada_host: str - IP адрес или hostname SSH jump сервера
        username: str - Имя пользователя для SSH аутентификации
        tunnels: dict[str, subprocess.Popen] - Активные SSH процессы
            Ключ: "{service_name}_{local_port}"
            Значение: Popen объект SSH процесса

    МЕХАНИЗМ РАБОТЫ:
        1. Запуск SSH процесса с опцией -L для локального forwarding
        2. Мониторинг доступности локального порта (socket connection test)
        3. Хранение ссылок на subprocess.Popen для управления жизненным циклом
        4. Корректное завершение процессов при закрытии туннелей
    """

    def __init__(self, mirada_host: str, username: str = "codemaster"):
        """
        Инициализирует менеджер SSH туннелей.

        ПАРАМЕТРЫ:
            mirada_host: str - IP адрес SSH сервера для tunneling
            username: str - Пользователь SSH (по умолчанию "codemaster")
        """
        self.mirada_host = mirada_host
        self.username = username
        self.tunnels = {}

    def _test_agent_health(self, local_port: int) -> bool:
        """
        Проверяет доступность агента через тестирование TCP соединения.

        ПАРАМЕТРЫ:
            local_port: int - Локальный порт для проверки

        ВОЗВРАЩАЕТ:
            bool: True если порт доступен для соединения
        """
        return self._is_port_available(local_port)

    def _is_port_available(self, port: int) -> bool:
        """
        Проверяет доступность TCP порта через socket connection.

        МЕХАНИЗМ:
            Попытка установить TCP соединение к 127.0.0.1:<port>
            с таймаутом 1 секунда.

        ПАРАМЕТРЫ:
            port: int - Номер TCP порта для проверки

        ВОЗВРАЩАЕТ:
            bool: True если порт принимает соединения (туннель активен)
        """
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                return s.connect_ex(('127.0.0.1', port)) == 0
        except Exception:
            return False

    def _get_ssh_executable(self):
        """
        Выполняет поиск исполняемого файла OpenSSH клиента в системе.

        АЛГОРИТМ:
            1. Проход по списку типичных путей установки SSH
            2. Попытка выполнения 'ssh -V' для валидации
            3. Проверка наличия 'OpenSSH' в stderr или успешного returncode

        ПУТИ ПОИСКА:
            - Unix: /usr/bin/ssh, /usr/local/bin/ssh
            - Windows: C:\\Windows\\System32\\OpenSSH\\ssh.exe
            - Git for Windows: C:\\Program Files\\Git\\usr\\bin\\ssh.exe

        ВОЗВРАЩАЕТ:
            str | None: Абсолютный путь к ssh executable или None при отсутствии
        """
        candidates = [
            'ssh',
            'C:\\Windows\\System32\\OpenSSH\\ssh.exe',
            'C:\\Program Files\\Git\\usr\\bin\\ssh.exe',
            'C:\\Program Files (x86)\\Git\\usr\\bin\\ssh.exe',
            '/usr/bin/ssh',
            '/usr/local/bin/ssh',
        ]
        for path in candidates:
            try:
                result = subprocess.run([path, '-V'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=5)
                if result.returncode == 0 or b'OpenSSH' in result.stderr:
                    return path
            except Exception:
                continue
        return None

    def create_tunnel(self, service_name: str, local_port: int, remote_port: int, remote_host: str = "127.0.0.1") -> bool:
        """
        Создаёт SSH туннель с локальным port forwarding.

        МЕХАНИЗМ:
            Выполнение команды: ssh -N -L 127.0.0.1:<local_port>:<remote_host>:<remote_port> user@jump_host

        АЛГОРИТМ:
            1. Проверка существования активного туннеля с идентичным ключом
            2. Поиск SSH executable в системе
            3. Формирование команды SSH с параметрами forwarding
            4. Запуск subprocess.Popen с платформо-зависимыми опциями
            5. Polling проверка доступности локального порта (5 попыток, 2s интервал)
            6. Регистрация Popen объекта в self.tunnels при успехе

        ОПЦИИ SSH:
            -N: Не выполнять удалённую команду (только forwarding)
            -L: Спецификация локального forwarding
            -o BatchMode=yes: Отключение интерактивных промптов
            -o StrictHostKeyChecking=no: Автоматическое добавление host keys

        ПАРАМЕТРЫ:
            service_name: str - Логическое имя сервиса для идентификации
            local_port: int - Локальный порт для bind (127.0.0.1:<local_port>)
            remote_port: int - Порт на удалённой стороне туннеля
            remote_host: str - IP адрес целевого хоста (по умолчанию "127.0.0.1")

        ВОЗВРАЩАЕТ:
            bool: True при успешном создании туннеля и доступности порта

        ПОБОЧНЫЕ ЭФФЕКТЫ:
            Создание фонового SSH процесса и регистрация в self.tunnels
        """
        tunnel_key = f"{service_name}_{local_port}"
        if tunnel_key in self.tunnels:
            proc = self.tunnels[tunnel_key]
            if proc.poll() is None:
                logger.info(f"Tunnel {tunnel_key} already running")
                return True
            else:
                del self.tunnels[tunnel_key]

        ssh_exe = self._get_ssh_executable()
        if not ssh_exe:
            logger.error("SSH client not found.")
            return False

        ssh_cmd = [
            ssh_exe,
            "-N",
            "-L", f"127.0.0.1:{local_port}:{remote_host}:{remote_port}",
            "-o", "BatchMode=yes",
            "-o", "StrictHostKeyChecking=no",
            f"{self.username}@{self.mirada_host}"
        ]
        if IS_WINDOWS:
            ssh_cmd += ["-o", "UserKnownHostsFile=NUL"]
        else:
            ssh_cmd += ["-o", "UserKnownHostsFile=/dev/null"]

        popen_kwargs = {
            'stdout': subprocess.PIPE,
            'stderr': subprocess.PIPE,
            'stdin': subprocess.PIPE,
        }
        if IS_UNIX and hasattr(os, 'setsid'):
            popen_kwargs['preexec_fn'] = os.setsid
        elif IS_WINDOWS:
            popen_kwargs['creationflags'] = subprocess.CREATE_NEW_PROCESS_GROUP

        try:
            proc = subprocess.Popen(ssh_cmd, **popen_kwargs)
            for _ in range(5):
                if proc.poll() is None and self._is_port_available(local_port):
                    self.tunnels[tunnel_key] = proc
                    logger.info(f"Tunnel {tunnel_key} created (PID: {proc.pid})")
                    return True
                else:
                    logger.info(f"Waiting for tunnel {tunnel_key}...")
                    import time; time.sleep(2)
            proc.terminate()
            logger.error(f"Tunnel {tunnel_key} failed to start.")
            return False
        except Exception as e:
            logger.error(f"Error creating tunnel: {e}")
            return False

    def close_tunnel(self, service_name: str, local_port: int) -> bool:
        """
        Завершает SSH туннель и удаляет его из реестра активных туннелей.

        АЛГОРИТМ:
            1. Поиск туннеля по ключу "{service_name}_{local_port}"
            2. Проверка состояния процесса (proc.poll())
            3. Вызов proc.terminate() для корректного завершения SSH
            4. Удаление записи из self.tunnels

        ПАРАМЕТРЫ:
            service_name: str - Логическое имя сервиса
            local_port: int - Локальный порт туннеля

        ВОЗВРАЩАЕТ:
            bool: True при успешном закрытии или отсутствии туннеля

        ПРИМЕЧАНИЕ:
            Использует terminate() вместо kill() для корректного
            завершения SSH процесса и освобождения портов.
        """
        tunnel_key = f"{service_name}_{local_port}"
        if tunnel_key not in self.tunnels:
            logger.info(f"Tunnel {tunnel_key} not found.")
            return True
        proc = self.tunnels[tunnel_key]
        try:
            if proc.poll() is None:
                proc.terminate()
            del self.tunnels[tunnel_key]
            logger.info(f"Tunnel {tunnel_key} closed.")
            return True
        except Exception as e:
            logger.error(f"Error closing tunnel: {e}")
            return False
