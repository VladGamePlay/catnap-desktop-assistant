import customtkinter as ctk
from PIL import Image, ImageGrab
import google.generativeai as genai
import os
import tkinter
from tkinter import messagebox # Для диалоговых окон
import mss
import io
import random
import time
import subprocess
import webbrowser
import json # Для работы с JSON файлом предпочтений

# --- Настройки ---
SPRITE_IMAGE_PATH = "assets/catnap_idle.png"
WINDOW_TARGET_WIDTH = 200
WINDOW_TARGET_HEIGHT = 250
APP_VERSION = "1.4.0" 
APP_YEAR = "2025"
PREFERENCES_FILE_NAME = "user_preferences.json"

# --- Настройки Gemini API ---
GEMINI_API_KEY = "ВАШ_API_КЛЮЧ_СЮДА" # Замените на ваш ключ!
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
KNOWN_PROGRAMS = {
    "блокнот": "notepad.exe", "калькулятор": "calc.exe",
    "paint": "mspaint.exe", "пеинт": "mspaint.exe",
    "хром": "_BROWSER_", "chrome": "_BROWSER_", "браузер": "_BROWSER_"
}


class PreferencesWindow(ctk.CTkToplevel):
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
        self.name_entry = ctk.CTkEntry(main_frame, width=400)
        self.name_entry.pack(fill="x", pady=(0,10))

        ctk.CTkLabel(main_frame, text="Твои хобби и интересы (через запятую):").pack(pady=(5,2), anchor="w")
        self.hobbies_textbox = ctk.CTkTextbox(main_frame, height=100, width=400)
        self.hobbies_textbox.pack(fill="x", pady=(0,10))

        ctk.CTkLabel(main_frame, text="Темы, которые CatNap стоит избегать (через запятую):").pack(pady=(5,2), anchor="w")
        self.disliked_topics_textbox = ctk.CTkTextbox(main_frame, height=100, width=400)
        self.disliked_topics_textbox.pack(fill="x", pady=(0,20))

        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(fill="x", pady=(10,0))

        self.save_button = ctk.CTkButton(button_frame, text="Сохранить и закрыть", command=self.save_and_close)
        self.save_button.pack(side="right", padx=(10,0))

        self.cancel_button = ctk.CTkButton(button_frame, text="Отмена", command=self.close_window, fg_color="gray")
        self.cancel_button.pack(side="right")
        self.clear_button = ctk.CTkButton(button_frame, text="Очистить все", command=self.clear_preferences,
                                       fg_color="#D32F2F", hover_color="#B71C1C") # Красные цвета
        self.clear_button.pack(side="left", padx=(0, 10)) # Слева от остальных

        self.load_preferences_to_ui()
        self.protocol("WM_DELETE_WINDOW", self.close_window)

    # В классе PreferencesWindow

    def clear_preferences(self):
        # Запросить подтверждение у пользователя
        confirm = messagebox.askyesno("Подтверждение",
                                    "Ты уверен, что хочешь удалить все свои предпочтения?\n"
                                    "CatNap забудет все, что ты ему рассказал о себе.",
                                    parent=self)
        if confirm:
            # Очистить поля в UI
            self.name_entry.delete(0, "end")
            self.hobbies_textbox.delete("1.0", "end")
            self.disliked_topics_textbox.delete("1.0", "end")

            # Создать пустой словарь предпочтений
            cleared_prefs = {
                "user_name": "",
                "hobbies": [],
                "disliked_topics": []
            }
            
            # Обновить предпочтения в главном приложении и сохранить их (как пустые)
            self.master_app.user_preferences = cleared_prefs
            self.master_app._save_preferences() # Сохраняем пустые предпочтения в файл
            self.master_app.on_preferences_updated() # Обновляем сессию Gemini

            messagebox.showinfo("Предпочтения очищены",
                                "Все твои предпочтения были удалены. CatNap теперь ничего о тебе не знает (кроме того, что ты его хозяин, конечно!).",
                                parent=self)
            # Можно и закрыть окно после очистки, если хочешь:
            # self.destroy_window()

    def load_preferences_to_ui(self):
        prefs = self.master_app.user_preferences
        self.name_entry.delete(0, "end") # Очищаем поле перед вставкой
        self.name_entry.insert(0, prefs.get("user_name", ""))

        hobbies_list = prefs.get("hobbies", [])
        self.hobbies_textbox.delete("1.0", "end") # Очищаем текстовое поле
        self.hobbies_textbox.insert("1.0", ", ".join(hobbies_list)) # Вставляем через запятую и пробел

        disliked_list = prefs.get("disliked_topics", [])
        self.disliked_topics_textbox.delete("1.0", "end") # Очищаем текстовое поле
        self.disliked_topics_textbox.insert("1.0", ", ".join(disliked_list)) # Вставляем через запятую и пробел

    def save_and_close(self):
        user_name_str = self.name_entry.get().strip()

        # Хобби: берем текст, разделяем по ЗАПЯТОЙ, убираем пустые строки и лишние пробелы
        hobbies_input_str = self.hobbies_textbox.get("1.0", "end-1c").strip()
        hobbies_list = [hob.strip() for hob in hobbies_input_str.split(',') if hob.strip()] if hobbies_input_str else []

        # Избегаемые темы: аналогично, по ЗАПЯТОЙ
        disliked_input_str = self.disliked_topics_textbox.get("1.0", "end-1c").strip()
        disliked_list = [topic.strip() for topic in disliked_input_str.split(',') if topic.strip()] if disliked_input_str else []
        
        new_prefs = {
            "user_name": user_name_str,
            "hobbies": hobbies_list,
            "disliked_topics": disliked_list
        }
        self.master_app.user_preferences = new_prefs
        self.master_app._save_preferences()
        self.master_app.on_preferences_updated()
        messagebox.showinfo("Предпочтения", "Твои предпочтения сохранены! CatNap постарается их учесть.", parent=self)
        self.destroy_window()

    def close_window(self):
        self.destroy_window()

    def destroy_window(self):
        if self.master_app: # Проверка на случай, если master_app уже None
             self.master_app.preferences_window_instance = None
        self.destroy()

