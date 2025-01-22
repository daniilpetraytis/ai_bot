from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from states import ProfileSetup
import requests

router = Router()

users = {}

# Обработчик команды /start
@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.reply("Добро пожаловать! Я ваш бот.\nВведите /help для списка команд.")

# Обработчик команды /help
@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.reply(
        "Доступные команды:\n"
        "/start - Начало работы\n"
        "/set_profile - Настройка вашего профиля\n"
        "/log_water <количество> - Зарегистрировать количество выпитой воды в мл\n"
        "/log_food <название продукта> - Зарегистрировать потребление еды (пример: /log_food банан)\n"
        "/log_workout <тип тренировки> <время (мин)> - Зарегистрировать тренировку (пример: /log_workout бег 30)\n"
        "/check_progress - Проверить ваш прогресс по воде и калориям\n"
        "/help - Показать это сообщение"
    )


# Обработчик команды /set_profile
@router.message(Command("set_profile"))
async def cmd_set_profile(message: Message, state: FSMContext):
    await message.answer("Введите ваш вес (в кг):")
    await state.set_state(ProfileSetup.weight)

@router.message(ProfileSetup.weight)
async def process_weight(message: Message, state: FSMContext):
    users[message.from_user.id] = {"weight": float(message.text)}
    await state.update_data(weight=message.text)
    await message.answer("Введите ваш рост (в см):")
    await state.set_state(ProfileSetup.height)

@router.message(ProfileSetup.height)
async def process_height(message: Message, state: FSMContext):
    users[message.from_user.id]["height"] = float(message.text)
    await state.update_data(height=message.text)
    await message.answer("Введите ваш возраст:")
    await state.set_state(ProfileSetup.age)

@router.message(ProfileSetup.age)
async def process_age(message: Message, state: FSMContext):
    users[message.from_user.id]["age"] = int(message.text)
    await state.update_data(age=message.text)
    await message.answer("Введите уровень вашей активности (минуты в день):")
    await state.set_state(ProfileSetup.activity)

@router.message(ProfileSetup.activity)
async def process_activity(message: Message, state: FSMContext):
    users[message.from_user.id]["activity"] = int(message.text)
    await state.update_data(activity=message.text)
    await message.answer("Введите ваш город:")
    await state.set_state(ProfileSetup.city)

@router.message(ProfileSetup.city)
async def process_city(message: Message, state: FSMContext):
    users[message.from_user.id]["city"] = message.text
    await state.update_data(city=message.text)
    await message.answer("Введите вашу цель по калориям (по умолчанию рассчитывается автоматически):")
    await state.set_state(ProfileSetup.calorie_goal)

@router.message(ProfileSetup.calorie_goal)
async def process_calorie_goal(message: Message, state: FSMContext):
    users[message.from_user.id]["calorie_goal"] = int(message.text)
    await state.clear()
    await message.answer("Профиль успешно настроен!")
    print(users)  # Для отладки


