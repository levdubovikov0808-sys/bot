import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    CallbackContext,
    filters
)
import matplotlib.pyplot as plt
import pandas as pd
from io import BytesIO
import json
from datetime import datetime
from typing import Dict, List
import os

# Настройка логгирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Состояния диалога
SELECTING_ACTION, SELECT_EXERCISE, INPUT_SETS, INPUT_WEIGHT, TRACK_WATER = range(5)

# Тексты кнопок
ARMS_BUTTON = "💪 День Рук"
LEGS_BUTTON = "🦵 День Ног"
CORE_BUTTON = "🔥 Пресс+Руки"
ENDURANCE_BUTTON = "🏃‍♂️ Выносливость"
PROGRESS_BUTTON = "📊 Мой прогресс"
ADD_RESULT_BUTTON = "➕ Добавить результат"
FINISH_WORKOUT_BUTTON = "🏁 Тренировка окончена"
WATER_BUTTON = "💧 Добавить воду"
WATER_PROGRESS_BUTTON = "💧 Мой график воды"

# База тренировок
workouts = {
    "arms": {
        "description": "💪 Прокачка бицепса и трицепса",
        "exercises": [
            {"name": "Подъем штанги на бицепс", "sets": 4, "reps": "10-12"},
            {"name": "Подъем гантелей 'молот'", "sets": 3, "reps": "12"},
            {"name": "Подтягивания обратным хватом", "sets": 3, "reps": "8-10"},
            {"name": "Жим узким хватом (трицепс)", "sets": 4, "reps": "10"},
            {"name": "Французский жим лежа", "sets": 3, "reps": "12"},
            {"name": "Разгибания на блоке (канат)", "sets": 3, "reps": "15"}
        ]
    },
    "legs": {
        "description": "🦵 Тренировка ног",
        "exercises": [
            {"name": "Приседания со штангой", "sets": 4, "reps": "8-10"},
            {"name": "Жим ногами", "sets": 3, "reps": "12"},
            {"name": "Выпады с гантелями", "sets": 3, "reps": "10 (на каждую ногу)"},
            {"name": "Румынская тяга", "sets": 4, "reps": "10"},
            {"name": "Подъем на носки стоя", "sets": 4, "reps": "15-20"}
        ]
    },
    "core": {
        "description": "🔥 Упражнения на пресс",
        "exercises": [
            {"name": "Подъем ног в висе", "sets": 4, "reps": "15-20"},
            {"name": "Скручивания с весом", "sets": 3, "reps": "20"},
            {"name": "Планка", "sets": 3, "reps": "60 сек"},
            {"name": "Боковые скручивания", "sets": 3, "reps": "15 (на каждую сторону)"},
            {"name": "Гиперэкстензия", "sets": 3, "reps": "15"}
        ]
    },
    "legs_day2": {
        "description": "🏃‍♂️ День: Ноги + Выносливость",
        "exercises": [
            {"name": "Фронтальные приседания", "sets": 4, "reps": "8"},
            {"name": "Болгарские выпады", "sets": 3, "reps": "10"},
            {"name": "Сгибания ног лежа", "sets": 3, "reps": "12"},
            {"name": "Ягодичный мостик со штангой", "sets": 4, "reps": "12"},
            {"name": "Берпи", "sets": 3, "reps": "15"},
            {"name": "Прыжки на скакалке", "sets": 1, "reps": "5 мин"}
        ]
    }
}


def load_user_data() -> Dict:
    """Загружает данные пользователей из JSON файла"""
    if not os.path.exists("user_data.json"):
        with open("user_data.json", "w", encoding="utf-8") as f:
            json.dump({}, f)

    try:
        with open("user_data.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Ошибка загрузки данных: {e}")
        return {}


