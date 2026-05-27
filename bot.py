#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, json, datetime, logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

logging.basicConfig(level=logging.INFO)

BOT_TOKEN = os.environ.get("BOT_TOKEN", "8722497069:AAESVIlS8NNT00U9v31TS_TR7IPYOhniw00")
DATA_FILE = "data.json"

# ── ДАННЫЕ ────────────────────────────────────────────────
def load():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "groups": ["ИС-21", "ИС-22", "ПО-21"],
        "students": {
            "ИВТ-22": ["Иванов Иван", "Петрова Мария", "Сидоров Алексей", "Козлова Анна", "Новиков Дмитрий"],
            "ИВТ-23": ["Абдурашитова Элина", "Абдыгапарова Айтурган", "Азимбеков Усон", "Акмалова Мадинабону", "Али уулу Икрамидин", "Алыбеков Нурсултан", "Атькелдиева Нуржана", "Бадалов Орхон", "Балтабаева Айсырга", "Зулпуев Мыктыбек", "Зулпукааров Мухаммед", "Ишанов Абдулкудус", "Карибеков Маматкул", "Кариева Рамина", "Курбанбаева Лунара", "Манасов Арзуубек", "Матазов Азирет", "Нуралиев Айдар", "Ормошова Алтынай", "Пазылов Омурбек", "Пайзылдаев Мухаммадали", "Турсунбаев Абдуллох", "Усенбаев Абубакир", "Холмухамматов Абдуразак", "Чыныбек кызы Альбина", "Шарапов Бекзод", "Ырыстууев Бектур", "Рахманбердиева Умида", "Жамаев Бектур", "Садырбеков Байтур", "Кадиров Мухаммадюсуп", "Жолдошбаев Нуржиги"],
            "ИВТ-24": ["Зайцева Ольга", "Соколов Максим", "Белов Артём"],
        },
        "subjects": ["1С","С#","Программирование микроконтролеров","Инженерная графика","Системное программирование","Сети и телекомуникации"],
        "records": [],
        "session": None,
        "admins": []  # сюда добавим ваш Telegram ID
    }

def save(d):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(d, f, ensure_ascii=False, indent=2)

def is_admin(user_id):
    d = load()
    return str(user_id) in [str(a) for a in d.get("admins", [])] or not d.get("admins")

# ── /start — студент попадает сюда после QR ───────────────
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user.first_name
    d    = load()

    # Показываем список групп сразу
    groups = d.get("groups", [])
    kb = [[InlineKeyboardButton(g, callback_data=f"grp|{g}")] for g in groups]
    kb.append([InlineKeyboardButton("📋 Я преподаватель", callback_data="admin")])

    await update.message.reply_text(
        f"👋 Привет, {user}!\n\n"
        "📋 Выбери свою группу чтобы отметиться на паре:",
        reply_markup=InlineKeyboardMarkup(kb)
    )

