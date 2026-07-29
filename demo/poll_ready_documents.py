"""
Демо-скрипт: опрашивает GET /documents/ready каждые N секунд и печатает
готовые группы документов. Использовать так:

1. Поднять сервис (docker-compose up).
2. Написать боту в Telegram несколько фото с одного аккаунта, часть с паузой
   меньше GROUP_TIMEOUT_MINUTES (попадут в одну группу), часть с большей
   паузой (попадут в разные группы).
3. Запустить этот скрипт и подождать: как только группа "остынет"
   (истечёт таймаут), она появится в выводе.
4. Скрипт автоматически подтверждает получение (ack), группа больше
   не будет отдаваться повторно.
"""

import time

import httpx

BASE_URL = "http://localhost:8000"
POLL_INTERVAL_SECONDS = 15


def main():
    print(f"Опрашиваю {BASE_URL}/documents/ready каждые {POLL_INTERVAL_SECONDS} сек. Ctrl+C для выхода.")
    while True:
        resp = httpx.get(f"{BASE_URL}/documents/ready")
        resp.raise_for_status()
        groups = resp.json()

        if not groups:
            print("Готовых групп пока нет...")
        else:
            for group in groups:
                print(f"\nГруппа {group['id']} (отправитель {group['sender_id']}):")
                for f in group["files"]:
                    print(f"  - {f['local_path']} [{f['download_status']}]")

                ack = httpx.post(f"{BASE_URL}/documents/{group['id']}/ack")
                print(f"  ack -> {ack.json()['status']}")

        time.sleep(POLL_INTERVAL_SECONDS)


if __name__ == "__main__":
    main()
