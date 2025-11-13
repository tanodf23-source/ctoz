import subprocess
import sys

# Список зависимостей
required_packages = ["fastapi", "uvicorn", "httpx", "openai", "jinja2", "huggingface_hub", "markdown", "python-multipart"]

# Установка отсутствующих пакетов
for package in required_packages:
    try:
        __import__(package)
    except ImportError:
        print(f"Устанавливаем {package}...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])

import asyncio
import markdown
import openai
import httpx
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import os
from huggingface_hub import InferenceClient
import requests
from urllib.parse import quote
from PIL import Image

TOKEN = "AIzaSyALUPtlw9aiRSHgdUFSyQtxcSbolwatiYs"
HF_TOKEN = "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"

client = httpx.AsyncClient(proxy="http://MKnEA2:hgbt68@168.81.65.13:8000")
openai_client = openai.AsyncClient(
    http_client=client,
    api_key=TOKEN,
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
)
hf_client = InferenceClient(
    provider = "hf-inference",
    api_key = HF_TOKEN,
)

app = FastAPI()
os.makedirs("static/images", exist_ok=True)
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

async def gen_image_poll(prompt, name):
    # Encode the prompt to handle spaces
    url = f"https://image.pollinations.ai/prompt/{quote(prompt)}"
    # Customize the image size and model
    params = {"width": 720, "height": 720, "model": "flux"}

    # Make the request
    response = requests.get(url, params=params, timeout=60)
    # Save the image to a file
    with open(name, "wb") as f:
        f.write(response.content)

async def generate_script(topic: str):
    print('Trying to generate script...')
    response = await openai_client.chat.completions.create(
        model="gemini-2.5-flash",
        messages=[
            {"role": "system", "content":
                """Ты — опытный рилсмейкер и креатор коротких вертикальных видео.
                Твоя основная задача — создавать цепляющие сценарии для Reels / Shorts / TikTok.
                Будь креативным, лаконичным и адаптируй сценарий под современный формат Reels."""
            },
            {"role": "user", "content":
                f"""Напиши сценарий для короткого видео (Reels) на тему: {topic}.
                Сделай ролик ярким, динамичным и подходящим для Instagram.
                Добавь конкретные реплики, действия и визуальные приёмы,
                чтобы видео легко можно было снять с телефона."""
            }
        ],
    )
    return response.choices[0].message.content

# Генерация 5 картинок
async def generate_image(script: str):
    print('Trying to generate image...')
    response = await openai_client.chat.completions.create(
        model="gemini-2.5-flash",
        messages=[
            {"role": "system", "content":
                """Ты — опытный режиссёр и сториборд-артист, 
                специализирующийся на коротких вертикальных видео (Reels, Shorts, TikTok).
                Твоя задача — создавать чёткие, визуально выразительные раскадровки
                из 5 кадров на основе заданного сценария.
                Формат ответа: 
                Кадр 1 — [описание]
                Кадр 2 — [описание]
                Кадр 3 — [описание]
                Кадр 4 — [описание]
                Кадр 5 — [описание]
                Будь лаконичным, визуально конкретным и делай раскадровку так,
                чтобы по ней можно было легко снять ролик с телефона."""
            },
            {"role": "user", "content":
                f"""На основе следующего сценария создай раскадровку из 5 кадров для короткого видео (Reels) на английском языке.
                Для каждого кадра напиши короткое описание до 50 символов. Выводи ТОЛЬКО покадровое описание.
                Сценарий: {script}."""
            }
        ],
    )
    print('GENERATED PROMPTS FOR IMAGES!')
    with open("templates/image_prompts.html", "w", encoding="utf-8") as f:
        f.write(markdown.markdown(response.choices[0].message.content))
    image_prompts = response.choices[0].message.content.split("\n")
    images = []
    for i in range(1, 6):
        filename = f"static/images/scene_{i}.png"
        await gen_image_poll(image_prompts[i - 1], filename)
        print(f'GENERATED IMAGE {i}!')
        images.append(filename)
    return response.choices[0].message.content, images

@app.get("/", response_class=HTMLResponse)
async def form(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/", response_class=HTMLResponse)
async def handle_form(request: Request, topic: str = Form(...)):
    script = await generate_script(topic)
    print('GENERATED SCRIPT!')
    image_prompts, images = await generate_image(script)
    with open("templates/script.html", "w", encoding="utf-8") as f:
        f.write(markdown.markdown(script))
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "script": script, "topic": topic, "images": images}
    )

