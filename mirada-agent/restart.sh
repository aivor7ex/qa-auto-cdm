#!/bin/bash

# Mirada Agent - Перезапуск с sudo
# Улучшенная версия с проверками и обработкой ошибок

echo "=== Mirada Agent - Перезапуск с sudo ==="

# Проверяем, запущен ли скрипт с sudo
if [ "$EUID" -ne 0 ]; then
    echo "ОШИБКА: Этот скрипт должен быть запущен с привилегиями root"
    echo "Запустите: sudo $0"
    exit 1
fi

echo "✓ Проверка привилегий root пройдена"

cd "$(dirname "$0")"

# Проверяем существование скриптов
if [ ! -f "./stop.sh" ]; then
    echo "ОШИБКА: Скрипт stop.sh не найден"
    exit 1
fi

if [ ! -f "./start.sh" ]; then
    echo "ОШИБКА: Скрипт start.sh не найден"
    exit 1
fi

# Проверяем права на выполнение
if [ ! -x "./stop.sh" ]; then
    echo "Устанавливаем права на выполнение для stop.sh..."
    chmod +x ./stop.sh
fi

if [ ! -x "./start.sh" ]; then
    echo "Устанавливаем права на выполнение для start.sh..."
    chmod +x ./start.sh
fi

echo "Останавливаем сервис..."
if ./stop.sh; then
    echo "✓ Сервис успешно остановлен"
else
    echo "Предупреждение: Возникли проблемы при остановке сервиса"
fi

# Небольшая пауза между остановкой и запуском
echo "Пауза перед запуском..."
sleep 3

echo "Запускаем сервис..."
if ./start.sh; then
    echo "✓ Сервис успешно запущен"
else
    echo "✗ ОШИБКА: Не удалось запустить сервис"
    exit 1
fi

echo ""
echo "=== Mirada Agent успешно перезапущен ===" 