import discord
from discord.ext import commands
from google import genai

import json
import re

import os
from dotenv import load_dotenv

load_dotenv()

discord_token = os.getenv("DISCORD_TOKEN")
gemini_api_key = os.getenv("GEMINI_API_KEY")
channel_id_list = os.getenv("CHANNEL_ID_LIST")
target_languages = os.getenv("TARGET_LANGUAGES")

client = genai.Client(api_key=gemini_api_key)

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'Babel Bot Online. Monitoring {len(channel_id_list)} channels.')

@bot.event
async def on_message(message):
    if message.author == bot.user: return
    
    if message.channel.id not in channel_id_list: return

    # Prevent triggering on emoji or commands
    clean_content = re.sub(r'<a?:[a-zA-Z0-9_]+:[0-9]+>', '', message.content)
    has_meaningful_text = any(char.isalnum() for char in clean_content)
    
    if not has_meaningful_text:
        return

    # 1. Prompt - returns JSON with translations
    prompt = (
        f"Analyze this text: '{message.content}'\n"
        f"1. Remove anything that could trigger something on Discord, like '@' or '\\' at the beginning of the message.\n"
        f"2. Identify the language of the text (e.g., 'English', 'German', 'French').\n"
        f"3. Translate the text into ALL of these languages: {', '.join(target_languages)}.\n"
        f"4. Return a JSON object with two keys:\n"
        f"   - 'source': The detected language name.\n"
        f"   - 'targets': A dictionary of the translations.\n"
    )

    async with message.channel.typing():
        try:
            # 2. Call Gemini
            response = client.models.generate_content(
                model='gemini-3-flash-preview',
                contents=prompt,
                config={'response_mime_type': 'application/json'}
            )
            
            # 3. Parse the data
            data = json.loads(response.text)
            source_lang = data.get("source")
            translations = data.get("targets", {})

            # 4. Iterate through the translations and print those that are different from source language
            output_text = ""
            for lang, text in translations.items():
                if source_lang and lang.lower() != source_lang.lower():
                    flag = get_flag(lang)
                    output_text += f"{flag} {text}\n"

            # 5. Send
            if output_text:
                await message.reply(output_text, mention_author=False)

        except Exception as e:
            print(f"Translation Error: {e}")
            
            # DEBUG LLM RESPONSE
            # print(response.text)

    await bot.process_commands(message)

def get_flag(lang_name):
    flags = {
        "English": "🇺🇸",
        "German": "🇩🇪", 
        "French": "🇫🇷",
        "Spanish": "🇪🇸",
        "Russian": "🇷🇺",
    }
    return flags.get(lang_name.title(), "🏳️")

bot.run(discord_token)
