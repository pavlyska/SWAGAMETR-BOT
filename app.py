import telebot
from telebot import types, formatting
import sqlite3
import random
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
import traceback
import math
import time
import requests
import string
import uuid
import re
from time import sleep
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from base import conn, cursor

from base import *

from data import (
    RANKS,
    FARMS,
    LEAGUES,
    MULTIPLIERS,
    MULTIPLIER_COSTS
)

from base import generate_wallet_id

def check_and_add_disable_farm_notifications():
    conn = sqlite3.connect("swag_boti.db")
    cursor = conn.cursor()

    cursor.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in cursor.fetchall()]

    if "disable_farm_notifications" not in columns:
        try:
            cursor.execute("ALTER TABLE users ADD COLUMN disable_farm_notifications INTEGER DEFAULT 0")
            conn.commit()
            print("✅ Колонка 'disable_farm_notifications' успешно добавлена.")
        except Exception as e:
            print(f"❌ Ошибка при добавлении колонки: {e}")
    else:
        print("🔔 Колонка 'disable_farm_notifications' уже существует.")

    conn.close()

def check_all_premium_users():
    cursor.execute('SELECT user_id, premium_end_date FROM users WHERE is_premium = 1')
    users = cursor.fetchall()

    for user_id, premium_end_date in users:
        if premium_end_date:
            end_date = datetime.strptime(premium_end_date, '%Y-%m-%d %H:%M:%S')
            if datetime.now() > end_date:
                update_premium_status(user_id, is_premium=False)
                try:
                    bot.send_message(user_id, "❌ Ваша премиум-подписка истекла. GIF удалена из профиля.")
                except Exception as e:
                    print(f"Ошибка при отправке сообщения пользователю {user_id}: {e}")

def schedule_premium_check():
    scheduler = BackgroundScheduler()
    scheduler.add_job(check_all_premium_users, 'interval', hours=3)  
    scheduler.start()

bot = telebot.TeleBot('') 

ADMIN_ID =  

CHANNEL_USERNAME = ''  

def get_db_connection():
    return sqlite3.connect("swag_boti.db")  

def get_rank(total_swag):
    for threshold, rank in sorted(RANKS.items(), reverse=True):
        if total_swag >= threshold:
            return rank
    return "Нуб 👶"

def get_next_rank(total_swag):
    for threshold, rank in sorted(RANKS.items()):
        if total_swag < threshold:
            return rank, threshold - total_swag
    return "ПОВЕЛИТЕЛЬ СВАГИ 🛡️", 0

def get_next_league(current_league):
    leagues = list(LEAGUES.keys())
    try:
        index = leagues.index(current_league)
        if index + 1 < len(leagues):
            return leagues[index + 1]
    except ValueError:
        pass
    return None

def get_user_balance_position(user_id):
    cursor.execute("SELECT user_id, hide_top FROM users ORDER BY swag DESC")
    users = [(row[0], row[1]) for row in cursor.fetchall()]
    user_list = [user[0] for user in users if not user[1]]  

    if user_id in user_list:
        return user_list.index(user_id) + 1
    return len(user_list) + 1  

def get_username(user_id):
    cursor.execute('SELECT username FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    return result[0] if result else f"User_{user_id}"

def get_duel_searches():
    cursor.execute('SELECT user_id, bet FROM duel_searches')
    return cursor.fetchall()

def start_duel_search(user_id, bet):
    cursor.execute('SELECT swag FROM users WHERE user_id = ?', (user_id,))
    swag = cursor.fetchone()[0]

def get_user_total_swag_position(user_id):
    cursor.execute("SELECT user_id, hide_top FROM users ORDER BY total_swag DESC")
    users = [(row[0], row[1]) for row in cursor.fetchall()]
    user_list = [user[0] for user in users if not user[1]]  

    if user_id in user_list:
        return user_list.index(user_id) + 1
    return len(user_list) + 1  

def get_top_users_by_swag():
    cursor.execute("SELECT username, hide_top, swag FROM users ORDER BY swag DESC LIMIT 10")
    users = cursor.fetchall()
    return [("Скрыто🐱‍👤" if hide else username, f"{swag:,}".replace(",", ".")) for username, hide, swag in users]

def get_top_users_by_total_swag():
    cursor.execute("SELECT username, hide_top, total_swag FROM users ORDER BY total_swag DESC LIMIT 10")
    users = cursor.fetchall()
    return [("Скрыто🐱‍👤" if hide else username, f"{total_swag:,}".replace(",", ".")) for username, hide, total_swag in users]

def get_user_stats(user_id):
    cursor.execute('SELECT swag, total_swag, rank, league, registration_date FROM users WHERE user_id = ?', (user_id,))
    return cursor.fetchone()

def update_swag(user_id, amount):
    cursor = get_cursor()  
    cursor.execute('UPDATE users SET swag = swag + ?, total_swag = total_swag + ? WHERE user_id = ?', (amount, amount, user_id))
    conn.commit()

def update_rank(user_id):
    cursor = get_cursor()  
    cursor.execute('SELECT total_swag FROM users WHERE user_id = ?', (user_id,))
    total_swag = cursor.fetchone()[0]
    rank = get_rank(total_swag)
    cursor.execute('UPDATE users SET rank = ? WHERE user_id = ?', (rank, user_id))
    conn.commit()

def update_league(user_id, new_league):
    cursor.execute('UPDATE users SET league = ?, swag = 0, total_swag = 0, rank = ? WHERE user_id = ?', (new_league, "Нуб 👶", user_id))
    conn.commit()

def buy_multiplier(user_id, multiplier):
    cost = MULTIPLIERS[multiplier]
    cursor.execute('SELECT swag FROM users WHERE user_id = ?', (user_id,))
    swag = cursor.fetchone()[0]
    if swag >= cost:

        multiplier_value = int(''.join(filter(str.isdigit, multiplier)))
        cursor.execute('UPDATE users SET swag = swag - ?, multiplier = ? WHERE user_id = ?', (cost, multiplier_value, user_id))
        conn.commit()
        return True
    return False

def buy_farm(user_id, farm_type):
    cost = FARMS[farm_type]["cost"]
    cursor.execute('SELECT swag FROM users WHERE user_id = ?', (user_id,))
    swag = cursor.fetchone()[0]
    if swag >= cost:
        cursor.execute('UPDATE users SET swag = swag - ? WHERE user_id = ?', (cost, user_id))
        cursor.execute('INSERT INTO farms (user_id, farm_type, quantity) VALUES (?, ?, 1)', (user_id, farm_type))
        conn.commit()
        return True
    return False

def delete_message(call):
    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except:
        pass

def tax_click(user_id, earned_swag):
    conn = sqlite3.connect("swag_boti.db")
    cursor = conn.cursor()
    try:
        cursor.execute('SELECT clan_id FROM clan_members WHERE user_id = ?', (user_id,))
        user_clan = cursor.fetchone()
        if not user_clan:
            return earned_swag, 0, None

        clan_id = user_clan[0]

        tax_rate = 5  
        tax_amount = max(1, math.ceil(earned_swag * (tax_rate / 100)))

        cursor.execute('UPDATE clans SET balance = balance + ? WHERE clan_id = ?', (tax_amount, clan_id))
        conn.commit()
        return earned_swag - tax_amount, tax_amount, clan_id
    except Exception as e:
        print(f"[Ошибка налога] {e}")
        return earned_swag, 0, None
    finally:
        cursor.close()
        conn.close()

def get_cursor():
    """Функция для получения нового курсора"""
    return conn.cursor()

def get_rank(total_swag):
    for threshold, rank in sorted(RANKS.items(), reverse=True):
        if total_swag >= threshold:
            return rank
    return "Нуб 👶"

def main_menu():
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(types.KeyboardButton('Тапать 🤑'), types.KeyboardButton('Баланс 💰'))
    markup.add(types.KeyboardButton('Профиль 👤'), types.KeyboardButton('Топ по сваги 🏆'))
    markup.add(types.KeyboardButton('Магазин 🛒'), types.KeyboardButton('Игры 🎲'))
    markup.add(types.KeyboardButton('Лиги 🏅'), types.KeyboardButton('Фермы 🏡'))
    markup.add(types.KeyboardButton('Кланы 🏰'), types.KeyboardButton('Наш телеграм 📢'))
    markup.add(types.KeyboardButton('Инвентарь 🎁'), types.KeyboardButton('Настройки ⚙️'))
    markup.add(types.KeyboardButton('Информация ℹ️'))
    return markup

def get_db_connection():
    return sqlite3.connect("swag_boti.db")

def tax_click(user_id, earned_swag):
    conn = sqlite3.connect("swag_boti.db")  
    cursor = conn.cursor()

    try:
        cursor.execute('SELECT clan_id FROM clan_members WHERE user_id = ?', (user_id,))
        user_clan = cursor.fetchone()

        if user_clan:
            clan_id = user_clan[0]
            tax_amount = math.ceil(earned_swag * 0.05)  

            if tax_amount < 1:
                tax_amount = 1  

            cursor.execute('SELECT balance FROM clans WHERE clan_id = ?', (clan_id,))
            clan = cursor.fetchone()

            if clan:
                cursor.execute('UPDATE clans SET balance = balance + ? WHERE clan_id = ?', (tax_amount, clan_id))
                conn.commit()
                return earned_swag - tax_amount, tax_amount, clan_id

        return earned_swag, 0, None  

    except sqlite3.OperationalError as e:
        print(f"[Ошибка базы данных] {e}")
        return earned_swag, 0, None

    finally:
        cursor.close()
        conn.close()  

@bot.message_handler(func=lambda message: message.text == 'Тапать 🤑')
def tap(message):
    user_id = message.from_user.id
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT league, multiplier, swag, use_clan_multiplier, is_premium FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()

    if result is None:
        bot.send_message(message.chat.id, "❌ Ошибка: пользователь не найден.")
        cursor.close()
        return

    league, user_multiplier, balance, use_clan_multiplier, is_premium = result

    cursor.execute('SELECT clan_id FROM clan_members WHERE user_id = ?', (user_id,))
    user_clan = cursor.fetchone()

    if user_clan and use_clan_multiplier:
        cursor.execute('SELECT multiplier FROM clans WHERE clan_id = ?', (user_clan[0],))
        clan_multiplier = cursor.fetchone()
        if clan_multiplier:
            user_multiplier = clan_multiplier[0]  

    if league not in LEAGUES:
        bot.send_message(message.chat.id, f"❌ Ошибка: неизвестная лига '{league}'.")
        cursor.close()
        return

    min_swag, max_swag = LEAGUES[league]["min"], LEAGUES[league]["max"]
    swag = random.randint(min_swag, max_swag) * user_multiplier

    if is_premium:
        swag = int(swag * 1.2)  

    swag_after_tax, tax_amount, clan_id = tax_click(user_id, swag)

    cursor.execute('UPDATE users SET swag = swag + ?, total_swag = total_swag + ? WHERE user_id = ?', 
                   (swag_after_tax, swag_after_tax, user_id))
    conn.commit()
    cursor.close()

    new_balance = int(balance + swag_after_tax)  
    balance_formatted = f"{new_balance:,}".replace(",", ".")

    if tax_amount > 0:
        bot.send_message(message.chat.id, f"🌎 Вы получили {swag_after_tax} сваги! 🌲 (из них {tax_amount} ушло в клан)\nВаш баланс: {balance_formatted} сваги ⌚")
    else:
        bot.send_message(message.chat.id, f"🌎 Вы получили {swag_after_tax} сваги! 🌲\nВаш баланс: {balance_formatted} сваги 💵")

crypto_enabled = True

@bot.message_handler(func=lambda message: message.text == 'Баланс 💰')
def balance(message):
    user_id = message.from_user.id
    cursor.execute('SELECT swag FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()  

    if result is None:
        bot.send_message(message.chat.id, "❌ Ошибка: пользователь не найден.")
        return

    swag = f"{int(result[0]):,}".replace(",", ".")  
    bot.send_message(message.chat.id, f"🔺 Ваш баланс: {swag} сваги. 💵")

def get_user_stats(user_id):
    cursor.execute('SELECT swag, total_swag, rank, league, registration_date FROM users WHERE user_id = ?', (user_id,))
    return cursor.fetchone()

@bot.message_handler(func=lambda message: message.text == '🚪 Выйти из клана')
def leave_clan(message):
    user_id = message.from_user.id
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT clan_id FROM clan_members WHERE user_id = ?', (user_id,))
    user_clan = cursor.fetchone()

    if user_clan:
        cursor.execute('DELETE FROM clan_members WHERE user_id = ?', (user_id,))
        cursor.execute('UPDATE users SET use_clan_multiplier = 0 WHERE user_id = ?', (user_id,))
        conn.commit()
        bot.send_message(user_id, "❌ Вы покинули клан. Ваш множитель восстановлен.")
    else:
        bot.send_message(user_id, "❌ Вы не состоите в клане.")

    cursor.close()

@bot.message_handler(func=lambda message: message.text == 'Профиль 👤')
def show_profile(message):
    user_id = message.from_user.id
    profile_text, gif_id = get_user_profile_menu(user_id)  

    if gif_id:
        try:
            bot.send_animation(message.chat.id, gif_id)
        except Exception as e:
            print(f"Ошибка при отправке GIF: {e}")

    bot.send_message(message.chat.id, profile_text, parse_mode="Markdown")

def get_user_profile_menu(user_id):
    cursor.execute('SELECT username, swag, total_swag, rank, league, registration_date, hide_top, gif_id, is_premium, selected_badge, premium_end_date FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    if result:
        username, swag, total_swag, rank, league, registration_date, hide_top, gif_id, is_premium, selected_badge, premium_end_date = result

        swag = int(round(swag))
        total_swag = int(round(total_swag))

        display_name = username if username else "None"
        if selected_badge:
            display_name = f"{display_name} {selected_badge}"

        next_rank, swag_needed = get_next_rank(total_swag)

        cursor.execute('SELECT COUNT(*) FROM users WHERE registration_date <= ?', (registration_date,))
        register_id = cursor.fetchone()[0]

        profile_text = (
            "👤 **Ваш профиль**\n\n"
            "📋 **Основная информация:**\n"
            f"🆔 **Ник:** {display_name}\n"
            f"💰 **Баланс:** {swag:,} сваги\n"
            f"🏆 **Натапано всего:** {total_swag:,} сваги\n"
            f"🎖 **Ранг:** {rank}\n"
            f"🏅 **Лига:** {league}\n"
            f"📅 **Дата регистрации:** {registration_date}\n"
            f"🔢 **Register ID:** {register_id}\n\n"  
        )

        if is_premium and premium_end_date:
            end_date = datetime.strptime(premium_end_date, "%Y-%m-%d %H:%M:%S")
            time_left = end_date - datetime.now()
            if time_left.total_seconds() > 0:
                days_left = time_left.days
                hours_left = time_left.seconds // 3600
                profile_text += (
                    "💎 **Премиум-подписка:**\n"
                    f"⏳ **Осталось:** {days_left} дней {hours_left} часов\n\n"
                )
            else:
                profile_text += "💎 **Премиум-подписка:** Отсутствует\n\n"
        else:
            profile_text += "💎 **Премиум-подписка:** Отсутствует\n\n"

        cursor.execute('SELECT badge FROM user_badges WHERE user_id = ?', (user_id,))
        badges = [row[0] for row in cursor.fetchall()]
        if badges:
            profile_text += "🏅 **Достижения:**\n\n"
            for badge in badges:
                if badge == "🌐":
                    profile_text += "🌐 — Повелитель сваги.\n"
                elif badge == "⭕":
                    profile_text += "⭕ — BETA TESTER.\n"
                elif badge == "🔰":
                    profile_text += "🔰 — Кланы - обьединяйтесь!\n"
                elif badge == "⚜":
                    profile_text += "⚜ — Народный деятель сваги.\n"
            profile_text += "\n"

        if user_id == ADMIN_ID:
            profile_text += (
                "⚠️ **Администратор бота:**\n"
                "Вы являетесь администратором бота.\n\n"
            )

        profile_text += (
            "⚙️ **Настройки профиля:**\n"
            f"👀 **Отображение в топах:** {'Включено ✅' if not hide_top else 'Выключено ❌'}\n"
        )

        return profile_text, gif_id
    return "❌ Профиль не найден.", None

def update_premium_status(user_id, is_premium):
    """
    Обновляет премиум-статус пользователя и автоматически добавляет/удаляет знак 💎.
    """
    if is_premium:

        cursor.execute('UPDATE users SET is_premium = 1, selected_badge = ? WHERE user_id = ?', ("💎", user_id))
    else:

        cursor.execute('UPDATE users SET is_premium = 0, selected_badge = NULL WHERE user_id = ?', (user_id,))
    conn.commit()

def get_top_users_by_swag():

    cursor.execute("SELECT user_id, username, hide_top, swag, is_premium, selected_badge FROM users ORDER BY swag DESC LIMIT 10")
    users = cursor.fetchall()

    medals = ["🥇", "🥈", "🥉", "🎖", "🏅", "🎗", "💠", "🔱", "⚜", "🌀"]
    top_message = "💰 **ТОП-10 ПО БАЛАНСУ:**\n\n"
    markup = types.InlineKeyboardMarkup()

    for i, (user_id, username, hide, swag, is_premium, selected_badge) in enumerate(users):
        medal = medals[i] if i < len(medals) else "🎲"

        display_name = username if username else "None"  

        if selected_badge:
            display_name = f"{display_name} {selected_badge}"

        display_name = display_name.replace("*", "\\*").replace("_", "\\_").replace("[", "\\[").replace("]", "\\]")

        swag_formatted = f"{int(swag):,}".replace(",", ".")

        top_message += f"{medal} {i+1}. {display_name} - {swag_formatted} сваги\n"

        if not hide:
            markup.add(types.InlineKeyboardButton(f"👤 Профиль {display_name}", callback_data=f"profile_{user_id}"))

    return top_message, markup

@bot.message_handler(func=lambda message: message.text.strip().lower() == 'топ по сваги 🏆')
def top_all(message):
    top_message, markup = get_top_users_by_swag()
    bot.send_message(message.chat.id, top_message, parse_mode="Markdown", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == 'Магазин 🛒')
def shop(message):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton('Множители 🎲', callback_data='multipliers'))
    markup.add(types.InlineKeyboardButton('Фермы 🌾', callback_data='farms'))
    markup.add(types.InlineKeyboardButton('Премиум 💎', callback_data='premium'))
    markup.add(types.InlineKeyboardButton('Назад 🔙', callback_data='back_to_main'))
    bot.send_message(message.chat.id, "🛒 Выберите категорию:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data == 'premium')
def premium_menu(call):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton('💎 Купить Премиум', url='https://t.me/swagametershop_bot'))
    markup.add(types.InlineKeyboardButton('🔙 Назад', callback_data='back_to_shop'))

    bot.edit_message_text(
        chat_id=call.message.chat.id,
        message_id=call.message.message_id,
        text="💎 **Премиум-подписка открывает вам новые горизонты:**\n\n"
             "• +20% к доходу от кликов и ферм\n"
             "• Эксклюзивный значок 💎 в профиле\n"
             "• Возможность добавить GIF в профиль\n"
             "• Отключение уведомлений от ферм\n"
             "• Доступ к эксклюзивным функциям\n\n"
             "Для покупки нажмите кнопку ниже:",
        reply_markup=markup,
        parse_mode="Markdown"
    )

@bot.message_handler(func=lambda message: message.text == 'Лиги 🏅')
def leagues(message):
    user_id = message.from_user.id
    conn = get_db_connection()  
    cursor = conn.cursor()  

    try:
        cursor.execute('SELECT league FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()

        if result is None:
            bot.send_message(message.chat.id, "❌ Ошибка: пользователь не найден.")
            return

        current_league = result[0]
        next_league = get_next_league(current_league)

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)

        if next_league:
            cost = LEAGUES[next_league]["cost"]
            markup.add(types.KeyboardButton(f'⬆️ Перейти в {next_league} за {cost} сваги'))

        markup.add(types.KeyboardButton('ℹ️ Узнать о лигах'))
        markup.add(types.KeyboardButton('Назад 🔙'))

        bot.send_message(message.chat.id, f"🏅 Ваша текущая лига: {current_league}\nВыберите действие:", reply_markup=markup)

    except sqlite3.Error as e:
        bot.send_message(message.chat.id, f"❌ Произошла ошибка при работе с базой данных: {e}")

    finally:
        cursor.close()  
        conn.close()  

@bot.message_handler(func=lambda message: message.text == 'ℹ️ Узнать о лигах')
def league_info(message):
    info_text = (
        "**🏅 Лиги и их бонусы:**\n\n"
        "1️⃣ **Лига Нормисов 🏅** – 2-5 сваги за клик.\n"
        "2️⃣ **Лига Дрипа 🕶️** – 100k сваги, 5-10 сваги за клик.\n"
        "3️⃣ **Лига Nameles 🌌** – 250k сваги, 10-15 сваги за клик.\n"
        "4️⃣ **Лига Гранд Сваги 💎** – 500k сваги, 15-20 сваги за клик.\n"
        "5️⃣ **ЛИГА СВАГИ 🚀** – 1M сваги, 20-50 сваги за клик.\n"
        "6️⃣ **Лига Величия 👑** – 5M сваги, 50-100 сваги за клик.\n"
        "7️⃣ **Лига Титанов 🗿** – 10M сваги, 100-200 сваги за клик.\n"
        "8️⃣ **Лига Божеств 👼** – 25M сваги, 200-500 сваги за клик.\n"
        "9️⃣ **Лига Абсолютного Превосходства ⚡** – 50M сваги, 500-1000 сваги за клик.\n"
        "🔟 **Лига Вечных Знаменитостей 🌟** – 100M сваги, 1000-5000 сваги за клик.\n"
        "1️⃣1️⃣ **Лига Легендарных Королей 👑✨** – 500M сваги, 5000-10000 сваги за клик.\n\n"
        "💡 **При переходе в новую лигу ваш аккаунт полностью обнуляется**, но сваги за клик становится больше!"
    )
    bot.send_message(message.chat.id, info_text, parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text.startswith('⬆️ Перейти в'))
def confirm_league_upgrade(message):
    user_id = message.from_user.id
    next_league = message.text.split(' в ')[1].split(' за')[0]

    cursor.execute('SELECT swag FROM users WHERE user_id = ?', (user_id,))
    swag = cursor.fetchone()[0]
    cost = LEAGUES[next_league]["cost"]

    if swag < cost:
        bot.send_message(message.chat.id, f"❌ У вас недостаточно сваги для перехода в {next_league}.")
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton(f'✅ Подтвердить переход в {next_league}'))
    markup.add(types.KeyboardButton('❌ Отмена'))

    bot.send_message(
        message.chat.id,
        f"⚠️ **Внимание!** Переход в {next_league} полностью **обнулит ваш аккаунт**.\n\n"
        f"Но свага за клик увеличится! Вы уверены?",
        reply_markup=markup,
        parse_mode="Markdown"
    )

@bot.message_handler(func=lambda message: message.text.startswith('✅ Подтвердить переход в'))
def upgrade_league(message):
    user_id = message.from_user.id
    next_league = message.text.split(' в ')[1]

    cursor.execute('SELECT swag FROM users WHERE user_id = ?', (user_id,))
    swag = cursor.fetchone()[0]
    cost = LEAGUES[next_league]["cost"]

    if swag < cost:
        bot.send_message(message.chat.id, "❌ У вас недостаточно сваги для перехода.")
        return

    cursor.execute('UPDATE users SET league = ?, swag = 0, total_swag = 0, rank = ?, multiplier = 1 WHERE user_id = ?', 
                   (next_league, "Нуб 👶", user_id))
    conn.commit()

    bot.send_message(message.chat.id, f"🎉 Вы успешно перешли в {next_league}! Ваш аккаунт был полностью очищен.")
    leagues(message)  

@bot.message_handler(func=lambda message: message.text == '❌ Отмена')
def cancel_league_upgrade(message):
    leagues(message)

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):

    if call.data.startswith("profile_"):
        show_profile(call)
        return

    if call.data == "back_to_top":
        back_to_top(call)
        return

    try:
        if call.data in ['multipliers', 'farms', 'back_to_shop', 'back_to_main'] or call.data.startswith('buy_') or call.data.startswith('upgrade_') or call.data.startswith('confirm_upgrade_') or call.data == 'delete_clan':
            bot.delete_message(call.message.chat.id, call.message.message_id)
    except:
        pass  

    if call.data == 'multipliers':
        markup = types.InlineKeyboardMarkup()
        for multiplier, cost in MULTIPLIERS.items():
            markup.add(types.InlineKeyboardButton(f'{multiplier} - {cost} сваги', callback_data=f'buy_{multiplier}'))
        markup.add(types.InlineKeyboardButton('Назад 🔙', callback_data='back_to_shop'))
        bot.send_message(call.message.chat.id, "🎲 Выберите множитель:", reply_markup=markup)

    elif call.data == 'farms':
        markup = types.InlineKeyboardMarkup()
        for farm, data in FARMS.items():
            markup.add(types.InlineKeyboardButton(f'{farm} - {data["cost"]} сваги', callback_data=f'buy_{farm}'))
        markup.add(types.InlineKeyboardButton('Назад 🔙', callback_data='back_to_shop'))
        bot.send_message(call.message.chat.id, "🌾 Выберите ферму:", reply_markup=markup)

    elif call.data.startswith('buy_'):
        item = call.data[4:]
        user_id = call.from_user.id
        if item in MULTIPLIERS:
            if buy_multiplier(user_id, item):
                bot.send_message(call.message.chat.id, f"🎉 Вы успешно купили множитель {item}!")
            else:
                bot.send_message(call.message.chat.id, "😢 У вас недостаточно сваги для покупки этого множителя.")
        elif item in FARMS:
            if buy_farm(user_id, item):
                bot.send_message(call.message.chat.id, f"🎉 Вы успешно купили {item}!")
            else:
                bot.send_message(call.message.chat.id, "😢 У вас недостаточно сваги для покупки этой фермы.")

    elif call.data.startswith('upgrade_'):
        next_league = call.data[8:]
        user_id = call.from_user.id
        cursor.execute('SELECT swag FROM users WHERE user_id = ?', (user_id,))
        swag = cursor.fetchone()[0]
        cost = LEAGUES[next_league]["cost"]
        if swag >= cost:
            update_league(user_id, next_league)
            bot.send_message(call.message.chat.id, f"🎉 Вы перешли в лигу {next_league}! Ваш аккаунт был обнулен.")
        else:
            bot.send_message(call.message.chat.id, f"😢 У вас недостаточно сваги для перехода в лигу {next_league}.")

    elif call.data == 'back_to_shop':
        shop(call.message)

    elif call.data == 'back_to_main':
        main_menu(call.message)

