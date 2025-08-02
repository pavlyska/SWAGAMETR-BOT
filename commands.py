import telebot
import uuid
from datetime import datetime, timedelta
from base import cursor, conn
from app import bot, ADMIN_ID, main_menu , CHANNEL_USERNAME , types
from base import generate_wallet_id
from base import get_cursor
from app import get_cursor
import sqlite3
from data import GIFTS
from app import get_username
from app import get_clan_member_count
from data import FARMS
import time , datetime
from app import BOT_START_TIME
from app import update_premium_status

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    if user_id == ADMIN_ID:
        main_menu(message)
        return

    try:
        channel_member = bot.get_chat_member(CHANNEL_USERNAME, user_id)
        if channel_member.status not in ['member', 'administrator', 'creator']:
            bot.send_message(
                chat_id,
                "🧩 <b>Добро пожаловать в мир возможностей!</b> 🎉\n\n"
                "🔐 Чтобы разблокировать все функции бота, просто подпишись на наш канал:\n"
                f"👉 @{CHANNEL_USERNAME}\n\n"
                "🔄 После подписки нажми /start снова и получи доступ ко всем фишкам! ✨",
                parse_mode="HTML",
                disable_web_page_preview=True
            )
            return
    except Exception as e:
        bot.send_message(
            chat_id,
            "🛠️ <b>Ой, техническая неполадка!</b> 🤖\n\n"
            f"Не смог проверить подписку: {str(e)}\n\n"
            "🔧 Попробуй позже или напиши админу @blixmanager",
            parse_mode="HTML"
        )
        return

    username = message.from_user.username
    first_name = message.from_user.first_name

    cursor = get_cursor()
    try:
        cursor.execute('SELECT wallet_id FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()

        if result is None:
            wallet_id = generate_wallet_id()
            cursor.execute('INSERT INTO users (user_id, username, first_name, registration_date, wallet_id) VALUES (?, ?, ?, ?, ?)', 
                           (user_id, username, first_name, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), wallet_id))
            conn.commit()
        else:
            cursor.execute('UPDATE users SET first_name = ? WHERE user_id = ?', (first_name, user_id))
            conn.commit()
            if not result[0]:
                wallet_id = generate_wallet_id()
                cursor.execute('UPDATE users SET wallet_id = ? WHERE user_id = ?', (wallet_id, user_id))
                conn.commit()

        welcome_message = (
            "🧩 <b>Ура! Ты в игре!</b> 🎮\n\n"
            "✨ <b>Что умеет этот бот:</b>\n"
            "🤑 Тапать и зарабатывать\n"
            "💎 Получать бонусы и награды\n"
            "⚔️ Участвовать в дуэлях\n"
            "🏆 Подниматься в топах\n\n"
            "🎁 А ещё тут есть магазин, фермы и кланы!\n\n"
            "🚀 <b>Готов начать?</b> Выбирай кнопку ниже!"
        )

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(
            types.KeyboardButton('Тапать 🤑'), types.KeyboardButton('Баланс 💰'),
            types.KeyboardButton('Профиль 👤'), types.KeyboardButton('Топ по сваги 🏆'),
            types.KeyboardButton('Магазин 🛒'), types.KeyboardButton('Игры 🎲'),
            types.KeyboardButton('Лиги 🏅'), types.KeyboardButton('Фермы 🏡'),
            types.KeyboardButton('Кланы 🏰'), types.KeyboardButton('Инвентарь 🎁'),
            types.KeyboardButton('Наш телеграм 📢'), types.KeyboardButton('Настройки ⚙️'),
            types.KeyboardButton('Информация ℹ️')
        )

        bot.send_message(
            chat_id,
            welcome_message,
            parse_mode="HTML",
            reply_markup=markup
        )

        bot.send_message(
            chat_id,
            "❓ Есть вопросы? Пиши нашему менеджеру: @blixmanager 📩",
            parse_mode="HTML"
        )

    except sqlite3.Error as e:
        bot.send_message(
            chat_id,
            "🛑 <b>Ой, ошибка базы данных!</b> 💾\n\n"
            f"Попробуй позже или сообщи админу: {e}",
            parse_mode="HTML"
        )
    finally:
        cursor.close()

