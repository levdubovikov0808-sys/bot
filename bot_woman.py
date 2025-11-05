import logging
import json
import os
import re
import matplotlib.pyplot as plt
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)
from random import choice
from datetime import datetime

# Настройка логирования
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Определение кнопок
UPPER_BODY_BUTTON = "💪 Верх тела"
LOWER_BODY_BUTTON = "🦵 Низ тела"
CORE_BUTTON = "🔥 Пресс+Корсет"
FLEXIBILITY_BUTTON = "🤸‍♀️ Растяжка"
PROGRESS_BUTTON = "📈 Прогресс"
ADD_RESULT_BUTTON = "➕ Добавить результат"
MOTIVATION_BUTTON = "💖 Мотивация"
FINISH_WORKOUT_BUTTON = "🏁 Завершить"
ADD_WORKOUT_BUTTON = "✨ Добавить тренировку"
ADD_EXERCISE_BUTTON = "🏋️‍♀️ Добавить упражнение"

# Кнопки главного меню
main_menu_keyboard = [
    [UPPER_BODY_BUTTON, LOWER_BODY_BUTTON],
    [CORE_BUTTON, FLEXIBILITY_BUTTON],
    [PROGRESS_BUTTON, ADD_RESULT_BUTTON],
    [MOTIVATION_BUTTON, FINISH_WORKOUT_BUTTON],
    [ADD_WORKOUT_BUTTON, ADD_EXERCISE_BUTTON]
]

# Константы состояний
(
    SELECTING_ACTION, SELECT_EXERCISE, INPUT_SETS, INPUT_WEIGHT,
    ADDING_WORKOUT, ADDING_EXERCISE, INPUT_EXERCISE_NAME,
    INPUT_WORKOUT_NAME, INPUT_WORKOUT_EXERCISES
) = range(9)


