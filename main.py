import json
import os
import sys
import discord
from discord.ext import commands
from discord import FFmpegPCMAudio
import openai
from google.cloud import texttospeech

os.environ['GOOGLE_APPLICATION_CREDENTIALS']=os.path.join(sys.path[0],'GoogleTTS.json')


f = open(os.path.join(sys.path[0],'bot_data.json'))
data = json.load(f)
f.close()




openai.api_key = data['openai_token']  # replace with your API key
intents = discord.Intents(messages=True, guilds=True, message_content=True, voice_states=True)
client = commands.Bot(command_prefix = '%', intents=intents, help_command=commands.DefaultHelpCommand())
voice = None

class Chatbot:
    def __init__(self, model_engine="gpt-3.5-turbo"):
        self.model_engine = model_engine

    def respond(self, message):
        prompt = f"User: {message}\nSylva the vtuber:"
        response = openai.ChatCompletion.create(
            model=self.model_engine,
            messages=[
                {"role":"user","content":prompt},
                {"role":"system","content":"Your name is Sylva and you are a catgirl who attends high school in Tokyo.  You should act like a vtuber when you respond"}
            ],
        )
        return split_message(response['choices'][0]['message']['content'])

@client.event
async def on_ready():
    print(f"Logged in as {client.user.name}")
    await client.change_presence(status=discord.Status.online, activity=discord.Activity(type=discord.ActivityType.listening, name="to the organics"))

@client.command(pass_context = True)
async def talk(ctx):
    global voice
    global labVoice
    if not ctx.voice_client:
        await ctx.send("pwease let me talk in a voice channel :point_right: :point_left: ")
        return

    message = ctx.message
    message_content = message.content[len("!talk "):].strip()
    print("Generating a response to:" + message_content)
    chatbot_response = Chatbot().respond(message_content)
    for segment in chatbot_response:
        synthesize_text(segment)
        source = FFmpegPCMAudio('voice.mp3')
        if(voice):
            voice.play(source)
        await ctx.send(segment)
        

@client.command(pass_contenxt = True)
async def join(ctx):
    if(ctx.author.voice):
        global voice
        print(ctx.author.voice.channel)
        channel = ctx.message.author.voice.channel
        voice = await channel.connect()
    else:
        await ctx.send("You are not in a voice channel, you must be in a voice channel to run this command!")

@client.command(pass_context = True)
async def leave(ctx):
    if(ctx.voice_client):
        global voice
        await ctx.guild.voice_client.disconnect()
        voice=None
        await ctx.send("Voice channel left.")
    else:
        await ctx.send("I am not in a voice channel.")

#Discord doesn't let bots send message over 2000 characters so we bypass
def split_message(msg, maxLength = 2000):
    output = []
    while len(msg) > maxLength:
        subMsg = msg[:maxLength]
        msg = msg[maxLength:]
        output.append(subMsg)

    output.append(msg)
    return output
    
def synthesize_text(text):
    """Synthesizes speech from the input string of text."""

    client = texttospeech.TextToSpeechClient()
    input_text = texttospeech.SynthesisInput(text=text)
    # Note: the voice can also be specified by name.
    # Names of voices can be retrieved with client.list_voices().
    voice = texttospeech.VoiceSelectionParams(
    language_code="en-US",
    name="en-US-Standard-F",
    ssml_gender=texttospeech.SsmlVoiceGender.FEMALE,
    )
    audio_config = texttospeech.AudioConfig(
    audio_encoding=texttospeech.AudioEncoding.MP3
    )
    response = client.synthesize_speech(
    request={"input": input_text, "voice": voice, "audio_config": audio_config}
    )
    # The response's audio_content is binary.
    with open("voice.mp3", "wb") as out:
        out.write(response.audio_content)
    print('Audio content written to file "voice.mp3"')

client.run(data['discord_token'] )  # replace with your bot token