@bot.message_handler(commands=['gift'])
def give_gift(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, "❌ У вас нет прав для выполнения этой команды.")
        return

    try:
        _, action, user_id_str, gift_emoji = message.text.split()
        user_id = int(user_id_str)
    except:
        bot.send_message(message.chat.id, "❌ Используйте: /gift выдать <user_id> <эмодзи>")
        return

    if action == 'выдать':
        if gift_emoji not in GIFTS:
            bot.send_message(message.chat.id, "❌ Такого подарка не существует.")
            return

        cursor.execute('INSERT INTO user_gifts (user_id, gift_name) VALUES (?, ?)', (user_id, gift_emoji))
        conn.commit()
        bot.send_message(message.chat.id, f"✅ Вы выдали подарок {gift_emoji} пользователю {user_id}.")
    elif action == 'забрать':
        cursor.execute('DELETE FROM user_gifts WHERE user_id = ? AND gift_name = ?', (user_id, gift_emoji))
        conn.commit()
        bot.send_message(message.chat.id, f"✅ Забрали подарок {gift_emoji} у пользователя {user_id}.")
    else:
        bot.send_message(message.chat.id, "❌ Неизвестное действие. Используйте 'выдать' или 'забрать'.")

@bot.message_handler(commands=['aclans'])
def admin_clans_list(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    thread_id = message.message_thread_id if message.is_topic_message else None

    if user_id != ADMIN_ID:
        bot.send_message(chat_id, "❌ У вас нет прав для использования этой команды.", message_thread_id=thread_id)
        return

    cursor.execute('SELECT clan_id, clan_name, owner_id, balance, multiplier, clan_description FROM clans')
    clans = cursor.fetchall()

    if not clans:
        bot.send_message(chat_id, "❌ Пока нет кланов.", message_thread_id=thread_id)
        return

    clans_text = "📋 **Список всех кланов:**\n\n"

    for clan in clans:
        clan_id, clan_name, owner_id, balance, multiplier, clan_description = clan
        owner_username = get_username(owner_id) if owner_id else "Неизвестно"
        balance_formatted = f"{balance:,}".replace(",", ".")
        member_count = get_clan_member_count(clan_id)
        farm_count = get_clan_farm_count(clan_id)  

        clans_text += (f"🏆 Название клана: {clan_name}\n"
                      f"💰 Баланс: {balance_formatted} сваги\n"
                      f"🚜 Количество ферм: {farm_count}\n"
                      f"👑 Лидер: @{owner_username} (ID: {owner_id})\n"
                      f"👥 Участников: {member_count}\n\n"
                      "    ")  

    bot.send_message(chat_id, clans_text, parse_mode="Markdown", message_thread_id=thread_id)

@bot.message_handler(commands=['farmtest'])
def farm_test(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    thread_id = message.message_thread_id if message.is_topic_message else None

    if user_id != ADMIN_ID:
        bot.send_message(chat_id, "❌ У вас нет прав для использования этой команды.", message_thread_id=thread_id)
        return

    try:

        conn = sqlite3.connect('swag_boti.db', check_same_thread=False)
        cursor = conn.cursor()

        cursor.execute('SELECT farm_type, SUM(quantity), clan_connected FROM farms WHERE user_id = ? GROUP BY farm_type, clan_connected', (user_id,))
        farms = cursor.fetchall()

        if not farms:
            bot.send_message(chat_id, "❌ У вас пока нет ферм.", message_thread_id=thread_id)
            return

        message_parts = ["💌 Ваши фермы принесли доход!:"]
        for farm_type, quantity, clan_connected in farms:
            if clan_connected:
                continue  
            if farm_type in FARMS:
                income_per_farm = FARMS[farm_type]["income"]
                total_income = income_per_farm * quantity
                message_parts.append(f"{farm_type} x{quantity}")

        personal_income = sum(FARMS[farm_type]["income"] * quantity for farm_type, quantity, _ in farms if farm_type in FARMS)
        message_parts.append(f"💰 Вы получили {personal_income:,} сваги на ваш баланс.".replace(",", "."))

        full_message = "\n".join(message_parts)
        bot.send_message(chat_id, full_message, message_thread_id=thread_id)

    except sqlite3.Error as e:
        bot.send_message(chat_id, f"❌ Ошибка базы данных: {e}", message_thread_id=thread_id)
    except Exception as e:
        bot.send_message(chat_id, f"❌ Неизвестная ошибка: {e}", message_thread_id=thread_id)

@bot.message_handler(commands=['post'])
def post_step_1(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, "❌ У вас нет прав для использования этой команды.")
        return

    bot.send_message(message.chat.id, "✍️ Введите текст для поста:")
    bot.register_next_step_handler(message, post_step_2)

def post_step_2(message):
    if not message.text:
        bot.send_message(message.chat.id, "❌ Пожалуйста, введите текст для поста!")
        return bot.register_next_step_handler(message, post_step_2)

    post_text = message.text
    bot.send_message(message.chat.id, "📷 Хотите добавить картинку? Отправьте изображение или напишите 'нет'.")
    bot.register_next_step_handler(message, post_step_3, post_text)

def post_step_3(message, post_text):
    photo = None
    if message.photo:
        photo = message.photo[-1].file_id  
    elif message.text and message.text.lower() == "нет":
        photo = None
    else:
        bot.send_message(message.chat.id, "❌ Пожалуйста, отправьте изображение или напишите 'нет'.")
        return bot.register_next_step_handler(message, post_step_3, post_text)

    send_post_to_channel(post_text, photo, message.chat.id)

def send_post_to_channel(text, photo, admin_chat_id):
    channel_username = 'metrswagi'  

    try:
        if photo:
            bot.send_photo(chat_id=channel_username, photo=photo, caption=text, parse_mode="Markdown")
        else:
            bot.send_message(chat_id=channel_username, text=text, parse_mode="Markdown")

        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔷 Играть", url='https://t.me/swagametr_bot'))  

        if photo:
            sent_message = bot.send_photo(chat_id=channel_username, photo=photo, caption=text, reply_markup=markup, parse_mode="Markdown")
        else:
            sent_message = bot.send_message(chat_id=channel_username, text=text, reply_markup=markup, parse_mode="Markdown")

        bot.send_message(admin_chat_id, "✅ Пост успешно отправлен в канал.")

    except Exception as e:
        bot.send_message(admin_chat_id, f"❌ Ошибка при отправке поста в канал: {e}")

def get_clan_farm_count(clan_id):
    cursor.execute('SELECT COUNT(*) FROM farms WHERE clan_connected = 1 AND user_id IN (SELECT user_id FROM clan_members WHERE clan_id = ?)', (clan_id,))
    count = cursor.fetchone()
    return count[0] if count else 0

@bot.message_handler(commands=['help'])
def help_command(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    thread_id = message.message_thread_id if message.is_topic_message else None

    help_text = (
        "✨ **Список команд бота:** ✨\n\n"
        "📌 **Основные команды:**\n"
        "➡️ `/start` — Обновить кнопки 🎮 **[B]**\n"
        "➡️ `/profile` — Показать ваш профиль 👤 **[G]**\n"
        "➡️ `/telegram` — Ссылка на наш Telegram-канал 📢 **[G]**\n"
        "➡️ `/buy` — Купить премиум с помощью API-ключа 💎 **[B]**\n"
        "➡️ `/crypto` — Показать курсы криптовалют 💱 **[G]**\n"
        "➡️ `/invite` — Получить ссылку для приглашения бота 🤝 **[B]**\n"
        "➡️ `/swag` — Увеличить башню сваги 🏯 **[M]**\n"
        "➡️ `/topswag` — Топ башен сваги в чате 🏆 **[M]**\n"
        "➡️ `/duel <ставка>` — Начать дуэль ⚔️ **[M]**\n\n"
        "ℹ️ **Обозначения:**\n"
        "**[M]** — Работает только в беседах\n"
        "**[B]** — Работает только в личке бота\n"
        "**[G]** — Работает везде\n\n"
        "🎉 **Начинайте играть и зарабатывать свагу!**"
    )

    try:

        if message.chat.type in ['group', 'supergroup']:
            bot.send_message(
                user_id,
                help_text,
                parse_mode="Markdown"
            )
            bot.send_message(
                chat_id,
                f"📩 @{message.from_user.username or 'User'}! Список команд отправлен вам в личные сообщения.",
                message_thread_id=thread_id
            )
        else:

            bot.send_message(
                chat_id,
                help_text,
                parse_mode="Markdown"
            )

    except telebot.apihelper.ApiTelegramException as e:
        if "Forbidden" in str(e):
            bot.send_message(
                chat_id,
                "❌ Пожалуйста, начните диалог со мной в личке с помощью /start, чтобы я мог отправить вам список команд!",
                message_thread_id=thread_id
            )
        elif e.error_code == 400 and "TOPIC_CLOSED" in e.description:
            bot.send_message(
                chat_id,
                "❌ Эта тема закрыта. Используйте команду в активной теме или в личке бота.",
                message_thread_id=thread_id
            )
        else:
            bot.send_message(
                chat_id,
                f"❌ Ошибка при отправке: {e.description}",
                message_thread_id=thread_id
            )

@bot.message_handler(commands=['stats'])
def stats_command(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    thread_id = message.message_thread_id if message.is_topic_message else None

    if user_id != ADMIN_ID:
        bot.send_message(chat_id, "❌ У вас нет прав для использования этой команды.", message_thread_id=thread_id)
        return

    try:

        conn = sqlite3.connect('swag_boti.db', check_same_thread=False)
        cursor = conn.cursor()

        cursor.execute('SELECT SUM(swag), SUM(total_swag) FROM users')
        swag_data = cursor.fetchone()
        total_swag = swag_data[0] or 0  
        total_swag_earned = swag_data[1] or 0  

        cursor.execute('SELECT COUNT(*) FROM users')
        total_users = cursor.fetchone()[0] or 0

        uptime_seconds = int(time.time() - BOT_START_TIME)
        uptime_days = uptime_seconds // (24 * 3600)
        uptime_hours = (uptime_seconds % (24 * 3600)) // 3600
        uptime_minutes = (uptime_seconds % 3600) // 60
        uptime_str = f"{uptime_days} дн. {uptime_hours} ч. {uptime_minutes} мин."

        cursor.execute('SELECT COUNT(*) FROM clans')
        total_clans = cursor.fetchone()[0] or 0

        cursor.execute('SELECT SUM(quantity) FROM farms')
        total_farms = cursor.fetchone()[0] or 0

        cursor.execute('SELECT COUNT(DISTINCT user_id) FROM crypto_wallets')
        api_users = cursor.fetchone()[0] or 0

        stats_message = (
            "📊 **Статистика бота**\n\n"
            f"💰 **Общий капитал сваги:**\n"
            f"Текущий баланс: {total_swag:,} сваги\n"
            f"Всего заработано: {total_swag_earned:,} сваги\n\n"
            f"👥 **Пользователи:**\n"
            f"Всего: {total_users}\n\n"
            f"⏳ **Время работы бота:** {uptime_str}\n\n"
            f"🏰 **Кланы:**\n"
            f"Создано: {total_clans}\n\n"
            f"🚜 **Фермы:**\n"
            f"Всего у игроков: {total_farms}\n\n"
            f"🔑 **API-ключи:**\n"
            f"Использовано игроками: {api_users}"
        )

        bot.send_message(chat_id, stats_message, parse_mode="Markdown", message_thread_id=thread_id)

    except sqlite3.Error as e:
        bot.send_message(chat_id, f"❌ Ошибка базы данных: {e}", message_thread_id=thread_id)
        if 'conn' in locals():
            conn.rollback()
    except Exception as e:
        bot.send_message(chat_id, f"❌ Неизвестная ошибка: {e}", message_thread_id=thread_id)
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

@bot.message_handler(commands=['tegreload'])
def tegreload_command(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    thread_id = message.message_thread_id if message.is_topic_message else None

    if user_id != ADMIN_ID:
        bot.send_message(chat_id, "❌ У вас нет прав для использования этой команды.", message_thread_id=thread_id)
        return

    try:

        conn = sqlite3.connect('swag_boti.db', check_same_thread=False)
        cursor = conn.cursor()

        cursor.execute('SELECT user_id, username FROM users')
        users = cursor.fetchall()

        if not users:
            bot.send_message(chat_id, "❌ В базе нет зарегистрированных пользователей.", message_thread_id=thread_id)
            cursor.close()
            conn.close()
            return

        updated_count = 0

        for db_user_id, db_username in users:
            try:

                user_info = bot.get_chat_member(chat_id, db_user_id)
                current_username = user_info.user.username

                if current_username != db_username:
                    cursor.execute('UPDATE users SET username = ? WHERE user_id = ?', (current_username, db_user_id))
                    updated_count += 1
                    print(f"Обновлён тег для ID {db_user_id}: {db_username} -> @{current_username}")

            except telebot.apihelper.ApiTelegramException as e:
                print(f"Ошибка получения данных для ID {db_user_id}: {e}")
                continue  

        conn.commit()

        bot.send_message(
            chat_id,
            f"✅ Обновление тегов завершено.\n"
            f"Обновлено пользователей: {updated_count}\n"
            f"Всего проверено: {len(users)}",
            message_thread_id=thread_id
        )

    except sqlite3.Error as e:
        bot.send_message(chat_id, f"❌ Ошибка базы данных: {e}", message_thread_id=thread_id)
        if 'conn' in locals():
            conn.rollback()
    except Exception as e:
        bot.send_message(chat_id, f"❌ Неизвестная ошибка: {e}", message_thread_id=thread_id)
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

@bot.message_handler(commands=['reacc'])
def reacc_command(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    thread_id = message.message_thread_id if message.is_topic_message else None

    if user_id != ADMIN_ID:
        bot.send_message(chat_id, "❌ У вас нет прав для использования этой команды.", message_thread_id=thread_id)
        return

    try:
        parts = message.text.split()
        if len(parts) != 3:
            bot.send_message(chat_id, "❌ Неверный формат. Используйте: /reacc <old_user_id> <new_user_id>\nПример: /reacc 123456789 987654321", message_thread_id=thread_id)
            return

        old_user_id = int(parts[1])  
        new_user_id = int(parts[2])  

        conn = sqlite3.connect('swag_boti.db', check_same_thread=False)
        cursor = conn.cursor()

        cursor.execute('SELECT username FROM users WHERE user_id = ?', (old_user_id,))
        old_user = cursor.fetchone()
        if not old_user:
            bot.send_message(chat_id, f"❌ Пользователь с ID {old_user_id} не найден.", message_thread_id=thread_id)
            return

        cursor.execute('SELECT username FROM users WHERE user_id = ?', (new_user_id,))
        new_user = cursor.fetchone()
        if not new_user:
            bot.send_message(chat_id, f"❌ Пользователь с ID {new_user_id} не найден.", message_thread_id=thread_id)
            return

        old_username = old_user[0] if old_user[0] else "Без имени"
        new_username = new_user[0] if new_user[0] else "Без имени"

        try:

            cursor.execute('SELECT swag, total_swag FROM users WHERE user_id = ?', (old_user_id,))
            old_user_data = cursor.fetchone()
            old_swag, old_total_swag = old_user_data if old_user_data else (0, 0)

            cursor.execute('SELECT swag, total_swag FROM users WHERE user_id = ?', (new_user_id,))
            new_user_data = cursor.fetchone()
            current_swag, current_total_swag = new_user_data if new_user_data else (0, 0)

            new_swag = current_swag + old_swag
            new_total_swag = current_total_swag + old_total_swag
            cursor.execute('UPDATE users SET swag = ?, total_swag = ? WHERE user_id = ?', (new_swag, new_total_swag, new_user_id))

            cursor.execute('SELECT crypto_type, amount FROM crypto_wallets WHERE user_id = ?', (old_user_id,))
            old_crypto = cursor.fetchall()
            for crypto_type, amount in old_crypto:
                cursor.execute('SELECT amount FROM crypto_wallets WHERE user_id = ? AND crypto_type = ?', (new_user_id, crypto_type))
                existing_amount = cursor.fetchone()
                new_amount = amount + (existing_amount[0] if existing_amount else 0)
                cursor.execute('INSERT OR REPLACE INTO crypto_wallets (user_id, crypto_type, amount) VALUES (?, ?, ?)', 
                               (new_user_id, crypto_type, new_amount))

            cursor.execute('DELETE FROM crypto_wallets WHERE user_id = ?', (old_user_id,))

            cursor.execute('SELECT farm_type, quantity, clan_connected FROM farms WHERE user_id = ?', (old_user_id,))
            old_farms = cursor.fetchall()
            for farm_type, quantity, clan_connected in old_farms:
                cursor.execute('SELECT quantity FROM farms WHERE user_id = ? AND farm_type = ?', (new_user_id, farm_type))
                existing_quantity = cursor.fetchone()
                new_quantity = quantity + (existing_quantity[0] if existing_quantity else 0)
                cursor.execute('INSERT OR REPLACE INTO farms (user_id, farm_type, quantity, clan_connected) VALUES (?, ?, ?, ?)', 
                               (new_user_id, farm_type, new_quantity, clan_connected))

            cursor.execute('DELETE FROM farms WHERE user_id = ?', (old_user_id,))

            cursor.execute('UPDATE clan_members SET user_id = ? WHERE user_id = ?', (new_user_id, old_user_id))
            cursor.execute('UPDATE clans SET owner_id = ? WHERE owner_id = ?', (new_user_id, old_user_id))

            cursor.execute('DELETE FROM users WHERE user_id = ?', (old_user_id,))

            conn.commit()

            bot.send_message(
                chat_id,
                f"✅ Имущество успешно перенесено:\n"
                f"От: ID {old_user_id} (@{old_username})\n"
                f"К: ID {new_user_id} (@{new_username})\n"
                f"Перенесено: клан, свага, криптовалюта, фермы.\n"
                f"Старый аккаунт удалён.",
                message_thread_id=thread_id
            )

            try:
                bot.send_message(
                    new_user_id,
                    f"⚠️ Администратор забрал имущество с аккаунта ID {old_user_id} и перенёс его на ваш аккаунт.\n"
                    f"Вам добавлены: клан, свага, криптовалюта, фермы."
                )
            except Exception as e:
                print(f"Ошибка уведомления нового пользователя {new_user_id}: {e}")

        except sqlite3.Error as e:
            conn.rollback()
            bot.send_message(chat_id, f"❌ Ошибка при переносе имущества: {e}", message_thread_id=thread_id)
        except Exception as e:
            bot.send_message(chat_id, f"❌ Неизвестная ошибка: {e}", message_thread_id=thread_id)
        finally:
            cursor.close()
            conn.close()

    except ValueError:
        bot.send_message(chat_id, "❌ Ошибка: ID должны быть числами.", message_thread_id=thread_id)
    except Exception as e:
        bot.send_message(chat_id, f"❌ Ошибка: {e}", message_thread_id=thread_id)

@bot.message_handler(commands=['atop'])
def top_by_id_command(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    thread_id = message.message_thread_id if message.is_topic_message else None

    if user_id != ADMIN_ID:
        bot.send_message(chat_id, "❌ У вас нет прав для использования этой команды.", message_thread_id=thread_id)
        return

    cursor.execute("""
        SELECT user_id, username, swag, hide_top 
        FROM users 
        ORDER BY swag DESC 
        LIMIT 10
    """)
    users = cursor.fetchall()

    if not users:
        bot.send_message(chat_id, "❌ Топ пуст. Нет зарегистрированных пользователей.", message_thread_id=thread_id)
        return

    medals = ["🥇", "🥈", "🥉", "🎖", "🏅", "🎗", "💠", "🔱", "⚜", "🌀"]
    top_message = "💰 **ТОП-10 ПО БАЛАНСУ (с ID):**\n\n"

    for i, (user_id, username, swag, hide_top) in enumerate(users):
        medal = medals[i] if i < len(medals) else "🎲"
        display_name = username if username else "None"
        swag_formatted = f"{int(swag):,}".replace(",", ".")  
        hide_status = "👀 Скрыт" if hide_top else "👁 Видим"

        top_message += (
            f"{medal} {i+1}. **ID:** <code>{user_id}</code>   |   "
            f"@{display_name}   |   "
            f"💰 {swag_formatted} сваги   |   "
            f"{hide_status}\n\n"  
        )

    try:
        bot.send_message(
            chat_id,
            top_message,
            parse_mode="HTML",  
            message_thread_id=thread_id
        )
    except telebot.apihelper.ApiTelegramException as e:
        if e.error_code == 400 and "TOPIC_CLOSED" in e.description:
            bot.send_message(
                chat_id,
                "❌ Эта тема закрыта. Пожалуйста, используйте команду в активной теме или в личных сообщениях с ботом.",
                message_thread_id=thread_id
            )
        else:
            bot.send_message(chat_id, f"❌ Ошибка: {e.description}", message_thread_id=thread_id)

@bot.message_handler(commands=['buy'])
def buy_premium_with_key(message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    if message.chat.type != 'private':
        bot.send_message(chat_id, "❌ Эта команда работает только в личных сообщениях с ботом! 😊\nПожалуйста, напишите мне в личку и используйте /buy там.")
        return

    cursor.execute('SELECT is_premium, premium_end_date FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()

    if result and result[0] == 1:
        end_date = datetime.strptime(result[1], '%Y-%m-%d %H:%M:%S')
        if datetime.now() < end_date:
            days_left = (end_date - datetime.now()).days
            bot.send_message(chat_id, f"❌ У вас уже есть активная премиум-подписка (осталось {days_left} дней).")
            return

    bot.send_message(chat_id, "🔑 Введите ваш уникальный API ключ для активации премиум-подписки на 30 дней:")
    bot.register_next_step_handler(message, process_premium_key)

def process_premium_key(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    api_key = message.text.strip()

    cursor.execute('SELECT days, used_by FROM premium_api_keys WHERE key = ?', (api_key,))
    key_data = cursor.fetchone()

    if not key_data:
        bot.send_message(chat_id, "❌ Неверный API ключ. Пожалуйста, проверьте правильность ввода.")
        return

    days, used_by = key_data

    if used_by is not None:
        bot.send_message(chat_id, "❌ Этот ключ уже был использован.")
        return

    end_date = datetime.now() + timedelta(days=days)
    cursor.execute('UPDATE users SET is_premium = 1, premium_end_date = ?, selected_badge = "💎" WHERE user_id = ?',
                   (end_date.strftime('%Y-%m-%d %H:%M:%S'), user_id))

    cursor.execute('UPDATE premium_api_keys SET used_by = ?, used_at = ? WHERE key = ?',
                   (user_id, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), api_key))
    conn.commit()

    bot.send_message(chat_id, f"🎉 Поздравляем! Вам активирована премиум-подписка на {days} дней!")

@bot.message_handler(commands=['api'])
def api_management(message):
    user_id = message.from_user.id

    if user_id != ADMIN_ID:
        bot.send_message(message.chat.id, "❌ У вас нет прав для использования этой команды.")
        return

    args = message.text.split()
    if len(args) < 2:
        bot.send_message(message.chat.id, "❌ Неверный формат команды. Используйте:\n/api create - создать новый ключ\n/api list - список ключей")
        return

    subcommand = args[1].lower()

    if subcommand == 'create':

        new_key = str(uuid.uuid4()).replace('-', '')[:16]  

        cursor.execute('INSERT INTO premium_api_keys (key, created_by, created_at, days) VALUES (?, ?, ?, ?)',
                       (new_key, user_id, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 30))
        conn.commit()

        bot.send_message(message.chat.id, f"🔑 Новый API ключ создан:\n`{new_key}`\n\nЭтот ключ дает премиум на 30 дней. Отправьте его пользователю.", parse_mode="Markdown")

    elif subcommand == 'list':

        cursor.execute('SELECT key, created_at, used_by, used_at FROM premium_api_keys ORDER BY created_at DESC LIMIT 10')
        keys = cursor.fetchall()

        if not keys:
            bot.send_message(message.chat.id, "❌ Нет созданных API ключей.")
            return

        response = "📋 Последние 10 API ключей:\n\n"
        for key, created_at, used_by, used_at in keys:
            status = "✅ Использован" if used_by else "🆓 Активен"
            used_info = f"пользователем {used_by}" if used_by else "еще не использован"
            response += f"🔑 `{key}`\n📅 Создан: {created_at}\n🔄 Статус: {status} ({used_info})\n\n"

        bot.send_message(message.chat.id, response, parse_mode="Markdown")

    else:
        bot.send_message(message.chat.id, "❌ Неизвестная подкоманда. Используйте:\n/api create - создать новый ключ\n/api list - список ключей")

@bot.message_handler(commands=['telegram'])
def telegram_command(message):
    chat_id = message.chat.id
    telegram_link = "https://t.me/metrswagi"  

    bot.send_message(chat_id, f"📢 Подписывайтесь на наш Telegram-канал: {telegram_link}") 

@bot.message_handler(commands=['disablecrypto'])
def toggle_crypto(message):
    global crypto_enabled
    user_id = message.from_user.id

    if user_id != ADMIN_ID:
        bot.send_message(message.chat.id, "❌ У вас нет прав для использования этой команды.")
        return

    try:
        parts = message.text.split()
        if len(parts) < 2:
            bot.send_message(message.chat.id, "❌ Неверный формат. Используйте: /disablecrypto <on/off>")
            return

        state = parts[1].lower()
        if state not in ['on', 'off']:
            bot.send_message(message.chat.id, "❌ Укажите состояние: 'on' или 'off'.")
            return

        if state == 'on':
            crypto_enabled = True
            bot.send_message(message.chat.id, "✅ Раздел криптовалюты включён.")
        elif state == 'off':
            crypto_enabled = False
            bot.send_message(message.chat.id, "✅ Раздел криптовалюты отключён.")

    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Произошла ошибка: {e}")  

@bot.message_handler(commands=['resetmoney'])
def reset_money(message):
    user_id = message.from_user.id
    if user_id != ADMIN_ID:  
        bot.send_message(message.chat.id, "❌ У вас нет прав для использования этой команды.")
        return

    try:
        parts = message.text.split()
        if len(parts) < 2:  
            bot.send_message(message.chat.id, "❌ Неверный формат. Используйте: /resetmoney <user_id>")
            return

        target_user_id = int(parts[1])  

        cursor.execute('SELECT swag FROM users WHERE user_id = ?', (target_user_id,))
        result = cursor.fetchone()
        if not result:
            bot.send_message(message.chat.id, f"❌ Пользователь с ID {target_user_id} не найден.")
            return

        cursor.execute('UPDATE users SET swag = 0 WHERE user_id = ?', (target_user_id,))
        conn.commit()

        bot.send_message(message.chat.id, f"✅ Баланс сваги пользователя {target_user_id} обнулён.")

        admin_username = message.from_user.username or "Администратор"
        try:
            bot.send_message(target_user_id, f"❌ Ваш баланс сваги обнулён администратором @{admin_username}.")
        except Exception as e:
            print(f"Ошибка уведомления {target_user_id}: {e}")

    except ValueError:
        bot.send_message(message.chat.id, "❌ Ошибка: ID должен быть числом.")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Ошибка: {e}")

@bot.message_handler(commands=['resetcrypto'])
def reset_crypto(message):
    user_id = message.from_user.id
    if user_id != ADMIN_ID:  
        bot.send_message(message.chat.id, "❌ У вас нет прав для использования этой команды.")
        return

    try:
        parts = message.text.split()
        if len(parts) < 3:  
            bot.send_message(message.chat.id, "❌ Неверный формат. Используйте: /resetcrypto <user_id> <crypto_type>\nПример: /resetcrypto 123456789 BL")
            return

        target_user_id = int(parts[1])  
        crypto_type = parts[2].upper()  

        valid_crypto_types = ["BL", "DP", "DG"]
        if crypto_type not in valid_crypto_types:
            bot.send_message(message.chat.id, f"❌ Неверный тип криптовалюты. Допустимые: {', '.join(valid_crypto_types)}")
            return

        cursor.execute('SELECT swag FROM users WHERE user_id = ?', (target_user_id,))
        user_result = cursor.fetchone()
        if not user_result:
            bot.send_message(message.chat.id, f"❌ Пользователь с ID {target_user_id} не найден.")
            return

        cursor.execute('SELECT amount FROM crypto_wallets WHERE user_id = ? AND crypto_type = ?', 
                       (target_user_id, crypto_type))
        crypto_result = cursor.fetchone()

        if not crypto_result or crypto_result[0] == 0:
            bot.send_message(message.chat.id, f"❌ У пользователя {target_user_id} нет {crypto_type} для обнуления.")
            return

        cursor.execute('UPDATE crypto_wallets SET amount = 0 WHERE user_id = ? AND crypto_type = ?', 
                       (target_user_id, crypto_type))
        conn.commit()

        bot.send_message(message.chat.id, f"✅ Баланс {crypto_type} пользователя {target_user_id} обнулён.")

        admin_username = message.from_user.username or "Администратор"
        try:
            bot.send_message(target_user_id, f"❌ Ваш баланс {crypto_type} обнулён администратором @{admin_username}.")
        except Exception as e:
            print(f"Ошибка уведомления {target_user_id}: {e}")

    except ValueError:
        bot.send_message(message.chat.id, "❌ Ошибка: ID должен быть числом.")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Ошибка: {e}")

@bot.message_handler(commands=['setwallet'])
def set_wallet(message):
    user_id = message.from_user.id

    if user_id != ADMIN_ID:
        bot.send_message(message.chat.id, "❌ У вас нет прав для использования этой команды.")
        return

    try:
        parts = message.text.split(maxsplit=1)  
        if len(parts) < 2:
            bot.send_message(message.chat.id, "❌ Неверный формат команды. Используйте: /setwallet <новый_номер_кошелька>")
            return

        new_wallet_id = parts[1].strip()  

        cursor.execute('SELECT user_id FROM users WHERE wallet_id = ? AND user_id != ?', (new_wallet_id, user_id))
        existing_user = cursor.fetchone()
        if existing_user:
            bot.send_message(message.chat.id, "❌ Этот номер кошелька уже используется другим пользователем.")
            return

        cursor.execute('UPDATE users SET wallet_id = ? WHERE user_id = ?', (new_wallet_id, user_id))
        conn.commit()

        bot.send_message(message.chat.id, f"✅ Ваш номер кошелька успешно изменён на: `{new_wallet_id}`", parse_mode="Markdown")

    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Произошла ошибка: {e}")

@bot.message_handler(commands=['setpremium'])
def set_premium(message):
    user_id = message.from_user.id
    if user_id != ADMIN_ID:  
        bot.send_message(message.chat.id, "❌ У вас нет прав для использования этой команды.")
        return

    try:
        parts = message.text.split()
        if len(parts) < 3:  
            bot.send_message(message.chat.id, "❌ Неверный формат команды. Используйте: /setpremium <user_id> <дней>")
            return

        target_user_id = int(parts[1])  
        days = int(parts[2])  

        if days <= 0:  
            bot.send_message(message.chat.id, "❌ Количество дней должно быть больше 0.")
            return

        update_premium_status(target_user_id, is_premium=True, days=days)

        bot.send_message(message.chat.id, f"✅ Пользователю {target_user_id} установлена премиум-подписка на {days} дней.")

        admin_username = message.from_user.username
        try:
            bot.send_message(target_user_id, f"🎉 Администратор @{admin_username} выдал вам премиум-статус на {days} дней!")
        except Exception as e:
            print(f"Ошибка при отправке сообщения пользователю {target_user_id}: {e}")
    except ValueError:
        bot.send_message(message.chat.id, "❌ Ошибка: ID пользователя и количество дней должны быть числами.")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Произошла ошибка: {e}")

@bot.message_handler(commands=['removepremium'])
def remove_premium(message):
    user_id = message.from_user.id
    if user_id != ADMIN_ID:  
        bot.send_message(message.chat.id, "❌ У вас нет прав для использования этой команды.")
        return

    try:
        parts = message.text.split()
        if len(parts) < 2:  
            bot.send_message(message.chat.id, "❌ Неверный формат команды. Используйте: /removepremium <user_id>")
            return

        target_user_id = int(parts[1])  

        update_premium_status(target_user_id, is_premium=False)

        bot.send_message(message.chat.id, f"✅ Премиум-статус у пользователя {target_user_id} удалён.")

        admin_username = message.from_user.username
        try:
            bot.send_message(target_user_id, f"❌ Администратор @{admin_username} забрал у вас премиум-статус!")
        except Exception as e:
            print(f"Ошибка при отправке сообщения пользователю {target_user_id}: {e}")
    except ValueError:
        bot.send_message(message.chat.id, "❌ Ошибка: ID пользователя должен быть числом.")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Произошла ошибка: {e}")