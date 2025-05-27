# CatNap Desktop Assistant

Милый и полезный настольный ассистент в виде кота CatNap!

## Описание

CatNap - это ваш личный фиолетовый кот-помощник, который живет на рабочем столе. Он умеет:
- Общаться и отвечать на вопросы (с разными настроениями!)
- Запускать программы (Блокнот, Калькулятор, Paint, Браузер)
- Искать информацию в интернете
- Рассказывать о том, что видит на экране (скриншот)
- Учитывать ваши предпочтения (имя, хобби, нелюбимые темы)
- И многое другое в будущих версиях!

## Требования

- Python 3.x
- API ключ для Google Gemini (получить можно [здесь](https://aistudio.google.com/app/apikey))

## Установка и Запуск

1.  **Склонируйте репозиторий:**
    ```bash
    git clone https://github.com/VladGamePlay/catnap-desktop-assistant.git
    cd catnap-desktop-assistant
    ```

2.  **(Рекомендуется) Создайте и активируйте виртуальное окружение:**
    ```bash
    python -m venv venv
    # Windows
    .\venv\Scripts\activate
    # macOS/Linux
    source venv/bin/activate
    ```

3.  **Установите зависимости:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Настройте API ключ:**
    - Скопируйте файл `.env.example` и переименуйте копию в `.env`.
    - Откройте файл `.env` и вставьте свой API ключ Gemini вместо `ВАШ_API_КЛЮЧ_СЮДА`.
      ```
      GEMINI_API_KEY=ВАШ_РЕАЛЬНЫЙ_API_КЛЮЧ
      ```

5.  **Запустите приложение:**
    ```bash
    python catnap_points.py
    ```

## Используемые технологии

- Python
- CustomTkinter
- Google Gemini API
- Pillow
- mss
- python-dotenv

## Автор

- Идея: VladGamePlay
- Основная разработка (с помощью Gemini): VladGamePlay

![Демонстрация CatNap](assets/images/catnap_demo.png) 

Милый и полезный настольный ассистент...

---