@bot.message_handler(func=lambda message: message.text == 'Казино 🎰')
def casino(message):
    bot.send_message(
        message.chat.id,
        "🎰 **Добро пожаловать в казино!** 🎰\n\n"
        "Введите сумму ставки (от 50 до 5 000 000 сваги), а затем выберите цвет.\n\n"
        "🔴 Красный — 45% шанс, коэффициент **x2**\n"
        "⚫ Чёрный — 45% шанс, коэффициент **x2**\n"
        "🟢 Зелёный — 10% шанс, коэффициент **x10**\n\n"
        "💰 Если угадаете — получите выигрыш по коэффициенту!",
        parse_mode="Markdown"
    )

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton('Назад 🔙'))

    bot.send_message(message.chat.id, "💵 Введите сумму ставки:", reply_markup=markup)
    bot.register_next_step_handler(message, handle_bet_input)

def handle_bet_input(message):
    if message.text == "Назад 🔙":
        return main_menu(message)  

    user_id = message.from_user.id
    try:
        bet = int(message.text)
        if bet < 50 or bet > 5000000:
            bot.send_message(message.chat.id, "❌ Ошибка: ставка должна быть от 50 до 5 000 000 сваги. Введите заново:")
            return bot.register_next_step_handler(message, handle_bet_input)

        cursor.execute('SELECT swag FROM users WHERE user_id = ?', (user_id,))
        swag = cursor.fetchone()[0]

        if swag < bet:
            bot.send_message(message.chat.id, "❌ Ошибка: у вас недостаточно сваги. Введите ставку заново:")
            return bot.register_next_step_handler(message, handle_bet_input)

        choose_color(message, bet)

    except ValueError:
        bot.send_message(message.chat.id, "❌ Ошибка: введите корректное число.")
        return bot.register_next_step_handler(message, handle_bet_input)

def choose_color(message, bet):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("🔴 Красный"), types.KeyboardButton("⚫ Чёрный"))
    markup.add(types.KeyboardButton("🟢 Зелёный"))
    markup.add(types.KeyboardButton("Назад 🔙"))

    bot.send_message(message.chat.id, "🎰 Выберите цвет для ставки:", reply_markup=markup)
    bot.register_next_step_handler(message, process_bet, bet)

def process_bet(message, bet):
    user_id = message.from_user.id
    chosen_color = message.text

    if chosen_color == "Назад 🔙":
        return casino(message)  

    if chosen_color not in ["🔴 Красный", "⚫ Чёрный", "🟢 Зелёный"]:
        bot.send_message(message.chat.id, "❌ Ошибка: выберите цвет из предложенных.")
        return bot.register_next_step_handler(message, process_bet, bet)

    roll = random.randint(1, 100)
    if roll <= 45:
        result_color = "🔴 Красный"
    elif roll <= 90:
        result_color = "⚫ Чёрный"
    else:
        result_color = "🟢 Зелёный"

    win_multipliers = {"🔴 Красный": 2, "⚫ Чёрный": 2, "🟢 Зелёный": 10}

    if result_color == chosen_color:
        win_amount = bet * win_multipliers[result_color]
        cursor.execute('UPDATE users SET swag = swag + ? WHERE user_id = ?', (win_amount, user_id))
        bot.send_message(message.chat.id, f"🎉 Поздравляем! Вы выиграли {win_amount} сваги! Выпал {result_color}!")
    else:
        cursor.execute('UPDATE users SET swag = swag - ? WHERE user_id = ?', (bet, user_id))
        bot.send_message(message.chat.id, f"😢 Вы проиграли {bet} сваги. Выпал {result_color}, не повезло!")

    conn.commit()

    bot.send_message(message.chat.id, "🎰 Хотите сыграть ещё раз? Введите сумму ставки:")
    bot.register_next_step_handler(message, handle_bet_input)

def main_menu(message):
    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(types.KeyboardButton('Тапать 🤑'), types.KeyboardButton('Баланс 💰'))
    markup.add(types.KeyboardButton('Профиль 👤'), types.KeyboardButton('Топ по сваги 🏆'))
    markup.add(types.KeyboardButton('Магазин 🛒'), types.KeyboardButton('Игры 🎲'))
    markup.add(types.KeyboardButton('Лиги 🏅'), types.KeyboardButton('Фермы 🏡'))
    markup.add(types.KeyboardButton('Кланы 🏰'), types.KeyboardButton('Наш телеграм 📢'))
    markup.add(types.KeyboardButton('Настройки ⚙️'), types.KeyboardButton('Информация ℹ️'))

    bot.send_message(message.chat.id, "Вы вернулись в главное меню! 🎰", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == 'Наш телеграм 📢')
def telegram_channel(message):
    bot.send_message(message.chat.id, "📢 Подписывайтесь на наш канал: https://t.me/metrswagi")

@bot.callback_query_handler(func=lambda call: call.data.startswith('upgrade_'))
def confirm_league_upgrade(call):
    delete_message(call)
    next_league = call.data[8:]
    user_id = call.from_user.id
    cursor.execute('SELECT swag FROM users WHERE user_id = ?', (user_id,))
    swag = cursor.fetchone()[0]
    cost = LEAGUES[next_league]["cost"]

    if swag < cost:
        bot.send_message(call.message.chat.id, f"❌ У вас недостаточно сваги для перехода в {next_league}.")
        return

    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton('✅ Подтвердить', callback_data=f'confirm_upgrade_{next_league}'))
    markup.add(types.InlineKeyboardButton('❌ Отмена', callback_data='back_to_main'))
    bot.send_message(call.message.chat.id, f"⚠️ При переходе в {next_league} ваш аккаунт будет полностью очищен! Вы уверены?", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith('confirm_upgrade_'))
def upgrade_league(call):
    delete_message(call)
    next_league = call.data[15:]
    user_id = call.from_user.id
    cursor.execute('UPDATE users SET league = ?, swag = 0, total_swag = 0, rank = ?, multiplier = 1 WHERE user_id = ?', (next_league, "Нуб 👶", user_id))
    conn.commit()
    bot.send_message(call.message.chat.id, f"🎉 Вы успешно перешли в {next_league}! Ваш аккаунт был полностью очищен.")

@bot.message_handler(func=lambda message: message.text == 'Назад 🔙')
def go_back(message):

    markup = types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add(types.KeyboardButton('Тапать 🤑'), types.KeyboardButton('Баланс 💰'))
    markup.add(types.KeyboardButton('Профиль 👤'), types.KeyboardButton('Топ по сваги 🏆'))
    markup.add(types.KeyboardButton('Магазин 🛒'), types.KeyboardButton('Игры 🎲'))
    markup.add(types.KeyboardButton('Лиги 🏅'), types.KeyboardButton('Фермы 🏡'))
    markup.add(types.KeyboardButton('Кланы 🏰'), types.KeyboardButton('Наш телеграм 📢'))
    markup.add(types.KeyboardButton('Информация ℹ️'))
    markup.add(types.KeyboardButton('Настройки ⚙️'))

    bot.send_message(message.chat.id, "🔶 Вы вернулись в главное меню! Продолжаем игру! 💲", reply_markup=markup)