def save_user_data(data: Dict) -> None:
    """Сохраняет данные пользователей в JSON файл"""
    try:
        with open("user_data.json", "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        logger.error(f"Ошибка сохранения данных: {e}")


def get_main_keyboard():
    """Основная клавиатура меню"""
    return ReplyKeyboardMarkup([
        [ARMS_BUTTON, LEGS_BUTTON],
        [CORE_BUTTON, ENDURANCE_BUTTON],
        [PROGRESS_BUTTON, ADD_RESULT_BUTTON],
        [WATER_BUTTON, WATER_PROGRESS_BUTTON],
        [FINISH_WORKOUT_BUTTON]
    ], resize_keyboard=True)


def get_exercises_keyboard() -> List[List[KeyboardButton]]:
    """Клавиатура с упражнениями"""
    exercises = {ex["name"] for w in workouts.values() for ex in w["exercises"]}
    keyboard = []
    row = []
    for i, ex in enumerate(sorted(exercises), 1):
        row.append(KeyboardButton(ex))
        if i % 2 == 0:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    keyboard.append([KeyboardButton("✏️ Ввести свое упражнение")])
    keyboard.append([KeyboardButton("Отмена")])
    return keyboard


async def start(update: Update, context: CallbackContext) -> int:
    """Обработчик команды /start"""
    await update.message.reply_text(
        "🏋️‍♂️ Добро пожаловать в FitnessBot!\nВыберите действие:",
        reply_markup=get_main_keyboard()
    )
    return SELECTING_ACTION


async def show_workout(update: Update, context: CallbackContext) -> int:
    """Показывает выбранную тренировку"""
    text = update.message.text.strip()
    workout_map = {
        ARMS_BUTTON: "arms",
        LEGS_BUTTON: "legs",
        CORE_BUTTON: "core",
        ENDURANCE_BUTTON: "legs_day2"
    }

    if text not in workout_map:
        await update.message.reply_text("Неизвестная тренировка.", reply_markup=get_main_keyboard())
        return SELECTING_ACTION

    workout = workouts[workout_map[text]]
    reply = f"{workout['description']}:\n\n"
    for i, ex in enumerate(workout["exercises"], 1):
        reply += f"{i}. {ex['name']} – {ex['sets']}х{ex['reps']}\n"
    reply += "\nНажмите '🏁 Тренировка окончена' по завершении"
    await update.message.reply_text(reply, reply_markup=get_main_keyboard())
    return SELECTING_ACTION


async def workout_completed(update: Update, context: CallbackContext) -> int:
    """Обработчик завершения тренировки"""
    await update.message.reply_text(
        "🏆 Тренировка завершена! Хотите добавить результат?",
        reply_markup=ReplyKeyboardMarkup([[ADD_RESULT_BUTTON], ["В главное меню"]], resize_keyboard=True)
    )
    return SELECTING_ACTION


async def show_progress(update: Update, context: CallbackContext) -> int:
    """Показывает график прогресса по весам"""
    chart = generate_progress_chart(update.effective_user.id)
    if chart:
        await update.message.reply_photo(
            photo=chart,
            caption="📈 Ваш прогресс в тренировках",
            reply_markup=get_main_keyboard()
        )
    else:
        await update.message.reply_text(
            "Нет данных для отображения прогресса.",
            reply_markup=get_main_keyboard()
        )
    return SELECTING_ACTION


def generate_progress_chart(user_id: str) -> BytesIO:
    """Генерирует график прогресса по весам"""
    user_data = load_user_data()
    if str(user_id) not in user_data or not user_data[str(user_id)].get("workouts"):
        return None

    try:
        df = pd.DataFrame(user_data[str(user_id)]["workouts"])
        df['date'] = pd.to_datetime(df['date'], format="%d.%m.%Y %H:%M")
        df['weight'] = df['weight'].str.replace(' кг', '').astype(float)

        plt.figure(figsize=(12, 6))
        for exercise in df['exercise'].unique():
            ex_data = df[df['exercise'] == exercise]
            plt.plot(ex_data['date'], ex_data['weight'], 'o-', label=exercise)

        plt.title("Прогресс по весам")
        plt.xlabel("Дата")
        plt.ylabel("Вес (кг)")
        plt.legend()
        plt.grid()
        plt.xticks(rotation=45)
        plt.tight_layout()

        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=100)
        buf.seek(0)
        plt.close()
        return buf
    except Exception as e:
        logger.error(f"Ошибка генерации графика: {e}")
        return None


