import customtkinter as ctk
from PIL import Image, ImageTk # ImageTk может понадобиться для Tkinter PhotoImage, но CTkImage должен справиться
import google.generativeai as genai
import os
import tkinter
from tkinter import messagebox
import mss
import io
import random
import time
import subprocess
import webbrowser
import json

# --- Настройки ---
SPRITE_IMAGE_PATH = "assets/catnap_idle3.gif" # Путь к твоему GIF
WINDOW_TARGET_WIDTH = 200 # Эти значения теперь могут быть ориентиром, если GIF масштабируется
WINDOW_TARGET_HEIGHT = 250 # или если GIF не загрузится
APP_VERSION = "1.5.0" # Новая версия
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
        self.name_entry = ctk.CTkEntry(main_frame, width=400); self.name_entry.pack(fill="x", pady=(0,10))

        # Хобби/Интересы
        ctk.CTkLabel(main_frame, text="Твои хобби и интересы (через запятую):").pack(pady=(5,2), anchor="w")
        self.hobbies_textbox = ctk.CTkTextbox(main_frame, height=100, width=400)
        self.hobbies_textbox.pack(fill="x", pady=(0,10))

        # Избегаемые темы
        ctk.CTkLabel(main_frame, text="Темы, которые CatNap стоит избегать (через запятую):").pack(pady=(5,2), anchor="w")
        self.disliked_topics_textbox = ctk.CTkTextbox(main_frame, height=100, width=400)
        self.disliked_topics_textbox.pack(fill="x", pady=(0,20))

        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent"); button_frame.pack(fill="x", pady=(10,0))
        self.save_button = ctk.CTkButton(button_frame, text="Сохранить и закрыть", command=self.save_and_close); self.save_button.pack(side="right", padx=(10,0))
        self.cancel_button = ctk.CTkButton(button_frame, text="Отмена", command=self.close_window, fg_color="gray"); self.cancel_button.pack(side="right")
        self.clear_button = ctk.CTkButton(button_frame, text="Очистить все", command=self.clear_preferences, fg_color="#D32F2F", hover_color="#B71C1C"); self.clear_button.pack(side="left", padx=(0, 10))
        self.load_preferences_to_ui()
        self.protocol("WM_DELETE_WINDOW", self.close_window)

    def load_preferences_to_ui(self):
        prefs = self.master_app.user_preferences
        self.name_entry.insert(0, prefs.get("user_name", ""))

        hobbies_list = prefs.get("hobbies", [])
        # Отображаем хобби через запятую и пробел для лучшей читаемости
        self.hobbies_textbox.insert("1.0", ", ".join(hobbies_list))

        disliked_list = prefs.get("disliked_topics", [])
        # Аналогично для нелюбимых тем
        self.disliked_topics_textbox.insert("1.0", ", ".join(disliked_list))


    def save_and_close(self):
        new_prefs = {
            "user_name": self.name_entry.get().strip(),
        }

        # Обработка хобби
        hobbies_text = self.hobbies_textbox.get("1.0", "end-1c")
        # Сначала заменяем переносы строк на запятые, чтобы иметь единый разделитель
        hobbies_text_normalized = hobbies_text.replace("\n", ",")
        # Затем разделяем по запятой и убираем лишние пробелы и пустые строки
        new_prefs["hobbies"] = [hob.strip() for hob in hobbies_text_normalized.split(",") if hob.strip()]

        # Обработка нелюбимых тем
        disliked_text = self.disliked_topics_textbox.get("1.0", "end-1c")
        disliked_text_normalized = disliked_text.replace("\n", ",")
        new_prefs["disliked_topics"] = [topic.strip() for topic in disliked_text_normalized.split(",") if topic.strip()]
        
        self.master_app.user_preferences = new_prefs
        self.master_app._save_preferences()
        self.master_app.on_preferences_updated()
        messagebox.showinfo("Предпочтения", "Твои предпочтения сохранены! CatNap постарается их учесть.", parent=self)
        self.destroy_window()
    
    def clear_preferences(self):
        confirm = messagebox.askyesno("Подтверждение", "Ты уверен, что хочешь удалить все свои предпочтения?\nCatNap забудет все, что ты ему рассказал о себе.", parent=self)
        if confirm:
            self.name_entry.delete(0, "end"); self.hobbies_textbox.delete("1.0", "end"); self.disliked_topics_textbox.delete("1.0", "end")
            cleared_prefs = {"user_name": "", "hobbies": [], "disliked_topics": []}
            self.master_app.user_preferences = cleared_prefs
            self.master_app._save_preferences()
            self.master_app.on_preferences_updated()
            messagebox.showinfo("Все твои предпочтения были удалены. CatNap теперь ничего о тебе не знает (кроме того, что ты его хозяин, конечно!).", parent=self)

    def close_window(self): self.destroy_window()
    def destroy_window(self):
        if self.master_app: self.master_app.preferences_window_instance = None
        self.destroy()