def farm_income():
    conn = sqlite3.connect("swag_boti.db")
    cursor = conn.cursor()

    cursor.execute('''
        SELECT user_id, farm_type, SUM(quantity), clan_connected, last_income 
        FROM farms 
        GROUP BY user_id, farm_type, clan_connected
    ''')
    farms = cursor.fetchall()

    user_income_data = {}  

    all_user_ids = list(set(farm[0] for farm in farms))

    user_manual_mode = {}
    user_clans = {}
    clan_tax_rates = {}

    for user_id in all_user_ids:

        cursor.execute('SELECT manual_farm_collection FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()
        user_manual_mode[user_id] = result[0] if result else 0

        cursor.execute('SELECT clan_id FROM clan_members WHERE user_id = ?', (user_id,))
        clan_result = cursor.fetchone()
        user_clans[user_id] = clan_result[0] if clan_result else None

        clan_id = user_clans.get(user_id)
        if clan_id:
            cursor.execute('SELECT tax_rate FROM clans WHERE clan_id = ?', (clan_id,))
            tax_result = cursor.fetchone()
            clan_tax_rates[clan_id] = tax_result[0] if tax_result else 5  

    for user_id, farm_type, total_quantity, clan_connected, last_income in farms:
        if farm_type not in FARMS:
            continue

        income_per_farm = FARMS[farm_type]["income"]
        total_income = income_per_farm * total_quantity

        manual_collection = user_manual_mode.get(user_id, 0)

        if not manual_collection:  
            if last_income:
                try:
                    last_income_time = datetime.strptime(last_income, "%Y-%m-%d %H:%M:%S")
                    if (datetime.now() - last_income_time).total_seconds() < 3600:
                        continue  
                except ValueError:
                    pass  

        if user_id not in user_income_data:
            user_income_data[user_id] = {
                "personal_income": 0,
                "clan_income": 0,
                "farms_details": []
            }

        if clan_connected:
            clan_id = user_clans.get(user_id)
            if clan_id:
                cursor.execute('UPDATE clans SET balance = balance + ? WHERE clan_id = ?', (total_income, clan_id))
                conn.commit()
                user_income_data[user_id]["clan_income"] += total_income
        else:

            tax_amount = 0
            clan_id = user_clans.get(user_id)
            if clan_id:
                tax_rate = clan_tax_rates.get(clan_id, 5)
                tax_amount = math.ceil(total_income * (tax_rate / 100))  

            income_after_tax = total_income - tax_amount

            cursor.execute('UPDATE users SET swag = swag + ?, total_swag = total_swag + ? WHERE user_id = ?', 
                           (income_after_tax, income_after_tax, user_id))
            conn.commit()

            user_income_data[user_id]["personal_income"] += income_after_tax

        user_income_data[user_id]["farms_details"].append(f"{farm_type} x{total_quantity}")

        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute('''
            UPDATE farms 
            SET last_income = ? 
            WHERE user_id = ? AND farm_type = ?
        ''', (current_time, user_id, farm_type))
        conn.commit()

    conn.close()

    for user_id, data in user_income_data.items():
        message_parts = []

        if data["farms_details"]:
            message_parts.append("🌾 Ваши фермы принесли доход:")
            for detail in data["farms_details"]:
                message_parts.append(f"- {detail}")
        if data["personal_income"] > 0:
            message_parts.append(f"💰 Вы получили {data['personal_income']} сваги.")
        if data["clan_income"] > 0:
            message_parts.append(f"🧾 Ваш клан получил {data['clan_income']} сваги.")

        if message_parts:
            try:
                bot.send_message(user_id, "\n".join(message_parts), parse_mode="Markdown")
            except Exception as e:
                print(f"[Ошибка отправки] Пользователь {user_id}: {e}")

def connect_farm_to_clan(user_id, farm_type):

    cursor.execute('SELECT clan_id FROM clans WHERE owner_id = ?', (user_id,))
    clan = cursor.fetchone()
    if not clan:
        return False, "❌ Вы не являетесь лидером клана."

    clan_id = clan[0]

    cursor.execute('SELECT quantity, clan_connected FROM farms WHERE user_id = ? AND farm_type = ?', (user_id, farm_type))
    farm = cursor.fetchone()
    if not farm or farm[0] <= 0:
        return False, f"❌ У вас нет {farm_type}."

    if farm[1] == 1:
        return False, f"❌ Эта {farm_type} уже подключена к клану."

    cursor.execute('SELECT COUNT(*) FROM farms WHERE user_id = ? AND clan_connected = 1', (user_id,))
    connected_farms = cursor.fetchone()[0]

    cursor.execute('SELECT is_premium FROM users WHERE user_id = ?', (user_id,))
    is_premium = cursor.fetchone()[0]
    max_farms = 5 if is_premium else 3

    if connected_farms >= max_farms:
        return False, f"❌ Вы достигли лимита ({max_farms} ферм) для подключения к клану."

    cursor.execute('UPDATE farms SET clan_connected = 1 WHERE user_id = ? AND farm_type = ?', (user_id, farm_type))
    conn.commit()
    return True, f"🎉 {farm_type} успешно подключена к клану! Теперь её доход идёт в казну."

def disconnect_farm_from_clan(user_id, farm_type):

    cursor.execute('SELECT clan_id FROM clans WHERE owner_id = ?', (user_id,))
    clan = cursor.fetchone()
    if not clan:
        return False, "❌ Вы не являетесь лидером клана."

    cursor.execute('SELECT clan_connected FROM farms WHERE user_id = ? AND farm_type = ?', (user_id, farm_type))
    farm = cursor.fetchone()
    if not farm or farm[0] == 0:
        return False, f"❌ Эта {farm_type} не подключена к клану."

    cursor.execute('UPDATE farms SET clan_connected = 0 WHERE user_id = ? AND farm_type = ?', (user_id, farm_type))
    conn.commit()
    return True, f"✅ {farm_type} отключена от клана. Доход снова идёт вам."

@bot.message_handler(func=lambda message: message.text == '💰 Собрать доход')
def collect_farm_income(message):
    user_id = message.from_user.id

    cursor.execute('SELECT manual_farm_collection FROM users WHERE user_id = ?', (user_id,))
    manual_collection = cursor.fetchone()[0]

    if not manual_collection:
        bot.send_message(message.chat.id, "❌ Ручная сборка доходов отключена. Доходы начисляются автоматически.")
        return

    cursor.execute('SELECT farm_type, quantity, clan_connected, last_income FROM farms WHERE user_id = ?', (user_id,))
    farms = cursor.fetchall()

    if not farms:
        bot.send_message(message.chat.id, "❌ У вас нет ферм.")
        return

    total_income = 0
    has_clan_connected_farms = False  
    has_farms_in_cooldown = False  

    for farm_type, quantity, clan_connected, last_income in farms:
        if farm_type in FARMS:
            if clan_connected:  
                has_clan_connected_farms = True
                continue  

            last_income_time = datetime.strptime(last_income, "%Y-%m-%d %H:%M:%S") if last_income else None
            if last_income_time and (datetime.now() - last_income_time) < timedelta(hours=1):
                has_farms_in_cooldown = True
                continue  

            income_per_farm = FARMS[farm_type]["income"]
            total_income += income_per_farm * quantity

    if has_clan_connected_farms:
        bot.send_message(message.chat.id, "⚠️ Некоторые фермы привязаны к клану. Их доход собирается автоматически.")

    if total_income == 0:
        if has_farms_in_cooldown:
            bot.send_message(message.chat.id, "⏳ Ваши фермы в кулдауне! Попробуйте позже.")
        else:
            bot.send_message(message.chat.id, "❌ У вас нет доступных ферм для сбора дохода.")
        return

    cursor.execute('SELECT is_premium FROM users WHERE user_id = ?', (user_id,))
    is_premium = cursor.fetchone()[0]

    if is_premium:
        total_income = int(total_income * 1.2)

    tax_amount = max(1, total_income // 20)  
    income_after_tax = total_income - tax_amount

    cursor.execute('SELECT swag FROM users WHERE user_id = ?', (user_id,))
    current_swag = cursor.fetchone()[0]
    new_swag = current_swag + income_after_tax
    cursor.execute('UPDATE users SET swag = ? WHERE user_id = ?', (new_swag, user_id))

    cursor.execute('SELECT clan_id FROM clan_members WHERE user_id = ?', (user_id,))
    clan = cursor.fetchone()
    if clan:
        clan_id = clan[0]
        cursor.execute('UPDATE clans SET balance = balance + ? WHERE clan_id = ?', (tax_amount, clan_id))

    current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    cursor.execute('UPDATE farms SET last_income = ? WHERE user_id = ?', (current_time, user_id))

    conn.commit()

    bot.send_message(message.chat.id, f"💰 Вы собрали {income_after_tax} сваги от ваших ферм (налог {tax_amount} сваги ушёл в клан).")

def schedule_farm_income():
    scheduler = BackgroundScheduler()
    scheduler.add_job(farm_income, 'interval', hours=1)
    scheduler.start()

def is_admin(user_id):
    return user_id == ADMIN_ID

@bot.message_handler(commands=['give'])
def give_swag(message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        bot.send_message(message.chat.id, "❌ У вас нет прав для использования этой команды.")
        return

    try:
        parts = message.text.split()
        target_user_id = int(parts[1])  
        amount = int(parts[2])  

        if amount <= 0:
            bot.send_message(message.chat.id, "❌ Количество сваги должно быть положительным числом.")
            return

        cursor.execute('SELECT swag FROM users WHERE user_id = ?', (target_user_id,))
        result = cursor.fetchone()

        if result:
            cursor.execute('UPDATE users SET swag = swag + ? WHERE user_id = ?', (amount, target_user_id))
            conn.commit()
            bot.send_message(message.chat.id, f"🎉 {amount} сваги было добавлено пользователю {target_user_id}.")
        else:
            bot.send_message(message.chat.id, "❌ Пользователь не найден.")
    except IndexError:
        bot.send_message(message.chat.id, "❌ Неверный формат команды. Используйте: /give <user_id> <amount>")
    except ValueError:
        bot.send_message(message.chat.id, "❌ Пожалуйста, укажите корректные данные.")

@bot.message_handler(commands=['take'])
def take_swag(message):
    user_id = message.from_user.id
    if not is_admin(user_id):
        bot.send_message(message.chat.id, "❌ У вас нет прав для использования этой команды.")
        return

    try:
        parts = message.text.split()
        target_user_id = int(parts[1])  
        amount = int(parts[2])  

        if amount <= 0:
            bot.send_message(message.chat.id, "❌ Количество сваги должно быть положительным числом.")
            return

        cursor.execute('SELECT swag FROM users WHERE user_id = ?', (target_user_id,))
        result = cursor.fetchone()

        if result:
            current_swag = result[0]
            if current_swag >= amount:
                cursor.execute('UPDATE users SET swag = swag - ? WHERE user_id = ?', (amount, target_user_id))
                conn.commit()
                bot.send_message(message.chat.id, f"❌ {amount} сваги было забрано у пользователя {target_user_id}.")
            else:
                bot.send_message(message.chat.id, "❌ У пользователя недостаточно сваги для изъятия.")
        else:
            bot.send_message(message.chat.id, "❌ Пользователь не найден.")
    except IndexError:
        bot.send_message(message.chat.id, "❌ Неверный формат команды. Используйте: /take <user_id> <amount>")
    except ValueError:
        bot.send_message(message.chat.id, "❌ Пожалуйста, укажите корректные данные.")

@bot.message_handler(func=lambda message: message.text == 'Фермы 🏡')
def farms_menu(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton('🏡 Мои фермы'))
    markup.add(types.KeyboardButton('💰 Собрать доход'))
    markup.add(types.KeyboardButton('⚙️ Режимы работы ферм'))
    markup.add(types.KeyboardButton('ℹ️ Подробнее о фермах'))
    markup.add(types.KeyboardButton('Назад 🔙'))

    bot.send_message(message.chat.id, "🌾 Добро пожаловать в меню ферм! Выберите действие:", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == '⚙️ Режимы работы ферм')
def farm_modes(message):
    user_id = message.from_user.id
    conn = get_db_connection()
    cursor = conn.cursor()

    try:

        cursor.execute('''
            SELECT manual_farm_collection, disable_farm_notifications, is_premium 
            FROM users 
            WHERE user_id = ?
        ''', (user_id,))
        result = cursor.fetchone()
        if not result:
            bot.send_message(message.chat.id, "❌ Ошибка: пользователь не найден.")
            return

        manual_collection, disable_notifications, is_premium = result

        mode_text = "🔄 **Текущий режим работы ферм:**\n"
        mode_text += "✅ **Ручной сбор дохода** (нажмите для смены)\n" if manual_collection else "🔁 **Автоматический сбор дохода** (нажмите для смены)\n"

        notification_text = ""
        if is_premium:
            notification_text = "🔕 **Уведомления отключены** (нажмите, чтобы включить)\n" if disable_notifications else "🔔 **Уведомления включены** (нажмите, чтобы отключить)\n"
        else:
            notification_text = "\n💎 *Отключение уведомлений доступно только премиум-пользователям!*"

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton('🔄 Сменить режим'))

        if is_premium:
            btn_text = '🔕 Отключить уведомления' if not disable_notifications else '🔔 Включить уведомления'
            markup.add(types.KeyboardButton(btn_text))

        markup.add(types.KeyboardButton('🔙 Назад в меню ферм'))  

        bot.send_message(
            message.chat.id,
            mode_text + ("\n" + notification_text if notification_text.strip() else ""),
            reply_markup=markup,
            parse_mode="Markdown"
        )

    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Ошибка при открытии настроек ферм: {e}")
    finally:
        cursor.close()
        conn.close()

@bot.message_handler(func=lambda message: message.text == '🔄 Сменить режим')
def toggle_farm_mode(message):
    user_id = message.from_user.id
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('SELECT manual_farm_collection FROM users WHERE user_id = ?', (user_id,))
        current_mode = cursor.fetchone()[0]
        new_mode = 0 if current_mode else 1
        cursor.execute('UPDATE users SET manual_farm_collection = ? WHERE user_id = ?', (new_mode, user_id))
        conn.commit()
        bot.send_message(message.chat.id, "🔄 Режим фермы изменён.")
        farm_modes(message)  
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Ошибка изменения режима фермы: {e}")
    finally:
        cursor.close()
        conn.close()

@bot.message_handler(func=lambda message: message.text in ['🔔 Включить уведомления', '🔕 Отключить уведомления'])
def toggle_farm_notifications(message):
    user_id = message.from_user.id
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute('SELECT disable_farm_notifications FROM users WHERE user_id = ?', (user_id,))
        current_status = cursor.fetchone()[0]
        new_status = 0 if current_status else 1  
        cursor.execute('UPDATE users SET disable_farm_notifications = ? WHERE user_id = ?', (new_status, user_id))
        conn.commit()
        status_text = "🔔 Уведомления включены." if new_status == 0 else "🔕 Уведомления отключены."
        bot.send_message(message.chat.id, status_text)
        farm_modes(message)  
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Ошибка изменения уведомлений: {e}")
    finally:
        cursor.close()
        conn.close()

@bot.message_handler(func=lambda message: message.text == '🔙 Назад в меню ферм')
def back_to_farms(message):
    farms_menu(message)  

@bot.message_handler(func=lambda message: message.text == 'ℹ️ Подробнее о фермах')
def farms_info(message):
    info_text = (
        "**🌾 Фермы и их доход:**\n\n"
        "1️⃣ **Ферма Дрипа 🌾** – 100k сваги, приносит **1k/час**.\n"
        "2️⃣ **Ферма Майнер ⛏️** – 500k сваги, приносит **5k/час**.\n"
        "3️⃣ **Ферма мобов 👾** – 1M сваги, приносит **10k/час**.\n"
        "4️⃣ **Ферма сваги 💰** – 5M сваги, приносит **50k/час**.\n\n"
        "💡 **Каждая ферма приносит доход раз в 1 час!**"
    )
    bot.send_message(message.chat.id, info_text, parse_mode="Markdown")

def buy_farm(user_id, farm_type):
    cost = FARMS[farm_type]["cost"]
    cursor.execute('SELECT swag FROM users WHERE user_id = ?', (user_id,))
    swag = cursor.fetchone()[0]

    if swag >= cost:
        cursor.execute('UPDATE users SET swag = swag - ? WHERE user_id = ?', (cost, user_id))
        cursor.execute(
            'INSERT INTO farms (user_id, farm_type, quantity, last_income) VALUES (?, ?, 1, ?)',
            (user_id, farm_type, datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        )
        conn.commit()
        return True
    return False

@bot.message_handler(func=lambda message: message.text == '🏡 Мои фермы')
def user_farms(message):
    user_id = message.from_user.id

    cursor.execute('SELECT manual_farm_collection FROM users WHERE user_id = ?', (user_id,))
    manual_collection = cursor.fetchone()[0]

    cursor.execute('SELECT farm_type, quantity, last_income, clan_connected FROM farms WHERE user_id = ?', (user_id,))
    farms = cursor.fetchall()

    if not farms:
        bot.send_message(message.chat.id, "😔 У вас пока нет ферм. Купите ферму в магазине!")
        return

    grouped_farms = {}

    for farm_type, quantity, last_income, clan_connected in farms:
        if farm_type not in grouped_farms:
            grouped_farms[farm_type] = {
                "quantity": 0,
                "last_income": last_income,
                "clan_connected": clan_connected
            }
        grouped_farms[farm_type]["quantity"] += quantity

    farms_info = "**🏡 Ваши фермы:**\n\n"

    for farm_type, data in grouped_farms.items():
        quantity = data["quantity"]
        clan_connected = data["clan_connected"]
        last_income = data["last_income"]

        if clan_connected:
            farms_info += f"{farm_type} ×{quantity} | Привязано к клану (доход идёт в казну клана)\n"
        else:
            if last_income is None:
                time_text = "❌ Данные о доходе недоступны"
            else:
                last_income_time = datetime.strptime(last_income, "%Y-%m-%d %H:%M:%S")
                next_income_time = last_income_time + timedelta(hours=1)
                time_remaining = (next_income_time - datetime.now()).total_seconds()

                if time_remaining > 0:
                    hours = int(time_remaining // 3600)
                    minutes = int((time_remaining % 3600) // 60)
                    time_text = f"⏳ Следующий доход через {hours}ч {minutes}м"
                else:
                    if manual_collection:
                        time_text = "✅ Готово к сбору!"
                    else:
                        time_text = "✅ Доход собирается автоматически"

            farms_info += f"{farm_type} ×{quantity} | {time_text}\n"

    bot.send_message(message.chat.id, farms_info, parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == '💰 Собрать доход')
def collect_farm_income(message):
    user_id = message.from_user.id

    cursor.execute('SELECT manual_farm_collection FROM users WHERE user_id = ?', (user_id,))
    manual_collection = cursor.fetchone()[0]

    if not manual_collection:
        bot.send_message(message.chat.id, "❌ Ручная сборка доходов отключена. Доходы начисляются автоматически.")
        return

    cursor.execute('SELECT farm_type, quantity, clan_connected FROM farms WHERE user_id = ?', (user_id,))
    farms = cursor.fetchall()

    if not farms:
        bot.send_message(message.chat.id, "❌ У вас нет ферм.")
        return

    total_income = 0
    has_clan_connected_farms = False  

    for farm_type, quantity, clan_connected in farms:
        if farm_type in FARMS:
            if clan_connected:  
                has_clan_connected_farms = True
                continue  
            income_per_farm = FARMS[farm_type]["income"]
            total_income += income_per_farm * quantity

    if has_clan_connected_farms:
        bot.send_message(message.chat.id, "⚠️ Некоторые фермы привязаны к клану. Их доход собирается автоматически.")

    if total_income == 0:
        bot.send_message(message.chat.id, "❌ Нет ферм, доступных для ручного сбора.")
        return

    cursor.execute('SELECT is_premium FROM users WHERE user_id = ?', (user_id,))
    is_premium = cursor.fetchone()[0]

    if is_premium:
        total_income = int(total_income * 1.2)  

    cursor.execute('SELECT clan_id FROM clan_members WHERE user_id = ?', (user_id,))
    clan = cursor.fetchone()
    tax_rate = 5  
    if clan:
        clan_id = clan[0]
        cursor.execute('SELECT tax_rate FROM clans WHERE clan_id = ?', (clan_id,))
        tax_data = cursor.fetchone()
        if tax_data and tax_data[0] is not None:
            tax_rate = tax_data[0]

    tax_amount = math.ceil(total_income * (tax_rate / 100))  
    income_after_tax = total_income - tax_amount

    cursor.execute('SELECT swag FROM users WHERE user_id = ?', (user_id,))
    current_swag = cursor.fetchone()[0]
    new_swag = current_swag + income_after_tax
    cursor.execute('UPDATE users SET swag = ? WHERE user_id = ?', (new_swag, user_id))

    cursor.execute('SELECT clan_id FROM clan_members WHERE user_id = ?', (user_id,))
    clan = cursor.fetchone()
    if clan:
        clan_id = clan[0]
        cursor.execute('UPDATE clans SET balance = balance + ? WHERE clan_id = ?', (tax_amount, clan_id))

    conn.commit()

    bot.send_message(message.chat.id, f"💰 Вы собрали {income_after_tax} сваги от ваших ферм (налог {tax_amount} сваги ушёл в клан).")

def schedule_clan_multiplier_upgrade():
    scheduler = BackgroundScheduler()
    scheduler.add_job(auto_buy_clan_multiplier, 'interval', minutes=10)
    scheduler.start()

@bot.message_handler(func=lambda message: message.text == 'Настройки ⚙️')
def settings(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton('🙈 Переключить видимость в топах'))
    markup.add(types.KeyboardButton('🔄 Переключить множитель клана'))
    markup.add(types.KeyboardButton('🎞️ Добавить GIF в профиль'))
    markup.add(types.KeyboardButton('🔖 Выбрать знак для ника'))
    markup.add(types.KeyboardButton('🔖 Удалить знак у ника'))
    markup.add(types.KeyboardButton('🔄 Обновить ник'))  
    markup.add(types.KeyboardButton('Назад 🔙'))
    bot.send_message(message.chat.id, "⚙️ Настройки:\nВы можете скрыть или показать свое имя в топах, управлять множителем клана, добавлять GIF в профиль, выбирать знак для ника, а также обновлять свой ник.", reply_markup=markup)

@bot.message_handler(func=lambda message: message.text == '🔄 Обновить ник')
def update_nickname(message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    try:

        user_info = bot.get_chat_member(chat_id, user_id)
        current_username = user_info.user.username

        if current_username:

            cursor.execute('UPDATE users SET username = ? WHERE user_id = ?', (current_username, user_id))
            conn.commit()
            bot.send_message(chat_id, f"✅ Ваш никнейм успешно обновлён на @{current_username}.")
        else:
            bot.send_message(chat_id, "❌ Вы не установили никнейм в Telegram. Пожалуйста, установите его в настройках Telegram и попробуйте снова.")

    except telebot.apihelper.ApiTelegramException as e:
        if e.error_code == 400 and "CHAT_ADMIN_REQUIRED" in e.description:
            bot.send_message(chat_id, "❌ Бот должен быть администратором в этом чате, чтобы получить информацию о вас.")
        else:
            bot.send_message(chat_id, f"❌ Произошла ошибка при обновлении ника: {e}")
    except Exception as e:
        bot.send_message(chat_id, f"❌ Произошла ошибка: {e}")

def process_badge_selection(message, badges):
    user_id = message.from_user.id

    if message.text == 'Назад 🔙':
        settings(message)
        return

    selected_badge = None
    for badge in badges:
        if f"Выбрать {badge}" in message.text:
            selected_badge = badge
            break

    if selected_badge:

        cursor.execute('UPDATE users SET selected_badge = ? WHERE user_id = ?', (selected_badge, user_id))
        conn.commit()
        bot.send_message(message.chat.id, f"✅ Знак {selected_badge} теперь будет отображаться у вашего ника.")
    else:
        bot.send_message(message.chat.id, "❌ Неверный выбор знака. Попробуйте снова.")
        select_badge(message)

@bot.message_handler(func=lambda message: message.text == '🔖 Выбрать знак для ника')
def select_badge(message):
    user_id = message.from_user.id

    cursor.execute('SELECT badge FROM user_badges WHERE user_id = ?', (user_id,))
    badges = [row[0] for row in cursor.fetchall()]

    if user_id == ADMIN_ID:
        badges.append("⚠️")  
    cursor.execute('SELECT is_premium FROM users WHERE user_id = ?', (user_id,))
    is_premium = cursor.fetchone()[0]
    if is_premium:
        badges.append("💎")  

    if not badges:
        bot.send_message(message.chat.id, "❌ У вас нет доступных знаков.")
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for badge in badges:
        markup.add(types.KeyboardButton(f"Выбрать {badge}"))
    markup.add(types.KeyboardButton('Удалить знак'))  
    markup.add(types.KeyboardButton('Назад 🔙'))

    bot.send_message(message.chat.id, "🔖 Выберите знак для отображения у вашего ника:", reply_markup=markup)
    bot.register_next_step_handler(message, process_badge_selection, badges)

@bot.message_handler(func=lambda message: message.text == '🔖 Удалить знак у ника')
def remove_badge(message):
    user_id = message.from_user.id

    cursor.execute('UPDATE users SET selected_badge = NULL WHERE user_id = ?', (user_id,))
    conn.commit()

    bot.send_message(message.chat.id, "✅ Все знаки у вашего ника удалены. Вы можете снова выбрать знак.")

@bot.message_handler(func=lambda message: message.text == '🎞️ Добавить GIF в профиль')
def request_gif(message):
    user_id = message.from_user.id
    cursor.execute('SELECT is_premium FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    is_premium = result[0] if result else 0

    if not is_premium:
        bot.send_message(message.chat.id, "❌ Эта функция доступна только премиум-пользователям.")
        settings(message)
        return

    bot.send_message(message.chat.id, "📤 Отправьте GIF-анимацию, которую хотите добавить в свой профиль, или напишите 'удалить', чтобы убрать текущую GIF.")

    bot.register_next_step_handler(message, process_gif_or_back)

def process_gif_or_back(message):
    if message.text == 'Назад 🔙':
        settings(message)  
        return

    process_gif(message)

def process_gif(message):
    user_id = message.from_user.id
    cursor.execute('SELECT is_premium FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    is_premium = result[0] if result else 0

    if not is_premium:
        bot.send_message(message.chat.id, "❌ Эта функция доступна только премиум-пользователям.")
        settings(message)
        return

    if message.text and message.text.lower() == 'удалить':
        cursor.execute('UPDATE users SET gif_id = NULL WHERE user_id = ?', (user_id,))
        conn.commit()
        bot.send_message(message.chat.id, "✅ GIF удалён из вашего профиля.")
        settings(message)
        return

    if message.animation:
        gif_id = message.animation.file_id

        cursor.execute('UPDATE users SET gif_id = ? WHERE user_id = ?', (gif_id, user_id))
        conn.commit()
        bot.send_message(message.chat.id, "🎉 GIF успешно добавлен в ваш профиль!")
        settings(message)
    else:
        bot.send_message(message.chat.id, "❌ Пожалуйста, отправьте GIF-анимацию или напишите 'удалить'.")
        bot.register_next_step_handler(message, process_gif_or_back)  

@bot.message_handler(func=lambda message: message.text == '🙈 Переключить видимость в топах')
def toggle_top_visibility(message):
    user_id = message.from_user.id
    conn = get_db_connection()  
    cursor = conn.cursor()  

    try:

        cursor.execute('SELECT hide_top FROM users WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()

        if result is None:
            bot.send_message(message.chat.id, "❌ Ошибка: пользователь не найден.")
            return

        current_status = result[0]
        new_status = 0 if current_status else 1  

        cursor.execute('UPDATE users SET hide_top = ? WHERE user_id = ?', (new_status, user_id))
        conn.commit()

        status_text = "✅ Ваш профиль теперь отображается в топе!" if new_status == 0 else "✅ Ваш профиль теперь скрыт из топов!"
        bot.send_message(message.chat.id, status_text)

    except sqlite3.Error as e:
        bot.send_message(message.chat.id, f"❌ Произошла ошибка при работе с базой данных: {e}")

    finally:
        cursor.close()  
        conn.close()  

@bot.message_handler(func=lambda message: message.text == '🔄 Переключить множитель клана')
def toggle_clan_multiplier(message):
    user_id = message.from_user.id
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT clan_id FROM clan_members WHERE user_id = ?', (user_id,))
    user_clan = cursor.fetchone()

    if not user_clan:
        bot.send_message(message.chat.id, "❌ Вы не состоите в клане, переключение невозможно.")
        cursor.close()
        return

    cursor.execute('SELECT use_clan_multiplier FROM users WHERE user_id = ?', (user_id,))
    current_setting = cursor.fetchone()[0]
    new_setting = 0 if current_setting else 1

    cursor.execute('UPDATE users SET use_clan_multiplier = ? WHERE user_id = ?', (new_setting, user_id))
    conn.commit()
    cursor.close()

    status = "включен" if new_setting else "выключен"
    bot.send_message(message.chat.id, f"🔄 Множитель клана теперь {status}!")

@bot.message_handler(commands=['id'])
def send_user_id(message):
    user_id = message.from_user.id
    bot.send_message(message.chat.id, f"🆔 Ваш Telegram ID: `{user_id}`", parse_mode="Markdown")

@bot.message_handler(commands=['say'])
def say_step_1(message):
    if message.from_user.id != ADMIN_ID:
        bot.send_message(message.chat.id, "❌ У вас нет прав для использования этой команды.")
        return

    bot.send_message(message.chat.id, "✍ Введите текст для рассылки:")
    bot.register_next_step_handler(message, say_step_2)

def say_step_2(message):
    if not message.text:
        bot.send_message(message.chat.id, "❌ Пожалуйста, введите текст!")
        return bot.register_next_step_handler(message, say_step_2)

    message_text = message.text
    bot.send_message(message.chat.id, "📷 Хотите добавить картинку? Отправьте изображение или напишите 'нет'.")
    bot.register_next_step_handler(message, say_step_3, message_text)

def say_step_3(message, text):
    photo = None
    if message.photo:
        photo = message.photo[-1].file_id  
    elif message.text and message.text.lower() == "нет":
        photo = None
    else:
        bot.send_message(message.chat.id, "❌ Пожалуйста, отправьте изображение или напишите 'нет'.")
        return bot.register_next_step_handler(message, say_step_3, text)

    send_broadcast(text, photo, message.chat.id)

def send_broadcast(text, photo, admin_chat_id):
    cursor.execute('SELECT user_id FROM users')
    users = [row[0] for row in cursor.fetchall()]

    sent_count = 0
    failed_users = []

    for user_id in users:
        try:
            if photo:
                bot.send_photo(user_id, photo, caption=text)
            else:
                bot.send_message(user_id, text)
            sent_count += 1
        except Exception as e:
            if "chat not found" in str(e):
                failed_users.append(user_id)
            print(f"Ошибка отправки пользователю {user_id}: {e}")

    if failed_users:
        cursor.executemany('DELETE FROM users WHERE user_id = ?', [(uid,) for uid in failed_users])
        conn.commit()
        bot.send_message(admin_chat_id, f"⚠️ {len(failed_users)} неактивных пользователей удалены из базы.")

    bot.send_message(admin_chat_id, f"✅ Сообщение отправлено {sent_count} пользователям.")

def is_clan_owner(user_id):
    cursor.execute('SELECT clan_id FROM clans WHERE owner_id = ?', (user_id,))
    result = cursor.fetchone()
    return result if result else None

def get_top_clans():
    cursor.execute('SELECT clan_name, balance FROM clans ORDER BY balance DESC LIMIT 10')
    return cursor.fetchall()

def get_user_clan(user_id):
    cursor.execute('SELECT clan_id FROM clan_members WHERE user_id = ?', (user_id,))
    return cursor.fetchone()

@bot.callback_query_handler(func=lambda call: call.data == 'delete_clan')
def delete_clan(call):
    user_id = call.from_user.id
    owner_clan = is_clan_owner(user_id)

    if not owner_clan:
        bot.send_message(call.message.chat.id, "❌ Вы не являетесь владельцем клана.")
        return

    cursor.execute('DELETE FROM clans WHERE owner_id = ?', (user_id,))
    cursor.execute('DELETE FROM clan_members WHERE clan_id = ?', (owner_clan[0],))
    conn.commit()
    bot.send_message(call.message.chat.id, "🏰 Клан успешно удален.")
    clans_menu(call.message)  

def get_clan_info(clan_id):
    cursor.execute('SELECT clan_name, balance, multiplier, owner_id FROM clans WHERE clan_id = ?', (clan_id,))
    result = cursor.fetchone()
    if result and len(result) == 3:  
        return (*result, None)
    return result

def get_clan_info(clan_id):
    cursor.execute('''
        SELECT clan_name, balance, multiplier, owner_id, clan_description, tax_rate 
        FROM clans 
        WHERE clan_id = ?
    ''', (clan_id,))
    return cursor.fetchone()

def create_clan(user_id, clan_name):
    cursor.execute('SELECT swag FROM users WHERE user_id = ?', (user_id,))
    swag = cursor.fetchone()
    if not swag or swag[0] < 10000000:
        return False, "❌ Недостаточно сваги для создания клана (10 000 000 сваги)", None

    cursor.execute('UPDATE users SET swag = swag - 10000000 WHERE user_id = ?', (user_id,))
    cursor.execute('INSERT INTO clans (clan_name, owner_id, balance, multiplier) VALUES (?, ?, 0, 1)', (clan_name, user_id))
    clan_id = cursor.lastrowid
    cursor.execute('INSERT INTO clan_members (user_id, clan_id) VALUES (?, ?)', (user_id, clan_id))
    conn.commit()
    return True, f"🎉 Клан '{clan_name}' успешно создан!", clan_id

def join_clan(user_id, clan_name):
    cursor.execute('SELECT clan_id FROM clans WHERE clan_name = ?', (clan_name,))
    clan = cursor.fetchone()
    if clan:
        cursor.execute('INSERT INTO clan_members (user_id, clan_id) VALUES (?, ?)', (user_id, clan[0]))
        conn.commit()
        return True
    return False

def get_top_clans():
    cursor.execute('SELECT clan_name, balance FROM clans ORDER BY balance DESC LIMIT 10')
    return cursor.fetchall()

def get_clan_member_count(clan_id):
    cursor.execute('SELECT COUNT(*) FROM clan_members WHERE clan_id = ?', (clan_id,))
    count = cursor.fetchone()
    return count[0] if count else 0

@bot.message_handler(func=lambda message: message.text == 'Кланы 🏰')
def clans_menu(message):
    user_id = message.from_user.id
    user_clan = get_user_clan(user_id)
    owner_clan = is_clan_owner(user_id)
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if user_clan:
        markup.add(types.KeyboardButton('💰 Баланс клана'))
        markup.add(types.KeyboardButton('📄 Страница клана'))
        markup.add(types.KeyboardButton('🚪 Выйти из клана'))

        if owner_clan:
            markup.add(types.KeyboardButton('✏️ Редактировать тему клана'))
            markup.add(types.KeyboardButton('🔄 Переименовать клан'))  
    else:

        markup.add(types.KeyboardButton('🤝 Вступить в клан'))
        markup.add(types.KeyboardButton('🏗️ Создать клан'))
    if owner_clan:
        markup.add(types.KeyboardButton('💸 Снять деньги с клана'))
        markup.add(types.KeyboardButton('🚷 Удалить клан'))
        markup.add(types.KeyboardButton('⚡ Улучшить множитель'))
        markup.add(types.KeyboardButton('🌾 Управление фермами'))
    markup.add(types.KeyboardButton('🏆 Топ кланов'))
    markup.add(types.KeyboardButton('ℹ️ Информация о кланах'))
    markup.add(types.KeyboardButton('🔙 Назад'))
    bot.send_message(message.chat.id, "🏰 **Меню кланов:**", reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == '🔧 Установить налог')
def set_clan_tax(message):
    user_id = message.from_user.id
    conn = sqlite3.connect("swag_boti.db")
    cursor = conn.cursor()

    cursor.execute('SELECT clan_id FROM clans WHERE owner_id = ?', (user_id,))
    clan = cursor.fetchone()
    if not clan:
        bot.send_message(message.chat.id, "❌ Вы не являетесь лидером клана.")
        return

    bot.send_message(message.chat.id, "Введите новый процент налога (от 0 до 90):")
    bot.register_next_step_handler(message, process_tax_input, clan[0])

def process_tax_input(message, clan_id):
    try:
        tax = int(message.text)
        if tax < 0 or tax > 90:
            raise ValueError("Налог должен быть от 0 до 90")

        conn = sqlite3.connect("swag_boti.db")
        cursor = conn.cursor()
        cursor.execute('UPDATE clans SET tax_rate = ? WHERE clan_id = ?', (tax, clan_id))
        conn.commit()
        bot.send_message(message.chat.id, f"✅ Новый налог для клана установлен: {tax}%")

    except ValueError:
        bot.send_message(message.chat.id, "❌ Введите целое число от 0 до 90.")

    except Exception as e:
        print(f"[Ошибка] Установка налога: {e}")
        bot.send_message(message.chat.id, "⚠️ Произошла ошибка при установке налога.")

@bot.message_handler(func=lambda message: message.text == '🔄 Переименовать клан')
def rename_clan(message):
    user_id = message.from_user.id
    owner_clan = is_clan_owner(user_id)
    if not owner_clan:
        bot.send_message(message.chat.id, "❌ Вы не являетесь лидером клана.")
        return
    bot.send_message(message.chat.id, "Введите новое название для вашего клана:")
    bot.register_next_step_handler(message, process_rename_clan, owner_clan[0])

def process_rename_clan(message, clan_id):
    new_clan_name = message.text.strip()
    if not new_clan_name:
        bot.send_message(message.chat.id, "❌ Название клана не может быть пустым. Пожалуйста, введите новое название:")
        bot.register_next_step_handler(message, process_rename_clan, clan_id)
        return

    cursor.execute('SELECT clan_id FROM clans WHERE clan_name = ?', (new_clan_name,))
    existing_clan = cursor.fetchone()
    if existing_clan:
        bot.send_message(message.chat.id, "❌ Клан с таким названием уже существует. Пожалуйста, выберите другое название:")
        bot.register_next_step_handler(message, process_rename_clan, clan_id)
        return

    cursor.execute('UPDATE clans SET clan_name = ? WHERE clan_id = ?', (new_clan_name, clan_id))
    conn.commit()
    bot.send_message(message.chat.id, f"🎉 Название вашего клана успешно изменено на '{new_clan_name}'.")
    clans_menu(message)  

@bot.message_handler(func=lambda message: message.text == '📄 Страница клана')
def clan_page(message):
    user_id = message.from_user.id
    user_clan = get_user_clan(user_id)

    if not user_clan:
        bot.send_message(message.chat.id, "❌ Вы не состоите в клане.", parse_mode=None)
        return

    clan_info = get_clan_info(user_clan[0])

    if not clan_info:
        bot.send_message(message.chat.id, "❌ Ошибка получения информации о клане.", parse_mode=None)
        return

    clan_name, balance, multiplier, owner_id, clan_description = clan_info
    member_count = get_clan_member_count(user_clan[0])
    owner_name = get_owner_name(owner_id) if owner_id else "Неизвестно"
    balance_formatted = f"{balance:,}".replace(",", ".")

    clan_page_message = (
        f"📄 **Страница клана:** {clan_name}\n\n"
        f"👑 **Владелец:** {owner_name}\n"
        f"👥 **Участники:** {member_count}/50\n"
        f"💰 **Баланс:** {balance_formatted} сваги\n"
        f"⚡ **Множитель:** x{multiplier}\n\n"
    )

    if clan_description:
        clan_page_message += f"📝 **Тема клана:**\n{clan_description}\n"
    else:
        clan_page_message += "📝 **Тема клана:**\nНе задана.\n"

    bot.send_message(message.chat.id, clan_page_message, parse_mode=None, reply_markup=message.reply_markup)

def time_until_next_income():
    now = datetime.now()
    next_hour = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
    delta = next_hour - now
    minutes_left = int(delta.total_seconds() / 60)
    return minutes_left

def generate_clan_page_message(clan_id):
    clan_info = get_clan_info(clan_id)
    if not clan_info:
        return "❌ Ошибка получения информации о клане."

    clan_name, balance, multiplier, owner_id, clan_description = clan_info
    member_count = get_clan_member_count(clan_id)
    owner_name = get_owner_name(owner_id) if owner_id else "Неизвестно"
    balance_formatted = f"{balance:,}".replace(",", ".")

    clan_page_message = (
        f"📄 **Страница клана:** {clan_name}\n\n"
        f"👑 **Владелец:** {owner_name}\n"
        f"👥 **Участники:** {member_count}/50\n"
        f"💰 **Баланс:** {balance_formatted} сваги\n"
        f"⚡ **Множитель:** x{multiplier}\n\n"
    )

    if clan_description:
        clan_page_message += f"📝 **Тема клана:**\n{clan_description}\n"
    else:
        clan_page_message += "📝 **Тема клана:**\nНе задана.\n"

    return clan_page_message

def process_clan_topic(message, clan_id):
    """
    Обрабатывает ввод нового описания клана и обновляет его в базе данных.

    :param message: Объект сообщения Telegram, содержащий текст нового описания.
    :param clan_id: ID клана, для которого обновляется описание.
    """
    new_description = message.text.strip()

    if len(new_description) > 500:
        bot.send_message(message.chat.id, "❌ Описание клана не должно превышать 500 символов. Пожалуйста, сократите текст и попробуйте снова.")

        bot.send_message(message.chat.id, "✍️ Пожалуйста, введите новое описание для вашего клана (до 500 символов):")
        bot.register_next_step_handler(message, process_clan_topic, clan_id)
        return

    if not new_description:
        bot.send_message(message.chat.id, "❌ Описание клана не может быть пустым. Пожалуйста, введите текст и попробуйте снова.")

        bot.send_message(message.chat.id, "✍️ Пожалуйста, введите новое описание для вашего клана (до 500 символов):")
        bot.register_next_step_handler(message, process_clan_topic, clan_id)
        return

    try:

        cursor.execute('UPDATE clans SET clan_description = ? WHERE clan_id = ?', (new_description, clan_id))
        conn.commit()

        bot.send_message(message.chat.id, "✅ Описание клана успешно обновлено.")

        clan_page_message = generate_clan_page_message(clan_id)
        bot.send_message(message.chat.id, clan_page_message, parse_mode="Markdown")

    except sqlite3.Error as e:

        bot.send_message(message.chat.id, f"❌ Произошла ошибка при обновлении описания клана: {e}")

        print(f"Ошибка при обновлении описания клана: {e}")

@bot.message_handler(func=lambda message: message.text == '✏️ Редактировать тему клана')
def edit_clan_topic(message):
    user_id = message.from_user.id
    owner_clan = is_clan_owner(user_id)

    if not owner_clan:
        bot.send_message(message.chat.id, "❌ Вы не являетесь владельцем клана и не можете редактировать тему.")
        return

    clan_id = owner_clan[0]

    bot.send_message(message.chat.id, "✍️ Введите новое описание для вашего клана (до 500 символов):")
    bot.register_next_step_handler(message, process_clan_topic, clan_id)

def is_clan_owner(user_id):
    cursor.execute('SELECT clan_id, clan_name, balance, owner_id FROM clans WHERE owner_id = ?', (user_id,))
    result = cursor.fetchone()
    return result  

def get_clan_info(clan_id):
    cursor.execute('SELECT clan_name, balance, multiplier, owner_id, clan_description FROM clans WHERE clan_id = ?', (clan_id,))
    return cursor.fetchone()  

def process_farm_connection(message):
    user_id = message.from_user.id
    if message.text == 'Назад 🔙':
        return clans_menu(message)  

    cursor.execute('SELECT clan_id FROM clans WHERE owner_id = ?', (user_id,))
    clan = cursor.fetchone()
    if not clan:
        bot.send_message(message.chat.id, "❌ Только лидер клана может управлять фермами.")
        return

    clan_id = clan[0]

    selected_farm = message.text.split(" - ")[0]  
    cursor.execute('SELECT farm_type, clan_connected FROM farms WHERE user_id = ? AND farm_type = ?', (user_id, selected_farm))
    farm = cursor.fetchone()

    if not farm:
        bot.send_message(message.chat.id, "❌ Ферма не найдена.")
        return

    farm_type, clan_connected = farm

    if clan_connected:

        cursor.execute('UPDATE farms SET clan_connected = 0 WHERE user_id = ? AND farm_type = ?', (user_id, farm_type))
        conn.commit()
        bot.send_message(message.chat.id, f"✅ Ферма {farm_type} отвязана от клана.")
    else:

        cursor.execute('UPDATE farms SET clan_connected = 1 WHERE user_id = ? AND farm_type = ?', (user_id, farm_type))
        conn.commit()
        bot.send_message(message.chat.id, f"✅ Ферма {farm_type} привязана к клану.")

    farm_connection_menu(message)

@bot.message_handler(func=lambda message: message.text == '🌾 Управление фермами')
def farm_connection_menu(message):
    user_id = message.from_user.id

    if not is_clan_owner(user_id):
        bot.send_message(message.chat.id, "❌ Только лидер клана может управлять фермами.")
        return

    cursor.execute('SELECT farm_type, clan_connected, SUM(quantity) FROM farms WHERE user_id = ? GROUP BY farm_type, clan_connected', (user_id,))
    grouped_farms = cursor.fetchall()

    connected_farms = [farm for farm in grouped_farms if farm[1] == 1]
    total_connected = sum(farm[2] for farm in connected_farms)
    total_farms = sum(farm[2] for farm in grouped_farms)

    minutes_left = time_until_next_income()

    message_text = "🌾 Управление фермами клана\n\n"
    message_text += f"Всего ферм: {total_farms}\n"
    message_text += f"Подключено: {total_connected}\n\n"

    if connected_farms:
        message_text += "Подключённые фермы:\n"
        for farm_type, _, quantity in connected_farms:
            message_text += f"- {farm_type} ×{quantity}\n"
        message_text += f"\n⏳ До следующего дохода: {minutes_left} минут\n"
    else:
        message_text += "Нет подключённых ферм.\n"

    message_text += "\nВыберите действие:"

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)

    for farm_type, clan_connected, quantity in grouped_farms:
        status = "✅" if clan_connected else "❌"
        btn_text = f"{status} {farm_type}" if quantity == 1 else f"{status} {farm_type} ×{quantity}"
        markup.add(types.KeyboardButton(btn_text))

    markup.row(types.KeyboardButton('🔗 Привязать все фермы'))
    markup.row(types.KeyboardButton('🔌 Отвязать все фермы'))
    markup.row(types.KeyboardButton('Назад 🔙'))

    bot.send_message(message.chat.id, message_text, reply_markup=markup)
    bot.register_next_step_handler(message, process_farm_connection)

def process_farm_connection(message):
    user_id = message.from_user.id

    if message.text == 'Назад 🔙':
        return main_menu(message)

    if message.text == '🔗 Привязать все фермы':
        cursor.execute('UPDATE farms SET clan_connected = 1 WHERE user_id = ?', (user_id,))
        conn.commit()
        bot.send_message(message.chat.id, "✅ Все фермы успешно привязаны к клану!")
        return farm_connection_menu(message)

    elif message.text == '🔌 Отвязать все фермы':
        cursor.execute('UPDATE farms SET clan_connected = 0 WHERE user_id = ?', (user_id,))
        conn.commit()
        bot.send_message(message.chat.id, "✅ Все фермы успешно отвязаны от клана!")
        return farm_connection_menu(message)

    try:

        btn_text = message.text
        status_emoji = btn_text[0]  
        farm_type = btn_text[2:].split(' ×')[0]  

        new_status = 1 if status_emoji == "❌" else 0

        cursor.execute('UPDATE farms SET clan_connected = ? WHERE user_id = ? AND farm_type = ?', 
                      (new_status, user_id, farm_type))
        conn.commit()

        action = "привязаны" if new_status == 1 else "отвязаны"
        bot.send_message(message.chat.id, f"✅ Все фермы {farm_type} успешно {action}!")

    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Ошибка: {str(e)}")

    farm_connection_menu(message)

@bot.message_handler(func=lambda message: message.text == '⚡ Улучшить множитель')
def upgrade_clan_multiplier(message):
    user_id = message.from_user.id
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT clan_id FROM clans WHERE owner_id = ?', (user_id,))
    user_clan = cursor.fetchone()

    if not user_clan:
        bot.send_message(message.chat.id, "❌ Вы не являетесь лидером клана.")
        return

    clan_id = user_clan[0]

    cursor.execute('SELECT multiplier, balance FROM clans WHERE clan_id = ?', (clan_id,))
    clan_data = cursor.fetchone()

    if not clan_data:
        bot.send_message(message.chat.id, "❌ Ошибка получения данных клана.")
        return

    current_multiplier, balance = clan_data

    next_multiplier = None
    for multiplier in sorted(MULTIPLIER_COSTS.keys()):
        if multiplier > current_multiplier:
            next_multiplier = multiplier
            break

    if next_multiplier is None:
        bot.send_message(message.chat.id, "🚀 Ваш множитель уже максимальный (x100)!")
        return

    cost = MULTIPLIER_COSTS[next_multiplier]

    if balance < cost:
        bot.send_message(message.chat.id, f"❌ Недостаточно средств! Нужно {cost:,} сваги.".replace(",", "."))
        return

    cursor.execute('UPDATE clans SET balance = balance - ?, multiplier = ? WHERE clan_id = ?', 
                   (cost, next_multiplier, clan_id))
    conn.commit()

    bot.send_message(message.chat.id, f"🎉 Клан улучшил общий множитель до x{next_multiplier} за {cost:,} сваги!".replace(",", "."))

@bot.message_handler(func=lambda message: message.text == '💸 Снять деньги с клана')
def ask_withdraw_amount(message):
    user_id = message.from_user.id
    conn = sqlite3.connect("swag_boti.db")
    cursor = conn.cursor()

    try:
        cursor.execute('SELECT clan_id FROM clans WHERE owner_id = ?', (user_id,))
        user_clan = cursor.fetchone()

        if not user_clan:
            bot.send_message(message.chat.id, "❌ Вы не являетесь лидером клана.")
            return
        else:
            bot.send_message(message.chat.id, "Введите сумму, которую хотите снять с баланса клана:")
            bot.register_next_step_handler(message, withdraw_from_clan)

    except sqlite3.OperationalError as e:
        print(f"[Ошибка базы данных] {e}")
    finally:
        cursor.close()
        conn.close()

def withdraw_from_clan(message):
    user_id = message.from_user.id
    conn = sqlite3.connect("swag_boti.db")
    cursor = conn.cursor()

    try:
        cursor.execute('SELECT clan_id FROM clans WHERE owner_id = ?', (user_id,))
        user_clan = cursor.fetchone()

        if not user_clan:
            bot.send_message(message.chat.id, "❌ Вы не являетесь лидером клана.")
            return

        clan_id = user_clan[0]

        if not message.text.isdigit():
            bot.send_message(message.chat.id, "❌ Укажите корректную сумму для снятия (только цифры).")
            return  

        amount = int(message.text)

        cursor.execute('SELECT balance FROM clans WHERE clan_id = ?', (clan_id,))
        clan_balance = cursor.fetchone()[0]

        if amount <= 0:
            bot.send_message(message.chat.id, "❌ Сумма должна быть больше 0.")
            return  

        if amount > clan_balance:
            bot.send_message(message.chat.id, f"❌ Недостаточно средств в казне. Доступно: {clan_balance:,} сваги.".replace(",", "."))
            return  

        cursor.execute('UPDATE clans SET balance = balance - ? WHERE clan_id = ?', (amount, clan_id))
        cursor.execute('UPDATE users SET swag = swag + ? WHERE user_id = ?', (amount, user_id))
        conn.commit()

        bot.send_message(message.chat.id, f"✅ Вы сняли {amount:,} сваги с баланса клана!".replace(",", "."))

    except sqlite3.OperationalError as e:
        print(f"[Ошибка базы данных] {e}")
    finally:
        cursor.close()
        conn.close()

def get_owner_name(owner_id):
    cursor.execute('SELECT username FROM users WHERE user_id = ?', (owner_id,))
    result = cursor.fetchone()
    return result[0] if result else "Неизвестно"

def auto_buy_clan_multiplier():
    cursor.execute('SELECT clan_id, multiplier, balance FROM clans')
    clans = cursor.fetchall()

    for clan_id, current_multiplier, balance in clans:
        next_multiplier = current_multiplier + 1

        if next_multiplier not in MULTIPLIER_COSTS:
            continue  

        cost = MULTIPLIER_COSTS[next_multiplier] * 3  

        if balance >= cost:

            cursor.execute('UPDATE clans SET balance = balance - ?, multiplier = ? WHERE clan_id = ?', 
                           (cost, next_multiplier, clan_id))
            conn.commit()

            cursor.execute('SELECT user_id FROM clan_members WHERE clan_id = ?', (clan_id,))
            members = [row[0] for row in cursor.fetchall()]

            for user_id in members:
                bot.send_message(user_id, f"⚡ Ваш клан прокачал множитель до x{next_multiplier}!")

@bot.message_handler(func=lambda message: message.text == '📊 Статистика клана')
def clan_statistics(message):
    user_id = message.from_user.id
    user_clan = get_user_clan(user_id)

    if not user_clan:
        bot.send_message(message.chat.id, "❌ Вы не состоите в клане.")
        return

    clan_info = get_clan_info(user_clan[0])

    if not clan_info:
        bot.send_message(message.chat.id, "❌ Ошибка получения информации о клане.")
        return

    clan_name, balance, multiplier, owner_id = clan_info
    member_count = get_clan_member_count(user_clan[0])

    owner_name = get_owner_name(owner_id) if owner_id else "Неизвестно"

    balance_formatted = f"{balance:,}".replace(",", ".")

    bot.send_message(
        message.chat.id,
        f"🏰 **Клан:** {clan_name}\n\n"
        f"💰 **Баланс:** {balance_formatted} сваги\n"
        f"⚡ **Множитель:** x{multiplier}\n"
        f"👥 **Участники:** {member_count}/50\n"
        f"👑 **Владелец:** {owner_name}",
        parse_mode="Markdown"
    )

@bot.message_handler(func=lambda message: message.text == '🚪 Выйти из клана')
def confirm_leave_clan(message):
    user_id = message.from_user.id
    user_clan = get_user_clan(user_id)

    if not user_clan:
        bot.send_message(message.chat.id, "❌ Вы не состоите в клане.")
        return

    bot.send_message(message.chat.id, "⚠️ Подтвердите выход из клана. Напишите 'Уйти' для подтверждения или 'Отмена' для отмены.")
    bot.register_next_step_handler(message, process_leave_clan, user_clan[0])

def process_leave_clan(message, clan_id):
    user_id = message.from_user.id
    if message.text.lower() == 'уйти':
        cursor.execute('DELETE FROM clan_members WHERE user_id = ?', (user_id,))
        conn.commit()
        bot.send_message(message.chat.id, "🚪 Вы вышли из клана.")
        clans_menu(message)  
    else:
        bot.send_message(message.chat.id, "❌ Выход отменен.")

@bot.message_handler(func=lambda message: message.text == '🏗️ Создать клан')
def ask_clan_name(message):
    bot.send_message(message.chat.id, "🏰 Введите название для вашего клана:")
    bot.register_next_step_handler(message, create_clan_handler)

def create_clan_handler(message):
    user_id = message.from_user.id
    clan_name = message.text.strip()
    success, response, clan_id = create_clan(user_id, clan_name)
    bot.send_message(message.chat.id, response)
    if success:
        clans_menu(message)  

@bot.callback_query_handler(func=lambda call: call.data == 'delete_clan')
def delete_clan_callback(call):
    user_id = call.from_user.id
    conn = get_db_connection()
    cursor = conn.cursor()

    try:

        cursor.execute('SELECT clan_id, clan_name, balance FROM clans WHERE owner_id = ?', (user_id,))
        clan = cursor.fetchone()
        if not clan:
            bot.send_message(call.message.chat.id, "❌ Вы не являетесь владельцем клана.")
            cursor.close()
            conn.close()
            return

        clan_id, clan_name, clan_balance = clan

        cursor.execute('SELECT user_id FROM clan_members WHERE clan_id = ?', (clan_id,))
        members = cursor.fetchall()
        member_ids = [member[0] for member in members]  

        if user_id not in member_ids:
            member_ids.append(user_id)

        total_members = len(member_ids)

        if total_members > 0 and clan_balance > 0:

            share_per_member = clan_balance // total_members
            remainder = clan_balance % total_members  

            for member_id in member_ids:
                cursor.execute('UPDATE users SET swag = swag + ? WHERE user_id = ?', (share_per_member, member_id))

            if remainder > 0:
                cursor.execute('UPDATE users SET swag = swag + ? WHERE user_id = ?', (remainder, user_id))

            for member_id in member_ids:
                try:
                    bot.send_message(
                        member_id,
                        f"🏰 Клан '{clan_name}' был удалён. Казна клана ({clan_balance:,} сваги) разделена между участниками. "
                        f"Вы получили {share_per_member:,} сваги.".replace(",", ".")
                    )
                except Exception as e:
                    print(f"Ошибка при отправке сообщения участнику {member_id}: {e}")

        cursor.execute('UPDATE farms SET clan_connected = 0 WHERE user_id = ?', (user_id,))

        cursor.execute('DELETE FROM clan_members WHERE clan_id = ?', (clan_id,))

        cursor.execute('DELETE FROM clans WHERE clan_id = ?', (clan_id,))

        conn.commit()

        bot.send_message(
            call.message.chat.id,
            f"✅ Клан '{clan_name}' успешно удалён. Все ваши фермы отвязаны от клана. "
            f"Казна ({clan_balance:,} сваги) была разделена между {total_members} участниками.".replace(",", ".")
        )
        clans_menu(call.message)

    except sqlite3.Error as e:
        bot.send_message(call.message.chat.id, f"❌ Ошибка при удалении клана: {e}")
    except Exception as e:
        bot.send_message(call.message.chat.id, f"❌ Произошла ошибка: {e}")
    finally:
        cursor.close()
        conn.close()

    delete_message(call)

def get_all_clans():
    cursor.execute('SELECT clan_id, clan_name FROM clans')
    return cursor.fetchall()

@bot.message_handler(func=lambda message: message.text.startswith("🏰 "))
def join_clan_handler(message):
    user_id = message.from_user.id
    clan_name = message.text[2:].split(" (")[0]  

    cursor.execute('SELECT clan_id FROM clans WHERE clan_name = ?', (clan_name,))
    clan = cursor.fetchone()
    if not clan:
        bot.send_message(message.chat.id, "❌ Клан не найден.")
        return

    clan_id = clan[0]
    member_count = get_clan_member_count(clan_id)

    if member_count >= 50:
        bot.send_message(message.chat.id, "❌ В этом клане уже 50 участников. Места нет.")
        return

    cursor.execute('INSERT INTO clan_members (user_id, clan_id) VALUES (?, ?)', (user_id, clan_id))
    conn.commit()
    bot.send_message(message.chat.id, f"🎉 Вы успешно вступили в клан '{clan_name}'!")

@bot.message_handler(func=lambda message: message.text == '🤝 Вступить в клан')
def show_clans_to_join(message):
    clans = get_all_clans()
    if not clans:
        bot.send_message(message.chat.id, "❌ Нет доступных кланов.")
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for clan_id, clan_name in clans:
        member_count = get_clan_member_count(clan_id)
        if member_count < 10:
            markup.add(types.KeyboardButton(f"🏰 {clan_name} ({member_count}/10)"))
    markup.add(types.KeyboardButton("🔙 Назад"))

    bot.send_message(message.chat.id, "🏰 Выберите клан для вступления:", reply_markup=markup)
    bot.register_next_step_handler(message, join_clan_handler)

@bot.message_handler(func=lambda message: message.text.startswith("🏰 "))
def join_clan_handler(message):
    user_id = message.from_user.id
    clan_name = message.text[2:].split(" (")[0]  

    cursor.execute('SELECT clan_id FROM clans WHERE clan_name = ?', (clan_name,))
    clan = cursor.fetchone()
    if not clan:
        bot.send_message(message.chat.id, "❌ Клан не найден.")
        return

    clan_id = clan[0]
    member_count = get_clan_member_count(clan_id)

    if member_count >= 10:
        bot.send_message(message.chat.id, "❌ В этом клане уже 10 участников. Места нет.")
        return

    cursor.execute('INSERT INTO clan_members (user_id, clan_id) VALUES (?, ?)', (user_id, clan_id))
    conn.commit()
    bot.send_message(message.chat.id, f"🎉 Вы успешно вступили в клан '{clan_name}'!")
    clans_menu(message)  

@bot.message_handler(func=lambda message: message.text == '🏆 Топ кланов')
def show_top_clans(message):
    top_clans = get_top_clans()
    if top_clans:
        leaderboard = "🏆 **Топ 10 кланов по балансу:**\n\n"
        for i, (clan_name, balance) in enumerate(top_clans, 1):
            leaderboard += f"{i}. {clan_name} - 💰 {balance:,} сваги\n\n".replace(",", ".")
        bot.send_message(message.chat.id, leaderboard, parse_mode="Markdown")
    else:
        bot.send_message(message.chat.id, "❌ Пока нет кланов в топе.")

def get_clan_balance(clan_id):
    cursor.execute('SELECT balance FROM clans WHERE clan_id = ?', (clan_id,))
    balance = cursor.fetchone()
    return balance[0] if balance else 0

@bot.message_handler(func=lambda message: message.text == '💰 Баланс клана')
def clan_balance(message):
    user_id = message.from_user.id
    user_clan = get_user_clan(user_id)

    if not user_clan:
        bot.send_message(message.chat.id, "❌ Вы не состоите в клане.")
        return

    balance = get_clan_balance(user_clan[0])
    balance_formatted = f"{balance:,}".replace(",", ".")  

    bot.send_message(message.chat.id, f"💰 Баланс вашего клана: {balance_formatted} сваги")

@bot.message_handler(func=lambda message: message.text == '🔙 Назад')
def back_to_main_menu(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    buttons = [
        'Тапать 🤑', 'Баланс 💰', 'Профиль 👤', 'Топ по сваги 🏆',
        'Магазин 🛒', 'Игры 🎲', 'Лиги 🏅', 'Фермы 🏡',
        'Кланы 🏰', 'Наш телеграм 📢', 'Настройки ⚙️', 'Информация ℹ️',
    ]

    for i in range(0, len(buttons) - 1, 2):  
        markup.add(types.KeyboardButton(buttons[i]), types.KeyboardButton(buttons[i+1]))

    if len(buttons) % 2 != 0:
        markup.add(types.KeyboardButton(buttons[-1]))  

    bot.send_message(message.chat.id, "🏠 Вы вернулись в главное меню.", reply_markup=markup)

def get_user_profile(user_id):
    cursor.execute('SELECT username, swag, total_swag, rank, league, hide_top, gif_id, is_premium, selected_badge FROM users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    if result:
        username, swag, total_swag, rank, league, hide_top, gif_id, is_premium, selected_badge = result
        if hide_top:
            return "❌ Этот пользователь скрыл свой профиль.", None  

        display_name = username if username else "None"  

        if selected_badge:
            display_name = f"{display_name} {selected_badge}"

        display_name = display_name.replace("*", "\\*").replace("_", "\\_").replace("[", "\\[").replace("]", "\\]")
        rank = rank.replace("*", "\\*").replace("_", "\\_").replace("[", "\\[").replace("]", "\\]")
        league = league.replace("*", "\\*").replace("_", "\\_").replace("[", "\\[").replace("]", "\\]")

        profile_text = (
            "📌 **Профиль игрока**:\n\n"
            f"👤 **Имя:** {display_name}\n"
            f"💰 **Баланс:** {swag:,} сваги\n"
            f"🏆 **Натапано всего:** {total_swag:,} сваги\n"
            f"🎖 **Ранг:** {rank}\n"
            f"🏅 **Лига:** {league}"
        )

        if user_id == ADMIN_ID:
            profile_text += "\n\n**⚠️ Администратор бота** — Этот пользователь является администратором бота."

        if is_premium:
            profile_text += "\n**💎 Премиум-пользователь** — Этот пользователь имеет премиум-статус."

        cursor.execute('SELECT badge FROM user_badges WHERE user_id = ?', (user_id,))
        badges = [row[0] for row in cursor.fetchall()]
        if badges:
            profile_text += "\n\n**Достижения:**\n"
            for badge in badges:
                if badge == "🌐":
                    profile_text += "🌐 — Повелитель сваги.\n"
                elif badge == "⭕":
                    profile_text += "⭕ — BETA TESTER.\n"
                elif badge == "🔰":
                    profile_text += "🔰 — Кланы - обьединяйтесь!\n"
                elif badge == "⚜":
                    profile_text += "⚜ — Народный деятель сваги.\n"

        return profile_text, gif_id
    return "❌ Профиль не найден.", None

@bot.message_handler(commands=['znak'])
def manage_badges(message):
    user_id = message.from_user.id
    if user_id != ADMIN_ID:
        bot.send_message(message.chat.id, "❌ У вас нет прав для использования этой команды.")
        return

    try:
        parts = message.text.split()
        if len(parts) < 4:
            bot.send_message(message.chat.id, "❌ Неверный формат команды. Используйте:\n/znak выдать <user_id> <знак>\n/znak забрать <user_id> <знак>")
            return

        action = parts[1].lower()
        target_user_id = int(parts[2])
        badge = parts[3]

        valid_badges = {"🌐", "⭕", "🔰", "⚜"}
        if badge not in valid_badges:
            bot.send_message(message.chat.id, f"❌ Недопустимый знак. Допустимые знаки: {', '.join(valid_badges)}")
            return

        if action == "выдать":
            cursor.execute('INSERT INTO user_badges (user_id, badge) VALUES (?, ?)', (target_user_id, badge))
            conn.commit()
            bot.send_message(message.chat.id, f"✅ Знак {badge} успешно выдан пользователю {target_user_id}.")
        elif action == "забрать":
            cursor.execute('DELETE FROM user_badges WHERE user_id = ? AND badge = ?', (target_user_id, badge))
            conn.commit()
            bot.send_message(message.chat.id, f"✅ Знак {badge} успешно забран у пользователя {target_user_id}.")
        else:
            bot.send_message(message.chat.id, "❌ Неверное действие. Используйте 'выдать' или 'забрать'.")
    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Ошибка: {e}")

@bot.callback_query_handler(func=lambda call: call.data.startswith("profile_"))
def show_profile(call):
    user_id = int(call.data.split("_")[1])  
    profile_text, gif_id = get_user_profile(user_id)  

    try:
        bot.delete_message(call.message.chat.id, call.message.message_id)
    except Exception as e:
        print(f"Ошибка при удалении топа в show_profile: {e}")

    if "❌ Этот пользователь скрыл свой профиль." in profile_text:
        bot.send_message(call.message.chat.id, profile_text)
        return

    if gif_id:
        try:
            bot.send_animation(call.message.chat.id, gif_id)
        except Exception as e:
            print(f"Ошибка при отправке GIF с file_id {gif_id}: {e}")
            bot.send_message(call.message.chat.id, "⚠️ Не удалось загрузить GIF.")

    try:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🔙 Вернуться в топ", callback_data="back_to_top"))
        bot.send_message(call.message.chat.id, profile_text, parse_mode="Markdown", reply_markup=markup)
    except Exception as e:
        print(f"Ошибка при отправке текста профиля: {e}")
        return

@bot.callback_query_handler(func=lambda call: call.data == "back_to_top")
def back_to_top(call):
    try:

        try:

            chat_id = call.message.chat.id
            last_message_id = call.message.message_id
            second_last_message_id = last_message_id - 1

            bot.delete_message(chat_id, last_message_id)
            bot.delete_message(chat_id, second_last_message_id)
        except Exception as e:
            print(f"Ошибка при удалении сообщений: {e}")

        top_message, markup = get_top_users_by_swag()
        bot.send_message(call.message.chat.id, top_message, parse_mode="Markdown", reply_markup=markup)

        bot.answer_callback_query(call.id)

    except Exception as e:
        print(f"Ошибка в back_to_top: {e}")
        bot.answer_callback_query(call.id, "⚠️ Произошла ошибка при возврате к топу.")

@bot.callback_query_handler(func=lambda call: call.data == "back_to_top")
def back_to_top(call):
    top_message, markup = get_top_users_by_swag()
    bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.message_id, text=top_message, parse_mode="Markdown", reply_markup=markup)

def update_premium_status(user_id, is_premium, days=30):
    """
    Обновляет премиум-статус пользователя и автоматически добавляет/удаляет знак 💎.
    Если is_premium = True, устанавливает срок подписки на указанное количество дней.
    """
    if is_premium:

        cursor.execute(
            'UPDATE users SET is_premium = 1, selected_badge = ?, premium_end_date = ? WHERE user_id = ?',
            ("💎", (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S'), user_id)
        )
    else:

        cursor.execute(
            'UPDATE users SET is_premium = 0, selected_badge = NULL, gif_id = NULL, premium_end_date = NULL WHERE user_id = ?',
            (user_id,)
        )
    conn.commit()

def update_premium_status(user_id, is_premium, days=30):
    if is_premium:

        cursor.execute('UPDATE users SET is_premium = 1, selected_badge = ?, premium_end_date = ? WHERE user_id = ?', 
                       ("💎", (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S'), user_id))
    else:

        cursor.execute('UPDATE users SET is_premium = 0, selected_badge = NULL, gif_id = NULL, premium_end_date = NULL WHERE user_id = ?', 
                       (user_id,))
    conn.commit()

def start_duel_search(user_id, bet):
    cursor.execute('SELECT swag FROM users WHERE user_id = ?', (user_id,))
    swag = cursor.fetchone()[0]

    if swag < bet:
        return False, "❌ У вас недостаточно сваги для этой ставки."

    cursor.execute('SELECT user_id FROM duel_searches WHERE user_id = ?', (user_id,))
    if cursor.fetchone():
        return False, "❌ Вы уже ищете дуэль. Дождитесь соперника или отмените поиск."

    cursor.execute('UPDATE users SET swag = swag - ? WHERE user_id = ?', (bet, user_id))

    cursor.execute('INSERT INTO duel_searches (user_id, bet, search_start_time) VALUES (?, ?, ?)',
                   (user_id, bet, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()

    return True, "🔍 Поиск дуэли начат! Вы добавлены в список ожидающих."

@bot.message_handler(func=lambda message: message.text == '🔍 Начать поиск дуэли')
def start_duel_search_handler(message):
    bot.send_message(message.chat.id, "💰 Введите сумму ставки для дуэли (минимум 100 сваги):")
    bot.register_next_step_handler(message, process_duel_bet)

def process_duel_bet(message):
    user_id = message.from_user.id
    try:
        bet = int(message.text)
        if bet < 100:
            bot.send_message(message.chat.id, "❌ Ставка должна быть минимум 100 сваги.")
            return duels_menu(message)  

        success, response = start_duel_search(user_id, bet)
        bot.send_message(message.chat.id, response)

    except ValueError:
        bot.send_message(message.chat.id, "❌ Введите корректное число.")

    duels_menu(message)

@bot.message_handler(func=lambda message: message.text == 'Игры 🎲')
def games_menu(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton('Казино 🎰'))
    markup.add(types.KeyboardButton('Дуэли ⚔️'))
    markup.add(types.KeyboardButton('Криптовалюта 💸'))
    markup.add(types.KeyboardButton('Назад 🔙'))
    bot.send_message(message.chat.id, "🎲 **Меню игр:**\nВыберите режим:", reply_markup=markup, parse_mode="Markdown")

def get_duel_searches():
    cursor.execute('SELECT user_id, bet FROM duel_searches')
    searches = cursor.fetchall()
    print("Результат get_duel_searches:", searches)  
    return searches

def start_duel(duel_id, player1_id, player2_id, bet):
    total_pot = bet * 2

    cursor.execute('SELECT username FROM users WHERE user_id = ?', (player1_id,))
    player1_username = cursor.fetchone()[0]
    player1_name = f"@{player1_username}" if player1_username else "Безымянный"

    cursor.execute('SELECT username FROM users WHERE user_id = ?', (player2_id,))
    player2_username = cursor.fetchone()[0]
    player2_name = f"@{player2_username}" if player2_username else "Безымянный"

    try:
        for player_id in [player1_id, player2_id]:
            bot.send_message(player_id, f"⚔️ Дуэль с {player2_name if player_id == player1_id else player1_name} началась!\n💠 Считаем косинусы...")
        time.sleep(2)
        for player_id in [player1_id, player2_id]:
            bot.send_message(player_id, "🐱‍👤 Входим в материю...")
        time.sleep(2)
        for player_id in [player1_id, player2_id]:
            bot.send_message(player_id, "💢 Проверка на честность дуэли... по системе BM3 🕳")
        time.sleep(2)

        winner_id = random.choice([player1_id, player2_id])
        loser_id = player2_id if winner_id == player1_id else player1_id
        winner_name = player1_name if winner_id == player1_id else player2_name
        loser_name = player2_name if winner_id == player1_id else player1_name

        cursor.execute('UPDATE active_duels SET status = "completed", winner_id = ? WHERE duel_id = ?',
                       (winner_id, duel_id))
        cursor.execute('UPDATE users SET swag = swag + ?, duel_wins = duel_wins + 1 WHERE user_id = ?', 
                       (total_pot, winner_id))
        conn.commit()

        bot.send_message(winner_id, f"🏆 Вы победили в дуэли против {loser_name}! Ваш выигрыш: {total_pot:,} сваги.".replace(",", "."))
        bot.send_message(loser_id, f"😢 Вы проиграли дуэль против {winner_name}. Попробуйте снова!")

        for player_id in [player1_id, player2_id]:
            duels_menu_by_id(player_id)

    except Exception as e:
        print(f"Ошибка в процессе дуэли: {e}")
        winner_id = random.choice([player1_id, player2_id])
        cursor.execute('UPDATE active_duels SET status = "completed", winner_id = ? WHERE duel_id = ?',
                       (winner_id, duel_id))
        cursor.execute('UPDATE users SET swag = swag + ?, duel_wins = duel_wins + 1 WHERE user_id = ?', 
                       (total_pot, winner_id))
        conn.commit()
        try:
            bot.send_message(player1_id, "⚠️ Произошла ошибка во время дуэли, но результат определён.")
            bot.send_message(player2_id, "⚠️ Произошла ошибка во время дуэли, но результат определён.")
            for player_id in [player1_id, player2_id]:
                duels_menu_by_id(player_id)
        except:
            pass

def duels_menu_by_id(user_id):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)

    cursor.execute('SELECT bet FROM duel_searches WHERE user_id = ?', (user_id,))
    in_search = cursor.fetchone()

    if in_search:
        markup.add(types.KeyboardButton('❌ Отменить поиск'))
    else:
        markup.add(types.KeyboardButton('🔍 Начать поиск дуэли'))

    markup.add(types.KeyboardButton('👥 Кто ищет дуэль'))
    markup.add(types.KeyboardButton('ℹ️ О дуэлях'))
    markup.add(types.KeyboardButton('Назад 🔙'))

    try:
        bot.send_message(user_id, "⚔️ **Меню дуэлей:**", reply_markup=markup, parse_mode="Markdown")
    except Exception as e:
        print(f"Ошибка при отправке меню дуэлей пользователю {user_id}: {e}")

@bot.message_handler(func=lambda message: message.text == 'Дуэли ⚔️')
def duels_menu(message):
    user_id = message.from_user.id
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)

    cursor.execute('SELECT bet FROM duel_searches WHERE user_id = ?', (user_id,))
    in_search = cursor.fetchone()

    if in_search:
        markup.add(types.KeyboardButton('❌ Отменить поиск'))
    else:
        markup.add(types.KeyboardButton('🔍 Начать поиск дуэли'))

    markup.add(types.KeyboardButton('👥 Кто ищет дуэль'))
    markup.add(types.KeyboardButton('ℹ️ О дуэлях'))
    markup.add(types.KeyboardButton('Назад 🔙'))

    bot.send_message(message.chat.id, "⚔️ **Меню дуэлей:**", reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == '❌ Отменить поиск')
def cancel_duel_search(message):
    user_id = message.from_user.id

    try:

        cursor.execute('SELECT bet FROM duel_searches WHERE user_id = ?', (user_id,))
        result = cursor.fetchone()

        if not result:
            bot.send_message(message.chat.id, "❌ Вы не находитесь в поиске дуэли.")
            return duels_menu(message)

        bet = result[0]

        cursor.execute('DELETE FROM duel_searches WHERE user_id = ?', (user_id,))

        cursor.execute('UPDATE users SET swag = swag + ? WHERE user_id = ?', (bet, user_id))

        conn.commit()

        bot.send_message(message.chat.id, f"✅ Поиск дуэли отменён. Ваша ставка ({bet}) возвращена.")

    except Exception as e:
        print(f"Ошибка при отмене поиска дуэли: {e}")
        bot.send_message(message.chat.id, "❌ Произошла ошибка при отмене поиска дуэли.")

    finally:
        duels_menu(message)

def start_duel_search(user_id, bet):
    cursor.execute('SELECT swag FROM users WHERE user_id = ?', (user_id,))
    swag = cursor.fetchone()[0]

    if swag < bet:
        return False, "❌ У вас недостаточно сваги для этой ставки."

    cursor.execute('SELECT user_id FROM duel_searches WHERE user_id = ?', (user_id,))
    if cursor.fetchone():
        return False, "❌ Вы уже ищете дуэль. Дождитесь соперника или отмените поиск."

    cursor.execute('UPDATE users SET swag = swag - ? WHERE user_id = ?', (bet, user_id))

    cursor.execute('INSERT INTO duel_searches (user_id, bet, search_start_time) VALUES (?, ?, ?)',
                   (user_id, bet, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()

    return True, "🔍 Поиск дуэли начат! Вы добавлены в список ожидающих."

def get_active_duels():
    cursor.execute('SELECT duel_id, player1_id, player2_id, bet FROM active_duels WHERE status = "active"')
    return cursor.fetchall()

def get_duel_searches():
    cursor.execute('SELECT user_id, bet, hide_duels FROM duel_searches')  
    return cursor.fetchall()

@bot.message_handler(func=lambda message: message.text == 'ℹ️ О дуэлях')
def duel_info(message):

    active_duels = get_active_duels()
    searches = get_duel_searches()

    active_count = len(active_duels)  
    search_count = len(searches)      

    info = (
        "⚔️ **Информация о дуэлях:**\n\n"
        "🔍 **Как начать**: Нажмите '🔍 Начать поиск дуэли', укажите ставку (минимум 100 сваги), и вы попадёте в список ожидающих.\n"
        "👥 **Выбор соперника**: В разделе '👥 Кто ищет дуэль' выберите игрока с подходящей ставкой.\n"
        "🎲 **Шанс победы**: 50/50 — исход дуэли определяется случайно.\n"
        "💰 **Награда**: Победитель забирает весь банк (ваша ставка + ставка соперника).\n"
        "⏳ **Отмена**: Если вы в поиске, нажмите '❌ Отменить поиск', чтобы вернуть ставку.\n\n"
        f"📊 **Сейчас:**\n"
        f"- Активных дуэлей: {active_count}\n"
        f"- Игроков в поиске: {search_count}\n\n"
        "💡 **Совет**: Чем выше ставка, тем больше выигрыш, но и выше риск!"
    )

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton('Назад 🔙'))

    bot.send_message(message.chat.id, info, reply_markup=markup, parse_mode="Markdown")

def get_duel_searches():
    cursor.execute('SELECT user_id, bet FROM duel_searches')  
    return cursor.fetchall()

@bot.message_handler(func=lambda message: message.text == '👥 Кто ищет дуэль')
def show_duel_searchers(message):
    searches = get_duel_searches()

    if not searches:
        bot.send_message(message.chat.id, "❌ Пока никто не ищет дуэль.")
        return duels_menu(message)

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    response = "👥 **Игроки, ищущие дуэль:**\n\n"

    for user_id, bet in searches:
        username = get_username(user_id)
        display_name = f"@{username}" if username else "Безымянный"  

        display_name = display_name.replace('*', '\\*') \
                                  .replace('_', '\\_') \
                                  .replace('[', '\\[') \
                                  .replace(']', '\\]') \
                                  .replace('`', '\\`')

        formatted_bet = f"{bet:,}".replace(",", ".")
        button_text = f"{display_name} - {formatted_bet} сваги"
        markup.add(types.KeyboardButton(button_text))
        response += f"{display_name} - {formatted_bet} сваги\n"

    markup.add(types.KeyboardButton('Назад 🔙'))

    bot.send_message(message.chat.id, response, reply_markup=markup, parse_mode="Markdown")
    bot.register_next_step_handler(message, process_searcher_selection)

def process_searcher_selection(message):
    if message.text == 'Назад 🔙':
        return duels_menu(message)

    try:
        selected_text = message.text
        bet_str = selected_text.split(' - ')[1].replace(' сваги', '').replace('.', '')
        bet = int(bet_str)

        cursor.execute('SELECT user_id FROM duel_searches WHERE bet = ?', (bet,))
        opponent = cursor.fetchone()

        if not opponent:
            bot.send_message(message.chat.id, "❌ Игрок не найден.")
            return duels_menu(message)

        opponent_id = opponent[0]

        if message.from_user.id == opponent_id:
            bot.send_message(message.chat.id, "❌ Вы не можете выбрать себя для дуэли.")
            return duels_menu(message)

        cursor.execute('SELECT swag FROM users WHERE user_id = ?', (message.from_user.id,))
        swag = cursor.fetchone()[0]

        if swag < bet:
            bot.send_message(message.chat.id, "❌ У вас недостаточно сваги для этой ставки.")
            return duels_menu(message)

        cursor.execute('DELETE FROM duel_searches WHERE user_id = ?', (opponent_id,))
        cursor.execute('UPDATE users SET swag = swag - ? WHERE user_id = ?', (bet, message.from_user.id))

        cursor.execute('INSERT INTO active_duels (player1_id, player2_id, bet) VALUES (?, ?, ?)',
                       (message.from_user.id, opponent_id, bet))
        duel_id = cursor.lastrowid
        conn.commit()

        start_duel(duel_id, message.from_user.id, opponent_id, bet)

        show_duel_searchers(message)

    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Ошибка: {e}")
        show_duel_searchers(message)  

user_navigation = {}

def set_navigation_state(user_id, state):
    user_navigation[user_id] = state

def main_menu(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton('Тапать 🤑'), types.KeyboardButton('Баланс 💰'))
    markup.add(types.KeyboardButton('Профиль 👤'), types.KeyboardButton('Топ по сваги 🏆'))
    markup.add(types.KeyboardButton('Магазин 🛒'), types.KeyboardButton('Игры 🎲'))
    markup.add(types.KeyboardButton('Лиги 🏅'), types.KeyboardButton('Фермы 🏡'))
    markup.add(types.KeyboardButton('Кланы 🏰'), types.KeyboardButton('Наш телеграм 📢'))
    markup.add(types.KeyboardButton('Настройки ⚙️'), types.KeyboardButton('Информация ℹ️'))
    bot.send_message(message.chat.id, "🏠 Вы вернулись в главное меню.", reply_markup=markup)

def get_total_swag():
    cursor.execute('SELECT SUM(swag) FROM users')
    total_swag = cursor.fetchone()[0] or 0  
    return total_swag

def burn_dg(user_id, amount):

    if amount < 1:
        return False, "❌ Минимальное количество для сжигания DG составляет 1."

    cursor.execute('SELECT amount FROM crypto_wallets WHERE user_id = ? AND crypto_type = "DG"', (user_id,))
    result = cursor.fetchone()
    if not result:
        return False, "❌ У вас нет DG для сжигания."
    current_balance = result[0]
    if current_balance < amount:
        return False, f"❌ У вас недостаточно DG. Доступно: {current_balance:.2f}."

    new_balance = current_balance - amount
    cursor.execute('UPDATE crypto_wallets SET amount = ? WHERE user_id = ? AND crypto_type = "DG"', (new_balance, user_id))

    cursor.execute('INSERT INTO dg_burn (user_id, amount, burn_date) VALUES (?, ?, ?)', 
                   (user_id, amount, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    cursor.execute('UPDATE crypto_emission SET total_amount = total_amount - ? WHERE crypto_type = "DG"', (amount,))

    rates = fetch_crypto_rates()
    new_dg_rate = max(rates["DG"] + (amount / 10000), 1)  
    cursor.execute('UPDATE crypto_emission SET total_amount = ? WHERE crypto_type = "DG"', (new_dg_rate,))  

    conn.commit()
    return True, (f"✨ **Сожжение DG** ✨\n\n"
                  f"Вы успешно сожгли **{amount} DG**.\n\n"
                  f"📈 Новый курс DG: **{int(new_dg_rate):,} сваги**.\n"
                  f"📊 Ваш новый баланс: **{new_balance:.2f} DG**.\n\n"
                  f"Благодаря вашему вкладу, курс DG вырос! 🚀")

import requests

def fetch_crypto_rates():
    try:

        url = "https://api.coingecko.com/api/v3/simple/price "
        params = {
            "ids": "bitcoin,toncoin",
            "vs_currencies": "usd"
        }
        response = requests.get(url, params=params, timeout=30)
        data = response.json()

        btc_usd = data.get("bitcoin", {}).get("usd", 88000)  
        ton_usd = data.get("toncoin", {}).get("usd", 3610)    

        swag_per_usd = 1

        bl_rate = btc_usd * swag_per_usd  
        dp_rate = ton_usd * swag_per_usd  

        total_swag = get_total_swag()

        local_conn = sqlite3.connect('swag_boti.db')
        local_cursor = local_conn.cursor()

        try:

            local_cursor.execute('SELECT SUM(amount) FROM crypto_wallets WHERE crypto_type = "BL"')
            total_bl = local_cursor.fetchone()[0] or 0
            local_cursor.execute('SELECT SUM(amount) FROM crypto_wallets WHERE crypto_type = "DP"')
            total_dp = local_cursor.fetchone()[0] or 0
            local_cursor.execute('SELECT SUM(amount) FROM crypto_wallets WHERE crypto_type = "LK"')
            total_lk = local_cursor.fetchone()[0] or 0

            total_bl_swag = total_bl * bl_rate
            total_dp_swag = total_dp * dp_rate

            local_cursor.execute('SELECT rate FROM crypto_rates WHERE crypto_type = "LK"')
            lk_rate_result = local_cursor.fetchone()
            lk_rate = lk_rate_result[0] if lk_rate_result else 1000  
            total_lk_swag = total_lk * lk_rate

            local_cursor.execute('SELECT total_burned FROM dg_burn_stats')
            total_burned_dg = local_cursor.fetchone()[0] or 0

            burn_coefficient = total_burned_dg / 1_000_000  

            total_capitalization = total_swag + total_bl_swag + total_dp_swag + total_lk_swag

            dg_rate = max((total_capitalization / 10000) + burn_coefficient, 0.1)

        finally:

            local_cursor.close()
            local_conn.close()

        return {
            "BL": int(bl_rate),
            "DP": int(dp_rate),
            "DG": round(dg_rate, 2),
            "LK": lk_rate
        }

    except Exception as e:
        print(f"[Ошибка] Не удалось получить курсы через CoinGecko: {e}")

        return {
            "BL": 88000,
            "DP": 3610,
            "DG": 0.1,
            "LK": 1000
        }

def get_crypto_balance(user_id, crypto_type):
    local_conn = sqlite3.connect('swag_boti.db')
    local_cursor = local_conn.cursor()
    try:
        local_cursor.execute('SELECT amount FROM crypto_wallets WHERE user_id = ? AND crypto_type = ?', 
                           (user_id, crypto_type))
        result = local_cursor.fetchone()
        return result[0] if result else 0.0
    finally:
        local_cursor.close()
        local_conn.close()

def update_crypto_balance(user_id, crypto_type, amount):
    cursor.execute('INSERT OR REPLACE INTO crypto_wallets (user_id, crypto_type, amount) VALUES (?, ?, ?)',
                   (user_id, crypto_type, amount))
    conn.commit()

def get_all_user_ids():
    cursor.execute('SELECT user_id FROM users')
    return [row[0] for row in cursor.fetchall()]

def buy_crypto(user_id, crypto_type, amount):
    rates = fetch_crypto_rates()
    cost = amount * rates[crypto_type]
    cursor.execute('SELECT swag FROM users WHERE user_id = ?', (user_id,))
    swag = cursor.fetchone()[0]

    if swag < cost:
        return False, f"❌ Недостаточно сваги. Нужно: {int(cost):,} сваги."

    if crypto_type == "LK":
        cursor.execute('SELECT total_amount FROM crypto_emission WHERE crypto_type = ?', ("LK",))
        total_lk = cursor.fetchone()[0]
        current_lk = sum(get_crypto_balance(uid, "LK") for uid in get_all_user_ids())
        if current_lk + amount > total_lk:
            return False, "❌ Превышена максимальная эмиссия LK (21,000,000,000)."

    cursor.execute('UPDATE users SET swag = swag - ? WHERE user_id = ?', (cost, user_id))
    current_balance = get_crypto_balance(user_id, crypto_type)
    update_crypto_balance(user_id, crypto_type, current_balance + amount)

    if crypto_type == "LK":

        cursor.execute('INSERT INTO lk_trading (user_id, trade_type, amount, swag_amount, trade_date) VALUES (?, ?, ?, ?, ?)',
                      (user_id, "buy", amount, cost, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    else:
        new_rate = rates[crypto_type]

    conn.commit()
    return True, f"✅ Вы купили {amount} {crypto_type} за {int(cost):,} сваги!\nНовый курс {crypto_type}: {int(new_rate):,} сваги.".replace(",", ".")

def get_total_dp():
    cursor.execute('SELECT SUM(amount) FROM crypto_wallets WHERE crypto_type = "DP"')
    total_dp = cursor.fetchone()[0] or 0  
    return total_dp

def sell_crypto(user_id, crypto_type, amount):
    rates = fetch_crypto_rates()
    current_balance = get_crypto_balance(user_id, crypto_type)
    if current_balance < amount:
        return False, f"❌ У вас недостаточно {crypto_type}. Доступно: {current_balance}."

    revenue = amount * rates[crypto_type]  
    cursor.execute('UPDATE users SET swag = swag + ? WHERE user_id = ?', (revenue, user_id))
    update_crypto_balance(user_id, crypto_type, current_balance - amount)

    if crypto_type == "LK":

        cursor.execute('INSERT INTO lk_trading (user_id, trade_type, amount, swag_amount, trade_date) VALUES (?, ?, ?, ?, ?)',
                      (user_id, "sell", amount, revenue, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    elif crypto_type == "DG":
        cursor.execute('UPDATE crypto_emission SET total_amount = total_amount - ? WHERE crypto_type = ?', (amount, crypto_type))

    conn.commit()
    return True, f"✅ Вы продали {amount} {crypto_type} и получили {revenue:,} сваги!\nНовый курс {crypto_type}: {int(rates[crypto_type]):,} сваги.".replace(",", ".")

def get_top_crypto_holders(crypto_type):
    cursor.execute("""
        SELECT u.username, u.hide_top, w.amount, u.selected_badge 
        FROM crypto_wallets w 
        JOIN users u ON w.user_id = u.user_id 
        WHERE w.crypto_type = ? AND w.amount > 0 
        ORDER BY w.amount DESC LIMIT 10
    """, (crypto_type,))
    holders = cursor.fetchall()
    medals = ["🥇", "🥈", "🥉", "🎖", "🏅", "🎗", "💠", "🔱", "⚜", "🌀"]
    top_list = []
    for i, (username, hide_top, amount, selected_badge) in enumerate(holders):
        medal = medals[i] if i < len(medals) else "🎲"
        display_name = "Скрыто🐱‍👤" if hide_top else (username if username else "None")
        if not hide_top and selected_badge:
            display_name += f" {selected_badge}"

        if crypto_type == "BL":
            amount_str = f"{amount:.8f}"
        else:
            amount_str = f"{amount:.2f}"
        top_list.append((medal, display_name, amount_str))
    return top_list

def format_crypto_top(crypto_type):
    holders = get_top_crypto_holders(crypto_type)
    if not holders:
        return f"🏆 **Топ-10 держателей {crypto_type}:**\n\n❌ Пока нет держателей {crypto_type}."

    response = f"🏆 **Топ-10 держателей {crypto_type}:**\n\n"
    for medal, name, amount in holders:
        response += f"{medal} {name} - {amount} {crypto_type}\n"
    return response

@bot.message_handler(func=lambda message: message.text == 'Криптовалюта 💸')
def crypto_menu(message):
    global crypto_enabled
    if not crypto_enabled:
        bot.send_message(message.chat.id, "❌ Раздел криптовалюты временно отключён администрацией.")
        return

    user_id = message.from_user.id
    local_conn = sqlite3.connect('swag_boti.db')
    local_cursor = local_conn.cursor()

    try:
        local_cursor.execute('SELECT swag, wallet_id FROM users WHERE user_id = ?', (user_id,))
        user_data = local_cursor.fetchone()

        if user_data is None:
            bot.send_message(message.chat.id, "❌ Ваш профиль не найден в базе данных.")
            return

        swag_balance, wallet_id = user_data

        bl_balance = get_crypto_balance(user_id, "BL")
        dp_balance = get_crypto_balance(user_id, "DP")
        dg_balance = get_crypto_balance(user_id, "DG")
        lk_balance = get_crypto_balance(user_id, "LK")

        rates = fetch_crypto_rates()

        response = (
            "💸 **Криптовалюта**\n\n"
            f"💰 Ваш баланс: {int(swag_balance):,}".replace(",", ".") + " сваги\n\n"
            f"🔑 Ваш номер кошелька: `{wallet_id}`\n\n"
            f"📊 Ваши активы:\n\n"
            f"- BL 🔺: {bl_balance:.8f} 🪙\n"
            f"- DP 🔶: {dp_balance:.2f} 💧\n"
            f"- DG 🔹: {dg_balance:.2f} ✨\n"
            f"- LK ⭐: {lk_balance:.2f} 💫\n\n"
            f"📈 Текущий курс:\n\n"
            f"- 1 BL = {int(rates['BL']):,}".replace(",", ".") + " сваги 🪙\n"
            f"- 1 DP = {int(rates['DP']):,}".replace(",", ".") + " сваги 💧\n"
            f"- 1 DG = {int(rates['DG']):,}".replace(",", ".") + " сваги ✨\n"
        )

        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton('🟢 Купить BL'), types.KeyboardButton('🟢 Купить DP'), types.KeyboardButton('🟢 Купить DG'))
        markup.add(types.KeyboardButton('🔴 Продать BL'), types.KeyboardButton('🔴 Продать DP'), types.KeyboardButton('🔴 Продать DG'))
        markup.add(types.KeyboardButton('🔥 Сжечь DG'))
        markup.add(types.KeyboardButton('🔄 Перевести'))
        markup.add(types.KeyboardButton('🏆 Топ держателей'))
        markup.add(types.KeyboardButton('Информация ℹ🌐'))
        markup.add(types.KeyboardButton('Назад 🔙'))

        bot.send_message(message.chat.id, response, reply_markup=markup, parse_mode="Markdown")

    except Exception as e:
        bot.send_message(message.chat.id, f"❌ Произошла ошибка: {str(e)}")
    finally:
        local_cursor.close()
        local_conn.close()

def fetch_crypto_rates():
    cursor.execute('SELECT crypto_type, rate FROM crypto_rates')
    return dict(cursor.fetchall())

def burn_dg(user_id, amount):

    if amount < 1:
        return False, "❌ Минимальное количество для сжигания DG составляет 1."

    cursor.execute('SELECT amount FROM crypto_wallets WHERE user_id = ? AND crypto_type = "DG"', (user_id,))
    result = cursor.fetchone()
    if not result:
        return False, "❌ У вас нет DG для сжигания."
    current_balance = result[0]
    if current_balance < amount:
        return False, f"❌ У вас недостаточно DG. Доступно: {current_balance:.2f} DG."

    new_balance = current_balance - amount
    cursor.execute('UPDATE crypto_wallets SET amount = ? WHERE user_id = ? AND crypto_type = "DG"', (new_balance, user_id))

    cursor.execute('INSERT INTO dg_burn (user_id, amount, burn_date) VALUES (?, ?, ?)', 
                   (user_id, amount, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

    cursor.execute('SELECT total_burned FROM dg_burn_stats')  
    result = cursor.fetchone()
    if result:
        total_burned = result[0] + amount
    else:
        total_burned = amount
    cursor.execute('UPDATE dg_burn_stats SET total_burned = ?', (total_burned,))

    burn_coefficient = total_burned / 1_000_000  

    rates = fetch_crypto_rates()
    rates['DG'] = rates['DG'] + burn_coefficient  

    cursor.execute('UPDATE crypto_rates SET rate = ? WHERE crypto_type = "DG"', (rates['DG'],))
    conn.commit()

    return True, (f"✨ **Сожжение DG** ✨\n\n"
                  f"Вы успешно сожгли **{amount} DG**.\n\n"
                  f"📈 Новый курс DG: **{int(rates['DG']):,} сваги**.\n"
                  f"🔥 Общее количество сожженных DG: **{int(total_burned):,} DG**.")

@bot.message_handler(func=lambda message: message.text == '🔥 Сжечь DG')
def burn_dg_menu(message):
    user_id = message.from_user.id
    chat_id = message.chat.id

    bot.send_message(chat_id, "💎 Введите количество DG для сжигания (минимум 1):")
    bot.register_next_step_handler(message, process_burn_dg, chat_id)

def process_burn_dg(message, chat_id):
    user_id = message.from_user.id
    try:
        amount = float(message.text)
        if amount < 1:
            bot.send_message(chat_id, "❌ Минимальное количество для сжигания DG составляет 1.")
            return
    except ValueError:
        bot.send_message(chat_id, "❌ Введите корректное число.")
        return

    success, response = burn_dg(user_id, amount)
    bot.send_message(chat_id, response, parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == '🏆 Топ держателей')
def show_crypto_top_menu(message):
    user_id = message.from_user.id
    set_navigation_state(user_id, 'crypto_top_menu')

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton('Топ BL 🪙'), types.KeyboardButton('Топ DP 💧'), 
               types.KeyboardButton('Топ DG ✨'), types.KeyboardButton('Топ LK 💫'))
    markup.add(types.KeyboardButton('Назад 🔙'))
    bot.send_message(message.chat.id, "🏆 Выберите криптовалюту для просмотра топа:", reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text in ['Топ BL 🪙', 'Топ DP 💧', 'Топ DG ✨', 'Топ LK 💫'])
def show_crypto_top(message):
    user_id = message.from_user.id
    set_navigation_state(user_id, 'crypto_top')

    crypto_type = message.text.split()[1]  
    top_text = format_crypto_top(crypto_type)

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton('Назад 🔙'))
    bot.send_message(message.chat.id, top_text, reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text in ['🟢 Купить BL', '🟢 Купить DP', '🟢 Купить DG', 
                                                         '🔴 Продать BL', '🔴 Продать DP', '🔴 Продать DG',])
def crypto_action(message):
    user_id = message.from_user.id
    set_navigation_state(user_id, 'crypto_transaction')

    action = message.text.split()[0]
    crypto_type = message.text.split()[2]

    bot.send_message(message.chat.id, f"✅ Введите количество {crypto_type} для {action.lower()} (например, 0.001 для BL или 1 для LK):")
    bot.register_next_step_handler(message, process_crypto_transaction, action, crypto_type)

def process_crypto_transaction(message, action, crypto_type):
    user_id = message.from_user.id
    if message.text == 'Назад 🔙':
        crypto_menu(message)  
        return

    try:
        amount = float(message.text)
        if amount <= 0:
            bot.send_message(message.chat.id, "❌ Количество должно быть больше 0. Попробуйте снова:")
            return bot.register_next_step_handler(message, process_crypto_transaction, action, crypto_type)

        if action == "🟢":
            success, response = buy_crypto(user_id, crypto_type, amount)
        else:  
            success, response = sell_crypto(user_id, crypto_type, amount)

        bot.send_message(message.chat.id, response)
        if success:
            crypto_menu(message)  
        else:
            bot.register_next_step_handler(message, process_crypto_transaction, action, crypto_type)  
    except ValueError:
        bot.send_message(message.chat.id, "❌ Введите корректное число (например, 0.001 для BL или 1 для DG). Попробуйте снова:")
        bot.register_next_step_handler(message, process_crypto_transaction, action, crypto_type)

@bot.message_handler(func=lambda message: message.text == 'Назад 🔙')
def back_handler(message):
    user_id = message.from_user.id
    current_state = user_navigation.get(user_id, 'main_menu')  

    if current_state == 'crypto_menu':
        main_menu(message)  
    elif current_state == 'crypto_top':
        show_crypto_top_menu(message)  
    elif current_state == 'crypto_top_menu':
        crypto_menu(message)  
    elif current_state == 'crypto_info':
        crypto_menu(message)  
    elif current_state == 'crypto_transaction':
        crypto_menu(message)  
    else:
        main_menu(message)  

@bot.message_handler(func=lambda message: message.text == '🔄 Перевести')
def transfer_crypto_menu(message):
    user_id = message.from_user.id
    set_navigation_state(user_id, 'crypto_transfer')

    bot.send_message(message.chat.id, "💸 Введите номер кошелька получателя (24 символа):")
    bot.register_next_step_handler(message, process_transfer_wallet)

def process_transfer_wallet(message):
    user_id = message.from_user.id
    wallet_id = message.text.strip()

    if len(wallet_id) != 24 or not all(c in (string.ascii_letters + string.digits) for c in wallet_id):
        bot.send_message(message.chat.id, "❌ Неверный формат номера кошелька. Он должен содержать 24 символа (буквы и цифры).")
        crypto_menu(message)
        return

    cursor.execute('SELECT user_id FROM users WHERE wallet_id = ?', (wallet_id,))
    recipient = cursor.fetchone()

    if not recipient:
        bot.send_message(message.chat.id, "❌ Кошелёк не найден. Проверьте номер.")
        crypto_menu(message)
        return

    recipient_id = recipient[0]
    if recipient_id == user_id:
        bot.send_message(message.chat.id, "❌ Вы не можете перевести криптовалюту самому себе.")
        crypto_menu(message)
        return

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton('BL 🔺'), types.KeyboardButton('DP 🔶'))
    markup.add(types.KeyboardButton('DG 🔹'), types.KeyboardButton('LK 🍀'))
    markup.add(types.KeyboardButton('Назад 🔙'))
    bot.send_message(message.chat.id, "💸 Выберите криптовалюту для перевода:", reply_markup=markup)
    bot.register_next_step_handler(message, process_transfer_crypto_type, recipient_id)

def process_transfer_crypto_type(message, recipient_id):
    user_id = message.from_user.id
    if message.text == 'Назад 🔙':
        return crypto_menu(message)

    crypto_type = message.text.split()[0]
    if crypto_type not in ["BL", "DP", "DG", "LK"]:  
        bot.send_message(message.chat.id, "❌ Выберите криптовалюту из предложенных. Попробуйте снова:")
        return bot.register_next_step_handler(message, process_transfer_crypto_type, recipient_id)

    bot.send_message(message.chat.id, f"💸 Введите сумму {crypto_type} для перевода (например, 0.001 для BL или 1 для DG/LK):")
    bot.register_next_step_handler(message, process_transfer_amount, recipient_id, crypto_type)

def process_transfer_amount(message, recipient_id, crypto_type):
    user_id = message.from_user.id
    try:
        amount = float(message.text)
        if amount <= 0:
            bot.send_message(message.chat.id, "❌ Сумма должна быть больше 0. Попробуйте снова:")
            return bot.register_next_step_handler(message, process_transfer_amount, recipient_id, crypto_type)

        if crypto_type == "BL" and amount < 0.00000001:
            bot.send_message(message.chat.id, "❌ Минимальная сумма перевода BL - 0.00000001")
            return bot.register_next_step_handler(message, process_transfer_amount, recipient_id, crypto_type)

        sender_balance = get_crypto_balance(user_id, crypto_type)
        if sender_balance < amount:
            precision = 8 if crypto_type == "BL" else 2
            bot.send_message(message.chat.id, f"❌ Недостаточно {crypto_type}. Ваш баланс: {sender_balance:.{precision}f}. Попробуйте снова:")
            return bot.register_next_step_handler(message, process_transfer_amount, recipient_id, crypto_type)

        if crypto_type == "DG":
            cursor.execute('SELECT total_amount FROM crypto_emission WHERE crypto_type = ?', ("DG",))
            total_dg = cursor.fetchone()[0]
            current_total_dg = sum([get_crypto_balance(uid, "DG") for uid in [user_id, recipient_id]])
            if current_total_dg + amount > total_dg:
                bot.send_message(message.chat.id, "❌ Ошибка: превышена общая эмиссия DG. Перевод невозможен.")
                return crypto_menu(message)

        sender_new_balance = sender_balance - amount
        recipient_balance = get_crypto_balance(recipient_id, crypto_type)
        recipient_new_balance = recipient_balance + amount

        update_crypto_balance(user_id, crypto_type, sender_new_balance)
        update_crypto_balance(recipient_id, crypto_type, recipient_new_balance)

        bot.send_message(user_id, f"✅ Вы перевели {amount} {crypto_type} на кошелёк пользователя {recipient_id}.")

        sender_username = get_username(user_id)
        try:
            bot.send_message(recipient_id, f"💸 Вам перевели {amount} {crypto_type} от @{sender_username if sender_username else 'Безымянного'}.")
        except Exception as e:
            print(f"Ошибка при уведомлении получателя {recipient_id}: {e}")

        crypto_menu(message)

    except ValueError:
        bot.send_message(message.chat.id, "❌ Введите корректное число (например, 0.001 для BL или 1 для DG/LK). Попробуйте снова:")
        bot.register_next_step_handler(message, process_transfer_amount, recipient_id, crypto_type)

schedule_farm_income()

BOT_START_TIME = time.time()

@bot.message_handler(func=lambda message: message.text == 'Информация ℹ️')
def info(message):
    info_message = (
        "**ℹ️ Информация о боте Swag**\n\n"
        "Добро пожаловать в мир сваги! Зарабатывайте валюту, соревнуйтесь с другими и станьте легендой! Узнайте всё о рангах, лигах, фермах и секретах игры.\n\n"

        "**🏅 Ранги: Докажи своё величие!**\n"
        "Зарабатывайте свагу и поднимайтесь по рангам:\n"
        "- **Нуб 👶**: от 1,000\n"
        "- **Нормис 🧑**: от 2,000\n"
        "- **На пути к успеху 🚀**: от 5,000\n"
        "- **Джигернаут 🦸**: от 10,000\n"
        "- **На дрипе 🕶️**: от 20,000\n"
        "- **Модник в классе 👔**: от 30,000\n"
        "- **Илон докс 🚗**: от 50,000\n"
        "- **Свага имеется 💼**: от 100,000\n"
        "- **Глава Тиктока 📱**: от 200,000\n"
        "- **Самый модный в школе 🏫**: от 500,000\n"
        "- **Величайший в дрипе 👑**: от 1,000,000\n"
        "- **Повелитель Сваги 🛡️**: от 10,000,000\n\n"

        "**🏆 Лиги: Новый уровень — новый вызов!**\n"
        "Переходите в следующую лигу, чтобы увеличить доход (аккаунт обнуляется):\n"
        "- **Лига Нормисов 🏅**: Бесплатно, 2-5 сваги/клик\n"
        "- **Лига Дрипа 🕶️**: 100,000 сваги, 5-10 сваги/клик\n"
        "- **Лига Nameles 🌌**: 250,000 сваги, 10-15 сваги/клик\n"
        "- **Лига Гранд Сваги 💎**: 500,000 сваги, 15-20 сваги/клик\n"
        "- **ЛИГА СВАГИ 🚀**: 1,000,000 сваги, 20-50 сваги/клик\n"
        "- **Лига Величия 👑**: 5,000,000 сваги, 50-100 сваги/клик\n"
        "- **Лига Титанов 🗿**: 10,000,000 сваги, 100-200 сваги/клик\n"
        "- **Лига Божеств 👼**: 25,000,000 сваги, 200-500 сваги/клик\n"
        "- **Лига Абсолютного Превосходства ⚡**: 50,000,000 сваги, 500-1000 сваги/клик\n"
        "- **Лига Вечных Знаменитостей 🌟**: 100,000,000 сваги, 1000-5000 сваги/клик\n"
        "- **Лига Легендарных Королей 👑✨**: 500,000,000 сваги, 5000-10000 сваги/клик\n\n"

        "**🌾 Фермы: Пассивный доход**\n"
        "Покупайте фермы и получайте свагу каждый час:\n"
        "- **Ферма Дрипа 🌾**: 100,000 сваги, 1,000/час\n"
        "- **Ферма Майнер ⛏️**: 500,000 сваги, 5,000/час\n"
        "- **Ферма мобов 👾**: 1,000,000 сваги, 10,000/час\n"
        "- **Ферма сваги 💰**: 5,000,000 сваги, 50,000/час\n\n"

        "**🎲 Множители: Увеличьте доход за клик**\n"
        "Покупайте множители в магазине:\n"
        "- **❄Х2**: 1,000 сваги\n"
        "- **♦Х3**: 2,000 сваги\n"
        "- **💠Х5**: 5,000 сваги\n"
        "- **🌲Х10**: 15,000 сваги\n"
        "- **⚜Х20**: 30,000 сваги\n"
        "- **⚠Х50**: 70,000 сваги\n"
        "- **🚩Х100**: 150,000 сваги\n\n"

        "**💡 Полезные советы:**\n"
        "- **Кланы 🏰**: Создание клана — 10,000,000 сваги. Делитесь 5% дохода и получайте бонусный множитель!\n"
        "- **Премиум 💎**: 150 RUB (на 30 дней) — +20% к доходу, уникальные значки и GIF в профиле.\n"
        "- **Казино 🎰**: Ставки от 50 до 10,000 сваги. Угадайте цвет и умножьте выигрыш (x2 или x10)!\n"
        "- **Магазин 🛒**: Вкладывайте свагу в фермы и множители для роста дохода.\n\n"

        "**📢 Подпишитесь на наш Telegram-канал:**\n"
        "Новости и бонусы: [t.me/metrswagi](https://t.me/metrswagi)"
    )
    bot.send_message(message.chat.id, info_message, parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == 'Информация ℹ🌐')
def crypto_info(message):
    user_id = message.from_user.id
    set_navigation_state(user_id, 'crypto_info')  

    rates = fetch_crypto_rates()  
    total_swag = get_total_swag()

    cursor.execute('SELECT SUM(amount) FROM crypto_wallets WHERE crypto_type = "BL"')
    total_bl = cursor.fetchone()[0] or 0
    cursor.execute('SELECT SUM(amount) FROM crypto_wallets WHERE crypto_type = "DP"')
    total_dp = cursor.fetchone()[0] or 0
    total_bl_swag = total_bl * rates["BL"]
    total_dp_swag = total_dp * rates["DP"]
    total_capitalization = total_swag + total_bl_swag + total_dp_swag

    cursor.execute('SELECT SUM(amount) FROM dg_burn')
    total_burned_dg = cursor.fetchone()[0] or 0

    dg_rate = max((total_capitalization - total_burned_dg) / 10000, 1)

    response = (f"ℹ️ **Информация о криптовалюте в игре**\n\n"
               "Это исключительно игровая механика для преумножения или сохранения сваги. "
               "Мы не связаны с реальной криптовалютой, все операции происходят только внутри игры!\n\n"
               "📌 *Что такое BL, DP и DG?*\n"
               f"- **BL (Бликс)** — игровая валюта, курс которой привязан к реальному Bitcoin (BTC). Текущий курс: {int(rates['BL']):,} сваги.\n"
               f"- **DP (Дрип)** — игровая валюта, курс которой привязан к реальному Toncoin (TON). Текущий курс: {int(rates['DP']):,} сваги.\n"
               f"- **DG (Цифровое золото)** — игровая валюта, курс которой зависит от общей капитализации игры. "
               f"Текущий курс: {int(dg_rate):,} сваги.\n"
               f"  💡 *Как считается DG?* Курс DG = (Общая свага + стоимость всех BL + стоимость всех DP + коофицент DG) / 10,000. "
               f"Текущая капитализация: {int(total_capitalization):,} сваги.\n\n"
               f"📌 *Сожжено DG:* {int(total_burned_dg):,} DG.\n\n"
               "Курсы BL и DP обновляются на основе реальных данных с Binance, а DG отражает внутреннюю экономику игры!").replace(",", ".")

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton('Назад 🔙'))

    bot.send_message(message.chat.id, response, reply_markup=markup, parse_mode="Markdown")

@bot.message_handler(commands=['ahelp'])
def admin_help(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    thread_id = message.message_thread_id if message.is_topic_message else None

    if user_id != ADMIN_ID:
        bot.send_message(chat_id, "❌ У вас нет прав для использования этой команды.", message_thread_id=thread_id)
        return

    help_text = (
        "⚙️ **Команды администратора:** ⚙️\n\n"
        "💰 **Управление свагой:**\n"
        "➡️ `/give <user_id> <amount>` — Выдать свагу пользователю 💸 **[G]**\n"
        "➡️ `/take <user_id> <amount>` — Забрать свагу у пользователя 💵 **[G]**\n"
        "➡️ `/resetmoney <user_id>` — Обнулить баланс сваги пользователя 🔄 **[G]**\n\n"
        "💎 **Управление премиум-статусом:**\n"
        "➡️ `/setpremium <user_id> <дней>` — Выдать премиум на указанное количество дней ✨ **[G]**\n"
        "➡️ `/removepremium <user_id>` — Забрать премиум-статус у пользователя ❌ **[G]**\n\n"
        "🔑 **Управление API ключами:**\n"
        "➡️ `/api create` — Создать новый API-ключ для премиума 🔑 **[G]**\n"
        "➡️ `/api list` — Показать список созданных API-ключей 📋 **[G]**\n\n"
        "📢 **Рассылка и информация:**\n"
        "➡️ `/say <текст>` — Сделать рассылку всем пользователям 📣 **[G]**\n"
        "➡️ `/telegram` — Отправить ссылку на Telegram-канал 📢 **[G]**\n\n"
        "🖼️ **Управление профилями:**\n"
        "➡️ `/profile <user_id>` — Просмотреть профиль пользователя 👤 **[G]**\n"
        "➡️ `/setwallet <user_id> <новый_номер_кошелька>` — Изменить номер кошелька пользователя 💼 **[G]**\n\n"
        "🔄 **Управление криптовалютой:**\n"
        "➡️ `/resetcrypto <user_id> <crypto_type>` — Обнулить баланс криптовалюты (BL, DP, DG) 💱 **[G]**\n"
        "➡️ `/disablecrypto <on/off>` — Включить/отключить раздел криптовалюты 🔒 **[G]**\n\n"
        "🏅 **Управление значками:**\n"
        "➡️ `/znak выдать <user_id> <значок>` — Выдать значок пользователю 🎖 **[G]**\n"
        "➡️ `/znak забрать <user_id> <значок>` — Забрать значок у пользователя 🚫 **[G]**\n\n"
        "📊 **Статистика и аналитика:**\n"
        "➡️ `/atop` — Топ-10 по балансу с ID пользователей 🏆 **[G]**\n"
        "➡️ `/stats` — Показать статистику бота 📈 **[G]**\n"
        "➡️ `/id` — Получить свой Telegram ID 🆔 **[G]**\n\n"
        "⚔️ **Дуэли:**\n"
        "➡️ `/duel <сумма>` — Создать открытый вызов на дуэль в групповом чате ⚡ **[M]**\n\n"
        "🔧 **Дополнительные инструменты:**\n"
        "➡️ `/reacc <old_user_id> <new_user_id>` — Перенести имущество между аккаунтами 🔄 **[G]**\n"
        "➡️ `/tegreload` — Обновить Telegram-теги всех пользователей 📅 **[G]**\n\n"
        "ℹ️ **Обозначения:**\n"
        "**[M]** — Работает только в беседах\n"
        "**[B]** — Работает только в личке бота\n"
        "**[G]** — Работает везде\n\n"
        "⚠️ **Внимание:** Все команды доступны только администратору."
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
                f"📩 @{message.from_user.username or 'Admin'}! Список админ-команд отправлен вам в личные сообщения.",
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

@bot.message_handler(func=lambda message: message.text == 'ℹ️ Информация о кланах')
def clan_info(message):
    info_message = (
        "ℹ️ **Информация о кланах**\n\n"
        "🏰 Кланы объединяют игроков для совместной игры.\n"
        "💰 Общий баланс клана используется для улучшений.\n"
        "📈 Все платят 5% дохода в казну клана.\n"
        "🌾 **Фермы лидера**: Лидер может подключить до 3 ферм (5 с премиумом), и их доход идёт в казну.\n"
        "🚀 При выходе из клана множитель возвращается к обычному.\n"
        "🔄 Использование множителя клана переключается в настройках.\n\n"
        "💹 **Цены на улучшение множителя**:\n"
        "- x2: 1,500,000 сваги\n"
        "- x3: 3,000,000 сваги\n"
        "- x4: 6,000,000 сваги\n"
        "- x5: 12,000,000 сваги\n"
        "- x10: 30,000,000 сваги\n"
        "- x25: 75,000,000 сваги\n"
        "- x50: 150,000,000 сваги\n"
        "- x100: 300,000,000 сваги\n\n"
        "🔄 **Автопокупка множителей**: При достаточном балансе множитель улучшается автоматически."
    )
    bot.send_message(message.chat.id, info_message, parse_mode="Markdown")

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
                "🧩 <b>Добро пожаловать в мир возможностей СВАГАМЕТРА!</b> 🎉\n\n"
                "🔐 Чтобы разблокировать все функции бота, просто подпишись на наш канал:\n"
                f"👉 @metrswagi\n\n"
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
            types.KeyboardButton('Кланы 🏰'), types.KeyboardButton('Наш телеграм 📢'),
            types.KeyboardButton('Настройки ⚙️'), types.KeyboardButton('Информация ℹ️')
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

@bot.message_handler(commands=['reclan'])
def reclan_handler(message):
    user_id = message.from_user.id
    chat_id = message.chat.id
    thread_id = message.message_thread_id if message.is_topic_message else None

    if user_id != ADMIN_ID:
        bot.send_message(chat_id, "❌ У вас нет прав для использования этой команды.", message_thread_id=thread_id)
        return

    try:
        parts = message.text.split()
        if len(parts) != 3:
            bot.send_message(chat_id,
                             "❌ Неверный формат. Используйте: /reclan <old_owner_id> <new_owner_id>\n"
                             "Пример: /reclan 123456789 987654321",
                             message_thread_id=thread_id)
            return

        old_owner_id = int(parts[1])  
        new_owner_id = int(parts[2])  

        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute('SELECT clan_id FROM clans WHERE owner_id = ?', (old_owner_id,))
        clan = cursor.fetchone()
        if not clan:
            bot.send_message(chat_id, "❌ У указанного пользователя нет клана.", message_thread_id=thread_id)
            return

        clan_id = clan[0]

        cursor.execute('UPDATE clans SET owner_id = ? WHERE clan_id = ?', (new_owner_id, clan_id))

        cursor.execute('DELETE FROM clan_members WHERE user_id = ?', (new_owner_id,))
        cursor.execute('INSERT INTO clan_members (user_id, clan_id) VALUES (?, ?)', (new_owner_id, clan_id))

        cursor.execute('DELETE FROM clan_members WHERE user_id = ?', (old_owner_id,))

        conn.commit()
        bot.send_message(chat_id,
                         f"✅ Владение кланом успешно передано с {old_owner_id} на {new_owner_id}.",
                         parse_mode="Markdown",
                         message_thread_id=thread_id)

    except ValueError:
        bot.send_message(chat_id,
                         "❌ ID старого и нового владельца должны быть числами.",
                         message_thread_id=thread_id)
    except Exception as e:
        conn.rollback()
        bot.send_message(chat_id,
                         f"❌ Произошла ошибка при передаче клана: {e}",
                         message_thread_id=thread_id)
        print(f"[Ошибка] Передача клана: {e}")
    finally:
        cursor.close()
        conn.close()

def print_startup_info():
    print("📊 Стартовая информация о системе:")
    print("-" * 40)

    try:

        conn = sqlite3.connect('swag_boti.db')
        cursor = conn.cursor()

        cursor.execute('SELECT COUNT(*) FROM users')
        total_users = cursor.fetchone()[0]
        print(f"👥 Всего пользователей: {total_users}")

        cursor.execute('SELECT SUM(swag) FROM users')
        total_swag = cursor.fetchone()[0] or 0
        print(f"💰 Общий баланс сваги: {total_swag:,}")

        cursor.execute('SELECT SUM(quantity) FROM farms')
        total_farms = cursor.fetchone()[0] or 0
        print(f"🚜 Общее количество ферм: {total_farms}")

        cursor.execute('SELECT COUNT(*) FROM clans')
        total_clans = cursor.fetchone()[0] or 0
        print(f"🏰 Общее количество кланов: {total_clans}")

        cursor.execute('SELECT COUNT(*) FROM users WHERE is_premium = 1')
        premium_users = cursor.fetchone()[0] or 0
        print(f"💎 Количество премиум-пользователей: {premium_users}")

        import time
        start_time = time.time()
        uptime_seconds = int(start_time - BOT_START_TIME)
        uptime_str = f"{uptime_seconds // 86400} дн. {(uptime_seconds % 86400) // 3600} ч. {(uptime_seconds % 3600) // 60} мин."
        print(f"⏳ Бот работает: {uptime_str}")

        print("🟢 Статус подключения к базе данных: успешно")

        print("-" * 40)
    except Exception as e:
        print(f"🔴 Ошибка при получении информации: {e}")
    finally:
        conn.close()

print_startup_info()
check_all_premium_users()

schedule_premium_check()

print("💲 Бот запущен.")
print("change this part")

bot.polling(non_stop=True, timeout=60)  