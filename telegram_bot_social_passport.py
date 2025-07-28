from telebot import telebot
import gspread
from google.oauth2.service_account import Credentials
from telegram_bot_calendar import DetailedTelegramCalendar, LSTEP
import re

scopes = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

credentials = Credentials.from_service_account_file(
    'APIgoogle.json',
    scopes=scopes
)

gc = gspread.authorize(credentials)

sht = gc.open_by_url('https://docs.google.com/spreadsheets/d/12dQfCQYb_DJYA8Esd75r-gdHR3TfJdLOzEqt0xMFiDc/edit?usp=sharing')

worksheet = sht.get_worksheet(0)

f = open("token.txt")
BOT_TOKEN = f.read().strip()
f.close()
bot = telebot.TeleBot(BOT_TOKEN)
user_states = {}

#Валидация
email_regex = r'^[\w.-]+@\w+\.[a-z]{2,3}$'
number_regex = r'^((8|\+7)[\- ]?)?(\(?\d{3}\)?[\- ]?)?[\d\- ]{7,10}$'

class UserRegistration:
    def __init__(self, chat_id):
        self.chat_id = chat_id
        self.person_name = None
        self.person_date = None
        self.email = None
        self.group = None
        self.nation = None
        self.education = None
        self.education_date = None
        self.address = None
        self.address_timeless = None
        self.number = None
        self.work_jobs = None
        self.parents_fullname = None
        self.parents_job = None
        self.parents_number = None
        self.empty_cell_index = None

    def start(self, message):
        bot.send_message(self.chat_id, "Приветствую вас на запись социального паспорта.")
        bot.send_message(self.chat_id, "Напишите вашу <Фамилия> <Имя> <Отчество>")
        bot.register_next_step_handler(message, self.register_person)

    def register_person(self, message):
        self.person_name = message.text
        if len(self.person_name) <= 40:
            bot.send_message(self.chat_id, "Записано")
            self.register_person_date(message)
        else:
            bot.send_message(self.chat_id, "Неправильно введенные данные, повторите еще раз")
            bot.register_next_step_handler(message, self.register_person)

    def register_person_date(self, message):
        bot.send_message(self.chat_id, "Выберите дату рождения")
        calendar, step = DetailedTelegramCalendar(locale='ru').build()
        bot.send_message(self.chat_id, f"Выберите {LSTEP[step]}", reply_markup=calendar)

    def register_person_date(self, message):
        bot.send_message(self.chat_id, "Выберите дату рождения")
        calendar, step = DetailedTelegramCalendar(locale='ru').build()
        bot.send_message(self.chat_id, f"Выберите {LSTEP[step]}", reply_markup=calendar)

    def calendar_callback(self, c):
        result, key, step = DetailedTelegramCalendar(locale='ru').process(c.data)
        if not result and key:
            bot.edit_message_text(f"Выбери {LSTEP[step]}", c.message.chat.id, c.message.message_id, reply_markup=key)
        elif result:
            bot.edit_message_text(f"Записано {result}", c.message.chat.id, c.message.message_id)
            self.person_date = result.strftime("%d.%m.%Y")
            self.check_person(c.message)

    def check_person(self, message):
        data = worksheet.get_all_records()
        values_in_column = worksheet.col_values(1)
        self.empty_cell_index = len(values_in_column) + 1
        flag = True
        for row in data:
            if self.person_name == row['ФИО'] and self.person_date == row['Дата рождения']:
                flag = False
                break
        if flag:
            worksheet.update_acell(f'A{self.empty_cell_index}', self.person_name)
            worksheet.update_acell(f'B{self.empty_cell_index}', self.person_date)
            bot.send_message(self.chat_id, "Записан")
            bot.send_message(self.chat_id, "Напишите электронную почту")
            bot.register_next_step_handler(message, self.add_email)
        else:
            bot.send_message(self.chat_id, "Данный пользователь зарегистрирован. Хотите отредактировать данные? <Да>/<Нет>")
            bot.register_next_step_handler(message, self.redacting_person_flag)

    def redacting_person_flag(self, message):
        if message.text.strip().lower() == "да":
            all_values = worksheet.get_all_values()
            self.cell_index = None
            for i, value in enumerate(all_values):
                if self.person_name in value and self.person_date in value:
                    self.cell_index = (i + 1, value.index(self.person_name) + 1)
                    break
            self.show_edit_menu(message)
        else:
            bot.send_message(self.chat_id, "Для повтора нажмите <Старт>")

    def show_edit_menu(self, message):
        markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
        buttons = [
            "ФИО", "Дата рождения", "Электронная почта", "Группа", "Национальность",
            "Базовое образование", "Год окончания", "Адрес по прописке", "Адрес временного проживания",
            "Номер телефона", "Место работы/Должность", "ФИО Родителей",
            "Место работы/Должность родителей", "Телефон родителей", "Выход"
        ]
        for btn in buttons:
            markup.add(telebot.types.KeyboardButton(btn))
        bot.send_message(self.chat_id, "Что вы хотите изменить?", reply_markup=markup)
        bot.register_next_step_handler(message, self.redacting_choose)

    def redacting_choose(self, message):
        mapping = {
            "ФИО": (self.redact_person_name, "Напишите ФИО"),
            "Дата рождения": (self.redact_person_date, "Напишите Дату Рождения в <дд.мм.гггг>"),
            "Электронная почта": (self.redact_person_mail, "Напишите электронная почта"),
            "Группа": (self.redact_person_group, "Напишите группу"),
            "Национальность": (self.redact_person_nation, "Напишите национальность"),
            "Базовое образование": (self.redact_person_education, "Напишите Базовое образование - какой вуз, специальность?"),
            "Год окончания": (self.redact_person_education_date, "Напишите год окончания"),
            "Адрес по прописке": (self.redact_person_address, "Напишите адрес по прописке"),
            "Адрес временного проживания": (self.redact_person_address_timeless, "Напишите адрес временного проживания"),
            "Номер телефона": (self.redact_person_number, "Напишите номер телефона"),
            "Место работы/Должность": (self.redact_work_jobs, "Напишите Место работы/Должность"),
            "ФИО Родителей": (self.redact_parents_fullname, "Напишите ФИО Родителей"),
            "Место работы/Должность родителей": (self.redact_parents_job, "Напишите Место работы/Должность родителей"),
            "Телефон родителей": (self.redact_parents_number, "Напишите Телефон родителей"),
            "Выход": (self.start, None)
        }
        func, text = mapping.get(message.text, (None, None))
        if func:
            if text:
                bot.send_message(self.chat_id, text)
            bot.register_next_step_handler(message, func)

    def redact_person_name(self, message):
        if self.cell_index:
            row, col = self.cell_index
            worksheet.update_cell(row, col, message.text)
            bot.send_message(self.chat_id, "ФИО отредактировано")
            bot.register_next_step_handler(message, self.redacting_choose)
        else:
            bot.send_message(self.chat_id, "Ошибка: не удалось найти строку для редактирования.")

    def redact_person_date(self, message):
        if self.cell_index:
            row, col = self.cell_index
            worksheet.update_cell(row, col + 1, message.text)
            bot.send_message(self.chat_id, "Дата Рождения отредактировано")
            bot.register_next_step_handler(message, self.redacting_choose)
        else:
            bot.send_message(self.chat_id, "Ошибка: не удалось найти строку для редактирования.")


    def redact_person_mail(self, message):
        if self.cell_index:
            row, col = self.cell_index
            worksheet.update_cell(row, col + 2, message.text)
            bot.send_message(self.chat_id, "Электронная почта отредактировано")
            bot.register_next_step_handler(message, self.redacting_choose)
        else:
            bot.send_message(self.chat_id, "Ошибка: не удалось найти строку для редактирования.")


    def redact_person_group(self, message):
        if self.cell_index:
            row, col = self.cell_index
            worksheet.update_cell(row, col + 3, message.text)
            bot.send_message(self.chat_id, "Группа отредактировано")
            bot.register_next_step_handler(message, self.redacting_choose)
        else:
            bot.send_message(self.chat_id, "Ошибка: не удалось найти строку для редактирования.")


    def redact_person_nation(self, message):
        if self.cell_index:
            row, col = self.cell_index
            worksheet.update_cell(row, col + 4, message.text)
            bot.send_message(self.chat_id, "Национальность отредактировано")
            bot.register_next_step_handler(message, self.redacting_choose)
        else:
            bot.send_message(self.chat_id, "Ошибка: не удалось найти строку для редактирования.")


    def redact_person_education(self, message):
        if self.cell_index:
            row, col = self.cell_index
            worksheet.update_cell(row, col + 5, message.text)
            bot.send_message(self.chat_id, "Базовое образование отредактировано")
            bot.register_next_step_handler(message, self.redacting_choose)
        else:
            bot.send_message(self.chat_id, "Ошибка: не удалось найти строку для редактирования.")


    def redact_person_education_date(self, message):
        if self.cell_index:
            row, col = self.cell_index
            worksheet.update_cell(row, col + 6, message.text)
            bot.send_message(self.chat_id, "Год окончания отредактировано")
            bot.register_next_step_handler(message, self.redacting_choose)
        else:
            bot.send_message(self.chat_id, "Ошибка: не удалось найти строку для редактирования.")


    def redact_person_address(self, message):
        if self.cell_index:
            row, col = self.cell_index
            worksheet.update_cell(row, col + 7, message.text)
            bot.send_message(self.chat_id, "Адрес по прописке отредактировано")
            bot.register_next_step_handler(message, self.redacting_choose)
        else:
            bot.send_message(self.chat_id, "Ошибка: не удалось найти строку для редактирования.")


    def redact_person_address_timeless(self, message):
        if self.cell_index:
            row, col = self.cell_index
            worksheet.update_cell(row, col + 8, message.text)
            bot.send_message(self.chat_id, "Адрес временного проживания отредактировано")
            bot.register_next_step_handler(message, self.redacting_choose)
        else:
            bot.send_message(self.chat_id, "Ошибка: не удалось найти строку для редактирования.")

    def redact_person_number(self, message):
        if self.cell_index:
            row, col = self.cell_index
            worksheet.update_cell(row, col + 9, message.text)
            bot.send_message(self.chat_id, "Номер телефона отредактировано")
            bot.register_next_step_handler(message, self.redacting_choose)
        else:
            bot.send_message(self.chat_id, "Ошибка: не удалось найти строку для редактирования.")


    def redact_work_jobs(self, message):
        if self.cell_index:
            row, col = self.cell_index
            worksheet.update_cell(row, col + 10, message.text)
            bot.send_message(self.chat_id, "Место работы/Должность отредактировано")
            bot.register_next_step_handler(message, self.redacting_choose)
        else:
            bot.send_message(self.chat_id, "Ошибка: не удалось найти строку для редактирования.")


    def redact_parents_fullname(self, message):
        if self.cell_index:
            row, col = self.cell_index
            worksheet.update_cell(row, col + 11, message.text)
            bot.send_message(self.chat_id, "ФИО Родителей отредактировано")
            bot.register_next_step_handler(message, self.redacting_choose)
        else:
            bot.send_message(self.chat_id, "Ошибка: не удалось найти строку для редактирования.")


    def redact_parents_job(self, message):
        if self.cell_index:
            row, col = self.cell_index
            worksheet.update_cell(row, col + 12, message.text)
            bot.send_message(self.chat_id, "Место работы/Должность родителей отредактировано")
            bot.register_next_step_handler(message, self.redacting_choose)
        else:
            bot.send_message(self.chat_id, "Ошибка: не удалось найти строку для редактирования.")


    def redact_parents_number(self, message):
        if self.cell_index:
            row, col = self.cell_index
            worksheet.update_cell(row, col + 13, message.text)
            bot.send_message(self.chat_id, "Телефон родителей отредактировано")
            bot.register_next_step_handler(message, self.redacting_choose)
        else:
            bot.send_message(self.chat_id, "Ошибка: не удалось найти строку для редактирования.")


    # --- Добавление новых данных ---
    def add_email(self, message):
        if re.match(email_regex, message.text):
            worksheet.update_acell(f'C{self.empty_cell_index}', message.text)
            bot.send_message(self.chat_id, "Записан")
            bot.send_message(self.chat_id, "Напишите в какой группе учитесь")
            bot.register_next_step_handler(message, self.add_group)
        else:
            bot.send_message(self.chat_id, "Неправильно ввели электронную почту. Напишите повторно")
            bot.register_next_step_handler(message, self.add_email)

    def add_group(self, message):
        worksheet.update_acell(f'D{self.empty_cell_index}', message.text)
        bot.send_message(self.chat_id, "Записан")
        bot.send_message(self.chat_id, "Напишите вашу национальность")
        bot.register_next_step_handler(message, self.add_nation)

    def add_nation(self, message):
        worksheet.update_acell(f'E{self.empty_cell_index}', message.text)
        bot.send_message(self.chat_id, "Записан")
        bot.send_message(self.chat_id, "Напишите Базовое образование - какой вуз, специальность?")
        bot.register_next_step_handler(message, self.add_education)

    def add_education(self, message):
        worksheet.update_acell(f'F{self.empty_cell_index}', message.text)
        bot.send_message(self.chat_id, "Записан")
        bot.send_message(self.chat_id, "Напишите в каком году закончили?")
        bot.register_next_step_handler(message, self.add_education_date)

    def add_education_date(self, message):
        worksheet.update_acell(f'G{self.empty_cell_index}', message.text)
        bot.send_message(self.chat_id, "Записан")
        bot.send_message(self.chat_id, "Напишите адрес по прописке")
        bot.register_next_step_handler(message, self.add_address)

    def add_address(self, message):
        worksheet.update_acell(f'H{self.empty_cell_index}', message.text)
        bot.send_message(self.chat_id, "Записан")
        bot.send_message(self.chat_id, "Напишите адрес временного проживания")
        bot.register_next_step_handler(message, self.add_address_timeless)

    def add_address_timeless(self, message):
        worksheet.update_acell(f'I{self.empty_cell_index}', message.text)
        bot.send_message(self.chat_id, "Записан")
        bot.send_message(self.chat_id, "Напишите номер телефона")
        bot.register_next_step_handler(message, self.add_number)

    def add_number(self, message):
        if re.match(number_regex, message.text):
            worksheet.update_acell(f'J{self.empty_cell_index}', message.text)
            bot.send_message(self.chat_id, "Записан")
            bot.send_message(self.chat_id, "Напишите место работы/Должность")
            bot.register_next_step_handler(message, self.add_work_jobs)
        else:
            bot.send_message(self.chat_id, "Неправильно ввели номер телефона. Напишите повторно")
            bot.register_next_step_handler(message, self.add_number)

    def add_work_jobs(self, message):
        worksheet.update_acell(f'K{self.empty_cell_index}', message.text)
        bot.send_message(self.chat_id, "Записан")
        bot.send_message(self.chat_id, "Напишите ФИО родителей")
        bot.register_next_step_handler(message, self.add_parents_fullname)

    def add_parents_fullname(self, message):
        worksheet.update_acell(f'L{self.empty_cell_index}', message.text)
        bot.send_message(self.chat_id, "Записан")
        bot.send_message(self.chat_id, "Напишите Место работы/Должность родителей")
        bot.register_next_step_handler(message, self.add_parents_job)

    def add_parents_job(self, message):
        worksheet.update_acell(f'M{self.empty_cell_index}', message.text)
        bot.send_message(self.chat_id, "Записан")
        bot.send_message(self.chat_id, "Напишите Телефон родителей")
        bot.register_next_step_handler(message, self.add_parents_number)

    def add_parents_number(self, message):
        if re.match(number_regex, message.text):
            worksheet.update_acell(f'N{self.empty_cell_index}', message.text)
            bot.send_message(self.chat_id, "Записан")
        else:
            bot.send_message(self.chat_id, "Неправильно ввели номер телефона. Напишите повторно")
            bot.register_next_step_handler(message, self.add_parents_number)

@bot.message_handler(commands=["start"])
def handle_start(message):
    user = UserRegistration(message.chat.id)
    user_states[message.chat.id] = user
    user.start(message)

@bot.callback_query_handler(func=DetailedTelegramCalendar.func())
def cal(c):
    user = user_states.get(c.message.chat.id)
    if user:
        user.calendar_callback(c)

bot.infinity_polling()