# ── КНОПКИ ────────────────────────────────────────────────
async def cmd_button(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q      = update.callback_query
    await q.answer()
    data   = q.data
    parts  = data.split("|", 2)
    action = parts[0]
    uid    = update.effective_user.id
    uname  = update.effective_user.first_name

    d = load()

    # Студент выбрал группу
    if action == "grp":
        group    = parts[1]
        ctx.user_data['group'] = group
        students = d.get("students", {}).get(group, [])

        if not students:
            await q.edit_message_text(f"❌ В группе {group} нет студентов.\nОбратитесь к преподавателю.")
            return

        kb = [[InlineKeyboardButton(s, callback_data=f"stu|{s}")] for s in students]
        kb.append([InlineKeyboardButton("◀ Назад", callback_data="back_grp")])

        await q.edit_message_text(
            f"📚 Группа: *{group}*\n\n"
            "👇 Найди своё имя в списке:",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(kb)
        )

    # Студент выбрал себя
    elif action == "stu":
        name  = parts[1]
        group = ctx.user_data.get('group', '?')
        sess  = d.get("session")

        ctx.user_data['name'] = name

        subject   = sess["subject"] if sess else None
        subj_text = f"📖 {subject}" if subject else "⚠️ Активной сессии нет"

        kb = []
        if subject:
            kb.append([InlineKeyboardButton("✅ Я здесь!", callback_data=f"mark|{name}|{group}|{subject}")])
        else:
            kb.append([InlineKeyboardButton("✅ Отметиться (без предмета)", callback_data=f"mark|{name}|{group}|нет")])
        kb.append([InlineKeyboardButton("◀ Назад", callback_data=f"grp|{group}")])

        await q.edit_message_text(
            f"👤 *{name}*\n"
            f"📚 Группа: *{group}*\n"
            f"{subj_text}\n\n"
            "Всё верно? Нажми кнопку:",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(kb)
        )

    # Подтверждение отметки
    elif action == "mark":
        name    = parts[1]
        group   = parts[2]
        subject = parts[3]
        now     = datetime.datetime.now()
        today   = now.date().isoformat()
        time_s  = now.strftime("%H:%M")

        # Дубликат?
        already = any(
            r['name'] == name and r['group'] == group and
            r['subject'] == subject and r['date'] == today
            for r in d.get('records', [])
        )
        if already:
            await q.edit_message_text(
                f"⚠️ *{name}*, вы уже отмечались сегодня!\n\n"
                f"📖 {subject} | 📚 {group}",
                parse_mode='Markdown'
            )
            return

        d.setdefault('records', []).append({
            'name': name, 'group': group, 'subject': subject,
            'date': today, 'time': time_s,
            'tg_id': str(uid), 'tg_name': uname
        })
        save(d)
        logging.info(f"ОТМЕТКА: {name} / {group} / {subject} / {time_s}")

        await q.edit_message_text(
            f"✅ *Отмечено!*\n\n"
            f"👤 {name}\n"
            f"📚 {group}\n"
            f"📖 {subject}\n"
            f"🕐 {time_s}\n"
            f"📅 {today}",
            parse_mode='Markdown'
        )

    # Назад к группам
    elif action == "back_grp":
        groups = d.get("groups", [])
        kb = [[InlineKeyboardButton(g, callback_data=f"grp|{g}")] for g in groups]
        kb.append([InlineKeyboardButton("📋 Я преподаватель", callback_data="admin")])
        await q.edit_message_text(
            "👇 Выбери свою группу:",
            reply_markup=InlineKeyboardMarkup(kb)
        )

    # Преподаватель
    elif action == "admin":
        kb = [
            [InlineKeyboardButton("▶ Начать пару",    callback_data="adm_start")],
            [InlineKeyboardButton("■ Завершить пару", callback_data="adm_stop")],
            [InlineKeyboardButton("📅 Сегодня",       callback_data="adm_today")],
            [InlineKeyboardButton("📊 Статистика НБ", callback_data="adm_stats")],
        ]
        await q.edit_message_text(
            "👩‍🏫 *Панель преподавателя*",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(kb)
        )

    # Начать пару — выбор группы
    elif action == "adm_start":
        groups = d.get("groups", [])
        kb = [[InlineKeyboardButton(g, callback_data=f"adm_grp|{g}")] for g in groups]
        kb.append([InlineKeyboardButton("◀ Назад", callback_data="admin")])
        await q.edit_message_text("Выбери группу для пары:", reply_markup=InlineKeyboardMarkup(kb))

    elif action == "adm_grp":
        group = parts[1]
        ctx.user_data['adm_group'] = group
        subjects = d.get("subjects", [])
        kb = [[InlineKeyboardButton(s, callback_data=f"adm_subj|{s}")] for s in subjects]
        kb.append([InlineKeyboardButton("◀ Назад", callback_data="adm_start")])
        await q.edit_message_text(f"Группа: *{group}*\n\nВыбери предмет:", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(kb))

    elif action == "adm_subj":
        subject = parts[1]
        group   = ctx.user_data.get('adm_group', '?')
        today   = datetime.date.today().isoformat()
        d['session'] = {'group': group, 'subject': subject, 'date': today}
        save(d)

        # Ссылка на бота для QR
        bot_info = await ctx.bot.get_me()
        link = f"https://t.me/{bot_info.username}?start=attend"

        await q.edit_message_text(
            f"✅ *Сессия запущена!*\n\n"
            f"👥 Группа: *{group}*\n"
            f"📖 Предмет: *{subject}*\n\n"
            f"📱 *Ссылка для QR-кода:*\n`{link}`\n\n"
            f"Скопируй ссылку, создай QR на сайте qr-code-generator.com и покажи студентам.\n"
            f"Или просто скинь эту ссылку студентам.",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀ Меню", callback_data="admin")]])
        )

    elif action == "adm_stop":
        d['session'] = None
        save(d)
        await q.edit_message_text(
            "✅ Пара завершена.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀ Меню", callback_data="admin")]])
        )

    elif action == "adm_today":
        today   = datetime.date.today().isoformat()
        records = [r for r in d.get('records', []) if r['date'] == today]
        if not records:
            text = "📋 Сегодня никто не отметился."
        else:
            by_sub = {}
            for r in records:
                by_sub.setdefault(r['subject'], []).append(r)
            text = f"📋 *Посещаемость {today}*\n\n"
            for sub, recs in by_sub.items():
                text += f"📖 *{sub}*\n"
                for i, r in enumerate(recs, 1):
                    text += f"  {i}. {r['name']} ({r['group']}) — {r['time']}\n"
                text += "\n"

        await q.edit_message_text(
            text[:4000],
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀ Меню", callback_data="admin")]])
        )

    elif action == "adm_stats":
        records  = d.get('records', [])
        students = d.get('students', {})
        if not records:
            await q.edit_message_text(
                "📊 Нет данных. Проведите хотя бы одну пару.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀ Меню", callback_data="admin")]])
            )
            return

        # Уникальные дни на предмет
        lesson_dates = {}
        for r in records:
            lesson_dates.setdefault(r['subject'], set()).add(r['date'])

        text = "📊 *Статистика НБ*\n\n"
        for group, names in students.items():
            text += f"👥 *{group}*\n"
            for name in names:
                for subj, dates in lesson_dates.items():
                    total   = len(dates)
                    present = sum(1 for r in records if r['name']==name and r['subject']==subj and r['group']==group)
                    absent  = total - present
                    pct     = int(present/total*100) if total else 0
                    icon    = "✅" if pct >= 70 else "⚠️" if pct >= 50 else "❌"
                    text   += f"  {icon} {name} | {subj[:12]}: {present}/{total} ({pct}%) НБ:{absent}\n"
            text += "\n"

        # Разбиваем если длинно
        for i in range(0, len(text), 3800):
            if i == 0:
                await q.edit_message_text(
                    text[i:i+3800], parse_mode='Markdown',
                    reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("◀ Меню", callback_data="admin")]])
                )
            else:
                await ctx.bot.send_message(q.message.chat.id, text[i:i+3800], parse_mode='Markdown')

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CallbackQueryHandler(cmd_button))
    print("✅ Бот запущен!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
