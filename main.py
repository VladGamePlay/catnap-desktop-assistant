import customtkinter as ctk
from PIL import Image 
import google.generativeai as genai
import tkinter
from tkinter import messagebox
import mss
import io
import random
import time
import subprocess
import webbrowser
import json
import pyautogui
import pyperclip
import traceback

import os
from dotenv import load_dotenv

load_dotenv()
print(f"Ключ из .env: {os.getenv('GEMINI_API_KEY')}") # Для отладки

# --- Настройки ---
SPRITE_IMAGE_PATH = "assets/catnap_idle2.gif" 
WINDOW_TARGET_WIDTH = 200 
WINDOW_TARGET_HEIGHT = 250 
APP_VERSION = "1.6.1" # Новая версия
APP_YEAR = "2025"
PREFERENCES_FILE_NAME = "user_preferences.json"

INTERACTIVE_ZONES_CONFIG = {
    'nose': {
        'rect': (90, 121, 120, 151), # Носик
        'messages': ["Кто это щекочет мой носик? *фырк*", "Мрр? Мой нос?", "Буп! Неожиданно!"]
    },
    'pendant': { # Кулон
        'rect': (89, 191, 119, 221),
        'messages': ["О, моя блестяшка! *смотрит на кулон*", "Это мой любимый кулончик!", "Не трогай, он волшебный... или нет? *хитро улыбается*"]
    },
    'tail_tip': { # Кончик хвоста
        'rect': (251, 263, 281, 293),
        'messages': ["Ай! Мой хвостик!", "Не дергай за хвост, я не собачка!", "Хвостик тоже хочет внимания!"]
    },
    'right_paw_foot': { # Правая лапка (ножка)
        'rect': (185, 247, 215, 277),
        'messages': ["Моя правая лапка!", "Щекотно же!", "Топ-топ... этой лапкой я хожу во сне."]
    },
    'left_paw_foot': { # Левая лапка (ножка)
        'rect': (5, 252, 35, 282),
        'messages': ["А это левая!", "Осторожнее, я могу и пнуть!", "Мои подушечки!"]
    },
    'right_ear': { # Правое ушко
        'rect': (162, 46, 192, 76),
        'messages': ["*Дергает правым ушком*", "Слышу-слышу!", "Что там шуршит?"]
    },
    'left_ear': { # Левое ушко
        'rect': (27, 42, 57, 72),
        'messages': ["*Поводит левым ушком*", "Тише, я слушаю тишину...", "Мрр, ушки тоже любят ласку."]
    }
}

# --- Настройки "Поглаживания" CatNap ---
PET_STROKE_THRESHOLD = 3       # Сколько движений мыши для срабатывания "поглаживания"
PET_COOLDOWN_S = 5             # Секунд перезарядки между реакциями на поглаживание
PET_DETECTION_WINDOW_MS = 400  # Окно в мс для подсчета движений (если за это время не было порога, сбрасываем)
PET_MAX_DRAG_DISTANCE_PX = 20  # Максимальное смещение курсора от начальной точки для поглаживания (чтобы отличить от перетаскивания)
PETTING_MESSAGES = [
    "Мрррр... *довольно мурлычет*",
    "О, это приятно! *трется о курсор*",
    "Мяу! Еще! *закрывает глазки*",
    "Так хорошо... *виляет хвостом (воображаемым)*",
    "Люблю, когда меня гладят... *муррр*"
]

# --- Настройки Gemini API ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
class Mood:
    SLEEPY = "SLEEPY"; PLAYFUL = "PLAYFUL"; THOUGHTFUL = "THOUGHTFUL"; NEUTRAL = "NEUTRAL"
ALL_MOODS_LIST = [Mood.SLEEPY, Mood.PLAYFUL, Mood.THOUGHTFUL, Mood.NEUTRAL]
MOOD_PROMPT_ADDITIONS = {
    Mood.SLEEPY: "Ты сейчас ОЧЕНЬ сонный. Твои ответы должны быть предельно короткими, ленивыми, ты часто зеваешь, упоминаешь желание поспать и стараешься отвечать как можно меньше, буквально одним-двумя предложениями. Избегай энтузиазма.",
    Mood.PLAYFUL: "Ты сейчас в очень игривом и веселом настроении! Твои ответы могут быть более длинными, с шутками, ты можешь предлагать поиграть или задавать встречные вопросы. Используй больше кошачьих восклицаний, вроде 'Мяу!', 'Мррр!' и т.п.",
    Mood.THOUGHTFUL: "Ты сейчас в задумчивом, философском настроении. Можешь отвечать немного отстраненно, размышляя о чем-то своем, но все так же по-кошачьи. Твои ответы могут быть чуть более глубокими, но не теряй своей ленивой натуры.",
    Mood.NEUTRAL: ""
}
MOOD_GREETINGS = {
    Mood.SLEEPY: "Мррр... *зевает* Опять ты? Дай поспать... Ну, что там у тебя?",
    Mood.PLAYFUL: "Привееет! *машет воображаемым хвостом* Поиграем? Или есть что-то важное?",
    Mood.THOUGHTFUL: "Хммм... *смотрит в окно* О, это ты. О чем задумался на этот раз?",
    Mood.NEUTRAL: "Мррр... Привет! Чем могу помочь? *потягивается*"
}
BASE_SYSTEM_INSTRUCTION = (
    "Ты — CatNap, милый, немного сонный, но дружелюбный и остроумный виртуальный ассистент "
    "в виде фиолетового кота. Ты живешь на рабочем столе пользователя. "
    "Твои ответы должны быть короткими, лаконичными, немного ленивыми, но всегда полезными и с долей юмора. "
    "Ты любишь дремать и иногда упоминаешь это в своих ответах. "
    "Не используй markdown форматирование в своих ответах, отвечай простым текстом. "
    "Избегай длинных абзацев. Говори как настоящий кот: игриво, любопытно, иногда отстраненно."
)
MOOD_CHANGE_INTERVAL_MIN_MS = 20 * 60 * 1000
MOOD_CHANGE_INTERVAL_MAX_MS = 30 * 60 * 1000
SEARCH_KEYWORDS = ["найди", "поищи", "узнай", "что такое", "кто такой", "покажи"]
EXECUTE_KEYWORDS = ["открой", "запусти"]
# --- Новые ключевые слова для записи в блокнот ---
WRITE_TO_NOTEPAD_KEYWORDS = ["напиши в блокнот", "запиши в блокнот", "блокнот напиши", "блокнот запиши"]

KNOWN_PROGRAMS = {
    "блокнот": "notepad.exe", "калькулятор": "calc.exe",
    "paint": "mspaint.exe", "пеинт": "mspaint.exe",
    "хром": "_BROWSER_", "chrome": "_BROWSER_", "браузер": "_BROWSER_"
}