async def add_result_start(update: Update, context: CallbackContext) -> int:
    """Начало добавления результата тренировки"""
    await update.message.reply_text(
        "Выберите упражнение:",
        reply_markup=ReplyKeyboardMarkup(get_exercises_keyboard(), resize_keyboard=True)
    )
    return SELECT_EXERCISE


async def select_exercise(update: Update, context: CallbackContext) -> int:
    """Выбор упражнения для добавления результата"""
    ex = update.message.text.strip()
    if ex == "Отмена":
        return await cancel(update, context)
    if ex == "✏️ Ввести свое упражнение":
        await update.message.reply_text(
            "Введите название упражнения:",
            reply_markup=ReplyKeyboardMarkup([["Отмена"]], resize_keyboard=True)
        )
        return SELECT_EXERCISE

    context.user_data["exercise_data"] = {"exercise": ex}
    await update.message.reply_text(
        f"Сколько подходов для {ex}?",
        reply_markup=ReplyKeyboardMarkup([["Отмена"]], resize_keyboard=True)
    )
    return INPUT_SETS


async def input_sets(update: Update, context: CallbackContext) -> int:
    """Ввод количества подходов"""
    if update.message.text.lower() == "отмена":
        return await cancel(update, context)

    try:
        sets = int(update.message.text)
        if sets <= 0:
            raise ValueError
        context.user_data["exercise_data"]["sets"] = sets
        ex = context.user_data["exercise_data"]["exercise"]
        await update.message.reply_text(
            f"Вес (в кг) для {ex}:",
            reply_markup=ReplyKeyboardMarkup([["Отмена"]], resize_keyboard=True)
        )
        return INPUT_WEIGHT
    except ValueError:
        await update.message.reply_text("Введите целое число больше 0.")
        return INPUT_SETS


async def input_weight(update: Update, context: CallbackContext) -> int:
    """Ввод веса для упражнения"""
    if update.message.text.lower() == "отмена":
        return await cancel(update, context)

    try:
        weight = float(update.message.text)
        if weight <= 0:
            raise ValueError

        ex_data = context.user_data["exercise_data"]
        user_id = str(update.effective_user.id)
        data = load_user_data()

        if "workouts" not in data.setdefault(user_id, {}):
            data[user_id]["workouts"] = []

        data[user_id]["workouts"].append({
            "date": datetime.now().strftime("%d.%m.%Y %H:%M"),
            "exercise": ex_data["exercise"],
            "sets": ex_data["sets"],
            "reps": "-",
            "weight": f"{weight} кг"
        })

        save_user_data(data)
        del context.user_data["exercise_data"]

        await update.message.reply_text(
            f"✅ Сохранено!\n{ex_data['exercise']}: {ex_data['sets']}x{weight} кг",
            reply_markup=get_main_keyboard()
        )
        return SELECTING_ACTION
    except ValueError:
        await update.message.reply_text("Введите корректный вес (например: 42.5).")
        return INPUT_WEIGHT


async def track_water_start(update: Update, context: CallbackContext) -> int:
    """Начало трекинга воды"""
    await update.message.reply_text(
        "Сколько мл воды вы выпили?",
        reply_markup=ReplyKeyboardMarkup([["Отмена"]], resize_keyboard=True)
    )
    return TRACK_WATER


async def save_water(update: Update, context: CallbackContext) -> int:
    """Сохранение данных о воде"""
    try:
        ml = int(update.message.text)
        if ml <= 0:
            raise ValueError

        user_id = str(update.effective_user.id)
        data = load_user_data()

        if "water" not in data.setdefault(user_id, {}):
            data[user_id]["water"] = []

        data[user_id]["water"].append({
            "date": datetime.now().strftime("%d.%m.%Y %H:%M"),
            "ml": ml
        })

        save_user_data(data)

        await update.message.reply_text(
            f"✅ +{ml} мл воды сохранено!",
            reply_markup=get_main_keyboard()
        )
        return SELECTING_ACTION
    except ValueError:
        await update.message.reply_text("Введите целое число больше 0.")
        return TRACK_WATER


