#!/bin/bash

# Mirada Agent - Полная остановка и очистка с sudo
# Улучшенная версия с поддержкой различных систем

echo "=== Mirada Agent - Полная остановка и очистка с sudo ==="

# Проверяем, запущен ли скрипт с sudo
if [ "$EUID" -ne 0 ]; then
    echo "ОШИБКА: Этот скрипт должен быть запущен с привилегиями root"
    echo "Запустите: sudo $0"
    exit 1
fi

echo "✓ Проверка привилегий root пройдена"

cd "$(dirname "$0")"

# Определяем порт
PORT=${MIRADA_PORT:-8000}

# Функция для освобождения порта
free_port() {
    local port="$1"
    
    # Способ 1: через lsof
    if command -v lsof > /dev/null 2>&1; then
        local pids=$(lsof -ti:$port 2>/dev/null)
        if [ ! -z "$pids" ]; then
            echo "Найдены процессы на порту $port: $pids"
            echo "Останавливаем..."
            echo $pids | xargs kill -9
            return 0
        fi
    fi
    
    # Способ 2: через netstat
    if command -v netstat > /dev/null 2>&1; then
        local pids=$(netstat -tlnp 2>/dev/null | grep ":$port" | awk '{print $7}' | cut -d'/' -f1 | grep -v "-")
        if [ ! -z "$pids" ]; then
            echo "Найдены процессы на порту $port: $pids"
            echo "Останавливаем..."
            echo $pids | xargs kill -9
            return 0
        fi
    fi
    
    # Способ 3: через ss
    if command -v ss > /dev/null 2>&1; then
        local pids=$(ss -tlnp 2>/dev/null | grep ":$port" | awk '{print $7}' | cut -d'/' -f1 | grep -v "-")
        if [ ! -z "$pids" ]; then
            echo "Найдены процессы на порту $port: $pids"
            echo "Останавливаем..."
            echo $pids | xargs kill -9
            return 0
        fi
    fi
    
    return 1
}

# Останавливаем процесс по PID файлу
if [ -f "mirada-agent.pid" ]; then
    PID=$(cat mirada-agent.pid)
    
    if ps -p $PID > /dev/null 2>&1; then
        echo "Останавливаем процесс (PID: $PID)..."
        kill $PID
        
        # Ждем завершения
        for i in {1..10}; do
            if ! ps -p $PID > /dev/null 2>&1; then
                echo "Процесс остановлен"
                break
            fi
            sleep 1
        done
        
        # Принудительная остановка
        if ps -p $PID > /dev/null 2>&1; then
            echo "Принудительная остановка..."
            kill -9 $PID
            echo "Процесс принудительно остановлен"
        fi
    else
        echo "Процесс не найден (PID: $PID)"
    fi
    rm -f mirada-agent.pid
else
    echo "PID файл не найден"
fi

# Дополнительно останавливаем все процессы на порту
echo "Проверка и очистка порта $PORT..."

if free_port "$PORT"; then
    echo "Процессы на порту $PORT остановлены"
else
    echo "Порт $PORT свободен"
fi

# Финальная проверка порта
sleep 2
if free_port "$PORT"; then
    echo "Порт $PORT все еще занят. Финальная очистка..."
else
    echo "Порт $PORT освобожден"
fi

# Удаляем виртуальное окружение
echo "Удаление виртуального окружения..."
if [ -d "venv" ]; then
    rm -rf venv
    echo "Виртуальное окружение удалено"
else
    echo "Виртуальное окружение не найдено"
fi

# Очищаем кеши pip
echo "Очистка кешей pip..."
if command -v pip > /dev/null 2>&1; then
    pip cache purge 2>/dev/null || echo "Кеш pip очищен"
elif command -v pip3 > /dev/null 2>&1; then
    pip3 cache purge 2>/dev/null || echo "Кеш pip3 очищен"
fi

# Удаляем логи
echo "Удаление логов..."
rm -f mirada-agent.log
rm -f *.log

# Удаляем временные файлы
echo "Удаление временных файлов..."
rm -f *.pid
rm -f *.tmp

# Очищаем кеши Python
echo "Очистка кешей Python..."
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true
find . -name "*.pyo" -delete 2>/dev/null || true

echo ""
echo "=== Mirada Agent полностью остановлен и очищен ==="
echo "Для запуска: sudo ./start.sh" 