class PreferencesWindow(ctk.CTkToplevel): # Без изменений от предыдущей версии
    def __init__(self, master_app: 'CatNapApp'):
        super().__init__(master_app)
        self.master_app = master_app
        self.title("Мои предпочтения для CatNap")
        self.geometry("500x450")
        self.attributes("-topmost", True)
        self.resizable(False, False)
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(padx=20, pady=20, expand=True, fill="both")
        ctk.CTkLabel(main_frame, text="Как CatNap может к тебе обращаться? (Имя):").pack(pady=(0,2), anchor="w")
        self.name_entry = ctk.CTkEntry(main_frame, width=400); self.name_entry.pack(fill="x", pady=(0,10))
        ctk.CTkLabel(main_frame, text="Твои хобби и интересы (через запятую):").pack(pady=(5,2), anchor="w")
        self.hobbies_textbox = ctk.CTkTextbox(main_frame, height=100, width=400); self.hobbies_textbox.pack(fill="x", pady=(0,10))
        ctk.CTkLabel(main_frame, text="Темы, которые CatNap стоит избегать (через запятую):").pack(pady=(5,2), anchor="w")
        self.disliked_topics_textbox = ctk.CTkTextbox(main_frame, height=100, width=400); self.disliked_topics_textbox.pack(fill="x", pady=(0,20))
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent"); button_frame.pack(fill="x", pady=(10,0))
        self.save_button = ctk.CTkButton(button_frame, text="Сохранить и закрыть", command=self.save_and_close); self.save_button.pack(side="right", padx=(10,0))
        self.cancel_button = ctk.CTkButton(button_frame, text="Отмена", command=self.close_window, fg_color="gray"); self.cancel_button.pack(side="right")
        self.clear_button = ctk.CTkButton(button_frame, text="Очистить все", command=self.clear_preferences, fg_color="#D32F2F", hover_color="#B71C1C"); self.clear_button.pack(side="left", padx=(0, 10))
        self.load_preferences_to_ui()
        self.protocol("WM_DELETE_WINDOW", self.close_window)
    def load_preferences_to_ui(self):
        prefs = self.master_app.user_preferences
        self.name_entry.insert(0, prefs.get("user_name", ""))
        self.hobbies_textbox.insert("1.0", ", ".join(prefs.get("hobbies", [])))
        self.disliked_topics_textbox.insert("1.0", ", ".join(prefs.get("disliked_topics", [])))
    def save_and_close(self):
        new_prefs = {"user_name": self.name_entry.get().strip()}
        hobbies_text_normalized = self.hobbies_textbox.get("1.0", "end-1c").replace("\n", ",")
        new_prefs["hobbies"] = [hob.strip() for hob in hobbies_text_normalized.split(",") if hob.strip()]
        disliked_text_normalized = self.disliked_topics_textbox.get("1.0", "end-1c").replace("\n", ",")
        new_prefs["disliked_topics"] = [topic.strip() for topic in disliked_text_normalized.split(",") if topic.strip()]
        self.master_app.user_preferences = new_prefs
        self.master_app._save_preferences()
        self.master_app.on_preferences_updated()
        messagebox.showinfo("Предпочтения", "Твои предпочтения сохранены!", parent=self)
        self.destroy_window()
    def clear_preferences(self):
        if messagebox.askyesno("Подтверждение", "Удалить все предпочтения?", parent=self):
            self.name_entry.delete(0, "end"); self.hobbies_textbox.delete("1.0", "end"); self.disliked_topics_textbox.delete("1.0", "end")
            cleared_prefs = {"user_name": "", "hobbies": [], "disliked_topics": []}
            self.master_app.user_preferences = cleared_prefs
            self.master_app._save_preferences(); self.master_app.on_preferences_updated()
            messagebox.showinfo("Предпочтения очищены", "Все твои предпочтения были удалены.", parent=self)
    def close_window(self): self.destroy_window()
    def destroy_window(self):
        if self.master_app: self.master_app.preferences_window_instance = None
        self.destroy()

class AboutWindow(ctk.CTkToplevel): # Без изменений
    def __init__(self, master):
        super().__init__(master)
        self.title("О программе"); self.geometry("450x400"); self.attributes("-topmost", True); self.resizable(False, False)
        main_frame = ctk.CTkFrame(self, fg_color="transparent"); main_frame.pack(padx=20, pady=20, expand=True, fill="both")
        main_frame.grid_rowconfigure(0, weight=0); main_frame.grid_rowconfigure(1, weight=1); main_frame.grid_rowconfigure(2, weight=0)
        main_frame.grid_columnconfigure(0, weight=1); main_frame.grid_columnconfigure(1, weight=0)
        program_name_label = ctk.CTkLabel(main_frame, text="CatNap Desktop Assistant", font=ctk.CTkFont(size=18, weight="bold")); program_name_label.grid(row=0, column=0, padx=(0,10), pady=(0,10), sticky="nw")
        try:
            about_sprite_pil = Image.open(SPRITE_IMAGE_PATH); sprite_width_orig, sprite_height_orig = about_sprite_pil.size
            aspect_ratio = sprite_height_orig / sprite_width_orig; new_sprite_width = 70; new_sprite_height = int(new_sprite_width * aspect_ratio)
            resized_sprite = about_sprite_pil.resize((new_sprite_width, new_sprite_height), Image.Resampling.LANCZOS)
            self.about_sprite_ctk = ctk.CTkImage(light_image=resized_sprite, dark_image=resized_sprite, size=(new_sprite_width, new_sprite_height))
            sprite_label = ctk.CTkLabel(main_frame, text="", image=self.about_sprite_ctk); sprite_label.grid(row=0, column=1, rowspan=2, padx=(10,0), pady=(0,10), sticky="ne")
        except Exception as e: print(f"Ошибка спрайта 'О программе': {e}"); sprite_label = ctk.CTkLabel(main_frame, text="[спрайт]", width=70, height=90); sprite_label.grid(row=0, column=1, rowspan=2, padx=(10,0), pady=(0,10), sticky="ne")
        text_content_holder = ctk.CTkScrollableFrame(main_frame, fg_color="transparent"); text_content_holder.grid(row=1, column=0, sticky="nsew", pady=(5,0))
        description_text = ("CatNap - это милый и немного сонный виртуальный ассистент "
            "в виде фиолетового кота, который живет на вашем рабочем столе. "
            "Он умеет общаться, выполнять команды и даже смотреть на экран!"); desc_label = ctk.CTkLabel(text_content_holder, text=description_text, wraplength=280, justify="left"); desc_label.pack(pady=5, anchor="w", fill="x")
        credits_label = ctk.CTkLabel(text_content_holder, text="Идея: VladGamePlay\nРеализация: Gemini", justify="left"); credits_label.pack(pady=(10,5), anchor="w")
        tech_label_title = ctk.CTkLabel(text_content_holder, text="Технологии:", font=ctk.CTkFont(weight="bold")); tech_label_title.pack(pady=(10,0), anchor="w")
        tech_text = ("- Python\n- CustomTkinter\n- Google Gemini API\n- Pillow (PIL)\n- mss, pyautogui, pyperclip"); tech_label_content = ctk.CTkLabel(text_content_holder, text=tech_text, justify="left"); tech_label_content.pack(anchor="w")
        version_year_label = ctk.CTkLabel(text_content_holder, text=f"Версия: {APP_VERSION}\nГод: {APP_YEAR}", justify="left"); version_year_label.pack(pady=(10,0), anchor="w")
        close_button = ctk.CTkButton(main_frame, text="Закрыть", command=self.destroy_window, width=100); close_button.grid(row=2, column=0, columnspan=2, pady=(20,0), sticky="s")
        self.protocol("WM_DELETE_WINDOW", self.destroy_window)
    def destroy_window(self):
        if self.master: self.master.about_window_instance = None
        self.destroy()

