import json
import os
import sys
import discord
from discord.ext import commands
from discord import FFmpegPCMAudio
import openai
from google.cloud import texttospeech
import random

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = os.path.join(
    sys.path[0], 'GoogleTTS.json')


f = open(os.path.join(sys.path[0], 'bot_data.json'))
data = json.load(f)
f.close()

ITER_PER_SUMMARY = 12


openai.api_key = data['openai_token']  # replace with your API key
intents = discord.Intents(messages=True, guilds=True,
                          message_content=True, voice_states=True)
client = commands.Bot(command_prefix='%', intents=intents,
                      help_command=commands.DefaultHelpCommand())
voice = None


class Chatbot:
    def __init__(self, model_engine="gpt-4"):
        self.model_engine = model_engine
        self.chat_memory = []
        self.time_since_last_summary = 0
        self.summary = ""

    def respond(self, message, author):
        prompt = self.generate_prompt(message, author)
        response = openai.ChatCompletion.create(
            model=self.model_engine,
            messages=[
                {"role": "user", "content": prompt},
                {"role": "system", "content": "Your name is Sylva and you are a catgirl who attends high school in Tokyo.  Your favorite classes are math and science, but you dabble in the arts for fun sometimes.  In the evening you also stream as a vtuber who likes to play games and teach your viewers how to cook.  You should stay in character when you respond and not admit that you're an AI language model.  This includes throwing in occasional catgirl themed vocabulary and emoji when responding.  You should also try to keep the conversation going when possible."}
            ],
        )

        self.chat_memory.append([author, message])
        self.chat_memory.append(
            ["Sylva", response['choices'][0]['message']['content']])
        self.time_since_last_summary += 1

        return split_message(response['choices'][0]['message']['content'])

    def generate_prompt(self, message, author):
        time_to_summarize = self.time_since_last_summary % ITER_PER_SUMMARY == 0 and self.time_since_last_summary > 0
        self.short_term_chat = ""
        distance_to_lookback = 2 * \
            (self.time_since_last_summary % ITER_PER_SUMMARY)
        if (time_to_summarize):
            distance_to_lookback = 2*ITER_PER_SUMMARY

        for idx, x in enumerate(self.chat_memory[-distance_to_lookback:]):
            if (idx % 2 == 0):
                self.short_term_chat += f"{x[0]}: "
            else:
                self.short_term_chat += "Sylva: "
            self.short_term_chat += f"{x[1].rstrip()}\n"

        if (time_to_summarize):
            response = openai.ChatCompletion.create(
                model=self.model_engine,
                messages=[
                    {"role": "user", "content": f"Summarize the following chat in a maximum of 5 sentences: {self.short_term_chat}"},
                ],
            )

            self.summary = response['choices'][0]['message']['content']

            return f"Here's a short summary of the conversation so far: {self.summary}\n{author}: {message}\nSylva: "

        if (self.summary != ""):
            return f"Here's a short summary of the conversation so far: {self.summary}\n{self.short_term_chat}{author}: {message}\nSylva: "

        return f"{self.short_term_chat}{author}: {message}\nSylva: "


Sylva = Chatbot(model_engine="gpt-4-1106-preview")


@client.event
async def on_ready():
    print(f"Logged in as {client.user.name}")
    await client.change_presence(status=discord.Status.online, activity=discord.Activity(type=discord.ActivityType.listening, name="to the organics"))


@client.command(pass_context=True)
async def talk(ctx):
    global voice
    global labVoice

    emojiList = ['😼', '🐱', '😹', '🙀', '😾',  '😻','😺', '😽', '🐾', '🐈', '🐠', '🐟', '🍥', '🍣', '🍙']
    await ctx.message.add_reaction(random.choice(emojiList))
    message = ctx.message
    message_content = message.content[len("%talk "):].strip()

    chatbot_response = Sylva.respond(message_content, message.author.name)

    for segment in chatbot_response:
        await ctx.send(segment)
        if ctx.voice_client and voice:
            await synthesize_text(segment)
            voice.play(FFmpegPCMAudio('voice.mp3'))

# TODO: Implement conversation stat tracking


@client.command(pass_context=True)
async def stats(ctx):
    await ctx.send("UwU")


@client.command(pass_contenxt=True)
async def join(ctx):
    if (ctx.author.voice):
        global voice
        print(ctx.author.voice.channel)
        channel = ctx.message.author.voice.channel
        voice = await channel.connect()
    else:
        await ctx.send("You are not in a voice channel, you must be in a voice channel to run this command!")


@client.command(pass_context=True)
async def leave(ctx):
    if (ctx.voice_client):
        global voice
        await ctx.voice_client.disconnect()
        voice = None
        await ctx.send("Voice channel left.")
    else:
        await ctx.send("I am not in a voice channel.")

# Discord doesn't let bots send message over 2000 characters so we bypass


def split_message(msg, maxLength=2000):
    output = []
    while len(msg) > maxLength:
        subMsg = msg[:maxLength]
        msg = msg[maxLength:]
        output.append(subMsg)

    output.append(msg)
    return output


async def synthesize_text(text):
    """Synthesizes speech from the input string of text."""

    client = texttospeech.TextToSpeechClient()
    input_text = texttospeech.SynthesisInput(text=text)
    # Note: the voice can also be specified by name.
    # Names of voices can be retrieved with client.list_voices().
    voice = texttospeech.VoiceSelectionParams(
        language_code="en-US",
        name="en-US-Wavenet-F",
        ssml_gender=texttospeech.SsmlVoiceGender.FEMALE,
    )
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3
    )
    response = client.synthesize_speech(
        request={"input": input_text, "voice": voice,
                 "audio_config": audio_config}
    )
    # The response's audio_content is binary.
    with open("voice.mp3", "wb") as out:
        out.write(response.audio_content)
    print('Audio content written to file "voice.mp3"')

client.run(data['discord_token'])  # replace with your bot token
