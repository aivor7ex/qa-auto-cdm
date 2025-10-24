#!/bin/bash

# Mirada Agent - Полная установка и запуск с sudo
# Улучшенная версия с поддержкой различных вариантов Python

echo "=== Mirada Agent - Полная установка и запуск с sudo ==="

# Проверяем, запущен ли скрипт с sudo
if [ "$EUID" -ne 0 ]; then
    echo "ОШИБКА: Этот скрипт должен быть запущен с привилегиями root"
    echo "Запустите: sudo $0"
    exit 1
fi

echo "✓ Проверка привилегий root пройдена"

cd "$(dirname "$0")"

# Останавливаем предыдущий процесс, если запущен
if [ -f "mirada-agent.pid" ]; then
    PID=$(cat mirada-agent.pid)
    if ps -p $PID > /dev/null 2>&1; then
        echo "Останавливаем предыдущий процесс (PID: $PID)..."
        kill $PID
        sleep 2
    fi
    rm -f mirada-agent.pid
fi

# Функция для поиска доступного Python
find_python() {
    local python_cmd=""
    
    # Список возможных команд Python в порядке приоритета
    local python_commands=("python3" "python" "py" "python3.11" "python3.10" "python3.9" "python3.8")
    
    for cmd in "${python_commands[@]}"; do
        if command -v "$cmd" > /dev/null 2>&1; then
            # Проверяем версию
            local version=$("$cmd" --version 2>&1)
            if [[ $? -eq 0 ]]; then
                echo "Найден Python: $cmd - $version" >&2
                python_cmd="$cmd"
                break
            fi
        fi
    done
    
    if [ -z "$python_cmd" ]; then
        echo "ОШИБКА: Python не найден на системе"
        echo "Установите Python 3.7+ и попробуйте снова"
        echo "Доступные команды для проверки:"
        for cmd in "${python_commands[@]}"; do
            echo "  - $cmd"
        done
        exit 1
    fi
    
    echo "$python_cmd"
}

# Функция для проверки версии Python
check_python_version() {
    local python_cmd="$1"
    local version_output=$("$python_cmd" --version 2>&1)
    local version=$(echo "$version_output" | grep -oE '[0-9]+\.[0-9]+' | head -1)
    
    if [ -z "$version" ]; then
        echo "ОШИБКА: Не удалось определить версию Python"
        exit 1
    fi
    
    local major_version=$(echo "$version" | cut -d. -f1)
    local minor_version=$(echo "$version" | cut -d. -f2)
    
    if [ "$major_version" -lt 3 ] || ([ "$major_version" -eq 3 ] && [ "$minor_version" -lt 7 ]); then
        echo "ОШИБКА: Требуется Python 3.7+, найдена версия $version"
        exit 1
    fi
    
    echo "✓ Версия Python $version поддерживается"
}

# Функция для поиска доступного pip
find_pip() {
    local python_cmd="$1"
    local pip_cmd=""
    
    # Список возможных команд pip
    local pip_commands=("pip3" "pip" "pip3.11" "pip3.10" "pip3.9" "pip3.8")
    
    for cmd in "${pip_commands[@]}"; do
        if command -v "$cmd" > /dev/null 2>&1; then
            pip_cmd="$cmd"
            break
        fi
    done
    
    # Если pip не найден, пробуем через python -m pip
    if [ -z "$pip_cmd" ]; then
        if "$python_cmd" -m pip --version > /dev/null 2>&1; then
            pip_cmd="$python_cmd -m pip"
        fi
    fi
    
    if [ -z "$pip_cmd" ]; then
        echo "ОШИБКА: pip не найден на системе"
        echo "Установите pip и попробуйте снова"
        exit 1
    fi
    
    echo "$pip_cmd"
}

# Находим Python
echo "Поиск Python..."
PYTHON_CMD=$(find_python)
check_python_version "$PYTHON_CMD"

# Находим pip
echo "Поиск pip..."
PIP_CMD=$(find_pip "$PYTHON_CMD") || true

if [ -z "$PIP_CMD" ]; then
    echo "pip не найден. Попытка установить python3-pip..."
    if command -v apt-get > /dev/null 2>&1; then
        apt-get update -y >/dev/null 2>&1 || true
        apt-get install -y python3-pip >/dev/null 2>&1 || true
    fi
    # повторная попытка поиска pip
    PIP_CMD=$(find_pip "$PYTHON_CMD") || true
fi

echo "Используем: $PYTHON_CMD"
echo "Используем pip: ${PIP_CMD:-<не найден>}"

# Удаляем старое виртуальное окружение, если есть
if [ -d "venv" ]; then
    echo "Удаляем старое виртуальное окружение..."
    rm -rf venv
fi

# Создаем новое виртуальное окружение
echo "Создание виртуального окружения..."
if ! "$PYTHON_CMD" -m venv venv 2>/dev/null; then
    echo "Не удалось создать venv. Пробуем установить python3-venv..."
    if command -v apt-get > /dev/null 2>&1; then
        apt-get update -y >/dev/null 2>&1 || true
        # пробуем установить точную версию venv для текущего python
        PY_MINOR=$("$PYTHON_CMD" -c 'import sys;print(f"{sys.version_info.major}.{sys.version_info.minor}")')
        apt-get install -y "python${PY_MINOR}-venv" >/dev/null 2>&1 || apt-get install -y python3-venv >/dev/null 2>&1 || true
    fi
    # повторная попытка
    if ! "$PYTHON_CMD" -m venv venv 2>/dev/null; then
        echo "ОШИБКА: не удалось создать виртуальное окружение (ensurepip недоступен). Установите пакет python3-venv и повторите."
        echo "Подсказка: sudo apt install -y python${PY_MINOR}-venv"
        exit 1
    fi