class ChatWindow(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master); self.master_app = master
        self.title("Диалог с CatNap"); self.geometry("400x500"); self.attributes("-topmost", True); self.protocol("WM_DELETE_WINDOW", self.hide_window)
        self.grid_columnconfigure(0, weight=1); self.grid_rowconfigure(0, weight=1)
        self.chat_history_textbox = ctk.CTkTextbox(self, state="disabled", wrap="word", font=("Arial", 14)); self.chat_history_textbox.grid(row=0, column=0, padx=10, pady=(10,0), sticky="nsew")
        self.input_frame = ctk.CTkFrame(self); self.input_frame.grid(row=1, column=0, padx=10, pady=10, sticky="ew"); self.input_frame.grid_columnconfigure(0, weight=1)
        self.user_input_entry = ctk.CTkEntry(self.input_frame, placeholder_text="Спроси что-нибудь у CatNap...", font=("Arial", 14)); self.user_input_entry.grid(row=0, column=0, padx=(0,5), pady=5, sticky="ew"); self.user_input_entry.bind("<Return>", self.send_message_event)
        self.send_button = ctk.CTkButton(self.input_frame, text="Отправить", command=self.send_message, font=("Arial", 14)); self.send_button.grid(row=0, column=1, padx=(0,0), pady=5, sticky="e")
        self.clear_button = ctk.CTkButton(self.input_frame, text="Очистить", command=self.clear_chat_history, font=("Arial", 13), width=80); self.clear_button.grid(row=0, column=2, padx=(5,0), pady=5, sticky="e")

    def set_initial_greeting(self): # Без изменений
        self.chat_history_textbox.configure(state="normal"); self.chat_history_textbox.delete("1.0", "end"); self.chat_history_textbox.configure(state="disabled")
        if self.master_app.chat_session: greeting = self.master_app.get_current_greeting(); self.add_message_to_chat("CatNap", greeting)
        elif self.master_app.gemini_api_error_message: self.add_message_to_chat("CatNap", f"Мррр... {self.master_app.gemini_api_error_message}")
        else: self.add_message_to_chat("CatNap", "Мррр... API не настроен.")

    def clear_chat_history(self, add_greeting=True): # Без изменений
        self.chat_history_textbox.configure(state="normal"); self.chat_history_textbox.delete("1.0", "end"); self.chat_history_textbox.configure(state="disabled")
        if self.master_app.gemini_model and self.master_app.chat_session:
            try:
                self.master_app._start_chat_session(system_instruction_override=self.master_app.get_current_system_instruction(), history_to_keep=[])
                if add_greeting: self.add_message_to_chat("CatNap", self.master_app.get_current_greeting(default_on_clear="Мррр... Начнем сначала?"))
            except Exception as e: print(f"Ошибка сброса Gemini: {e}");
            if add_greeting: self.add_message_to_chat("CatNap", "Мррр... Память почистил, а вот мысли... *задумался*")
        elif add_greeting: self.add_message_to_chat("CatNap", "Мррр... Доска чиста!")

    def send_message(self, direct_prompt=None, sender_override=None, is_vision_response=False):
        user_text_original = direct_prompt or self.user_input_entry.get()
        if not user_text_original.strip() and not direct_prompt : return

        if not direct_prompt:
            self.add_message_to_chat("Ты", user_text_original)
            self.user_input_entry.delete(0, "end")
        elif not sender_override: # Это команда из меню, которая не является прямой просьбой к CatNap
            self.add_message_to_chat("Ты (команда)", user_text_original)
        # Если sender_override есть, то это CatNap отвечает на команду из меню, текст пользователя не показываем

        user_text_lower = user_text_original.lower().strip()
        command_processed_locally = False

        # 1. Команда ЗАПИСИ В БЛОКНОТ (НОВАЯ)
        for keyword in WRITE_TO_NOTEPAD_KEYWORDS:
            if user_text_lower.startswith(keyword):
                # Извлекаем тему для записи. Ищем ":" или берем все после ключевого слова
                topic_to_write = ""
                if ":" in user_text_original: # Предполагаем, что тема после двоеточия
                    topic_to_write = user_text_original.split(":", 1)[1].strip()
                else: # Берем все после ключевой фразы
                    # Нужно найти, какое именно ключевое слово сработало, чтобы правильно отрезать
                    for kw_check in WRITE_TO_NOTEPAD_KEYWORDS: # Ищем самое длинное совпадение на всякий случай
                        if user_text_lower.startswith(kw_check):
                            topic_to_write = user_text_original[len(kw_check):].strip()
                            break # Нашли, выходим
                
                if topic_to_write:
                    self.master_app._generate_and_write_to_notepad(topic_to_write)
                    command_processed_locally = True
                    break
                else: # Ключевое слово есть, но темы нет
                    self.add_message_to_chat("CatNap", "Мрр... Я готов записать в Блокнот, но что именно ты хочешь, чтобы я написал?")
                    command_processed_locally = True # Считаем обработанной, чтобы не ушло в Gemini
                    break
        if command_processed_locally: return

        # 2. Команда ЗАПУСКА
        for keyword in EXECUTE_KEYWORDS:
            if user_text_lower.startswith(keyword + " "):
                target = user_text_lower[len(keyword):].strip()
                if target: self.master_app._execute_program(target); command_processed_locally = True; break
        if command_processed_locally: return

        # 3. Команда ПОИСКА
        for keyword in SEARCH_KEYWORDS:
            if user_text_lower.startswith(keyword + " "):
                query = user_text_original[len(keyword):].strip()
                if query: self.master_app._search_web(query); command_processed_locally = True; break
        if command_processed_locally: return

        # Если не локальная команда, то обычный чат
        if self.master_app.chat_session and not is_vision_response:
            try:
                thinking_msg = "Мрр... обдумываю..." if sender_override else "Мрр... думаю..."
                self.add_message_to_chat("CatNap", thinking_msg); self.update_idletasks()
                response = self.master_app.chat_session.send_message(user_text_original)
                self.chat_history_textbox.configure(state="normal"); all_text = self.chat_history_textbox.get("1.0", "end-1c")
                full_search = f"CatNap: {thinking_msg}"; last_idx = all_text.rfind(full_search)
                if last_idx != -1 and not all_text[last_idx + len(full_search):].strip():
                    self.chat_history_textbox.delete(self.chat_history_textbox.index(f"1.0 + {last_idx} chars"), "end-1c")
                self.chat_history_textbox.configure(state="disabled")
                self.add_message_to_chat(sender_override or "CatNap", response.text)
            except genai.types.BlockedPromptException:
                self.add_message_to_chat("CatNap", "Ой... Не хочу об этом говорить. *отворачивается*")
            except Exception as e:
                error_message_lower = str(e).lower()
                if "deadline" in error_message_lower or "unavailable" in error_message_lower or "network" in error_message_lower:
                    self.add_message_to_chat("CatNap", "Мррр... Кажется, мои мысли сейчас в тумане или связь барахлит. Попробуй чуть позже, когда я проснусь получше.")
                elif "permission denied" in error_message_lower or "authentication" in error_message_lower:
                     self.add_message_to_chat("CatNap", "Ой... Кажется, у меня нет ключика к моим мыслям (проблема с API ключом).")
                else:
                    # Можно добавить твою фразу для неопределенных ошибок, если нет специфики
                    self.add_message_to_chat("CatNap", f"... ой, мне кажется, ты куда-то переехал или я заблудился в мыслях! (Ошибка: {e})")
                print(f"Ошибка при общении с Gemini: {e}")
                traceback.print_exc() # Добавим traceback для всех ошибок в консоль

    def show_window(self): # Без изменений
        self.deiconify(); self.attributes("-topmost", True); self.lift(); self.focus_set()
        if hasattr(self, 'user_input_entry'): self.user_input_entry.focus()
        if self.chat_history_textbox.get("1.0", "end-1c").strip() == "": self.set_initial_greeting()
    def hide_window(self): self.withdraw()
    def send_message_event(self, event): self.send_message()
    def add_message_to_chat(self, sender, message):
        self.chat_history_textbox.configure(state="normal"); self.chat_history_textbox.insert("end", f"{sender}: {message}\n\n"); self.chat_history_textbox.configure(state="disabled"); self.chat_history_textbox.see("end")

class CatNapApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("CatNap"); self.overrideredirect(True); self.attributes("-topmost", True)
        self.gemini_model = None; self.chat_session = None; self.gemini_vision_model = None
        self.gemini_api_error_message = None
        self.generation_config_text = { "temperature": 0.7, "top_p": 1, "top_k": 1, "max_output_tokens": 2048, }
        self.safety_settings = [ {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"}, {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"}, {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"}, {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"}, ]
        self.current_mood = Mood.NEUTRAL; self.is_mood_enabled = False; self.mood_timer_id = None
        self.user_preferences = {}; self.preferences_window_instance = None
        # --- Атрибуты для "Поглаживания" ---
        self.last_pet_time = 0.0  # Время последнего успешного "поглаживания" (используем time.time())
        self.pet_stroke_count = 0 # Счетчик событий <B1-Motion> для определения поглаживания
        self.pet_detection_timer_id = None # ID таймера для сброса pet_stroke_count
        self.is_mouse_pressed_on_sprite = False # Флаг, что ЛКМ нажата на спрайте
        self.mouse_press_start_pos = (0, 0) # Координаты (x, y) спрайта в момент нажатия ЛКМ
        # --- Конец атрибутов для "Поглаживания" ---
        self._load_preferences()
        self.gif_frames = []; self.current_gif_frame_index = 0; self.gif_default_delay = 100; self.gif_animation_job = None
        
        current_theme = ctk.get_appearance_mode().lower()
        transparent_color_to_set = "#2B2B2B" if current_theme == "dark" else "#EBEBEB" # Или #FFFFFF для светлой
        self.configure(fg_color=transparent_color_to_set) # Явно ставим фон окна
        try: self.attributes("-transparentcolor", transparent_color_to_set)
        except tkinter.TclError as e: print(f"Ошибка -transparentcolor: {e}")


        self._initialize_gemini_models()
        self._load_and_setup_sprite()
        
        self.sprite_label.bind("<ButtonPress-1>", self.start_drag); self.sprite_label.bind("<B1-Motion>", self.do_drag); self.sprite_label.bind("<Button-3>", self.show_context_menu); self.sprite_label.bind("<Double-Button-1>", self.toggle_chat_window)
        # Бинды для СКМ (поглаживание) - НОВЫЕ
        self.sprite_label.bind("<ButtonPress-2>", self.start_petting_attempt)  # Обычно СКМ это Button-2
        self.sprite_label.bind("<B2-Motion>", self.handle_petting_motion)
        self.sprite_label.bind("<ButtonRelease-2>", self.stop_petting_attempt)
        
        self.chat_window_instance = ChatWindow(self); self.chat_window_instance.withdraw()
        self.about_window_instance = None
        self._setup_context_menu()
        if self.is_mood_enabled: self._set_initial_mood_and_start_timer()

    def _load_and_setup_sprite(self): # Без изменений от предыдущей версии
        try:
            pil_gif_image = Image.open(SPRITE_IMAGE_PATH)
            original_w, original_h = pil_gif_image.size
            target_w, target_h = original_w, original_h 
            frame_num = 0
            while True:
                try:
                    pil_gif_image.seek(frame_num)
                    duration = pil_gif_image.info.get('duration', self.gif_default_delay)
                    if duration == 0: duration = self.gif_default_delay
                    frame_pil_copy = pil_gif_image.copy()
                    if (original_w, original_h) != (target_w, target_h):
                        frame_pil_copy = frame_pil_copy.resize((target_w, target_h), Image.Resampling.LANCZOS)
                    ctk_frame = ctk.CTkImage(light_image=frame_pil_copy.convert("RGBA"), dark_image=frame_pil_copy.convert("RGBA"), size=(target_w, target_h))
                    self.gif_frames.append({'image': ctk_frame, 'duration': duration})
                    frame_num += 1
                except EOFError: break
            if not self.gif_frames: raise ValueError("Нет кадров в GIF.")
            screen_w, screen_h = self.winfo_screenwidth(), self.winfo_screenheight()
            x = screen_w - target_w - 50; y = screen_h - target_h - 100
            self.geometry(f"{target_w}x{target_h}+{x}+{y}")
            self.sprite_label = ctk.CTkLabel(self, text="", image=self.gif_frames[0]['image'], fg_color="transparent") # fg_color="transparent" для самого лейбла
            self.sprite_label.pack(expand=True, fill="both")
            self._start_gif_animation()
        except Exception as e:
            print(f"Ошибка загрузки GIF: {e}")
            fw, fh = WINDOW_TARGET_WIDTH, WINDOW_TARGET_HEIGHT
            screen_w, screen_h = self.winfo_screenwidth(), self.winfo_screenheight()
            x = screen_w - fw - 50; y = screen_h - fh - 100
            self.geometry(f"{fw}x{fh}+{x}+{y}")
            self.sprite_label = ctk.CTkLabel(self, text="Спрайт GIF\nошибка!", font=("Arial", 16))
            self.sprite_label.pack(expand=True, fill="both", padx=10, pady=10)
            
    def _animate_gif(self): # Без изменений
        if not self.gif_frames or not hasattr(self, 'sprite_label') or not self.sprite_label.winfo_exists(): return
        frame_info = self.gif_frames[self.current_gif_frame_index]
        self.sprite_label.configure(image=frame_info['image'])
        self.current_gif_frame_index = (self.current_gif_frame_index + 1) % len(self.gif_frames)
        self.gif_animation_job = self.after(frame_info['duration'], self._animate_gif)
    def _start_gif_animation(self): # Без изменений
        if self.gif_animation_job: self.after_cancel(self.gif_animation_job)
        self._animate_gif()
    def _stop_gif_animation(self): # Без изменений
        if self.gif_animation_job: self.after_cancel(self.gif_animation_job); self.gif_animation_job = None

    def _get_preferences_path(self): return os.path.join(os.path.dirname(os.path.abspath(__file__)), PREFERENCES_FILE_NAME) # Без изменений
    def _load_preferences(self): # Без изменений
        path = self._get_preferences_path()
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f: self.user_preferences = json.load(f)
                print(f"Предпочтения загружены: {self.user_preferences}")
            except Exception as e: print(f"Ошибка загрузки предпочтений: {e}"); self.user_preferences = {"user_name": "", "hobbies": [], "disliked_topics": []}
        else: self.user_preferences = {"user_name": "", "hobbies": [], "disliked_topics": []}
    def _save_preferences(self): # Без изменений
        path = self._get_preferences_path()
        try:
            with open(path, 'w', encoding='utf-8') as f: json.dump(self.user_preferences, f, ensure_ascii=False, indent=4)
            print(f"Предпочтения сохранены.")
        except Exception as e: print(f"Ошибка сохранения предпочтений: {e}"); messagebox.showerror("Ошибка", f"Не удалось сохранить: {e}", parent=self.preferences_window_instance or self)
    def show_preferences_window(self): # Без изменений
        if self.preferences_window_instance is None or not self.preferences_window_instance.winfo_exists(): self.preferences_window_instance = PreferencesWindow(self)
        else: self.preferences_window_instance.lift(); self.preferences_window_instance.focus_set()
        self.preferences_window_instance.update_idletasks(); w = self.preferences_window_instance.winfo_width(); h = self.preferences_window_instance.winfo_height()
        if w<=1:w=500; 
        if h<=1:h=450
        sw=self.winfo_screenwidth();sh=self.winfo_screenheight();x=(sw//2)-(w//2);y=(sh//2)-(h//2)
        self.preferences_window_instance.geometry(f"{w}x{h}+{x}+{y}");self.preferences_window_instance.deiconify()
    def on_preferences_updated(self): # Без изменений
        print("Предпочтения обновлены, перезапуск сессии..."); self._start_chat_session()
        if self.chat_window_instance and self.chat_window_instance.winfo_viewable(): self.chat_window_instance.add_message_to_chat("CatNap (система)", "Мрр... Запомнил новые предпочтения!")

    def _execute_program(self, name_query: str): # Без изменений
        chat_win = self.get_chat_window()
        if not chat_win.winfo_viewable(): self.toggle_chat_window(center_on_sprite=False)
        cmd = KNOWN_PROGRAMS.get(name_query.lower())
        if cmd == "_BROWSER_":
            try: webbrowser.open("https://google.com"); chat_win.add_message_to_chat("CatNap", "Мяу! Открываю браузер.")
            except Exception as e: chat_win.add_message_to_chat("CatNap", f"Упс, не открыл браузер: {e}")
        elif cmd:
            try: subprocess.Popen(cmd); chat_win.add_message_to_chat("CatNap", f"Мяу! Открываю {name_query.replace('.exe','')}.")
            except Exception as e: chat_win.add_message_to_chat("CatNap", f"Ой, не открыл '{name_query}': {e}")
        else: chat_win.add_message_to_chat("CatNap", f"Не знаю '{name_query}'. Попробуй: {', '.join(k for k,v in KNOWN_PROGRAMS.items() if v!='_BROWSER_')}.")

    def _search_web(self, query: str): # Без изменений
        chat_win = self.get_chat_window()
        if not chat_win.winfo_viewable(): self.toggle_chat_window(center_on_sprite=False)
        q_lower = query.lower()
        if any(k in q_lower for k in ["котик", "котят", "котов", "кошек"]):
            responses = ["Других котиков? А я?!", "Опять других котиков... *отвернулся*", "Я не ревную... *смотрит в сторону*"];
            chat_win.add_message_to_chat("CatNap", random.choice(responses)); chat_win.update_idletasks()
        else: chat_win.add_message_to_chat("CatNap", f"Мрр... Ищу '{query}'...");
        self._open_browser_for_search(query)
    def _open_browser_for_search(self, query: str): # Без изменений
        try: webbrowser.open(f"https://www.google.com/search?q={query.replace(' ', '+')}")
        except Exception as e:
            if self.chat_window_instance and self.chat_window_instance.winfo_viewable(): self.chat_window_instance.add_message_to_chat("CatNap", f"Не открыл браузер: {e}")
            else: print(f"Ошибка браузера (чат скрыт): {e}")

    # --- НОВЫЙ МЕТОД для генерации и записи в Блокнот ---
    def _generate_and_write_to_notepad(self, topic_for_gemini: str):
        chat_win = self.get_chat_window()
        if not chat_win.winfo_viewable():
            self.toggle_chat_window(center_on_sprite=False)

        chat_win.add_message_to_chat("CatNap", f"Мрр... Сейчас подумаю над \"{topic_for_gemini}\" и запишу в Блокнот...")
        chat_win.update_idletasks()

        if not self.chat_session:
            chat_win.add_message_to_chat("CatNap", "Ой... Я не могу сейчас думать, нет связи с моими мыслями (API).")
            return

        try:
            prompt_for_text_generation = (
                f"Пожалуйста, напиши содержательный текст на тему: \"{topic_for_gemini}\". "
                "Текст должен быть хорошо структурирован, разбит на абзацы, если это уместно. "
                "Избегай markdown форматирования, так как текст будет вставлен в простой текстовый файл (Блокнот). "
                "Постарайся быть информативным и полезным. Если это вопрос, дай развернутый ответ. Если это просьба о совете, дай несколько советов."
            )
            
            response = self.chat_session.send_message(prompt_for_text_generation)
            generated_text = response.text

            if not generated_text.strip():
                chat_win.add_message_to_chat("CatNap", "Хм... Почему-то ничего не придумалось на эту тему. Странно.")
                return

            # --- Улучшенная логика запуска и активации Блокнота ---
            try:
                # Запускаем Блокнот
                notepad_process = subprocess.Popen("notepad.exe")
                print(f"Блокнот запущен (PID: {notepad_process.pid}). Ожидание окна...")
                
                # Пытаемся найти и активировать окно Блокнота
                # Заголовки могут отличаться в зависимости от языка ОС
                # 'Безымянный - Блокнот' (рус) или 'Untitled - Notepad' (англ)
                # Можно добавить больше вариантов или сделать более универсальный поиск
                notepad_window_titles = ["Без имени — Блокнот", "Untitled — Notepad", "Блокнот", "Notepad"]
                notepad_window = None
                
                # Даем время на появление окна (до 10 секунд)
                for _ in range(20): # Проверяем 20 раз с интервалом 0.5 сек
                    time.sleep(0.5) 
                    active_windows = pyautogui.getAllWindows()
                    for window in active_windows:
                        # print(f"DEBUG: Найдено окно с заголовком: '{window.title}'") # Для отладки
                        for title_part in notepad_window_titles:
                            if title_part.lower() in window.title.lower(): # Регистронезависимый поиск части заголовка
                                notepad_window = window
                                break
                        if notepad_window:
                            break
                    if notepad_window:
                        break
                
                if notepad_window:
                    print(f"Окно Блокнота найдено: '{notepad_window.title}'. Активация...")
                    try:
                        if notepad_window.isMinimized:
                            notepad_window.restore()
                        if not notepad_window.isActive: # Проверяем, активно ли окно
                             notepad_window.activate()
                             time.sleep(0.2) # Небольшая пауза после активации
                        
                        # Дополнительная проверка, что окно действительно активно
                        # if not pyautogui.getActiveWindow() or pyautogui.getActiveWindow().title != notepad_window.title:
                        #     print("ПРЕДУПРЕЖДЕНИЕ: Окно Блокнота не стало активным после попытки активации.")
                        #     # Можно попробовать еще раз или выдать ошибку

                    except Exception as e_activate:
                        print(f"Ошибка при попытке активировать окно Блокнота: {e_activate}")
                        # Продолжаем, надеясь, что оно все же активно или станет активным

                    # Копируем текст в буфер обмена
                    pyperclip.copy(generated_text)
                    print("Текст скопирован в буфер обмена.")
                    
                    # Вставляем текст (Ctrl+V)
                    # Даем еще небольшую паузу перед вставкой
                    time.sleep(0.5) # Увеличим немного, если предыдущей было мало
                    pyautogui.hotkey('ctrl', 'v')
                    # pyautogui.press('enter') # Можно добавить Enter
                    print("Команда Ctrl+V отправлена.")

                    chat_win.add_message_to_chat("CatNap", f"Готово! Записал информацию о \"{topic_for_gemini}\" в новый файл Блокнота. Не забудь его сохранить! *мурр*")
                else:
                    print("Окно Блокнота не найдено после запуска.")
                    chat_win.add_message_to_chat("CatNap", "Мрр... Я запустил Блокнот, но не смог в него написать. Попробуешь сам скопировать текст?")
                    pyperclip.copy(generated_text) # Копируем в буфер, чтобы пользователь мог вставить сам
                    chat_win.add_message_to_chat("CatNap (система)", "(Текст скопирован в твой буфер обмена)")

            except Exception as e_notepad_interaction:
                chat_win.add_message_to_chat("CatNap", f"Упс... Что-то пошло не так с Блокнотом: {e_notepad_interaction}")
                traceback.print_exc()
                pyperclip.copy(generated_text) # На всякий случай копируем, если текст уже сгенерирован
                chat_win.add_message_to_chat("CatNap (система)", "(Текст на всякий случай скопирован в буфер обмена)")


        except AttributeError as e:
            if "NoneType object has no attribute 'send_message'" in str(e) or (hasattr(e, 'name') and e.name == 'send_message'): # type: ignore
                chat_win.add_message_to_chat("CatNap", "Ой, кажется, я не могу сейчас думать (проблема с API-сессией). Попробуй позже.")
            else:
                chat_win.add_message_to_chat("CatNap", f"Мяу... Что-то пошло не так при генерации: {e}")
            traceback.print_exc()
        except Exception as e:
            chat_win.add_message_to_chat("CatNap", f"Мяу... Произошла глобальная ошибка: {e}")
            traceback.print_exc()


    def _initialize_gemini_models(self): # Это метод экземпляра, поэтому self обязателен
        try:
            # GEMINI_API_KEY здесь будет глобальной переменной,
            # загруженной из .env с помощью os.getenv() в начале файла.
            if not GEMINI_API_KEY: # Если os.getenv("GEMINI_API_KEY") вернул None
                warning_msg = ("API ключ Gemini (GEMINI_API_KEY) не найден в переменных окружения "
                               "или .env файле. Функционал чата будет ограничен.")
                print(f"ПРЕДУПРЕЖДЕНИЕ: {warning_msg}")
                self.gemini_api_error_message = warning_msg
                return # Выходим из метода, если ключа нет
            genai.configure(api_key=GEMINI_API_KEY)
            self.gemini_model = genai.GenerativeModel(model_name="gemini-2.5-flash-preview-05-20", generation_config=self.generation_config_text, safety_settings=self.safety_settings)
            try: self.gemini_vision_model = genai.GenerativeModel(model_name="gemini-2.5-flash-preview-05-20", safety_settings=self.safety_settings)
            except Exception as e_vis: self.gemini_vision_model = None; print(f"Vision API ошибка: {e_vis}")
            self._start_chat_session()
        except Exception as e: self.gemini_api_error_message = f"Gemini API ошибка: {e}"; print(self.gemini_api_error_message)

    def get_current_system_instruction(self): # Без изменений
        mood_instr = MOOD_PROMPT_ADDITIONS.get(self.current_mood, "")
        prefs_parts = []
        if self.user_preferences.get("user_name"): prefs_parts.append(f"Пользователя зовут {self.user_preferences['user_name']}.")
        if self.user_preferences.get("hobbies"): prefs_parts.append(f"Его хобби: {', '.join(self.user_preferences['hobbies'])}.")
        if self.user_preferences.get("disliked_topics"): prefs_parts.append(f"Избегай тем: {', '.join(self.user_preferences['disliked_topics'])}.")
        return f"{BASE_SYSTEM_INSTRUCTION} {mood_instr} {' '.join(prefs_parts)}".strip().replace("  ", " ")

    def _start_chat_session(self, system_instruction_override=None, history_to_keep=None): # Без изменений
        if not self.gemini_model: print("Модель Gemini не инициализирована."); return
        history = history_to_keep if history_to_keep is not None else (self.chat_session.history if self.chat_session else [])
        instruction = system_instruction_override or self.get_current_system_instruction()
        try:
            self.gemini_model = genai.GenerativeModel(model_name="gemini-2.5-flash-preview-05-20", generation_config=self.generation_config_text, safety_settings=self.safety_settings, system_instruction=instruction)
            self.chat_session = self.gemini_model.start_chat(history=history)
            print(f"Сессия Gemini запущена. Настроение: {self.current_mood}")
        except Exception as e: self.gemini_api_error_message = f"Ошибка сессии: {e}"; print(self.gemini_api_error_message)

    def get_current_greeting(self, default_on_clear=None): return default_on_clear or MOOD_GREETINGS.get(self.current_mood, MOOD_GREETINGS[Mood.NEUTRAL]) # Без изменений
    def _setup_context_menu(self): # Без изменений
        self.context_menu = tkinter.Menu(self, tearoff=0); catnap_bg="#4a2b63"; catnap_fg="#e6e6fa"; active_bg="#6a3b83"; active_fg="#ffffff"
        self.context_menu.configure(bg=catnap_bg,fg=catnap_fg,activebackground=active_bg,activeforeground=active_fg,relief=tkinter.FLAT,bd=2)
        self.menu_actions = {
            "Помечтай о чём-нибудь...": "Представь, что ты лениво размышляешь о чем-то случайном. Поделись этой мыслью (коротко).",
            "Кошачьи думы?": "Что сейчас занимает твои кошачьи мысли? Расскажи в двух словах.",
            "Мяукни что-нибудь...": "Мяукни что-нибудь забавное или мудрое от себя, CatNap.",
            "Оглянись-ка...": "SCREENSHOT_COMMAND" # Промпт для скриншота генерируется в handle_vision_action
        }        
        for lbl, cmd_prompt in self.menu_actions.items():
            if cmd_prompt == "SCREENSHOT_COMMAND": self.context_menu.add_command(label=lbl, command=self.handle_vision_action, background=catnap_bg, foreground=catnap_fg, activebackground=active_bg, activeforeground=active_fg)
            else: self.context_menu.add_command(label=lbl, command=lambda p=cmd_prompt, l=lbl: self.handle_menu_action(p,l), background=catnap_bg, foreground=catnap_fg, activebackground=active_bg, activeforeground=active_fg)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Открыть/Скрыть чат", command=self.toggle_chat_window_from_menu, background=catnap_bg, foreground=catnap_fg, activebackground=active_bg, activeforeground=active_fg)
        self.settings_menu = tkinter.Menu(self.context_menu, tearoff=0, bg=catnap_bg,fg=catnap_fg,activebackground=active_bg,activeforeground=active_fg)
        self.context_menu.add_cascade(label="Настройки", menu=self.settings_menu)
        self.mood_enabled_var = tkinter.BooleanVar(value=self.is_mood_enabled)
        self.settings_menu.add_checkbutton(label="Живой КэтНэп", variable=self.mood_enabled_var, command=self.toggle_mood_functionality, background=catnap_bg, foreground=catnap_fg, activebackground=active_bg, activeforeground=active_fg, selectcolor=active_fg if ctk.get_appearance_mode().lower()=="dark" else "#cccccc")
        self.settings_menu.add_command(label="Мои предпочтения...", command=self.show_preferences_window, background=catnap_bg, foreground=catnap_fg, activebackground=active_bg, activeforeground=active_fg)
        self.context_menu.add_command(label="О программе", command=self.show_about_window, background=catnap_bg, foreground=catnap_fg, activebackground=active_bg, activeforeground=active_fg)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Выход", command=self.quit_app, background=catnap_bg, foreground=catnap_fg, activebackground=active_bg, activeforeground=active_fg)

    def toggle_mood_functionality(self): # Без изменений
        self.is_mood_enabled = self.mood_enabled_var.get()
        if self.is_mood_enabled: self._set_initial_mood_and_start_timer()
        else:
            if self.mood_timer_id: self.after_cancel(self.mood_timer_id); self.mood_timer_id=None
            self.current_mood = Mood.NEUTRAL; self.on_preferences_updated()
            if self.chat_window_instance and self.chat_window_instance.winfo_viewable(): self.chat_window_instance.add_message_to_chat("CatNap (система)", "Мрр... Буду просто собой."); self.chat_window_instance.set_initial_greeting()

    def _set_initial_mood_and_start_timer(self): self.current_mood = random.choice([m for m in ALL_MOODS_LIST if m != Mood.NEUTRAL] or [Mood.NEUTRAL]); self._start_chat_session(); self._schedule_next_mood_change() # Без изменений
    def _change_mood(self): # Без изменений
        if not self.is_mood_enabled: return
        self.current_mood = random.choice([m for m in ALL_MOODS_LIST if m != self.current_mood] or ALL_MOODS_LIST[:])
        self._start_chat_session()
        if self.chat_window_instance and self.chat_window_instance.winfo_viewable(): self.chat_window_instance.add_message_to_chat("CatNap (система)", f"*CatNap теперь {self.current_mood.lower()}*")
        self._schedule_next_mood_change()
    def _schedule_next_mood_change(self): # Без изменений
        if not self.is_mood_enabled: return
        if self.mood_timer_id: self.after_cancel(self.mood_timer_id)
        delay_ms = random.randint(MOOD_CHANGE_INTERVAL_MIN_MS, MOOD_CHANGE_INTERVAL_MAX_MS)
        minutes = delay_ms // 1000 // 60
        print(f"Следующая смена настроения примерно через: {minutes} минут")
        self.mood_timer_id = self.after(delay_ms, self._change_mood)
    def handle_menu_action(self, prompt, label): # Без изменений
        if self.chat_window_instance and not self.chat_window_instance.winfo_viewable(): self.toggle_chat_window(center_on_sprite=False)
        self.chat_window_instance.send_message(direct_prompt=prompt, sender_override=f"CatNap ({label})")

    def handle_vision_action(self): # Без изменений
        if not self.gemini_vision_model:
            chat_win = self.get_chat_window();
            if not chat_win.winfo_viewable(): self.toggle_chat_window(center_on_sprite=False)
            chat_win.add_message_to_chat("CatNap", "Глазки не видят (Vision API)."); return
        chat_win = self.get_chat_window();
        if not chat_win.winfo_viewable(): self.toggle_chat_window(center_on_sprite=False)
        chat_win.add_message_to_chat("CatNap", "Мрр... Осматриваюсь..."); chat_win.update_idletasks()
        try:
            with mss.mss() as sct: img = Image.frombytes("RGB", sct.grab(sct.monitors[1]).size, sct.grab(sct.monitors[1]).rgb) # type: ignore
            response = self.gemini_vision_model.generate_content([img, "Опиши скриншот кратко и забавно."])
            chat_win.add_message_to_chat("CatNap (увидел)", f"*Огляделся* {response.text}")
        except Exception as e: chat_win.add_message_to_chat("CatNap", f"Мяу... ошибка зрения: {e}"); traceback.print_exc()

    def show_about_window(self): # Без изменений
        if not self.about_window_instance or not self.about_window_instance.winfo_exists(): self.about_window_instance = AboutWindow(self)
        else: self.about_window_instance.lift()
        self.about_window_instance.update_idletasks();w=self.about_window_instance.winfo_width();h=self.about_window_instance.winfo_height();
        if w<=1:w=450;
        if h<=1:h=400
        sw=self.winfo_screenwidth();sh=self.winfo_screenheight();x=(sw//2)-(w//2);y=(sh//2)-(h//2)
        self.about_window_instance.geometry(f"{w}x{h}+{x}+{y}");self.about_window_instance.deiconify()

    def get_chat_window(self): # Без изменений
        if not self.chat_window_instance or not self.chat_window_instance.winfo_exists(): self.chat_window_instance = ChatWindow(self); self.chat_window_instance.withdraw()
        return self.chat_window_instance
    def toggle_chat_window_from_menu(self): self.toggle_chat_window(center_on_sprite=False) # Без изменений
    def toggle_chat_window(self, event=None, center_on_sprite=True):
        chat_win = self.get_chat_window()
        if chat_win.winfo_viewable(): # Если окно видимо
            chat_win.hide_window()
        else:
            # Определяем желаемые размеры окна чата
            desired_chat_width = 400
            desired_chat_height = 500

            if center_on_sprite:
                sprite_x = self.winfo_x()
                sprite_y = self.winfo_y()
                sprite_width = self.winfo_width()
                sprite_height = self.winfo_height()

                # Обновляем состояние окна, чтобы правильно рассчитать его текущие (минимальные) размеры, если нужно
                # но для установки геометрии мы будем использовать desired_chat_width/height
                chat_win.update_idletasks()
                # Старый код для получения chat_width/chat_height на основе winfo_ можно убрать или закомментировать,
                # так как мы теперь принудительно используем desired_chat_width/height для этого случая.

                # Рассчитываем позицию X
                chat_x = sprite_x - desired_chat_width - 10 # Слева от спрайта
                if chat_x < 0: # Если выходит за левый край экрана
                    chat_x = sprite_x + sprite_width + 10 # Справа от спрайта

                # Рассчитываем позицию Y (по центру спрайта)
                chat_y = sprite_y + (sprite_height // 2) - (desired_chat_height // 2)
                
                # Проверка границ экрана для Y
                screen_height = self.winfo_screenheight()
                if chat_y < 0:
                    chat_y = 10 # Отступ сверху
                elif chat_y + desired_chat_height > screen_height:
                    chat_y = screen_height - desired_chat_height - 10 # Отступ снизу
                
                # Повторная проверка границ экрана для X (на случай, если Y скорректировал позицию и X "уехал")
                screen_width = self.winfo_screenwidth()
                if chat_x < 0 : # Если все еще выходит за левый край
                     chat_x = 10 # Отступ слева
                elif chat_x + desired_chat_width > screen_width: # Если выходит за правый край
                    chat_x = screen_width - desired_chat_width - 10 # Отступ справа

                chat_win.geometry(f"{desired_chat_width}x{desired_chat_height}+{chat_x}+{chat_y}")
            else:
                # Если не центрируем (например, из меню), то просто показываем окно.
                # Оно должно использовать геометрию, заданную в ChatWindow.__init__ ("400x500")
                # или свою последнюю известную геометрию, если оно было просто скрыто.
                # Можно для надежности и здесь задать геометрию, если оно не было отцентрировано:
                # chat_win.geometry(f"{desired_chat_width}x{desired_chat_height}")
                # Но обычно это не требуется, если __init__ ChatWindow корректно ее задает.
                # Для консистентности, давайте убедимся, что оно имеет правильный размер,
                # если не было специального позиционирования.
                # Получим текущую позицию, чтобы не сбрасывать ее случайно.
                chat_win.update_idletasks() # Убедимся, что winfo_x/y актуальны
                current_x = chat_win.winfo_x()
                current_y = chat_win.winfo_y()
                # Если окно было только что создано, winfo_x/y могут быть не очень осмысленными (часто 1,1 или около того)
                # В таком случае, можно его отцентрировать на экране.
                if current_x <= 1 and current_y <=1 : # Предполагаем, что это "новое" окно без позиции
                    screen_width = self.winfo_screenwidth()
                    screen_height = self.winfo_screenheight()
                    current_x = (screen_width // 2) - (desired_chat_width // 2)
                    current_y = (screen_height // 2) - (desired_chat_height // 2)

                chat_win.geometry(f"{desired_chat_width}x{desired_chat_height}+{current_x}+{current_y}")


            chat_win.show_window()

    def start_drag(self, event):
        # Только логика для перетаскивания окна
        self.x_drag = event.x
        self.y_drag = event.y
        # self.is_mouse_pressed_on_sprite = True # Этот флаг теперь для поглаживания
        # self.mouse_press_start_pos = (event.x, event.y) # И это
        # self.pet_stroke_count = 0 # И это
        # Никаких таймеров для поглаживания здесь
    def _reset_pet_detection(self):
        #print("Pet detection window timed out.") # Для отладки
        self.pet_stroke_count = 0 # Сбрасываем счетчик
        self.is_mouse_pressed_on_sprite = False # Считаем, что нажатие уже не для поглаживания
        self.pet_detection_timer_id = None
    def do_drag(self, event):
        # Только логика перетаскивания окна
        deltax = event.x - self.x_drag
        deltay = event.y - self.y_drag
        x_win = self.winfo_x() + deltax
        y_win = self.winfo_y() + deltay
        self.geometry(f"+{x_win}+{y_win}")
        # Никакой логики поглаживания здесь
    def handle_mouse_release_on_sprite(self, event):
        # print("Mouse released on sprite") # Для отладки
        if self.pet_detection_timer_id: # Отменяем таймер, если он еще активен
            self.after_cancel(self.pet_detection_timer_id)
            self.pet_detection_timer_id = None
        
        self.is_mouse_pressed_on_sprite = False
        self.pet_stroke_count = 0
        self.mouse_press_start_pos = (0,0) # Сбрасываем
        # self.x_drag, self.y_drag остаются для возможного следующего перетаскивания, их не надо сбрасывать тут
    def start_petting_attempt(self, event):
        # print("СКМ Нажата - попытка погладить") # Для отладки
        self.is_mouse_pressed_on_sprite = True # Используем тот же флаг, но теперь он для СКМ
        self.mouse_press_start_pos = (event.x, event.y) # Начальная позиция для СКМ
        self.pet_stroke_count = 0

        # Отменяем предыдущий таймер обнаружения, если он был
        if self.pet_detection_timer_id:
            self.after_cancel(self.pet_detection_timer_id)
            self.pet_detection_timer_id = None
        
        self.pet_detection_timer_id = self.after(PET_DETECTION_WINDOW_MS, self._reset_pet_detection)

    def handle_petting_motion(self, event):
        current_time = time.time()
        if self.is_mouse_pressed_on_sprite: # Этот флаг теперь связан с СКМ
            dx = abs(event.x - self.mouse_press_start_pos[0])
            dy = abs(event.y - self.mouse_press_start_pos[1])

            if dx > PET_MAX_DRAG_DISTANCE_PX or dy > PET_MAX_DRAG_DISTANCE_PX:
                # Слишком большое движение для поглаживания СКМ, сбрасываем попытку
                # print(f"СКМ: Слишком далеко (dx={dx}, dy={dy}), сброс.") # Для отладки
                if self.pet_detection_timer_id:
                    self.after_cancel(self.pet_detection_timer_id)
                    self.pet_detection_timer_id = None
                self.is_mouse_pressed_on_sprite = False 
                self.pet_stroke_count = 0
                return # Важно выйти, чтобы не считать это за поглаживание
            else:
                self.pet_stroke_count += 1
                # print(f"СКМ: Stroke count: {self.pet_stroke_count}") # Для отладки

                if self.pet_stroke_count >= PET_STROKE_THRESHOLD and \
                (current_time - self.last_pet_time) > PET_COOLDOWN_S:
                    # print("СКМ: Поглаживание обнаружено!") # Для отладки
                    
                    # Пока используем общую реакцию. На следующем шаге будем определять зону.
                    self.current_petting_zone = self._get_pet_zone(event.x, event.y) # Определяем зону
                    self._react_to_petting_zone(self.current_petting_zone) # Реагируем на зону
                                        
                    self.last_pet_time = current_time
                    self.pet_stroke_count = 0 
                    
                    if self.pet_detection_timer_id:
                        self.after_cancel(self.pet_detection_timer_id)
                        self.pet_detection_timer_id = None
                    self.is_mouse_pressed_on_sprite = False 

    def stop_petting_attempt(self, event):
        # print("СКМ Отпущена") # Для отладки
        if self.pet_detection_timer_id:
            self.after_cancel(self.pet_detection_timer_id)
            self.pet_detection_timer_id = None
        
        self.is_mouse_pressed_on_sprite = False
        self.pet_stroke_count = 0
        self.mouse_press_start_pos = (0, 0)
        self.current_petting_zone = None # НОВЫЙ АТРИБУТ

    # _reset_pet_detection(self) - остается без изменений
    # def _reset_pet_detection(self):
    #     #print("Pet detection window timed out.")
    #     self.pet_stroke_count = 0
    #     self.is_mouse_pressed_on_sprite = False
    #     self.pet_detection_timer_id = None

    # _react_to_petting(self) - этот метод мы сейчас заменим на _react_to_petting_zone
    # def _react_to_petting(self):
    #     message = random.choice(PETTING_MESSAGES)
    #     # ... (остальная логика вывода сообщения) ...

    # НОВЫЙ метод для определения зоны и НОВЫЙ метод для реакции на зону
    def _get_pet_zone(self, x, y):
        """Определяет, в какую интерактивную зону попал клик."""
        # x, y - это координаты относительно спрайта (event.x, event.y из обработчика)
        for zone_name, zone_data in INTERACTIVE_ZONES_CONFIG.items():
            if 'rect' in zone_data:
                x_min, y_min, x_max, y_max = zone_data['rect']
                if x_min <= x <= x_max and y_min <= y <= y_max:
                    return zone_name
            # Добавить сюда 'circle', если будешь использовать круглые зоны
        return None # Не попали ни в одну специальную зону

    def _react_to_petting_zone(self, zone_name):
        """Реагирует на поглаживание в зависимости от зоны."""
        message = ""
        if zone_name and zone_name in INTERACTIVE_ZONES_CONFIG:
            message = random.choice(INTERACTIVE_ZONES_CONFIG[zone_name]['messages'])
            # print(f"Petting zone: {zone_name}") # Для отладки
        else:
            message = random.choice(PETTING_MESSAGES) # Общая реакция
            # print("General petting") # Для отладки
        
        chat_win = self.get_chat_window()
        if chat_win.winfo_viewable():
            if chat_win.chat_history_textbox.get("1.0", "end-1c").strip() == "":
                chat_win.set_initial_greeting()
            chat_win.add_message_to_chat("CatNap", message)
        else:
            print(f"CatNap petted ({zone_name or 'general'}): {message}")
    def show_context_menu(self, event): # Без изменений
        try: self.context_menu.tk_popup(event.x_root, event.y_root)
        finally: self.context_menu.grab_release()
    def quit_app(self): # Без изменений
        self._stop_gif_animation()
        if self.mood_timer_id: self.after_cancel(self.mood_timer_id)
        for win_ref_name in ["preferences_window_instance", "chat_window_instance", "about_window_instance"]:
            win = getattr(self, win_ref_name, None)
            if win and win.winfo_exists(): win.destroy()
        self.destroy()

if __name__ == "__main__":
    try: ctk.set_appearance_mode("System")
    except Exception: ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")
    app = CatNapApp()
    app.mainloop()