class AboutWindow(ctk.CTkToplevel):
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
        except Exception as e: print(f"Ошибка загрузки спрайта для окна 'О программе': {e}"); sprite_label = ctk.CTkLabel(main_frame, text="[спрайт]", width=70, height=90); sprite_label.grid(row=0, column=1, rowspan=2, padx=(10,0), pady=(0,10), sticky="ne")
        text_content_holder = ctk.CTkScrollableFrame(main_frame, fg_color="transparent"); text_content_holder.grid(row=1, column=0, sticky="nsew", pady=(5,0))
        description_text = ("CatNap - это милый и немного сонный виртуальный ассистент "
            "в виде фиолетового кота, который живет на вашем рабочем столе. "
            "Он умеет общаться, выполнять команды и даже смотреть на экран!"); desc_label = ctk.CTkLabel(text_content_holder, text=description_text, wraplength=280, justify="left"); desc_label.pack(pady=5, anchor="w", fill="x")
        credits_label = ctk.CTkLabel(text_content_holder, text="Идея: VladGamePlay\nРеализация: Gemini", justify="left"); credits_label.pack(pady=(10,5), anchor="w")
        tech_label_title = ctk.CTkLabel(text_content_holder, text="Технологии:", font=ctk.CTkFont(weight="bold")); tech_label_title.pack(pady=(10,0), anchor="w")
        tech_text = ("- Python\n- CustomTkinter\n- Google Gemini API\n- Pillow (PIL)\n- mss (скриншоты)"); tech_label_content = ctk.CTkLabel(text_content_holder, text=tech_text, justify="left"); tech_label_content.pack(anchor="w")
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

    def set_initial_greeting(self):
        self.chat_history_textbox.configure(state="normal"); self.chat_history_textbox.delete("1.0", "end"); self.chat_history_textbox.configure(state="disabled")
        if self.master_app.chat_session: greeting = self.master_app.get_current_greeting(); self.add_message_to_chat("CatNap", greeting)
        elif self.master_app.gemini_api_error_message: self.add_message_to_chat("CatNap", f"Мррр... {self.master_app.gemini_api_error_message}")
        else: self.add_message_to_chat("CatNap", "Мррр... API не настроен.")
    def clear_chat_history(self, add_greeting=True):
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
        if not direct_prompt: self.add_message_to_chat("Ты", user_text_original); self.user_input_entry.delete(0, "end")
        elif not sender_override: self.add_message_to_chat("Ты (команда)", user_text_original)
        user_text_lower = user_text_original.lower().strip(); command_processed_locally = False
        for keyword in EXECUTE_KEYWORDS:
            if user_text_lower.startswith(keyword + " "):
                target = user_text_lower[len(keyword):].strip()
                if target: self.master_app._execute_program(target); command_processed_locally = True; break
        if command_processed_locally: return
        for keyword in SEARCH_KEYWORDS:
            if user_text_lower.startswith(keyword + " "):
                query = user_text_original[len(keyword):].strip()
                if query: self.master_app._search_web(query); command_processed_locally = True; break
        if command_processed_locally: return
        if self.master_app.chat_session and not is_vision_response:
            try:
                thinking_msg = "Мрр... обдумываю..." if sender_override else "Мрр... думаю..."
                self.add_message_to_chat("CatNap", thinking_msg); self.update_idletasks()
                response = self.master_app.chat_session.send_message(user_text_original)
                # ... (удаление "думающего" сообщения) ...
                self.chat_history_textbox.configure(state="normal"); all_text = self.chat_history_textbox.get("1.0", "end-1c")
                full_search = f"CatNap: {thinking_msg}"; last_idx = all_text.rfind(full_search)
                if last_idx != -1 and not all_text[last_idx + len(full_search):].strip():
                    self.chat_history_textbox.delete(self.chat_history_textbox.index(f"1.0 + {last_idx} chars"), "end-1c")
                self.chat_history_textbox.configure(state="disabled")
                self.add_message_to_chat(sender_override or "CatNap", response.text)
            except Exception as e: self.add_message_to_chat("CatNap", f"Ой... мысли запутались: {e}")
        elif self.master_app.gemini_api_error_message: self.add_message_to_chat("CatNap", f"Нет связи с мыслями ({self.master_app.gemini_api_error_message}).")
        else: self.add_message_to_chat("CatNap", "Нет связи с мыслями (API не настроен).")
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
        self.title("CatNap"); self.overrideredirect(True); self.attributes("-topmost", True)
        self.gemini_model = None; self.chat_session = None; self.gemini_vision_model = None
        self.gemini_api_error_message = None
        self.generation_config_text = { "temperature": 0.7, "top_p": 1, "top_k": 1, "max_output_tokens": 2048, }
        self.safety_settings = [ {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"}, {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"}, {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"}, {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"}, ]
        self.current_mood = Mood.NEUTRAL; self.is_mood_enabled = True; self.mood_timer_id = None
        self.user_preferences = {}; self.preferences_window_instance = None
        self._load_preferences()

        # --- GIF Анимация ---
        self.gif_frames = []
        self.current_gif_frame_index = 0
        self.gif_default_delay = 100 # мс, если в GIF нет информации
        self.gif_animation_job = None
        # --- Конец GIF Анимация ---

        current_theme = ctk.get_appearance_mode().lower()
        transparent_color_to_set = "#2B2B2B" if current_theme == "dark" else "#EBEBEB" # Или #FFFFFF для светлой
        self.configure(fg_color=transparent_color_to_set) # Явно ставим фон окна
        try: self.attributes("-transparentcolor", transparent_color_to_set)
        except tkinter.TclError as e: print(f"Ошибка -transparentcolor: {e}")
        
        self._initialize_gemini_models()
        self._load_and_setup_sprite() # Выносим загрузку спрайта в отдельный метод

        self.sprite_label.bind("<ButtonPress-1>", self.start_drag); self.sprite_label.bind("<B1-Motion>", self.do_drag); self.sprite_label.bind("<Button-3>", self.show_context_menu); self.sprite_label.bind("<Double-Button-1>", self.toggle_chat_window)
        self.chat_window_instance = ChatWindow(self); self.chat_window_instance.withdraw()
        self.about_window_instance = None
        self._setup_context_menu()
        if self.is_mood_enabled: self._set_initial_mood_and_start_timer()

    def _load_and_setup_sprite(self):
        try:
            pil_gif_image = Image.open(SPRITE_IMAGE_PATH)
            original_w, original_h = pil_gif_image.size

            # --- Масштабирование GIF кадров (если нужно) ---
            # Задайте целевые размеры, если GIF не того размера, что вы хотите
            # target_w, target_h = WINDOW_TARGET_WIDTH, WINDOW_TARGET_HEIGHT 
            # Если масштабирование не нужно, используйте original_w, original_h
            target_w, target_h = original_w, original_h # По умолчанию используем оригинальный размер GIF

            # Если вы хотите масштабировать к WINDOW_TARGET_WIDTH/HEIGHT:
            # ratio = min(WINDOW_TARGET_WIDTH / original_w, WINDOW_TARGET_HEIGHT / original_h)
            # target_w = int(original_w * ratio)
            # target_h = int(original_h * ratio)
            # --- Конец блока масштабирования ---

            frame_num = 0
            while True:
                try:
                    pil_gif_image.seek(frame_num)
                    duration = pil_gif_image.info.get('duration', self.gif_default_delay)
                    if duration == 0: duration = self.gif_default_delay
                    
                    frame_pil_copy = pil_gif_image.copy()
                    if (original_w, original_h) != (target_w, target_h): # Масштабируем, если размеры не совпадают
                        frame_pil_copy = frame_pil_copy.resize((target_w, target_h), Image.Resampling.LANCZOS)
                    
                    ctk_frame = ctk.CTkImage(light_image=frame_pil_copy, dark_image=frame_pil_copy, size=(target_w, target_h))
                    self.gif_frames.append({'image': ctk_frame, 'duration': duration})
                    frame_num += 1
                except EOFError: break
            
            if not self.gif_frames: raise ValueError("Нет кадров в GIF.")

            screen_w, screen_h = self.winfo_screenwidth(), self.winfo_screenheight()
            x = screen_w - target_w - 50; y = screen_h - target_h - 100
            self.geometry(f"{target_w}x{target_h}+{x}+{y}")
            self.sprite_label = ctk.CTkLabel(self, text="", image=self.gif_frames[0]['image'], fg_color="transparent")
            self.sprite_label.pack(expand=True, fill="both")
            self._start_gif_animation()
        except Exception as e:
            print(f"Ошибка загрузки спрайта GIF: {e}")
            # Fallback, если GIF не загрузился
            fw, fh = WINDOW_TARGET_WIDTH, WINDOW_TARGET_HEIGHT
            screen_w, screen_h = self.winfo_screenwidth(), self.winfo_screenheight()
            x = screen_w - fw - 50; y = screen_h - fh - 100
            self.geometry(f"{fw}x{fh}+{x}+{y}")
            self.sprite_label = ctk.CTkLabel(self, text="Спрайт GIF\nошибка!", font=("Arial", 16))
            self.sprite_label.pack(expand=True, fill="both", padx=10, pady=10)
            
    def _animate_gif(self):
        if not self.gif_frames or not self.sprite_label.winfo_exists(): return # Проверка существования лейбла
        frame_info = self.gif_frames[self.current_gif_frame_index]
        self.sprite_label.configure(image=frame_info['image'])
        self.current_gif_frame_index = (self.current_gif_frame_index + 1) % len(self.gif_frames)
        self.gif_animation_job = self.after(frame_info['duration'], self._animate_gif)

    def _start_gif_animation(self):
        if self.gif_animation_job: self.after_cancel(self.gif_animation_job)
        self._animate_gif()

    def _stop_gif_animation(self):
        if self.gif_animation_job: self.after_cancel(self.gif_animation_job); self.gif_animation_job = None

    def _get_preferences_path(self): return os.path.join(os.path.dirname(os.path.abspath(__file__)), PREFERENCES_FILE_NAME)
    def _load_preferences(self):
        path = self._get_preferences_path()
        if os.path.exists(path):
            try:
                with open(path, 'r', encoding='utf-8') as f: self.user_preferences = json.load(f)
                print(f"Предпочтения загружены: {self.user_preferences}")
            except Exception as e: print(f"Ошибка загрузки предпочтений: {e}"); self.user_preferences = {"user_name": "", "hobbies": [], "disliked_topics": []}
        else: self.user_preferences = {"user_name": "", "hobbies": [], "disliked_topics": []}
    def _save_preferences(self):
        path = self._get_preferences_path()
        try:
            with open(path, 'w', encoding='utf-8') as f: json.dump(self.user_preferences, f, ensure_ascii=False, indent=4)
            print(f"Предпочтения сохранены.")
        except Exception as e: print(f"Ошибка сохранения предпочтений: {e}"); messagebox.showerror("Ошибка", f"Не удалось сохранить: {e}", parent=self.preferences_window_instance or self)
    def show_preferences_window(self):
        if self.preferences_window_instance is None or not self.preferences_window_instance.winfo_exists(): self.preferences_window_instance = PreferencesWindow(self)
        else: self.preferences_window_instance.lift(); self.preferences_window_instance.focus_set()
        # ... (центрирование PreferencesWindow)
        self.preferences_window_instance.update_idletasks(); w = self.preferences_window_instance.winfo_width(); h = self.preferences_window_instance.winfo_height()
        if w<=1:w=500
        if h<=1:h=450
        sw=self.winfo_screenwidth();sh=self.winfo_screenheight();x=(sw//2)-(w//2);y=(sh//2)-(h//2)
        self.preferences_window_instance.geometry(f"{w}x{h}+{x}+{y}");self.preferences_window_instance.deiconify()

    def on_preferences_updated(self):
        print("Предпочтения обновлены, перезапуск сессии..."); self._start_chat_session()
        if self.chat_window_instance and self.chat_window_instance.winfo_viewable(): self.chat_window_instance.add_message_to_chat("CatNap (система)", "Мрр... Запомнил новые предпочтения!")
    def _execute_program(self, name_query: str):
        # ... (код _execute_program без изменений отступов)
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

    def _search_web(self, query: str):
        # ... (код _search_web без изменений отступов)
        chat_win = self.get_chat_window()
        if not chat_win.winfo_viewable(): self.toggle_chat_window(center_on_sprite=False)
        q_lower = query.lower()
        if any(k in q_lower for k in ["котик", "котят", "котов", "кошек"]):
            responses = ["Других котиков? А я?!", "Опять других котиков... *отвернулся*", "Я не ревную... *смотрит в сторону*"];
            chat_win.add_message_to_chat("CatNap", random.choice(responses)); chat_win.update_idletasks()
        else: chat_win.add_message_to_chat("CatNap", f"Мрр... Ищу '{query}'...");
        self._open_browser_for_search(query)

    def _open_browser_for_search(self, query: str):
        try: webbrowser.open(f"https://www.google.com/search?q={query.replace(' ', '+')}")
        except Exception as e:
            if self.chat_window_instance and self.chat_window_instance.winfo_viewable(): self.chat_window_instance.add_message_to_chat("CatNap", f"Не открыл браузер: {e}")
            else: print(f"Ошибка браузера (чат скрыт): {e}")

    def _initialize_gemini_models(self):
        # ... (код _initialize_gemini_models без изменений)
        try:
            if not GEMINI_API_KEY or GEMINI_API_KEY == "ВАШ_API_КЛЮЧ_СЮДА": self.gemini_api_error_message = "API ключ не найден."; print(self.gemini_api_error_message); return
            genai.configure(api_key=GEMINI_API_KEY)
            self.gemini_model = genai.GenerativeModel(model_name="gemini-2.5-flash-preview-05-20", generation_config=self.generation_config_text, safety_settings=self.safety_settings)
            try: self.gemini_vision_model = genai.GenerativeModel(model_name="gemini-2.5-flash-preview-05-20", safety_settings=self.safety_settings)
            except Exception as e_vis: self.gemini_vision_model = None; print(f"Vision API ошибка: {e_vis}")
            self._start_chat_session()
        except Exception as e: self.gemini_api_error_message = f"Gemini API ошибка: {e}"; print(self.gemini_api_error_message)

    def get_current_system_instruction(self):
        # ... (код get_current_system_instruction с предпочтениями без изменений)
        mood_instr = MOOD_PROMPT_ADDITIONS.get(self.current_mood, "")
        prefs_parts = []
        if self.user_preferences.get("user_name"): prefs_parts.append(f"Пользователя зовут {self.user_preferences['user_name']}.")
        if self.user_preferences.get("hobbies"): prefs_parts.append(f"Его хобби: {', '.join(self.user_preferences['hobbies'])}.")
        if self.user_preferences.get("disliked_topics"): prefs_parts.append(f"Избегай тем: {', '.join(self.user_preferences['disliked_topics'])}.")
        return f"{BASE_SYSTEM_INSTRUCTION} {mood_instr} {' '.join(prefs_parts)}".strip().replace("  ", " ")

    def _start_chat_session(self, system_instruction_override=None, history_to_keep=None):
        # ... (код _start_chat_session без изменений)
        if not self.gemini_model: print("Модель Gemini не инициализирована."); return
        history = history_to_keep if history_to_keep is not None else (self.chat_session.history if self.chat_session else [])
        instruction = system_instruction_override or self.get_current_system_instruction()
        try:
            self.gemini_model = genai.GenerativeModel(model_name="gemini-2.5-flash-preview-05-20", generation_config=self.generation_config_text, safety_settings=self.safety_settings, system_instruction=instruction)
            self.chat_session = self.gemini_model.start_chat(history=history)
            print(f"Сессия Gemini запущена. Настроение: {self.current_mood}")
        except Exception as e: self.gemini_api_error_message = f"Ошибка сессии: {e}"; print(self.gemini_api_error_message)

    def get_current_greeting(self, default_on_clear=None): return default_on_clear or MOOD_GREETINGS.get(self.current_mood, MOOD_GREETINGS[Mood.NEUTRAL])
    def _setup_context_menu(self):
        # ... (код _setup_context_menu с предпочтениями без изменений)
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

    def toggle_mood_functionality(self):
        # ... (код toggle_mood_functionality без изменений)
        self.is_mood_enabled = self.mood_enabled_var.get()
        if self.is_mood_enabled: self._set_initial_mood_and_start_timer()
        else:
            if self.mood_timer_id: self.after_cancel(self.mood_timer_id); self.mood_timer_id=None
            self.current_mood = Mood.NEUTRAL; self.on_preferences_updated() # Обновляем сессию
            if self.chat_window_instance and self.chat_window_instance.winfo_viewable(): self.chat_window_instance.add_message_to_chat("CatNap (система)", "Мрр... Буду просто собой."); self.chat_window_instance.set_initial_greeting()

    def _set_initial_mood_and_start_timer(self): self.current_mood = random.choice([m for m in ALL_MOODS_LIST if m != Mood.NEUTRAL] or [Mood.NEUTRAL]); self._start_chat_session(); self._schedule_next_mood_change()
    def _change_mood(self):
        if not self.is_mood_enabled: return
        self.current_mood = random.choice([m for m in ALL_MOODS_LIST if m != self.current_mood] or ALL_MOODS_LIST[:])
        self._start_chat_session()
        if self.chat_window_instance and self.chat_window_instance.winfo_viewable(): self.chat_window_instance.add_message_to_chat("CatNap (система)", f"*CatNap теперь {self.current_mood.lower()}*")
        self._schedule_next_mood_change()
    def _schedule_next_mood_change(self):
        if not self.is_mood_enabled: return
        if self.mood_timer_id: self.after_cancel(self.mood_timer_id)
        
        delay_ms = random.randint(MOOD_CHANGE_INTERVAL_MIN_MS, MOOD_CHANGE_INTERVAL_MAX_MS)
        
        minutes = delay_ms // 1000 // 60 
        # Или для округления до ближайшей минуты, если хочешь:
        # minutes = round(delay_ms / (1000 * 60))

        print(f"Следующая смена настроения примерно через: {minutes} минут")
        
        self.mood_timer_id = self.after(delay_ms, self._change_mood)
    def handle_menu_action(self, prompt, label):
        if self.chat_window_instance and not self.chat_window_instance.winfo_viewable(): self.toggle_chat_window(center_on_sprite=False)
        self.chat_window_instance.send_message(direct_prompt=prompt, sender_override=f"CatNap ({label})")
    def handle_vision_action(self):
        # ... (код handle_vision_action с исправленными отступами, без изменений логики)
        if not self.gemini_vision_model:
            chat_win = self.get_chat_window();
            if not chat_win.winfo_viewable(): self.toggle_chat_window(center_on_sprite=False)
            chat_win.add_message_to_chat("CatNap", "Глазки не видят (Vision API)."); return
        chat_win = self.get_chat_window();
        if not chat_win.winfo_viewable(): self.toggle_chat_window(center_on_sprite=False)
        chat_win.add_message_to_chat("CatNap", "Мрр... Осматриваюсь..."); chat_win.update_idletasks()
        try:
            with mss.mss() as sct: img = Image.frombytes("RGB", sct.grab(sct.monitors[1]).size, sct.grab(sct.monitors[1]).rgb)
            response = self.gemini_vision_model.generate_content([img, "Опиши скриншот кратко и забавно."])
            chat_win.add_message_to_chat("CatNap (увидел)", f"*Огляделся* {response.text}")
        except Exception as e: chat_win.add_message_to_chat("CatNap", f"Мяу... ошибка зрения: {e}"); traceback.print_exc()

    def show_about_window(self):
        if not self.about_window_instance or not self.about_window_instance.winfo_exists(): self.about_window_instance = AboutWindow(self)
        else: self.about_window_instance.lift()
        # ... (центрирование AboutWindow)
        self.about_window_instance.update_idletasks();w=self.about_window_instance.winfo_width();h=self.about_window_instance.winfo_height();
        if w<=1:w=450
        if h<=1:h=400
        sw=self.winfo_screenwidth();sh=self.winfo_screenheight();x=(sw//2)-(w//2);y=(sh//2)-(h//2)
        self.about_window_instance.geometry(f"{w}x{h}+{x}+{y}");self.about_window_instance.deiconify()


    def get_chat_window(self):
        if not self.chat_window_instance or not self.chat_window_instance.winfo_exists(): self.chat_window_instance = ChatWindow(self); self.chat_window_instance.withdraw()
        return self.chat_window_instance
    def toggle_chat_window_from_menu(self): self.toggle_chat_window(center_on_sprite=False)
    def toggle_chat_window(self, event=None, center_on_sprite=True):
        # ... (код toggle_chat_window без изменений)
        chat_win = self.get_chat_window()
        if chat_win.winfo_viewable(): chat_win.hide_window()
        else:
            if center_on_sprite:
                sprite_x,sprite_y,sprite_w,sprite_h = self.winfo_x(),self.winfo_y(),self.winfo_width(),self.winfo_height()
                chat_win.update_idletasks(); chat_w,chat_h = chat_win.winfo_width(),chat_win.winfo_height()
                if chat_w<=1:chat_w=400
                if chat_h<=1:chat_h=500
                # ... (расчет позиции)
                chat_x=sprite_x-chat_w-10;
                if chat_x<0:chat_x=sprite_x+sprite_w+10
                chat_y=sprite_y+sprite_h//2-chat_h//2;sh=self.winfo_screenheight();
                if chat_y<0:chat_y=10
                elif chat_y+chat_h>sh:chat_y=sh-chat_h-10
                sw=self.winfo_screenwidth();
                if chat_x<0:chat_x=10
                elif chat_x+chat_w>sw:chat_x=sw-chat_w-10
                chat_win.geometry(f"{chat_w}x{chat_h}+{chat_x}+{y}") # Была опечатка y вместо chat_y
            chat_win.show_window()

    def start_drag(self, event): self.x_drag = event.x; self.y_drag = event.y
    def do_drag(self, event): deltax = event.x-self.x_drag; deltay = event.y-self.y_drag; self.geometry(f"+{self.winfo_x()+deltax}+{self.winfo_y()+deltay}")
    def show_context_menu(self, event):
        try: self.context_menu.tk_popup(event.x_root, event.y_root)
        finally: self.context_menu.grab_release()
    def quit_app(self):
        self._stop_gif_animation()
        if self.mood_timer_id: self.after_cancel(self.mood_timer_id)
        for win_ref_name in ["preferences_window_instance", "chat_window_instance", "about_window_instance"]:
            win = getattr(self, win_ref_name, None)
            if win and win.winfo_exists(): win.destroy()
        self.destroy()

if __name__ == "__main__":
    # Для отладки прозрачности можно временно закомментировать set_appearance_mode,
    # чтобы увидеть, как окно выглядит с стандартным фоном Tkinter/Windows
    try: ctk.set_appearance_mode("System")
    except Exception: ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")
    app = CatNapApp()
    app.mainloop()