def load_user_data(user_id: str) -> list:
    """Загружает данные пользователя из файла"""
    filename = f"{user_id}_data.json"
    if not os.path.exists(filename):
        return []

    try:
        with open(filename, "r", encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Error loading user data: {e}")
        return []


def save_user_data(user_id: str, data: list) -> bool:
    """Сохраняет данные пользователя в файл"""
    filename = f"{user_id}_data.json"
    try:
        with open(filename, "w", encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except IOError as e:
        logger.error(f"Error saving user data: {e}")
        return False


def load_custom_workouts(user_id: str) -> dict:
    filename = f"{user_id}_workouts.json"
    if not os.path.exists(filename):
        return {}

    try:
        with open(filename, "r", encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Error loading workouts: {e}")
        return {}


def save_custom_workouts(user_id: str, workouts: dict) -> bool:
    filename = f"{user_id}_workouts.json"
    try:
        with open(filename, "w", encoding='utf-8') as f:
            json.dump(workouts, f, ensure_ascii=False, indent=2)
        return True
    except IOError as e:
        logger.error(f"Error saving workouts: {e}")
        return False


def load_custom_exercises(user_id: str) -> dict:
    filename = f"{user_id}_exercises.json"
    if not os.path.exists(filename):
        return {
            UPPER_BODY_BUTTON: ["Отжимания", "Жим гантелей", "Тяга к подбородку"],
            LOWER_BODY_BUTTON: ["Приседания", "Выпады", "Ягодичный мостик"],
            CORE_BUTTON: ["Планка", "Подъём ног", "Скручивания", "Боковая планка"],
            FLEXIBILITY_BUTTON: ["Наклоны", "Растяжка спины", "Бабочка"]
        }

    try:
        with open(filename, "r", encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        logger.error(f"Error loading exercises: {e}")
        return {}


def save_custom_exercises(user_id: str, exercises: dict) -> bool:
    filename = f"{user_id}_exercises.json"
    try:
        with open(filename, "w", encoding='utf-8') as f:
            json.dump(exercises, f, ensure_ascii=False, indent=2)
        return True
    except IOError as e:
        logger.error(f"Error saving exercises: {e}")
        return False


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обработчик команды /start"""
    reply_markup = ReplyKeyboardMarkup(main_menu_keyboard, resize_keyboard=True)
    await update.message.reply_text(
        "Привет, красавица! 💕\nЯ твой персональный помощник для тренировок. Выбери действие:",
        reply_markup=reply_markup
    )
    return SELECTING_ACTION


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработчик команды /help"""
    await update.message.reply_text(
        "Я помогу тебе следить за твоими тренировками и прогрессом! 💪\n\n"
        "Как мной пользоваться:\n"
        "1. Выбери группу мышц для тренировки\n"
        "2. Добавляй результаты выполнения упражнений\n"
        "3. Следи за своим прогрессом на красивых графиках\n\n"
        "Ты сильная, красивая и у тебя всё получится! ✨"
    )


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отмена текущего действия"""
    await update.message.reply_text("Отменили действие. Возвращаемся в главное меню 💫")
    return await start(update, context)


async def show_workout(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Показывает упражнения для выбранной группы мышц"""
    category = update.message.text
    user_id = str(update.effective_user.id)

    exercises = load_custom_exercises(user_id).get(category, [])

    if not exercises:
        await update.message.reply_text("Ой, что-то пошло не так...")
        return SELECTING_ACTION

    context.user_data["category"] = category
    reply_markup = ReplyKeyboardMarkup([exercises + ["В главное меню"]], resize_keyboard=True)
    await update.message.reply_text(
        f"Выбирай упражнение для {category.lower()}:",
        reply_markup=reply_markup
    )
    return SELECT_EXERCISE


async def select_exercise(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает выбор упражнения"""
    exercise = update.message.text

    if exercise == "В главное меню":
        return await start(update, context)

    context.user_data["exercise"] = exercise

    if "category" not in context.user_data:
        user_id = str(update.effective_user.id)
        data = load_user_data(user_id)
        for d in data:
            if d["exercise"] == exercise:
                context.user_data["category"] = d["category"]
                break

    await update.message.reply_text(
        f"Сколько подходов ты сделала в упражнении '{exercise}'? 💪"
    )
    return INPUT_SETS


async def input_sets(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает ввод количества подходов"""
    sets = update.message.text
    if not sets.isdigit() or int(sets) <= 0:
        await update.message.reply_text("Милая, введи положительное число подходов 😊")
        return INPUT_SETS

    context.user_data["sets"] = int(sets)
    await update.message.reply_text(
        "Какой вес ты использовала (в кг)? Введи 0, если без веса."
    )
    return INPUT_WEIGHT


async def input_weight(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает ввод веса и сохраняет результат"""
    weight_str = update.message.text
    try:
        weight = float(weight_str)
        if weight < 0:
            raise ValueError("Вес не может быть отрицательным")
    except ValueError:
        await update.message.reply_text("Пожалуйста, введи корректный вес (число, большее или равное 0).")
        return INPUT_WEIGHT

    user_id = str(update.effective_user.id)
    exercise_data = {
        "category": context.user_data["category"],
        "exercise": context.user_data["exercise"],
        "sets": context.user_data["sets"],
        "weight": weight,
        "date": datetime.now().isoformat()
    }

    data = load_user_data(user_id)
    data.append(exercise_data)

    if save_user_data(user_id, data):
        await update.message.reply_text(
            f"✨ Отлично! Результат сохранён:\n"
            f"Упражнение: {exercise_data['exercise']}\n"
            f"Подходы: {exercise_data['sets']}\n"
            f"Вес: {exercise_data['weight']} кг\n\n"
            f"Ты молодец! 💕"
        )
    else:
        await update.message.reply_text("Ой, что-то пошло не так при сохранении...")

    return await start(update, context)


async def show_progress(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Показывает графики прогресса по упражнениям"""
    user_id = str(update.effective_user.id)
    data = load_user_data(user_id)

    if not data:
        await update.message.reply_text("У тебя ещё нет сохранённых данных для анализа прогресса, дорогая.")
        return SELECTING_ACTION

    exercises = {d["exercise"] for d in data}
    has_plots = False

    for exercise in sorted(exercises):
        exercise_data = sorted(
            [d for d in data if d["exercise"] == exercise],
            key=lambda x: x["date"]
        )

        if len(exercise_data) < 2:
            continue

        dates = [datetime.fromisoformat(d["date"]).strftime('%d.%m.%Y') for d in exercise_data]
        weights = [d["weight"] for d in exercise_data]

        plt.figure(figsize=(10, 5))
        plt.plot(dates, weights, 'o-', linewidth=2, markersize=8, color='deeppink')
        plt.title(f"Твой прогресс: {exercise}", pad=20, fontsize=14, color='darkviolet')
        plt.xlabel("Дата тренировки", labelpad=10)
        plt.ylabel("Вес, кг", labelpad=10)
        plt.xticks(rotation=45)
        plt.grid(True, linestyle='--', alpha=0.7)
        plt.tight_layout()

        filename = f"{user_id}_{exercise.replace(' ', '_')}.png"
        plt.savefig(filename, dpi=100)
        plt.close()

        with open(filename, "rb") as img:
            await update.message.reply_photo(
                photo=img,
                caption=f"Твой прогресс по упражнению: {exercise} 🌸"
            )
        os.remove(filename)
        has_plots = True

    if not has_plots:
        await update.message.reply_text(
            "Пока недостаточно данных для графиков, солнышко. "
            "Нужно минимум 2 тренировки по одному упражнению."
        )

    return SELECTING_ACTION


async def send_motivation(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Отправляет мотивационное сообщение для девушки"""
    quotes = [
        "Ты прекрасна в каждом своём проявлении! 💖",
        "Сила - это не только мышцы, это характер! И у тебя его хоть отбавляй! 💪",
        "Каждая капля пота - это шаг к лучшей версии себя! ✨",
        "Ты не тренируешься, ты создаёшь шедевр! 🎨",
        "Сегодняшний дискомфорт - завтрашняя гордость за себя! 🌸",
        "Ты сильнее, чем думаешь, красивее, чем представляешь, и умнее, чем веришь! 💫",
        "Не сравнивай себя с другими. Ты уникальна и неповторима! 🌺",
        "Тренировка - это праздник силы, который ты даришь своему телу! 💃",
        "Запомни: красивое тело - это побочный эффект сильного характера! 💕",
        "Ты не просто занимаешься спортом, ты строишь свою уверенность! 👑",
        "Каждое повторение - это инвестиция в твоё здоровье и красоту! 💎",
        "Ты восхитительна! И с каждой тренировкой становишься ещё лучше! 🌟"
    ]
    await update.message.reply_text(choice(quotes))
    return SELECTING_ACTION


async def workout_completed(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Завершает тренировку с женственным подходом"""
    await update.message.reply_text(
        "🌟 Ты потрясающая! Тренировка завершена! 🌟\n\n"
        "Не забывай о восстановлении:\n"
        "💧 Пей больше воды\n"
        "🍓 Питайся полезной едой\n"
        "🛌 Спи не менее 7-8 часов\n"
        "💆‍♀️ Сделай растяжку или массаж\n\n"
        "Завтра ты будешь ещё прекраснее! 💕"
    )
    return SELECTING_ACTION


async def add_custom_workout_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начинает процесс добавления своей тренировки"""
    await update.message.reply_text(
        "Как хочешь назвать свою тренировку? 💭\n"
        "(Например: 'Утренний комплекс', 'Разминка перед бегом')"
    )
    return INPUT_WORKOUT_NAME


async def input_workout_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает ввод названия тренировки"""
    workout_name = update.message.text
    context.user_data["workout_name"] = workout_name

    await update.message.reply_text(
        f"Отлично! Теперь введи упражнения для тренировки '{workout_name}', разделяя их запятой.\n"
        "Например: Планка, Приседания, Отжимания"
    )
    return INPUT_WORKOUT_EXERCISES


async def input_workout_exercises(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает ввод упражнений для тренировки"""
    exercises_text = update.message.text
    exercises = [ex.strip() for ex in exercises_text.split(",") if ex.strip()]

    user_id = str(update.effective_user.id)
    workouts = load_custom_workouts(user_id)
    workouts[context.user_data["workout_name"]] = exercises

    if save_custom_workouts(user_id, workouts):
        await update.message.reply_text(
            f"✨ Тренировка '{context.user_data['workout_name']}' успешно сохранена!\n"
            f"Упражнения: {', '.join(exercises)}"
        )
    else:
        await update.message.reply_text("Ой, не удалось сохранить тренировку...")

    return await start(update, context)


async def add_custom_exercise_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Начинает процесс добавления своего упражнения"""
    reply_markup = ReplyKeyboardMarkup(
        [[UPPER_BODY_BUTTON, LOWER_BODY_BUTTON],
         [CORE_BUTTON, FLEXIBILITY_BUTTON],
         ["В главное меню"]],
        resize_keyboard=True
    )

    await update.message.reply_text(
        "К какой группе относится твоё новое упражнение?",
        reply_markup=reply_markup
    )
    return ADDING_EXERCISE


async def select_category_for_new_exercise(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает выбор категории для нового упражнения"""
    category = update.message.text

    if category == "В главное меню":
        return await start(update, context)

    if category not in [UPPER_BODY_BUTTON, LOWER_BODY_BUTTON, CORE_BUTTON, FLEXIBILITY_BUTTON]:
        await update.message.reply_text("Пожалуйста, выбери одну из предложенных категорий.")
        return ADDING_EXERCISE

    context.user_data["exercise_category"] = category
    await update.message.reply_text(
        "Как называется твоё новое упражнение? 💭"
    )
    return INPUT_EXERCISE_NAME


async def input_exercise_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Обрабатывает ввод названия нового упражнения"""
    exercise_name = update.message.text
    category = context.user_data["exercise_category"]

    user_id = str(update.effective_user.id)
    exercises = load_custom_exercises(user_id)

    if category not in exercises:
        exercises[category] = []

    if exercise_name in exercises[category]:
        await update.message.reply_text("Такое упражнение уже есть в этой категории!")
        return await start(update, context)

    exercises[category].append(exercise_name)

    if save_custom_exercises(user_id, exercises):
        await update.message.reply_text(
            f"✨ Упражнение '{exercise_name}' успешно добавлено в категорию '{category}'!"
        )
    else:
        await update.message.reply_text("Ой, не удалось сохранить упражнение...")

    return await start(update, context)


def main() -> None:
    """Запуск бота"""
    TOKEN = "7084368010:AAFkU0TlYqaaKcI8H--qkQG4IYlQWB8Bhos"

    application = ApplicationBuilder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            SELECTING_ACTION: [
                MessageHandler(filters.Regex(f"^{re.escape(UPPER_BODY_BUTTON)}$"), show_workout),
                MessageHandler(filters.Regex(f"^{re.escape(LOWER_BODY_BUTTON)}$"), show_workout),
                MessageHandler(filters.Regex(f"^{re.escape(CORE_BUTTON)}$"), show_workout),
                MessageHandler(filters.Regex(f"^{re.escape(FLEXIBILITY_BUTTON)}$"), show_workout),
                MessageHandler(filters.Regex(f"^{re.escape(PROGRESS_BUTTON)}$"), show_progress),
                MessageHandler(filters.Regex(f"^{re.escape(ADD_RESULT_BUTTON)}$"), add_result_start),
                MessageHandler(filters.Regex(f"^{re.escape(MOTIVATION_BUTTON)}$"), send_motivation),
                MessageHandler(filters.Regex(f"^{re.escape(FINISH_WORKOUT_BUTTON)}$"), workout_completed),
                MessageHandler(filters.Regex(f"^{re.escape(ADD_WORKOUT_BUTTON)}$"), add_custom_workout_start),
                MessageHandler(filters.Regex(f"^{re.escape(ADD_EXERCISE_BUTTON)}$"), add_custom_exercise_start),
                MessageHandler(filters.Regex("^В главное меню$"), start),
            ],
            SELECT_EXERCISE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, select_exercise)
            ],
            INPUT_SETS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, input_sets)
            ],
            INPUT_WEIGHT: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, input_weight)
            ],
            INPUT_WORKOUT_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, input_workout_name)
            ],
            INPUT_WORKOUT_EXERCISES: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, input_workout_exercises)
            ],
            ADDING_EXERCISE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, select_category_for_new_exercise)
            ],
            INPUT_EXERCISE_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, input_exercise_name)
            ]
        },
        fallbacks=[
            CommandHandler("cancel", cancel),
            CommandHandler("help", help_command),
        ],
    )

    application.add_handler(conv_handler)
    logger.info("Бот запущен...")
    application.run_polling()


if __name__ == "__main__":
    main()