async def calculate_water(user_data: dict, temperature: float) -> int:
    base_water = user_data['weight'] * 30
    activity_bonus = 500 * (user_data['activity'] // 30)
    temperature_bonus = 500 if temperature > 25 else 0
    return base_water + activity_bonus + temperature_bonus


async def calculate_calorie(user_data: dict) -> int:
    base_calories = 10 * user_data['weight'] + 6.25 * user_data['height'] - 5 * user_data['age']
    activity_bonus = 200 + (user_data['activity'] // 30) * 50
    return base_calories + activity_bonus


@router.message(Command("log_water"))
async def log_water(message: Message, state: FSMContext):
    command_parts = message.text.split(maxsplit=1)
    
    if len(command_parts) < 2:
        await message.answer("Пожалуйста, укажите количество воды в миллилитрах, например, /log_water 250.")
        return

    try:
        amount = int(command_parts[1])
        user_id = message.from_user.id

        if user_id in users:
            users[user_id]['logged_water'] = users[user_id].get('logged_water', 0) + amount
            water_goal = await calculate_water(users[user_id], 25)  # Пример температуры
            remaining = water_goal - users[user_id]['logged_water']
            await message.answer(f"Вы записали {amount} мл воды. Осталось: {max(0, remaining)} мл до достижения вашей нормы.")
        else:
            await message.answer("Пожалуйста, сначала настройте свой профиль с помощью команды /set_profile.")
    except ValueError:
        await message.answer("Пожалуйста, введите корректное количество воды в миллилитрах, например, /log_water 250.")


@router.message(Command("log_workout"))
async def log_workout(message: Message, state: FSMContext):
    command_parts = message.text.split(maxsplit=2)

    if len(command_parts) != 3:
        await message.answer("Пожалуйста, укажите тип тренировки и время в минутах, например, /log_workout бег 30.")
        return

    workout_type, time_str = command_parts[1], command_parts[2]

    try:
        time = int(time_str)
    except ValueError:
        await message.answer("Пожалуйста, укажите корректное время в минутах.")
        return

    # Пример расчета калорий в зависимости от типа тренировки
    workout_calories = {
        "бег": 10,
        "ходьба": 5,
        "йога": 3,
        # Добавьте больше типов тренировок по мере необходимости
    }

    calories_per_minute = workout_calories.get(workout_type.lower(), 5)
    burned_calories = calories_per_minute * time

    user_id = message.from_user.id

    if user_id in users:
        users[user_id]['burned_calories'] = users[user_id].get('burned_calories', 0) + burned_calories
        extra_water = 200 * (time // 30)
        users[user_id]['logged_water'] = users[user_id].get('logged_water', 0) + extra_water
        
        await message.answer(
            f"🏃‍♂️ {workout_type.capitalize()} {time} минут — {burned_calories} ккал. Дополнительно: выпейте {extra_water} мл воды."
        )
    else:
        await message.answer("Пожалуйста, сначала настройте свой профиль с помощью команды /set_profile.")


@router.message(Command("check_progress"))
async def check_progress(message: Message):
    user_id = message.from_user.id
    
    if user_id not in users:
        await message.answer("Пожалуйста, сначала настройте свой профиль с помощью команды /set_profile.")
        return
    
    user = users[user_id]
    water_goal = await calculate_water(user, 25)
    calorie_goal = user.get('calorie_goal', await calculate_calorie(user))
    
    water_logged = user.get('logged_water', 0)
    calories_logged = user.get('logged_calories', 0)
    calories_burned = user.get('burned_calories', 0)
    
    water_remaining = max(0, water_goal - water_logged)
    calorie_balance = max(0, calories_logged + calories_burned - calorie_goal)

    await message.answer(
        f"📊 Прогресс:\n"
        f"Вода:\n"
        f"- Выпито: {water_logged} мл из {water_goal} мл.\n"
        f"- Осталось: {water_remaining} мл.\n\n"
        f"Калории:\n"
        f"- Потреблено: {calories_logged} ккал из {calorie_goal} ккал.\n"
        f"- Сожжено: {calories_burned} ккал.\n"
        f"- Баланс: {calorie_balance} ккал."
    )


def get_food_info(product_name):
    url = f"https://world.openfoodfacts.org/cgi/search.pl?action=process&search_terms={product_name}&json=true"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        products = data.get('products', [])
        if products:
            first_product = products[0]
            return {
                'name': first_product.get('product_name', 'Неизвестно'),
                'calories': first_product.get('nutriments', {}).get('energy-kcal_100g', 0)
            }
        return None
    print(f"Ошибка: {response.status_code}")
    return None

@router.message(Command("log_food"))
async def log_food(message: Message, state: FSMContext):
    command_parts = message.text.split(maxsplit=1)

    if len(command_parts) < 2:
        await message.answer("Пожалуйста, укажите название продукта, например, /log_food банан.")
        return

    product_name = command_parts[1]
    food_info = get_food_info(product_name)
    
    if food_info:
        await message.answer(
            f"{food_info['name']} — {food_info['calories']} ккал на 100 г. Сколько грамм вы съели?"
        )
        user_id = message.from_user.id
        users[user_id]['product_kcal'] = food_info['calories']
    else:
        await message.answer("Извините, не удалось найти информацию о продукте.")

@router.message()
async def log_food_amount(message: Message, state: FSMContext):
    try:
        amount = int(message.text)
        user_id = message.from_user.id

        if 'product_kcal' in users.get(user_id, {}):
            kcal_per_100g = users[user_id].pop('product_kcal')
            consumed_calories = (amount * kcal_per_100g) / 100
            users[user_id]['logged_calories'] = users[user_id].get('logged_calories', 0) + consumed_calories

            await message.answer(f"Записано: {consumed_calories} ккал.")
        else:
            await message.answer("Пожалуйста, сначала укажите название продукта с помощью команды /log_food.")
    except ValueError:
        await message.answer("Пожалуйста, укажите количество в граммах, например: 150.")


# Функция для подключения обработчиков
def setup_handlers(dp):
    dp.include_router(router)
