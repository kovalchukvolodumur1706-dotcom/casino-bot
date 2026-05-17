import asyncio
import aiosqlite
import random
import time

from aiogram import Bot, Dispatcher, F, types
from aiogram.types import Message, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters import Command

# ===== CONFIG =====
TOKEN = "8715708739:AAE0qilGv9ikohTq9tcCzBZmTJCukGhf8aI"
ADMIN_ID = 7989331423

bot = Bot(token=TOKEN)
dp = Dispatcher()

# ===== SETTINGS =====
START_BALANCE = 5000
BONUS_AMOUNT = 5000
BONUS_COOLDOWN = 86400

MINES_STEP = {
    5: 0.75,
    10: 2.30,
    15: 9.00
}

# ===== GAME STORAGE =====
mines_games = {}
bm_games = {}
blackjack_games = {}

# ===== FORMAT =====
def format_money(amount):
    return f"{amount:,}".replace(",", " ")

# ===== DATABASE =====
async def init_db():

    async with aiosqlite.connect("casino.db") as db:

        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                balance INTEGER DEFAULT 5000,
                last_bonus INTEGER DEFAULT 0
            )
        """)

        await db.commit()

# ===== BALANCE =====
async def get_balance(user_id):

    async with aiosqlite.connect("casino.db") as db:

        async with db.execute(
            "SELECT balance FROM users WHERE id = ?",
            (user_id,)
        ) as cursor:

            row = await cursor.fetchone()

            if not row:

                await db.execute(
                    "INSERT INTO users (id, balance) VALUES (?, ?)",
                    (user_id, START_BALANCE)
                )

                await db.commit()

                return START_BALANCE

            return row[0]

async def update_balance(user_id, amount):

    balance = await get_balance(user_id)

    async with aiosqlite.connect("casino.db") as db:

        await db.execute(
            "UPDATE users SET balance = ? WHERE id = ?",
            (balance + amount, user_id)
        )

        await db.commit()

# ===== START =====
@dp.message(Command("start"))
async def start_cmd(message: Message):

    text = (
        "🎰 ДОБРО ПОЖАЛОВАТЬ В КАЗИК-WIN 🎰\n\n"

        "💣 МИНЫ\n"
        "└ Мины [ставка]\n"
        "└ Міни [ставка]\n\n"

        "📈 БОЛЬШЕ / МЕНЬШЕ\n"
        "└ Бм [ставка]\n\n"

        "🃏 BLACKJACK\n"
        "└ Блекджек [ставка]\n\n"

        "🎁 БОНУС\n"
        "└ Бонус\n\n"

        "💸 ПЕРЕВОД\n"
        "└ П [сумма]\n"
        "└ П [сумма] ID\n\n"

        "🏆 РЕЙТИНГ\n"
        "└ Рейтинг\n\n"

        "📒 ИНСТРУМЕНТЫ\n"
        "└ Б — баланс\n"
        "└ Профиль\n\n"

        "👑 АДМИН\n"
        "└ Выдать [сумма] ID\n"
        "└ Видати [сумма] ID\n"
        "└ Обнулить ID\n"
        "└ Онулити ID"
    )

    await message.answer(text)

# ===== BALANCE =====
@dp.message(F.text.lower() == "б")
async def balance_cmd(message: Message):

    balance = await get_balance(message.from_user.id)

    await message.answer(
        f"💰 Баланс: {format_money(balance)} WIN"
    )

# ===== PROFILE =====
@dp.message(F.text.lower() == "профиль")
async def profile_cmd(message: Message):

    balance = await get_balance(message.from_user.id)

    await message.answer(
        f"👤 ПРОФИЛЬ\n\n"
        f"🆔 ID: {message.from_user.id}\n"
        f"💰 Баланс: {format_money(balance)} WIN"
    )

# ===== BONUS =====
@dp.message(F.text.lower() == "бонус")
async def bonus_cmd(message: Message):

    user_id = message.from_user.id

    await get_balance(user_id)

    async with aiosqlite.connect("casino.db") as db:

        async with db.execute(
            "SELECT last_bonus FROM users WHERE id = ?",
            (user_id,)
        ) as cursor:

            row = await cursor.fetchone()

        now = int(time.time())

        last_bonus = row[0] if row else 0

        if now - last_bonus < BONUS_COOLDOWN:

            remaining = BONUS_COOLDOWN - (now - last_bonus)

            hours = remaining // 3600
            minutes = (remaining % 3600) // 60

            return await message.answer(
                f"⏳ Бонус уже получен!\n\n"
                f"🕒 Через: {hours} ч. {minutes} мин."
            )

        await update_balance(user_id, BONUS_AMOUNT)

        await db.execute(
            "UPDATE users SET last_bonus = ? WHERE id = ?",
            (now, user_id)
        )

        await db.commit()

        await message.answer(
            f"🎁 Бонус получен!\n\n"
            f"💰 +{format_money(BONUS_AMOUNT)} WIN"
        )

# ===== РЕЙТИНГ =====
@dp.message(F.text.lower() == "рейтинг")
async def rating_cmd(message: Message):

    chat_id = message.chat.id

    members = []

    async with aiosqlite.connect("casino.db") as db:

        async with db.execute(
            "SELECT id, balance FROM users ORDER BY balance DESC"
        ) as cursor:

            rows = await cursor.fetchall()

    for user_id, balance in rows:

        try:

            member = await bot.get_chat_member(chat_id, user_id)

            if member.status not in ["left", "kicked"]:

                user = member.user

                name = user.first_name

                if user.username:
                    name += f" (@{user.username})"

                members.append(
                    (name, user_id, balance)
                )

        except:
            pass

    members = members[:10]

    text = "🏆 ТОП ИГРОКОВ ЧАТА\n\n"

    if not members:

        return await message.answer(
            "❌ В этом чате нет игроков."
        )

    for i, player in enumerate(members, start=1):

        name, user_id, balance = player

        text += (
            f"{i}. {name}\n"
            f"🆔 ID: {user_id}\n"
            f"💰 {format_money(balance)} WIN\n\n"
        )

    await message.answer(text)

# ===== ADMIN GIVE =====
@dp.message(
    lambda m: m.text and (
        m.text.lower().startswith("выдать ")
        or m.text.lower().startswith("видати ")
    )
)
async def give_money(message: Message):

    if message.from_user.id != ADMIN_ID:
        return

    try:

        parts = message.text.split()

        amount = int(parts[1])
        target_id = int(parts[2])

        await get_balance(target_id)
        await update_balance(target_id, amount)

        await message.answer(
            f"✅ Выдано {format_money(amount)} WIN\n"
            f"🆔 ID: {target_id}"
        )

    except:

        await message.answer(
            "❌ Пример:\nВыдать 100000 7989331423"
        )

# ===== ADMIN RESET =====
@dp.message(
    lambda m: m.text and (
        m.text.lower().startswith("обнулить ")
        or m.text.lower().startswith("онулити ")
    )
)
async def reset_balance(message: Message):

    if message.from_user.id != ADMIN_ID:
        return

    try:

        user_id = int(message.text.split()[1])

        async with aiosqlite.connect("casino.db") as db:

            await db.execute(
                "UPDATE users SET balance = 0 WHERE id = ?",
                (user_id,)
            )

            await db.commit()

        await message.answer(
            f"✅ Баланс игрока {user_id} обнулён"
        )

    except:

        await message.answer(
            "❌ Пример:\nОбнулить 7989331423"
        )

# ===== TRANSFER =====
@dp.message(lambda m: m.text and m.text.lower().startswith("п "))
async def transfer_cmd(message: Message):

    try:

        parts = message.text.split()

        amount = int(parts[1])

        sender_id = message.from_user.id

        if amount <= 0:
            return

        balance = await get_balance(sender_id)

        if balance < amount:

            return await message.answer(
                "❌ Недостаточно WIN"
            )

        if len(parts) >= 3:

            target_id = int(parts[2])

        else:

            if not message.reply_to_message:

                return await message.answer(
                    "❌ Ответьте на сообщение или укажите ID"
                )

            target_id = message.reply_to_message.from_user.id

        if sender_id == target_id:

            return await message.answer(
                "❌ Нельзя себе"
            )

        await update_balance(sender_id, -amount)
        await update_balance(target_id, amount)

        await message.answer(
            f"💸 Перевод успешен!\n\n"
            f"💰 {format_money(amount)} WIN"
        )

    except:
        pass

# ===== МИНЫ =====

mines_games = {}

def mines_kb(revealed=None, show=False, game=None):

    if revealed is None:
        revealed = {}

    builder = InlineKeyboardBuilder()

    for i in range(25):

        if show:

            text = "💥" if i in game["mines"] else "💰"

        else:

            text = revealed.get(i, "📦")

        builder.add(
            InlineKeyboardButton(
                text=text,
                callback_data=f"mine_{i}"
            )
        )

    builder.adjust(5)

    # Кнопка забрать
    if not show:

        current = int(
            game["bet"] * (
                1 + game["found"] * MINES_STEP[game["count"]]
            )
        )

        builder.row(
            InlineKeyboardButton(
                text=f"💵 ЗАБРАТЬ ({format_money(current)} WIN)",
                callback_data="mine_take"
            )
        )

    return builder.as_markup()

# ===== START MINES =====
@dp.message(
    lambda m: m.text and (
        m.text.lower().startswith("мины ")
        or m.text.lower().startswith("міни ")
    )
)
async def mines_start(message: Message):

    try:

        bet = int(message.text.split()[1])

        if bet <= 0:
            return

        balance = await get_balance(message.from_user.id)

        if bet > balance:

            return await message.answer(
                "❌ Недостаточно WIN"
            )

        # СРАЗУ снимаем ставку
        await update_balance(
            message.from_user.id,
            -bet
        )

        builder = InlineKeyboardBuilder()

        for bombs in [5, 10, 15]:

            builder.add(
                InlineKeyboardButton(
                    text=f"💣 {bombs} Бомб",
                    callback_data=f"mines_{bet}_{bombs}"
                )
            )

        await message.answer(
            f"💣 МИНЫ\n\n"
            f"💰 Ставка: {format_money(bet)} WIN",
            reply_markup=builder.as_markup()
        )

    except:
        pass

# ===== INIT GAME =====
@dp.callback_query(F.data.startswith("mines_"))
async def mines_init(call: types.CallbackQuery):

    _, bet, count = call.data.split("_")

    bet = int(bet)
    count = int(count)

    mines_games[call.from_user.id] = {

        "bet": bet,
        "count": count,
        "found": 0,

        "mines": random.sample(range(25), count),

        "open": {},

        # защита от дюпа
        "ended": False
    }

    await call.message.edit_text(
        f"💣 ИГРА НАЧАЛАСЬ\n\n"
        f"💰 Ставка: {format_money(bet)} WIN\n"
        f"💣 Бомб: {count}",
        reply_markup=mines_kb(
            game=mines_games[call.from_user.id]
        )
    )

# ===== PLAY =====
@dp.callback_query(F.data.startswith("mine_"))
async def mines_play(call: types.CallbackQuery):

    uid = call.from_user.id

    if uid not in mines_games:
        return

    game = mines_games[uid]

    # защита от повторных нажатий
    if game["ended"]:
        return await call.answer(
            "❌ Игра уже закончена",
            show_alert=True
        )

    # ===== ЗАБРАТЬ =====
    if call.data == "mine_take":

        game["ended"] = True

        win = int(
            game["bet"] * (
                1 + game["found"] * MINES_STEP[game["count"]]
            )
        )

        # выдаём выигрыш ТОЛЬКО ОДИН РАЗ
        await update_balance(uid, win)

        await call.message.edit_text(
            f"💰 ВЫ ЗАБРАЛИ\n\n"
            f"💵 +{format_money(win)} WIN",
            reply_markup=mines_kb(
                game["open"],
                True,
                game
            )
        )

        del mines_games[uid]

        return

    # ===== ОТКРЫТИЕ =====
    idx = int(call.data.split("_")[1])

    # если клетка уже открыта
    if idx in game["open"]:

        return await call.answer(
            "📦 Эта клетка уже открыта"
        )

    # ===== ПРОИГРЫШ =====
    if idx in game["mines"]:

        game["ended"] = True

        await call.message.edit_text(
            f"💥 ВЫ ПРОИГРАЛИ\n\n"
            f"💸 Потеряно: {format_money(game['bet'])} WIN",
            reply_markup=mines_kb(
                game["open"],
                True,
                game
            )
        )

        del mines_games[uid]

        return

    # ===== ЧИСТО =====
    game["found"] += 1

    game["open"][idx] = "💰"

    mult = 1 + (
        game["found"] *
        MINES_STEP[game["count"]]
    )

    current = int(game["bet"] * mult)

    await call.message.edit_text(
        f"💎 ЧИСТО\n\n"
        f"📈 Множитель: x{mult:.2f}\n"
        f"💰 Возможный выигрыш:\n"
        f"{format_money(current)} WIN",
        reply_markup=mines_kb(
            game["open"],
            False,
            game
        )
    )
# ===== BM =====
def bm_kb(current):

    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="📈 БОЛЬШЕ",
            callback_data="bm_more"
        ),

        InlineKeyboardButton(
            text="📉 МЕНЬШЕ",
            callback_data="bm_less"
        )
    )

    builder.row(
        InlineKeyboardButton(
            text=f"💵 ЗАБРАТЬ ({format_money(current)} WIN)",
            callback_data="bm_take"
        )
    )

    return builder.as_markup()

@dp.message(F.text.lower().startswith("бм "))
async def bm_start(message: Message):

    try:

        bet = int(message.text.split()[1])

        balance = await get_balance(message.from_user.id)

        if bet > balance:

            return await message.answer(
                "❌ Недостаточно WIN"
            )

        start = random.randint(1, 13)

        bm_games[message.from_user.id] = {
            "number": start,
            "bet": bet,
            "win": bet
        }

        await message.answer(
            f"🎲 Число: {start}\n\n"
            f"💵 Ставка: {format_money(bet)} WIN",
            reply_markup=bm_kb(bet)
        )

    except:
        pass

@dp.callback_query(F.data.startswith("bm_"))
async def bm_play(call: types.CallbackQuery):

    uid = call.from_user.id

    if uid not in bm_games:
        return

    game = bm_games[uid]

    if call.data == "bm_take":

        await update_balance(uid, game["win"])

        await call.message.edit_text(
            f"💰 Вы забрали:\n\n"
            f"{format_money(game['win'])} WIN"
        )

        del bm_games[uid]

        return

    old = game["number"]
    new = random.randint(1, 13)

    win = False

    if call.data == "bm_more" and new > old:
        win = True

    if call.data == "bm_less" and new < old:
        win = True

    if win:

        game["number"] = new
        game["win"] = int(game["win"] * 1.85)

        await call.message.edit_text(
            f"🎲 Число: {new}\n\n"
            f"💰 Возможный выигрыш:\n"
            f"{format_money(game['win'])} WIN",
            reply_markup=bm_kb(game["win"])
        )

    else:

        await update_balance(uid, -game["bet"])

        await call.message.edit_text(
            f"💀 ПРОИГРЫШ\n\n"
            f"🎲 Было: {old}\n"
            f"🎲 Стало: {new}\n\n"
            f"💸 -{format_money(game['bet'])} WIN"
        )

        del bm_games[uid]

# ===== BLACKJACK =====
def blackjack_total(cards):

    total = sum(cards)

    aces = cards.count(11)

    while total > 21 and aces:
        total -= 10
        aces -= 1

    return total

def blackjack_kb():

    builder = InlineKeyboardBuilder()

    builder.row(
        InlineKeyboardButton(
            text="➕ ВЗЯТЬ",
            callback_data="bj_hit"
        ),

        InlineKeyboardButton(
            text="✋ СТОП",
            callback_data="bj_stop"
        )
    )

    return builder.as_markup()

@dp.message(F.text.lower().startswith("блекджек "))
async def blackjack_start(message: Message):

    try:

        bet = int(message.text.split()[1])

        balance = await get_balance(message.from_user.id)

        if bet > balance:

            return await message.answer(
                "❌ Недостаточно WIN"
            )

        cards = [2,3,4,5,6,7,8,9,10,10,10,10,11]

        player = [
            random.choice(cards),
            random.choice(cards)
        ]

        dealer = [
            random.choice(cards),
            random.choice(cards)
        ]

        blackjack_games[message.from_user.id] = {
            "bet": bet,
            "player": player,
            "dealer": dealer
        }

        await message.answer(
            f"🃏 BLACKJACK\n\n"

            f"👤 Ваши карты:\n"
            f"{', '.join(map(str, player))}\n\n"

            f"💰 Ваши очки: {blackjack_total(player)}\n\n"

            f"━━━━━━━━━━\n\n"

            f"🎰 Карты дилера:\n"
            f"{dealer[0]}, ❓",

            reply_markup=blackjack_kb()
        )

    except:
        pass

@dp.callback_query(F.data == "bj_hit")
async def bj_hit(call: types.CallbackQuery):

    uid = call.from_user.id

    if uid not in blackjack_games:
        return

    cards = [2,3,4,5,6,7,8,9,10,10,10,10,11]

    game = blackjack_games[uid]

    game["player"].append(random.choice(cards))

    player_total = blackjack_total(game["player"])

    if player_total > 21:

        await update_balance(uid, -game["bet"])

        await call.message.edit_text(
            f"💥 ПЕРЕБОР\n\n"

            f"👤 Ваши карты:\n"
            f"{', '.join(map(str, game['player']))}\n\n"

            f"💰 Ваши очки: {player_total}\n\n"

            f"💸 -{format_money(game['bet'])} WIN"
        )

        del blackjack_games[uid]

        return

    await call.message.edit_text(
        f"🃏 BLACKJACK\n\n"

        f"👤 Ваши карты:\n"
        f"{', '.join(map(str, game['player']))}\n\n"

        f"💰 Ваши очки: {player_total}\n\n"

        f"━━━━━━━━━━\n\n"

        f"🎰 Карты дилера:\n"
        f"{game['dealer'][0]}, ❓",

        reply_markup=blackjack_kb()
    )

@dp.callback_query(F.data == "bj_stop")
async def bj_stop(call: types.CallbackQuery):

    uid = call.from_user.id

    if uid not in blackjack_games:
        return

    cards = [2,3,4,5,6,7,8,9,10,10,10,10,11]

    game = blackjack_games[uid]

    while blackjack_total(game["dealer"]) < 17:
        game["dealer"].append(random.choice(cards))

    player_total = blackjack_total(game["player"])
    dealer_total = blackjack_total(game["dealer"])

    result = ""

    if dealer_total > 21 or player_total > dealer_total:

        await update_balance(uid, game["bet"])

        result = (
            "🎉 ВЫ ВЫИГРАЛИ\n\n"
            f"💰 +{format_money(game['bet'] * 2)} WIN"
        )

    elif player_total == dealer_total:

        result = "🤝 НИЧЬЯ"

    else:

        await update_balance(uid, -game["bet"])

        result = (
            "💀 ВЫ ПРОИГРАЛИ\n\n"
            f"💸 -{format_money(game['bet'])} WIN"
        )

    await call.message.edit_text(
        f"🃏 BLACKJACK\n\n"

        f"👤 Ваши карты:\n"
        f"{', '.join(map(str, game['player']))}\n\n"

        f"💰 Ваши очки: {player_total}\n\n"

        f"━━━━━━━━━━\n\n"

        f"🎰 Карты дилера:\n"
        f"{', '.join(map(str, game['dealer']))}\n\n"

        f"💰 Очки дилера: {dealer_total}\n\n"

        f"{result}"
    )

    del blackjack_games[uid]

# ===== START =====
async def main():

    await init_db()

    print("✅ BOT STARTED")

    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())