async def show_water_progress(update: Update, context: CallbackContext) -> int:
    """Показывает график потребления воды"""
    chart = generate_water_chart(update.effective_user.id)
    if chart:
        await update.message.reply_photo(
            photo=chart,
            caption="💧 Ваше потребление воды",
            reply_markup=get_main_keyboard()
        )
    else:
        await update.message.reply_text(
            "Нет данных о потреблении воды.",
            reply_markup=get_main_keyboard()
        )
    return SELECTING_ACTION


def generate_water_chart(user_id: str) -> BytesIO:
    """Генерирует график потребления воды"""
    user_data = load_user_data()
    if str(user_id) not in user_data or not user_data[str(user_id)].get("water"):
        return None

    try:
        df = pd.DataFrame(user_data[str(user_id)]["water"])
        df['date'] = pd.to_datetime(df['date'], format="%d.%m.%Y %H:%M")
        df = df.groupby(df['date'].dt.date)['ml'].sum().reset_index()

        plt.figure(figsize=(10, 5))
        plt.bar(df['date'].astype(str), df['ml'], color='#1E90FF')
        plt.title("Потребление воды")
        plt.xlabel("Дата")
        plt.ylabel("Мл")
        plt.grid(axis='y')
        plt.tight_layout()

        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=100)
        buf.seek(0)
        plt.close()
        return buf
    except Exception as e:
        logger.error(f"Ошибка генерации графика воды: {e}")
        return None


async def cancel(update: Update, context: CallbackContext) -> int:
    """Отмена текущего действия"""
    context.user_data.clear()
    await update.message.reply_text(
        "Действие отменено.",
        reply_markup=get_main_keyboard()
    )
    return SELECTING_ACTION


async def help_command(update: Update, context: CallbackContext) -> None:
    """Обработчик команды /help"""
    await update.message.reply_text(
        "🏋️‍♂️ FitnessBot - ваш персональный тренер\n\n"
        "Основные команды:\n"
        "/start - начать работу\n"
        "/help - показать справку\n"
        "/cancel - отменить текущее действие\n\n"
        "Используйте кнопки для навигации.",
        reply_markup=get_main_keyboard()
    )


def main() -> None:
    """Запуск бота"""
    application = Application.builder().token("7148071242:AAHgRXEBN7OQnDFv7-K9jSgrVBbDxvZ-xvE").build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            SELECTING_ACTION: [
                MessageHandler(filters.Regex(f'^{PROGRESS_BUTTON}$'), show_progress),
                MessageHandler(filters.Regex(f'^{ADD_RESULT_BUTTON}$'), add_result_start),
                MessageHandler(filters.Regex(f'^{WATER_BUTTON}$'), track_water_start),
                MessageHandler(filters.Regex(f'^{WATER_PROGRESS_BUTTON}$'), show_water_progress),
                MessageHandler(filters.Regex(f'^{FINISH_WORKOUT_BUTTON}$'), workout_completed),
                MessageHandler(filters.Regex("^В главное меню$"), start),
                MessageHandler(
                    filters.Regex(f'^({"|".join([ARMS_BUTTON, LEGS_BUTTON, CORE_BUTTON, ENDURANCE_BUTTON])})$'),
                    show_workout),
            ],
            SELECT_EXERCISE: [MessageHandler(filters.TEXT & ~filters.COMMAND, select_exercise)],
            INPUT_SETS: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_sets)],
            INPUT_WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, input_weight)],
            TRACK_WATER: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_water)],
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CommandHandler("help", help_command)
        ],
    )

    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("help", help_command))

    logger.info("Бот запущен в режиме polling...")
    application.run_polling()


if __name__ == "__main__":
    main()