fi

"$(pwd)/venv/bin/python" -m ensurepip --upgrade >/dev/null 2>&1 || true

# Активируем виртуальное окружение
source venv/bin/activate
PYTHON_CMD="$(pwd)/venv/bin/python"
PIP_CMD="$(pwd)/venv/bin/pip"

# Обновляем pip
echo "Обновление pip..."
if ! "$PYTHON_CMD" -m pip install --upgrade pip; then
    echo "Не удалось обновить pip через бинарь, пробуем через python -m pip"
    "$PYTHON_CMD" -m ensurepip --upgrade || true
    "$PYTHON_CMD" -m pip install --upgrade pip
fi

# Устанавливаем зависимости
echo "Установка зависимостей..."
"$PYTHON_CMD" -m pip install --no-cache-dir -r requirements.txt

# Проверяем установку
echo "Провка установки..."
"$PYTHON_CMD" -c "
import sys
print(f'Python версия: {sys.version}')

try:
    import flask
    print(f'✓ Flask установлен: {flask.__version__}')
except ImportError as e:
    print(f'✗ Flask не установлен: {e}')
    sys.exit(1)

try:
    import flask_smorest
    print(f'✓ Flask-Smorest установлен')
except ImportError as e:
    print(f'✗ Flask-Smorest не установлен: {e}')
    sys.exit(1)

try:
    import marshmallow
    print(f'✓ Marshmallow установлен: {marshmallow.__version__}')
except ImportError as e:
    print(f'✗ Marshmallow не установлен: {e}')
    sys.exit(1)

print('✓ Все модули установлены успешно')
"

if [ $? -ne 0 ]; then
    echo "✗ Проблема с установкой зависимостей"
    exit 1
fi

# Определяем порт
PORT=${MIRADA_PORT:-8000}

# Агрессивно освобождаем порт
echo "Освобождение порта $PORT..."
PORT_IN_USE=false

# Функция для освобождения порта
free_port() {
    local port="$1"
    
    # Способ 1: через lsof
    if command -v lsof > /dev/null 2>&1; then
        local pids=$(lsof -ti:$port 2>/dev/null)
        if [ ! -z "$pids" ]; then
            echo "Найдены процессы на порту $port: $pids"
            echo "Принудительно останавливаем..."
            echo $pids | xargs kill -9
            return 0
        fi
    fi
    
    # Способ 2: через netstat
    if command -v netstat > /dev/null 2>&1; then
        local pids=$(netstat -tlnp 2>/dev/null | grep ":$port" | awk '{print $7}' | cut -d'/' -f1 | grep -v "-")
        if [ ! -z "$pids" ]; then
            echo "Найдены процессы на порту $port: $pids"
            echo "Принудительно останавливаем..."
            echo $pids | xargs kill -9
            return 0
        fi
    fi
    
    # Способ 3: через ss
    if command -v ss > /dev/null 2>&1; then
        local pids=$(ss -tlnp 2>/dev/null | grep ":$port" | awk '{print $7}' | cut -d'/' -f1 | grep -v "-")
        if [ ! -z "$pids" ]; then
            echo "Найдены процессы на порту $port: $pids"
            echo "Принудительно останавливаем..."
            echo $pids | xargs kill -9
            return 0
        fi
    fi
    
    return 1
}

# Освобождаем порт
if free_port "$PORT"; then
    PORT_IN_USE=true
fi

# Дополнительная проверка и очистка
if [ "$PORT_IN_USE" = true ]; then
    sleep 3
    # Повторная проверка
    if free_port "$PORT"; then
        echo "Повторная очистка порта $PORT..."
        sleep 2
    fi
fi

# Запускаем в фоне с перенаправлением вывода
echo "Запуск агента с привилегиями root..."
nohup "$PYTHON_CMD" main.py > mirada-agent.log 2>&1 &
PID=$!

# Сохраняем PID
echo $PID > mirada-agent.pid

sudo chown -R codemaster:codemaster .

echo ""
echo "=== Mirada Agent успешно установлен и запущен с sudo ==="
echo "PID: $PID"
echo "Python: $PYTHON_CMD"
echo "Порт: $PORT"
echo "Логи: tail -f mirada-agent.log"
echo "Остановка: sudo ./stop.sh"
echo "Перезапуск: sudo ./restart.sh"
echo ""
echo "ВНИМАНИЕ: Сервис запущен с привилегиями root"
echo "   - Убедитесь, что доступ к API защищен"
echo "   - Используйте HTTPS в продакшене"
echo "   - Регулярно проверяйте логи на подозрительную активность"

# Автоматически показываем логи
echo ""
echo "=== Автоматический просмотр логов ==="
echo "Нажмите Ctrl+C для выхода из просмотра логов"
echo ""

# Ждем немного чтобы логи появились
sleep 2

if [ -f "mirada-agent.log" ]; then
    tail -f mirada-agent.log
else
    echo "Файл логов не найден"
fi 