import random
from telegram import __version__ as ptb_version
from telegram.ext import (
    ApplicationBuilder, ContextTypes, JobQueue, Job,
)
from telegram import ChatPermissions

# 🔁 Поменяй эти константы:
BOT_TOKEN   = ''
CHAT_ID     = -1001549779482  # ID группы, куда бот пригнан
MEMBERS_FILE = 'members.txt'  # файл из предыдущего шага

# очереди и состояние храним глобально
queue = []

async def start_once(context: ContextTypes.DEFAULT_TYPE):
    """
    Запускается сразу после старта приложения:
    - Загружает и тасует очередь
    - Запускает первый раунд
    """
    global queue
    # 1) Загружаем
    with open(MEMBERS_FILE, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            uid, nick = line.split(':', 1)
            uid = int(uid.strip())
            nick = nick.strip().lstrip('@')
            queue.append((uid, nick))
    # 2) Исключаем бота самого и админа (тебя) – бот API не умеет получать свой ID прямо,
    #    так что он не будет в списке, а тебя нужно вырезать вручную, если есть.
    #    (Если чат-мемберы.txt не содержит тебя, можно пропустить.)
    random.shuffle(queue)

    # 3) Запускаем первый раунд
    await process_next(context.job_queue, context)


async def process_next(jq: JobQueue, context: ContextTypes.DEFAULT_TYPE):
    """
    Берёт следующего жертву из очереди, уведомляет её и планирует бан через 2 часа.
    """
    global queue
    if not queue:
        # очередь кончилась
        await context.bot.send_message(
            CHAT_ID,
            "🎉 Готово! В группе больше нет никого, кроме вас и бота."
        )
        return

    uid, nick = queue.pop(0)
    # формируем текст уведомления
    if queue:
        next_nick = queue[0][1]
        next_msg = f"@{next_nick} – ты следующий! Ты будешь забанен через 2 часа"
    else:
        next_msg = ""
    text = f"@{nick} ЗАБАНЕН!!! {next_msg}"

    # отправляем уведомление
    await context.bot.send_message(CHAT_ID, text)
    print(f"[Notify] {nick} → ban in 2h")

    # запланировать бан через 2 часа
    jq.run_once(ban_user, when=2 * 3600, data={'user_id': uid, 'nick': nick})


async def ban_user(context: ContextTypes.DEFAULT_TYPE):
    """
    Банит участника и запускает следующий раунд уведомления.
    """
    data = context.job.data
    uid = data['user_id']
    nick = data['nick']
    try:
        await context.bot.ban_chat_member(
            chat_id=CHAT_ID,
            user_id=uid
        )
        print(f"[Banned] {nick} ({uid})")
    except Exception as e:
        print(f"[Error ban] {nick} ({uid}): {e}")

    # после бана — уведомляем следующего
    await process_next(context.job_queue, context)


if __name__ == '__main__':
    # Проверим версию
    print("python-telegram-bot version:", ptb_version)

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # запустим наш «один раз» сразу после старта
    # (delay=0 означает выполнить сразу)
    app.job_queue.run_once(start_once, when=0)

    # стартуем лонг-поллинг
    app.run_polling()