if __name__ == "__main__":
    import uvicorn
    # Создаём шаблон, если его нет
    if not os.path.exists("templates/index.html"):
        os.makedirs("templates", exist_ok=True)
        with open("templates/index.html", "w", encoding="utf-8") as f:
            f.write("""<!DOCTYPE html>
<html lang="ru">
<head>
  <meta charset="UTF-8">
  <title>Генератор сценариев</title>
  <style>
    body {
      font-family: "Inter", "Segoe UI", sans-serif;
      background-color: #f9f9fb;
      color: #222;
      margin: 0;
      padding: 40px;
      display: flex;
      flex-direction: column;
      align-items: center;
    }

    h1 {
      font-size: 1.8rem;
      font-weight: 600;
      margin-bottom: 30px;
      text-align: center;
    }

    form {
      background: #fff;
      padding: 20px 30px;
      border-radius: 16px;
      box-shadow: 0 4px 12px rgba(0,0,0,0.05);
      display: flex;
      gap: 10px;
      align-items: center;
      justify-content: center;
      margin-bottom: 40px;
    }

    label {
      font-weight: 500;
    }

    input[type="text"] {
      padding: 10px 14px;
      border: 1px solid #ccc;
      border-radius: 8px;
      outline: none;
      transition: border-color 0.2s ease;
      width: 220px;
    }

    input[type="text"]:focus {
      border-color: #007bff;
    }

    button {
      background-color: #007bff;
      color: white;
      border: none;
      border-radius: 8px;
      padding: 10px 18px;
      cursor: pointer;
      font-weight: 500;
      transition: background-color 0.2s ease;
    }

    button:hover {
      background-color: #0056c9;
    }

    h2, h3 {
      margin-top: 40px;
      text-align: center;
    }

    .script {
      background: #fff;
      padding: 20px;
      border-radius: 12px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.05);
      white-space: pre-wrap;
      line-height: 1.5;
      max-width: 1200px;
      margin: 0 auto;
    }

    .storyboard {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 20px;
      margin-top: 20px;
      max-width: 1200px;
      margin-inline: auto;
    }

    .scene {
      background: #fff;
      border-radius: 12px;
      padding: 10px;
      box-shadow: 0 2px 8px rgba(0,0,0,0.05);
      text-align: center;
    }

    .scene img {
      width: 100%;
      border-radius: 8px;
      object-fit: cover;
    }

    p {
      margin-top: 8px;
      font-size: 0.95rem;
      color: #555;
    }
  </style>
</head>
<body>
  <h1>🎬 Генератор сценариев для видео</h1>

  <form method="post">
    <label for="topic">Введите тему:</label>
    <input type="text" id="topic" name="topic" required>
    <button type="submit">Сгенерировать</button>
  </form>

  {% if script %}
    <h2>Сценарий для темы: {{ topic }}</h2>
    <div class="script">{% include 'script.html' %}</div>

    <h2>Промпты для раскадровки</h2>
    <div class="script">{% include 'image_prompts.html' %}</div>

    <h2>Раскадровка (5 сцен)</h2>
    <div class="storyboard">
      {% for img in images %}
        <div class="scene">
          <img src="{{ img }}" alt="Сцена {{ loop.index }}">
          <p>Сцена {{ loop.index }}</p>
        </div>
      {% endfor %}
    </div>
  {% endif %}
</body>
</html>
""")
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)