class AboutWindow(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("О программе")
        self.geometry("450x400")
        self.attributes("-topmost", True)
        self.resizable(False, False)
        main_frame = ctk.CTkFrame(self, fg_color="transparent")
        main_frame.pack(padx=20, pady=20, expand=True, fill="both")
        main_frame.grid_rowconfigure(0, weight=0); main_frame.grid_rowconfigure(1, weight=1); main_frame.grid_rowconfigure(2, weight=0)
        main_frame.grid_columnconfigure(0, weight=1); main_frame.grid_columnconfigure(1, weight=0)
        program_name_label = ctk.CTkLabel(main_frame, text="CatNap Desktop Assistant", font=ctk.CTkFont(size=18, weight="bold"))
        program_name_label.grid(row=0, column=0, padx=(0,10), pady=(0,10), sticky="nw")
        try:
            about_sprite_pil = Image.open(SPRITE_IMAGE_PATH); sprite_width_orig, sprite_height_orig = about_sprite_pil.size
            aspect_ratio = sprite_height_orig / sprite_width_orig; new_sprite_width = 70; new_sprite_height = int(new_sprite_width * aspect_ratio)
            resized_sprite = about_sprite_pil.resize((new_sprite_width, new_sprite_height), Image.Resampling.LANCZOS)
            self.about_sprite_ctk = ctk.CTkImage(light_image=resized_sprite, dark_image=resized_sprite, size=(new_sprite_width, new_sprite_height))
            sprite_label = ctk.CTkLabel(main_frame, text="", image=self.about_sprite_ctk)
            sprite_label.grid(row=0, column=1, rowspan=2, padx=(10,0), pady=(0,10), sticky="ne")
        except Exception as e:
            print(f"Ошибка загрузки спрайта для окна 'О программе': {e}")
            sprite_label = ctk.CTkLabel(main_frame, text="[спрайт]", width=70, height=90)
            sprite_label.grid(row=0, column=1, rowspan=2, padx=(10,0), pady=(0,10), sticky="ne")
        text_content_holder = ctk.CTkScrollableFrame(main_frame, fg_color="transparent")
        text_content_holder.grid(row=1, column=0, sticky="nsew", pady=(5,0))
        description_text = ("CatNap - это милый и немного сонный виртуальный ассистент "
            "в виде фиолетового кота, который живет на вашем рабочем столе. "
            "Он умеет общаться, выполнять команды и даже смотреть на экран!")
        desc_label = ctk.CTkLabel(text_content_holder, text=description_text, wraplength=280, justify="left"); desc_label.pack(pady=5, anchor="w", fill="x")
        credits_label = ctk.CTkLabel(text_content_holder, text="Идея: VladGamePlay\nРеализация: Gemini", justify="left"); credits_label.pack(pady=(10,5), anchor="w")
        tech_label_title = ctk.CTkLabel(text_content_holder, text="Технологии:", font=ctk.CTkFont(weight="bold")); tech_label_title.pack(pady=(10,0), anchor="w")
        tech_text = ("- Python\n- CustomTkinter\n- Google Gemini API\n- Pillow (PIL)\n- mss (скриншоты)"); tech_label_content = ctk.CTkLabel(text_content_holder, text=tech_text, justify="left"); tech_label_content.pack(anchor="w")
        version_year_label = ctk.CTkLabel(text_content_holder, text=f"Версия: {APP_VERSION}\nГод: {APP_YEAR}", justify="left"); version_year_label.pack(pady=(10,0), anchor="w")
        close_button = ctk.CTkButton(main_frame, text="Закрыть", command=self.destroy_window, width=100); close_button.grid(row=2, column=0, columnspan=2, pady=(20,0), sticky="s")
        self.protocol("WM_DELETE_WINDOW", self.destroy_window)

    def destroy_window(self):
        if self.master: # Проверка на случай, если master уже None
            self.master.about_window_instance = None
        self.destroy()

class ChatWindow(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.master_app = master
        self.title("Диалог с CatNap"); self.geometry("400x500"); self.attributes("-topmost", True); self.protocol("WM_DELETE_WINDOW", self.hide_window)
        self.grid_columnconfigure(0, weight=1); self.grid_rowconfigure(0, weight=1)
        self.chat_history_textbox = ctk.CTkTextbox(self, state="disabled", wrap="word", font=("Arial", 14)); self.chat_history_textbox.grid(row=0, column=0, padx=10, pady=(10,0), sticky="nsew")
        self.input_frame = ctk.CTkFrame(self); self.input_frame.grid(row=1, column=0, padx=10, pady=10, sticky="ew"); self.input_frame.grid_columnconfigure(0, weight=1)
        self.user_input_entry = ctk.CTkEntry(self.input_frame, placeholder_text="Спроси что-нибудь у CatNap...", font=("Arial", 14)); self.user_input_entry.grid(row=0, column=0, padx=(0,5), pady=5, sticky="ew"); self.user_input_entry.bind("<Return>", self.send_message_event)
        self.send_button = ctk.CTkButton(self.input_frame, text="Отправить", command=self.send_message, font=("Arial", 14)); self.send_button.grid(row=0, column=1, padx=(0,0), pady=5, sticky="e")
        self.clear_button = ctk.CTkButton(self.input_frame, text="Очистить", command=self.clear_chat_history, font=("Arial", 13), width=80); self.clear_button.grid(row=0, column=2, padx=(5,0), pady=5, sticky="e")

    def set_initial_greeting(self):
        self.chat_history_textbox.configure(state="normal"); self.chat_history_textbox.delete("1.0", "end"); self.chat_history_textbox.configure(state="disabled")
        if self.master_app.chat_session: greeting = self.master_app.get_current_greeting(); self.add_message_to_chat("CatNap", greeting)
        elif self.master_app.gemini_api_error_message: self.add_message_to_chat("CatNap", f"Мррр... {self.master_app.gemini_api_error_message}")
        else: self.add_message_to_chat("CatNap", "Мррр... API не настроен, но я все равно тут. *мурлычет*")

    def clear_chat_history(self, add_greeting=True):
        self.chat_history_textbox.configure(state="normal"); self.chat_history_textbox.delete("1.0", "end"); self.chat_history_textbox.configure(state="disabled")
        if self.master_app.gemini_model and self.master_app.chat_session:
            try:
                current_system_instruction = self.master_app.get_current_system_instruction()
                self.master_app._start_chat_session(system_instruction_override=current_system_instruction, history_to_keep=[])
                print("История чата Gemini сброшена, сессия перезапущена с текущим настроением.");
                if add_greeting: greeting = self.master_app.get_current_greeting(default_on_clear="Мррр... Всё забыл, начнем сначала? *потягивается*"); self.add_message_to_chat("CatNap", greeting)
            except Exception as e:
                print(f"Ошибка при сбросе сессии Gemini: {e}");
                if add_greeting: self.add_message_to_chat("CatNap", "Мррр... Память почистил, а вот мысли... *задумался*")
        elif add_greeting: self.add_message_to_chat("CatNap", "Мррр... Доска чиста!")

    def send_message(self, direct_prompt=None, sender_override=None, is_vision_response=False):
        user_text_original = "";
        if direct_prompt:
            user_text_original = direct_prompt
            if not sender_override: self.add_message_to_chat("Ты (команда)", user_text_original)
        else:
            user_text_original = self.user_input_entry.get()
            if not user_text_original.strip(): return
            self.add_message_to_chat("Ты", user_text_original); self.user_input_entry.delete(0, "end")

        user_text_lower = user_text_original.lower().strip(); command_processed_locally = False
        for keyword in EXECUTE_KEYWORDS:
            if user_text_lower.startswith(keyword + " "):
                target_program_name = user_text_lower[len(keyword):].strip()
                if target_program_name: self.master_app._execute_program(target_program_name); command_processed_locally = True; break
        if command_processed_locally: return

        for keyword in SEARCH_KEYWORDS:
            if user_text_lower.startswith(keyword + " "):
                search_query = user_text_original[len(keyword):].strip()
                if search_query: self.master_app._search_web(search_query); command_processed_locally = True; break
        if command_processed_locally: return

        active_session = self.master_app.chat_session if not is_vision_response else None
        active_model_for_onetime_request = self.master_app.gemini_model if not is_vision_response else self.master_app.gemini_vision_model
        if (active_session or active_model_for_onetime_request) and not is_vision_response :
            if not active_session: self.add_message_to_chat("CatNap", "Ой... Кажется, я потерял нить разговора. Попробуй перезапустить чат."); return
            try:
                thinking_message = "Мрр... думаю...";
                if sender_override: thinking_message = "Мрр... обдумываю твою просьбу..."
                self.add_message_to_chat("CatNap", thinking_message); self.update_idletasks()
                response = active_session.send_message(user_text_original)
                self.chat_history_textbox.configure(state="normal"); all_text = self.chat_history_textbox.get("1.0", "end-1c")
                full_thinking_message_search = f"CatNap: {thinking_message}"; last_catnap_msg_start_str_index = all_text.rfind(full_thinking_message_search)
                if last_catnap_msg_start_str_index != -1:
                    text_after_found = all_text[last_catnap_msg_start_str_index + len(full_thinking_message_search):]
                    if not text_after_found.strip():
                        start_delete_index = self.chat_history_textbox.index(f"1.0 + {last_catnap_msg_start_str_index} chars")
                        self.chat_history_textbox.delete(start_delete_index, "end-1c")
                self.chat_history_textbox.configure(state="disabled")
                catnap_response_text = response.text; response_sender_name = sender_override if sender_override else "CatNap"
                self.add_message_to_chat(response_sender_name, catnap_response_text)
            except genai.types.BlockedPromptException as bpe: print(f"Запрос к Gemini был заблокирован: {bpe}"); self.add_message_to_chat("CatNap", "Ой... Что-то в твоих словах мне не понравилось. Не буду отвечать. *отворачивается*")
            except Exception as e: print(f"Ошибка при общении с Gemini: {e}"); self.add_message_to_chat("CatNap", "Ой... Кажется, у меня мысли запутались. Попробуй еще раз.")
        elif is_vision_response: self.add_message_to_chat("CatNap", "Мрр... (Это сообщение должно быть обработано в handle_vision_action)")
        elif self.master_app.gemini_api_error_message: self.add_message_to_chat("CatNap", f"Извини, я сейчас не могу подключиться к своим мыслям ({self.master_app.gemini_api_error_message}).")
        else: self.add_message_to_chat("CatNap", "Извини, я сейчас не могу подключиться к своим мыслям (API не настроен).")

    def show_window(self):
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
        self.title("CatNap")
        self.overrideredirect(True)
        self.attributes("-topmost", True)

        self.gemini_model = None; self.chat_session = None; self.gemini_vision_model = None
        self.gemini_api_error_message = None
        self.generation_config_text = { "temperature": 0.7, "top_p": 1, "top_k": 1, "max_output_tokens": 2048, }
        self.safety_settings = [ {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"}, {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"}, {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"}, {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"}, ]
        self.current_mood = Mood.NEUTRAL; self.is_mood_enabled = True; self.mood_timer_id = None

        self.user_preferences = {}
        self.preferences_window_instance = None
        self._load_preferences()

        self._initialize_gemini_models()
        try:
            self.catnap_image_pil = Image.open(SPRITE_IMAGE_PATH); original_width, original_height = self.catnap_image_pil.size
            ratio = min(WINDOW_TARGET_WIDTH / original_width, WINDOW_TARGET_HEIGHT / original_height); new_width = int(original_width * ratio); new_height = int(original_height * ratio)
            resized_image_pil = self.catnap_image_pil.resize((new_width, new_height), Image.Resampling.LANCZOS)
            self.catnap_ctk_image = ctk.CTkImage(light_image=resized_image_pil, dark_image=resized_image_pil, size=(new_width, new_height))
            screen_width = self.winfo_screenwidth(); screen_height = self.winfo_screenheight(); x_pos = screen_width - new_width - 50; y_pos = screen_height - new_height - 100
            self.geometry(f"{new_width}x{new_height}+{x_pos}+{y_pos}")
            self.sprite_label = ctk.CTkLabel(self, text="", image=self.catnap_ctk_image, fg_color="transparent"); self.sprite_label.pack(expand=True, fill="both")
        except Exception as e:
            print(f"Ошибка загрузки спрайта: {e}"); new_width, new_height = WINDOW_TARGET_WIDTH, WINDOW_TARGET_HEIGHT
            screen_width = self.winfo_screenwidth(); screen_height = self.winfo_screenheight(); x_pos = screen_width - new_width - 50; y_pos = screen_height - new_height - 100
            self.geometry(f"{new_width}x{new_height}+{x_pos}+{y_pos}")
            self.sprite_label = ctk.CTkLabel(self, text="Спрайт\nне найден!", font=("Arial", 16)); self.sprite_label.pack(expand=True, fill="both", padx=10, pady=10)

        self.sprite_label.bind("<ButtonPress-1>", self.start_drag); self.sprite_label.bind("<B1-Motion>", self.do_drag); self.sprite_label.bind("<Button-3>", self.show_context_menu); self.sprite_label.bind("<Double-Button-1>", self.toggle_chat_window)
        self.chat_window_instance = ChatWindow(self); self.chat_window_instance.withdraw()
        self.about_window_instance = None
        self._setup_context_menu()
        if self.is_mood_enabled: self._set_initial_mood_and_start_timer()

    def _get_preferences_path(self):
        return os.path.join(os.path.dirname(os.path.abspath(__file__)), PREFERENCES_FILE_NAME)

    def _load_preferences(self):
        path = self._get_preferences_path()
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    self.user_preferences = json.load(f)
                print(f"Предпочтения пользователя загружены из {path}: {self.user_preferences}")
            except json.JSONDecodeError:
                print(f"Ошибка декодирования JSON в файле предпочтений: {path}. Используются значения по умолчанию.")
                self.user_preferences = {}
            except Exception as e:
                print(f"Ошибка загрузки файла предпочтений {path}: {e}. Используются значения по умолчанию.")
                self.user_preferences = {}
        else:
            print(f"Файл предпочтений {path} не найден. Используются значения по умолчанию.")
            self.user_preferences = {"user_name": "", "hobbies": [], "disliked_topics": []} # Инициализируем ключи

    def _save_preferences(self):
        path = self._get_preferences_path()
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self.user_preferences, f, ensure_ascii=False, indent=4)
            print(f"Предпочтения пользователя сохранены в {path}")
        except Exception as e:
            print(f"Ошибка сохранения файла предпочтений {path}: {e}")
            parent_window = self.preferences_window_instance if self.preferences_window_instance and self.preferences_window_instance.winfo_exists() else self
            messagebox.showerror("Ошибка", f"Не удалось сохранить предпочтения: {e}", parent=parent_window)

    def show_preferences_window(self):
        if self.preferences_window_instance is None or not self.preferences_window_instance.winfo_exists():
            self.preferences_window_instance = PreferencesWindow(self)
        else:
            self.preferences_window_instance.lift()
            self.preferences_window_instance.focus_set()
        self.preferences_window_instance.update_idletasks()
        width = self.preferences_window_instance.winfo_width(); height = self.preferences_window_instance.winfo_height()
        if width <= 1: width = 500
        if height <= 1: height = 450
        screen_width = self.winfo_screenwidth(); screen_height = self.winfo_screenheight()
        x = (screen_width // 2) - (width // 2); y = (screen_height // 2) - (height // 2)
        self.preferences_window_instance.geometry(f'{width}x{height}+{x}+{y}')
        self.preferences_window_instance.deiconify()

    def on_preferences_updated(self):
        print("Предпочтения обновлены, перезапускаем чат-сессию Gemini...")
        self._start_chat_session()
        chat_win = self.get_chat_window()
        if chat_win.winfo_viewable():
            chat_win.add_message_to_chat("CatNap (система)", "Мрр... Я запомнил твои новые предпочтения!")

    def _execute_program(self, program_name_query: str):
        chat_win = self.get_chat_window() # ИСПРАВЛЕНО: точка с запятой убрана
        if not chat_win.winfo_viewable():
            self.toggle_chat_window(center_on_sprite=False) # ИСПРАВЛЕНО: отступ

        program_to_run = KNOWN_PROGRAMS.get(program_name_query.lower())
        if program_to_run == "_BROWSER_":
            try:
                webbrowser.open("https://google.com")
                chat_win.add_message_to_chat("CatNap", "Мяу! Открываю твой браузер по умолчанию.")
            except Exception as e:
                chat_win.add_message_to_chat("CatNap", f"Упс... Не смог открыть браузер. Ошибка: {e}")
        elif program_to_run:
            try:
                subprocess.Popen(program_to_run)
                display_name = program_name_query.replace(".exe", "")
                chat_win.add_message_to_chat("CatNap", f"Мяу! Открываю {display_name} для тебя.")
            except FileNotFoundError:
                chat_win.add_message_to_chat("CatNap", f"Ой... Не смог найти программу '{program_name_query}'. Может, она не установлена или я ее не знаю?")
            except Exception as e:
                chat_win.add_message_to_chat("CatNap", f"Мрр... Что-то пошло не так при попытке открыть '{program_name_query}'. Ошибка: {e}")
        else:
            known_apps_list = ", ".join(sorted(list(set(k for k, v in KNOWN_PROGRAMS.items() if not k.endswith(".exe") and v != "_BROWSER_"))))
            chat_win.add_message_to_chat("CatNap", f"Прости, я не умею открывать '{program_name_query}'. Попробуй что-то из этого: браузер, {known_apps_list}.")

    def _search_web(self, query: str):
        chat_win = self.get_chat_window() # ИСПРАВЛЕНО: точка с запятой убрана
        if not chat_win.winfo_viewable():
            self.toggle_chat_window(center_on_sprite=False) # ИСПРАВЛЕНО: отступ

        query_lower = query.lower(); catnap_response = ""
        if "котик" in query_lower or "котят" in query_lower or "котов" in query_lower or "кошек" in query_lower:
            offended_responses = [ "Мрр?! Других котиков? А я тебе чем не милый? *надулся*", "Искать других котиков, когда у тебя есть я?! Ну спасибо... *отвернулся*", "Пфф... Конечно, давай посмотрим на ДРУГИХ котиков. Я не ревную. Ни капельки. *смотрит в сторону*", "Серьезно? Еще котики? Мне тут одиноко становится от таких запросов! *вздохнул*" ]
            catnap_response = random.choice(offended_responses)
            chat_win.add_message_to_chat("CatNap", catnap_response)
            chat_win.update_idletasks()
            self._open_browser_for_search(query)
        else:
            catnap_response = f"Мрр... Ищу '{query}' в интернете для тебя. *щелкает мышкой*"
            chat_win.add_message_to_chat("CatNap", catnap_response)
            self._open_browser_for_search(query)

    def _open_browser_for_search(self, query: str):
        chat_win = self.get_chat_window()
        try:
            url = f"https://www.google.com/search?q={query.replace(' ', '+')}"
            webbrowser.open(url)
        except Exception as e:
            if chat_win.winfo_viewable():
                chat_win.add_message_to_chat("CatNap", f"Упс... Не смог открыть браузер для поиска. Ошибка: {e}")
            else:
                print(f"Ошибка открытия браузера (окно чата скрыто): {e}")

    def _initialize_gemini_models(self):
        try:
            if not GEMINI_API_KEY or GEMINI_API_KEY == "ВАШ_API_КЛЮЧ_СЮДА":
                warning_msg = "API ключ Gemini не установлен. Функционал чата будет ограничен."
                print(f"ПРЕДУПРЕЖДЕНИЕ: {warning_msg}")
                self.gemini_api_error_message = warning_msg; return
            genai.configure(api_key=GEMINI_API_KEY)
            self.gemini_model = genai.GenerativeModel( model_name="gemini-2.5-flash-preview-05-20", generation_config=self.generation_config_text, safety_settings=self.safety_settings )
            print("Gemini текстовая модель-шаблон успешно инициализирована.")
            try:
                self.gemini_vision_model = genai.GenerativeModel( model_name="gemini-2.5-flash-preview-05-20", safety_settings=self.safety_settings )
                print("Gemini Vision модель успешно инициализирована.")
            except Exception as e_vision:
                error_msg = f"Ошибка инициализации Gemini Vision модели: {e_vision}. Функция 'видения' будет недоступна."
                print(error_msg)
                if not self.gemini_api_error_message: self.gemini_api_error_message = "Проблемы с Vision API."
                self.gemini_vision_model = None
            self._start_chat_session()
        except Exception as e:
            error_msg = f"Критическая ошибка инициализации Gemini API: {e}"
            print(error_msg)
            self.gemini_api_error_message = error_msg
            self.gemini_model = None; self.chat_session = None; self.gemini_vision_model = None

    def get_current_system_instruction(self):
        mood_instruction = MOOD_PROMPT_ADDITIONS.get(self.current_mood, "")
        prefs_instruction_parts = []
        user_name = self.user_preferences.get("user_name")
        if user_name:
            prefs_instruction_parts.append(f"Пользователя зовут {user_name}. Можешь обращаться к нему по имени, если это уместно.")
        hobbies = self.user_preferences.get("hobbies", [])
        if hobbies:
            hobbies_str = ", ".join(hobbies)
            prefs_instruction_parts.append(f"Его хобби и интересы: {hobbies_str}. Постарайся иногда упоминать их или предлагать связанные темы, если это естественно вписывается в разговор.")
        disliked_topics = self.user_preferences.get("disliked_topics", [])
        if disliked_topics:
            disliked_str = ", ".join(disliked_topics)
            prefs_instruction_parts.append(f"Пожалуйста, избегай упоминания следующих тем: {disliked_str}.")
        prefs_instruction = " ".join(prefs_instruction_parts)
        full_instruction = f"{BASE_SYSTEM_INSTRUCTION} {mood_instruction} {prefs_instruction}".strip().replace("  ", " ")
        # print(f"DEBUG SysPrompt: {full_instruction}") # Для отладки
        return full_instruction


    def _start_chat_session(self, system_instruction_override=None, history_to_keep=None):
        if not self.gemini_model:
            print("Невозможно запустить чат-сессию: текстовая модель Gemini не инициализирована."); return
        current_history = []
        if history_to_keep is not None: current_history = history_to_keep
        elif self.chat_session:
            current_history = self.chat_session.history
            print(f"Сохранено {len(current_history)} сообщений из предыдущей сессии.")
        instruction_to_use = system_instruction_override if system_instruction_override else self.get_current_system_instruction()
        try:
            self.gemini_model = genai.GenerativeModel( model_name="gemini-2.5-flash-preview-05-20", generation_config=self.generation_config_text, safety_settings=self.safety_settings, system_instruction=instruction_to_use )
            self.chat_session = self.gemini_model.start_chat(history=current_history)
            print(f"Чат-сессия Gemini запущена/перезапущена. Текущее настроение: {self.current_mood}")
        except Exception as e:
            print(f"Ошибка при (пере)запуске чат-сессии Gemini: {e}")
            self.gemini_api_error_message = f"Ошибка чат-сессии: {e}"

    def get_current_greeting(self, default_on_clear=None):
        if default_on_clear: return default_on_clear
        return MOOD_GREETINGS.get(self.current_mood, MOOD_GREETINGS[Mood.NEUTRAL])

    def _setup_context_menu(self):
        self.context_menu = tkinter.Menu(self, tearoff=0)
        catnap_bg = "#4a2b63"; catnap_fg = "#e6e6fa"; catnap_active_bg = "#6a3b83"; catnap_active_fg = "#ffffff"
        self.context_menu.configure(bg=catnap_bg, fg=catnap_fg, activebackground=catnap_active_bg, activeforeground=catnap_active_fg, relief=tkinter.FLAT, bd=2)
        self.menu_actions = {
            "Подумай об этом": "Представь, что ты лениво размышляешь о чем-то случайном. Поделись этой мыслью (коротко).",
            "О чём задумался?": "Что сейчас занимает твои кошачьи мысли? Расскажи в двух словах.",
            "Что скажешь?": "Мяукни что-нибудь забавное или мудрое от себя, CatNap.",
            "Посмотри вокруг": "SCREENSHOT_COMMAND"
        }
        for label, command_or_prompt in self.menu_actions.items():
            if command_or_prompt == "SCREENSHOT_COMMAND": self.context_menu.add_command(label=label, command=self.handle_vision_action, background=catnap_bg, foreground=catnap_fg, activebackground=catnap_active_bg, activeforeground=catnap_active_fg)
            else: self.context_menu.add_command(label=label, command=lambda p=command_or_prompt, l=label: self.handle_menu_action(p, l), background=catnap_bg, foreground=catnap_fg, activebackground=catnap_active_bg, activeforeground=catnap_active_fg)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Открыть/Скрыть чат", command=self.toggle_chat_window_from_menu, background=catnap_bg, foreground=catnap_fg, activebackground=catnap_active_bg, activeforeground=catnap_active_fg)
        self.settings_menu = tkinter.Menu(self.context_menu, tearoff=0, bg=catnap_bg, fg=catnap_fg, activebackground=catnap_active_bg, activeforeground=catnap_active_fg)
        self.context_menu.add_cascade(label="Настройки", menu=self.settings_menu)
        self.mood_enabled_var = tkinter.BooleanVar(value=self.is_mood_enabled)
        self.settings_menu.add_checkbutton( label="Живой КэтНэп (смена настроений)", variable=self.mood_enabled_var, command=self.toggle_mood_functionality, background=catnap_bg, foreground=catnap_fg, activebackground=catnap_active_bg, activeforeground=catnap_active_fg, selectcolor=catnap_active_fg if ctk.get_appearance_mode().lower() == "dark" else "#cccccc" )
        self.settings_menu.add_command(label="Мои предпочтения...", command=self.show_preferences_window, background=catnap_bg, foreground=catnap_fg, activebackground=catnap_active_bg, activeforeground=catnap_active_fg)
        self.context_menu.add_command(label="Обо мне", command=self.show_about_window, background=catnap_bg, foreground=catnap_fg, activebackground=catnap_active_bg, activeforeground=catnap_active_fg)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Выход", command=self.quit_app, background=catnap_bg, foreground=catnap_fg, activebackground=catnap_active_bg, activeforeground=catnap_active_fg)

    def toggle_mood_functionality(self):
        self.is_mood_enabled = self.mood_enabled_var.get(); print(f"Смена настроений теперь: {'Включена' if self.is_mood_enabled else 'Выключена'}")
        chat_win = self.get_chat_window()
        if self.is_mood_enabled:
            self._set_initial_mood_and_start_timer() # Это уже вызовет _start_chat_session с новым промптом
            if chat_win.winfo_viewable(): chat_win.add_message_to_chat("CatNap (система)", f"Мрр... Я снова буду менять настроение! Текущее: {self.current_mood.lower()}.")
        else:
            if self.mood_timer_id: self.after_cancel(self.mood_timer_id); self.mood_timer_id = None; print("Таймер смены настроений остановлен.")
            self.current_mood = Mood.NEUTRAL
            self.on_preferences_updated() # Обновляем сессию, чтобы убрать влияние настроения, но оставить предпочтения
            if chat_win.winfo_viewable():
                chat_win.add_message_to_chat("CatNap (система)", "Мрр... Больше не буду менять настроение. Буду просто собой.")
                chat_win.set_initial_greeting()

    def _set_initial_mood_and_start_timer(self):
        possible_initial_moods = [m for m in ALL_MOODS_LIST if m != Mood.NEUTRAL];
        if not possible_initial_moods: possible_initial_moods = [Mood.NEUTRAL]
        self.current_mood = random.choice(possible_initial_moods); print(f"Установлено начальное настроение: {self.current_mood}")
        self._start_chat_session(); self._schedule_next_mood_change()

    def _change_mood(self):
        if not self.is_mood_enabled: return
        available_moods = [m for m in ALL_MOODS_LIST if m != self.current_mood];
        if not available_moods: available_moods = ALL_MOODS_LIST[:]
        self.current_mood = random.choice(available_moods); print(f"CatNap изменил настроение на: {self.current_mood}")
        self._start_chat_session()
        chat_win = self.get_chat_window()
        if chat_win.winfo_viewable(): chat_win.add_message_to_chat("CatNap (система)", f"*Кажется, CatNap теперь немного {self.current_mood.lower()}*")
        self._schedule_next_mood_change()

    def _schedule_next_mood_change(self):
        if not self.is_mood_enabled: return
        if self.mood_timer_id: self.after_cancel(self.mood_timer_id)
        delay_ms = random.randint(MOOD_CHANGE_INTERVAL_MIN_MS, MOOD_CHANGE_INTERVAL_MAX_MS); print(f"Следующая смена настроения через: {delay_ms // 1000 // 60} минут ({delay_ms} мс)")
        self.mood_timer_id = self.after(delay_ms, self._change_mood)

    def handle_menu_action(self, prompt_to_gemini, action_label):
        chat_win = self.get_chat_window();
        if not chat_win.winfo_viewable(): self.toggle_chat_window(center_on_sprite=False)
        chat_win.send_message(direct_prompt=prompt_to_gemini, sender_override=f"CatNap ({action_label})", is_vision_response=False)

    def handle_vision_action(self): # ИСПРАВЛЕНО
        if not self.gemini_vision_model:
            chat_win = self.get_chat_window()
            if not chat_win.winfo_viewable():
                self.toggle_chat_window(center_on_sprite=False)
            chat_win.add_message_to_chat("CatNap", "Мрр... Кажется, мои глазки сегодня не видят (Vision API не настроен).")
            return

        chat_win = self.get_chat_window()
        if not chat_win.winfo_viewable():
            self.toggle_chat_window(center_on_sprite=False)

        chat_win.add_message_to_chat("CatNap", "Мрр... Осматриваюсь... *щелк* (делаю фото)")
        chat_win.update_idletasks()
        try:
            with mss.mss() as sct:
                monitor = sct.monitors[1]
                sct_img = sct.grab(monitor)
                img = Image.frombytes("RGB", (sct_img.width, sct_img.height), sct_img.rgb)

            prompt_text = "Что ты видишь на этом скриншоте? Опиши кратко, что привлекло твое кошачье внимание. Будь ленивым и забавным, как обычно."
            chat_win.add_message_to_chat("CatNap", "Мрр... разглядываю фото...")
            chat_win.update_idletasks()
            response = self.gemini_vision_model.generate_content([img, prompt_text])

            chat_win.chat_history_textbox.configure(state="normal")
            all_text = chat_win.chat_history_textbox.get("1.0", "end-1c")
            thinking_message = "Мрр... разглядываю фото..."
            full_thinking_message_search = f"CatNap: {thinking_message}"
            last_catnap_msg_start_str_index = all_text.rfind(full_thinking_message_search)
            if last_catnap_msg_start_str_index != -1:
                text_after_found = all_text[last_catnap_msg_start_str_index + len(full_thinking_message_search):]
                if not text_after_found.strip():
                    start_delete_index = chat_win.chat_history_textbox.index(f"1.0 + {last_catnap_msg_start_str_index} chars")
                    chat_win.chat_history_textbox.delete(start_delete_index, "end-1c")
            chat_win.chat_history_textbox.configure(state="disabled")
            vision_response_text = response.text
            chat_win.add_message_to_chat("CatNap (увидел)", f"*лениво огляделся* {vision_response_text}")
        except genai.types.BlockedPromptException as bpe:
            print(f"Запрос к Vision API был заблокирован: {bpe}")
            chat_win.add_message_to_chat("CatNap", "Ой, что-то мне не понравилось на этом скриншоте... Не буду смотреть. *отворачивается*")
        except Exception as e:
            print(f"Ошибка при работе с Vision API или скриншотом: {e}")
            import traceback; traceback.print_exc()
            chat_win.add_message_to_chat("CatNap", "Мяу... Кажется, у меня что-то с глазками или фото не получилось.")

    def show_about_window(self):
        if self.about_window_instance is None or not self.about_window_instance.winfo_exists():
            self.about_window_instance = AboutWindow(self)
        else:
            self.about_window_instance.lift(); self.about_window_instance.focus_set()
        self.about_window_instance.update_idletasks()
        width = self.about_window_instance.winfo_width(); height = self.about_window_instance.winfo_height()
        if width <= 1: width = 450
        if height <= 1: height = 400
        screen_width = self.winfo_screenwidth(); screen_height = self.winfo_screenheight()
        x = (screen_width // 2) - (width // 2); y = (screen_height // 2) - (height // 2)
        self.about_window_instance.geometry(f'{width}x{height}+{x}+{y}'); self.about_window_instance.deiconify()

    def get_chat_window(self):
        if self.chat_window_instance is None or not self.chat_window_instance.winfo_exists():
            self.chat_window_instance = ChatWindow(self); self.chat_window_instance.withdraw()
        return self.chat_window_instance

    def toggle_chat_window_from_menu(self): self.toggle_chat_window(center_on_sprite=False)

    def toggle_chat_window(self, event=None, center_on_sprite=True):
        chat_win = self.get_chat_window()
        if chat_win.winfo_viewable():
            chat_win.hide_window()
        else:
            if center_on_sprite:
                sprite_x = self.winfo_x()
                sprite_y = self.winfo_y()
                sprite_width = self.winfo_width()
                sprite_height = self.winfo_height()

                chat_win.update_idletasks() # Важно для получения актуальных размеров, если окно было скрыто
                chat_width = chat_win.winfo_width()
                chat_height = chat_win.winfo_height()

                # Если размеры окна еще не определены (например, первый показ), используем значения по умолчанию
                if chat_width <= 1: chat_width = 400 
                if chat_height <= 1: chat_height = 500

                # Рассчитываем позицию слева от спрайта
                chat_x = sprite_x - chat_width - 10 
                # Если слева не помещается, ставим справа
                if chat_x < 0: # или chat_x + chat_width > self.winfo_screenwidth() / 2 (если хотим ближе к центру)
                    chat_x = sprite_x + sprite_width + 10

                # Центрируем по вертикали относительно спрайта
                chat_y = sprite_y + (sprite_height // 2) - (chat_height // 2)
                
                # Корректируем, чтобы окно не выходило за пределы экрана
                screen_width = self.winfo_screenwidth()
                screen_height = self.winfo_screenheight()

                if chat_x < 0: chat_x = 10
                if chat_x + chat_width > screen_width: chat_x = screen_width - chat_width - 10
                
                if chat_y < 0: chat_y = 10
                if chat_y + chat_height > screen_height: chat_y = screen_height - chat_height - 10
                
                # ИСПРАВЛЕНО ЗДЕСЬ: было +{y}, стало +{chat_y}
                chat_win.geometry(f"{chat_width}x{chat_height}+{chat_x}+{chat_y}")
            
            chat_win.show_window()

    def start_drag(self, event): self.x_drag = event.x; self.y_drag = event.y
    def do_drag(self, event):
        deltax = event.x - self.x_drag; deltay = event.y - self.y_drag
        x = self.winfo_x() + deltax; y = self.winfo_y() + deltay
        self.geometry(f"+{x}+{y}")

    def show_context_menu(self, event): # ИСПРАВЛЕНО
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    def quit_app(self):
        if self.mood_timer_id: self.after_cancel(self.mood_timer_id); self.mood_timer_id = None
        if self.preferences_window_instance and self.preferences_window_instance.winfo_exists(): self.preferences_window_instance.destroy()
        if self.chat_window_instance and self.chat_window_instance.winfo_exists(): self.chat_window_instance.destroy()
        if self.about_window_instance and self.about_window_instance.winfo_exists(): self.about_window_instance.destroy()
        self.destroy()

if __name__ == "__main__":
    try: ctk.set_appearance_mode("System")
    except Exception as e:
        print(f"Не удалось установить системную тему: {e}. Используется 'light'.")
        ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")
    app = CatNapApp()
    app.mainloop()