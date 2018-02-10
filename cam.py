
import requests
import discord
import asyncio
import functools
import subprocess
import re
import aiohttp
import aiofiles
import io
import string
import os
from sys import exc_info
from os import path
from os import listdir
from time import sleep
from time import time
from picamera import PiCamera
from datetime import datetime
from random import random

from config import token
from config import gfyid
from config import gfysecret

lastframe = ''
temp = True
tempid = '28-05168455e3ff'
tempx = 0
down = True
lowpower = True
if lowpower:
  down = False
dirs = {}
dirs['home'] = '/home/pi/camera/' #OPTIONAL
dirs['live'] = 'live'
dirs['timelapse'] = 'timelapse'
dirs['frames'] = 'timelapse/frames'
dirs['clips'] = 'timelapse/clips'
dirs['logs'] = 'logs'

dirs = {k:path.join(dirs['home'],v) for k, v in dirs.items() if k != 'home'}



async def iPic():
  global down
  global tempx
  while True:
    if temp:
      async with aiofiles.open(f'/sys/bus/w1/devices/{tempid}/w1_slave','r') as tempData:
        param = re.search('t=(\d+)',await tempData.read())
        if param:
          tempx = int(param.group(1)) / 1000
        else:
          tempx = -69
        
    if down and not lowpower:
      print(time())
      timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')
      timestampshort = datetime.now().strftime('%Y%m%d_%H%M%S')
      filepath = path.join(dirs['frames'],f'{timestampshort}.jpg')
      
      camera.annotate_text = timestamp
      fPic = functools.partial(camera.capture,filepath,'jpeg',)
      await client.loop.run_in_executor(None, fPic)
      global lastframe
      lastframe = filepath
      
      framefiles = listdir(dirs['frames'])
      framefiles.sort()
      if len(framefiles) > 250:
        listfile = await aiofiles.open(path.join(dirs['frames'], 'frames.txt'), 'a+')
        for ffile in framefiles:
          await listfile.write(f'{path.join(dirs["frames"],ffile)}\n')
        listfile.close()
        
        down = False
        break
        
        print("Deleting frames")
        for ffile in framefiles[:-1]:
          os.remove(path.join(dirs['frames'],ffile))
        os.remove(path.join(dirs['frames'],path.join(dirs['frames'], 'frames.txt')))
        
      print(time())
    await asyncio.sleep(1-(time()-int(time())))
    # await asyncio.sleep(0)

def log(message):
  print(datetime.now().strftime('%Y-%m-%d %H:%M:%S: ')+message)
async def olog(message):
  await client.send_message(me, message)

def valideffect(effect):
  if str(effect).lower() in PiCamera.IMAGE_EFFECTS:
    return str(effect).lower() 
  else:
    return False

async def cPic(message,params={}):
  global camera
  if down and not lowpower:
    await client.send_typing(message.channel)
    timestamp = f'Picture taken at:{datetime.fromtimestamp(path.getctime(lastframe)).strftime("%Y-%m-%d %H:%M:%S")} UTC \n **Temperature:** {round(tempx,2)}°C '
    
    try:
      await client.send_file(message.channel, lastframe , content=timestamp)
    except discord.errors.HTTPException as e:
      await client.send_message(message.channel, f'{message.author.mention} Upload failed with Error: `{str(e)}`')
    except:
      print(exc_info)
      raise
    return
  if params.get('help'):
    await client.send_message(message.channel, f'{message.author.mention} `!pic effect eff=effect`')
    return
  if message.channel.is_private:
    await olog(f'{message.author.mention} requested a pic privately')
  else:
    await olog(f'{message.author.mention} requested a pic on \n {message.server.name}\\_{message.server.id}\\_{message.channel.mention}')
  if lowpower:
    while not camera.closed:
      await asyncio.sleep(0.1)
    camera = PiCamera()
  # await asyncio.sleep(0.5)gfi
  camera.start_preview()
          
  await client.send_typing(message.channel)
  
  timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
  timestamp = f'Picture taken at: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} UTC \n**Temperature:** {round(tempx,2)}°C '
  timestampshort = datetime.now().strftime('%Y%m%d_%H%M%S')
  shortname = re.sub('[^0-9a-zA-Z]','',message.author.name)
  filepath = path.join(dirs['live'],f'{timestampshort}_{shortname}_{message.author.id}.jpg')
  
  fPic = functools.partial(camera.capture,filepath,'jpeg',)
  
  effect = None
  if params.get('eff'):
    effect = valideffect(params.get('eff'))
  else:
    for param in params.keys():
      if valideffect(param):
        effect = valideffect(param)
  
  waiting = True
  while waiting:
    try:
      camera.image_effect = effect or 'none'
      camera.resolution = (3280, 2464)
      await client.loop.run_in_executor(None, fPic)
      waiting = False
    except Exception as e:
      print(e)
      await asyncio.sleep(1)
  if lowpower:
    camera.close()
  try:
    await client.send_file(message.channel, filepath , content=timestamp)
  except discord.errors.HTTPException as e:
    await client.send_message(message.channel, f'{message.author.mention} Upload failed with Error: `{str(e)}`')
  except:
    print(exc_info)
    raise

async def cGif(message,params={}):
  global camera
  if down:
    await client.send_message(message.channel, f'Gifs are down while the bot is being rewritten.')
    return
  if params.get('help'):
    await client.send_message(message.channel, f'{message.author.mention} `!gif/gfy/gfycat fps=1-30 s=1-59 eff=effects`')
    return
  if lowpower:
    while not camera.closed:
      await asyncio.sleep(0.1)
    camera = PiCamera()
  camera.start_preview()
    
  timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC ')
  timestampshort = datetime.now().strftime('%Y%m%d_%H%M%S')
  shortname = re.sub('[^0-9a-zA-Z]','',message.author.name)
  filepath = path.join(dirs['live'],f'{timestampshort}_{shortname}.h264')
    
  embed = discord.Embed() 
  embed.title = f'Recording GIF for {message.author.name}'
  embed.type = 'rich'
  embed.description = '' 
  embed.colour = discord.Color.red()
  embed.set_footer(text=timestamp)
  field1 = embed.add_field(name='Status',value='Preparing',inline=True)
  embedm = await client.send_message(message.channel,embed=embed)
  
  if message.channel.is_private:
    await olog(f'{message.author.mention} requested a gif privately')
  else:
    await olog(f'{message.author.mention} requested a gif on \n {message.server.name}\\_{message.server.id}\\_{message.channel.mention}')
  
  
  try:
    delay = max(1,min(int(params.get('s')),59,))
  except TypeError:
    delay = 3
  try:
    fps = max(1,min(int(params.get('fps')),30))
  except TypeError:
    fps = 30
    
  effect = None
  if params.get('eff'):
    effect = valideffect(params.get('eff'))
  else:
    for param in params.keys():
      if valideffect(param):
        effect = valideffect(param)
  
  
  start = functools.partial(camera.start_recording,filepath, format='h264')
  
  waiting = True
  
  field1 = embed.set_field_at(index=0,name='Status',value='Waiting for Camera',inline=True)
  await client.edit_message(embedm,embed=embed)
  while waiting:
    try:
      camera.image_effect = effect or 'none'
      camera.resolution = (1640,1232)
      camera.framerate = fps
      await client.loop.run_in_executor(None, start)
      waiting = False
    except Exception as e:
      await asyncio.sleep(1)
      print(e)
  field1 = embed.set_field_at(index=0,name='Status',value='Recording',inline=True)
  embed.colour = discord.Color(0xFFFF00)
  await client.edit_message(embedm,embed=embed)
  waituntil = time() + delay
  while waituntil >= time():
    try:
      camera.wait_recording()
      await asyncio.sleep(0.25)
    except Exception as e:
      print(e)
  camera.stop_recording()
  if lowpower:
    camera.close()
  
  filepathmp4 = f"{filepath[:-5]}.mp4" 
  command = f"MP4Box -add {filepath} {filepathmp4}"
  try:
    output = subprocess.check_output(command, stderr=subprocess.STDOUT, shell=True)
  except subprocess.CalledProcessError as e:
    print('FAIL:\ncmd:{}\noutput:{}'.format(e.cmd, e.output))
    
  # data = aiohttp.FormData()
  # data.add_field("grant_type","client_credentials")
  # data.add_field("client_id",gfyid)
  # data.add_field("client_secret",gfysecret)
  
  data = {  
      "client_id": gfyid,
      "client_secret": gfysecret,
      "grant_type": "client_credentials"
  }
  
  field1 = embed.set_field_at(index=0,name='Status',value='Uploading',inline=True)
  embed.colour = discord.Color.green()
  await client.edit_message(embedm,embed=embed)
  async with session.post('https://api.gfycat.com/v1/oauth/token', data=str(data)) as rt:
    rtjson = await rt.json()
    token = f"Bearer {rtjson['access_token']}"
    
  headers = {'Content-Type': 'application/json',"Authorization": token}
  headers2 = {"Authorization": token }
    
  gfyname = ""
  
  
  async with session.post('https://api.gfycat.com/v1/gfycats', headers=headers) as r:
    rjson = await r.json()
    if rjson['isOk']:  
      gfyname = rjson['gfyname']
      async with aiofiles.open(filepathmp4,mode='rb',loop=client.loop) as f:
        fgfy = await f.read()
        
        with aiohttp.MultipartWriter('form-data') as mpwriter:
          
          
          part = mpwriter.append((rjson['gfyname']))
          part.set_content_disposition('form-data', name='key')
          part2 = mpwriter.append(fgfy,{'CONTENT-TYPE': 'video/mp4'})  
          part2.set_content_disposition('form-data', name='file', filename=rjson['gfyname'])
          body = b''.join(mpwriter.serialize())
          
          # print(len(body))
          # mpwriter.headers[aiohttp.hdrs.CONTENT_LENGTH] = str(len(body))
          async with session.request('post','https://filedrop.gfycat.com', data=body, headers = mpwriter.headers) as r2:
            pass
    else:
      print(rjson)
  waiting = True
  first = True
  oldprogress = ''
  progress = '0'
  while waiting:
    async with session.request('get',f'https://api.gfycat.com/v1/gfycats/fetch/status/{gfyname}', headers=headers2) as r3: 
    
      r3json = await r3.json()
      if 'gfyname' in r3json:
        gfyname = r3json['gfyname']
        waiting = False
      elif 'errorMessage' in r3json:
        await client.send_message(message.channel, f'{message.author.mention} Upload failed with Error: `{r3json["errorMessage"]["code"]} : {r3json["errorMessage"]["description"]}`')
        await client.delete_message(embedm)
        return
      elif 'task' in r3json:
        if r3json['task'] == 'encoding':
          if first:
            field1 = embed.set_field_at(index=0,name='Status',value='Encoding',inline=True)
            field2 = embed.add_field(name='Progress',value='0%',inline=True)
            first = False
          if 'progress' in r3json:
            pvalue = round(float(r3json['progress']) / 1.17  * 100,2)
            field2 = embed.set_field_at(index=1,name='Progress',value=f'{pvalue}%',inline=True)
            progress = r3json['progress']
          
          if oldprogress != progress:
            oldprogress = progress
            await client.edit_message(embedm,embed=embed)
          await asyncio.sleep(1)
      else:
          await asyncio.sleep(1)
            
  gfylink = f'https://gfycat.com/{gfyname}'
  gfylog = await aiofiles.open(path.join(dirs['logs'],'gfy.log'),'a+',loop=client.loop)
  await gfylog.write(f'\n{gfylink}')
  await gfylog.close()
   
  await client.delete_message(embedm)
  await client.send_message(message.channel, f'Gfy taken at: {timestamp} \n**Temperature:** {round(tempx,2)}°C \n{gfylink}')
     
async def cEffects(message,params={}):
    effectnames = "```"
    for effectname in PiCamera.IMAGE_EFFECTS:
      effectnames = f"{effectnames}\n{effectname}"
    effectnames = f"{effectnames}```"
    await client.send_message(message.channel, effectnames )

async def cReload(message,params={}):
  if message.author != me:
    await client.send_message(message.channel, "You can't tell me what to do!" )
    return
  await client.send_message(message.channel, "Will do." )
  async with aiofiles.open(path.join(dirs['logs'],'reload'),('w+')) as reloadfile:
    await reloadfile.write(message.channel.id)
  await client.logout()
  session.close()
  exit()

async def cShutdown(message,params={}):
  if message.author != me:
    await client.send_message(message.channel, "I hope you never wake up." )
    return
  await client.send_message(message.channel, "Sleep tight." )
  async with aiofiles.open(path.join(dirs['logs'],'reload'),('w+')) as reloadfile:
    await reloadfile.write(message.channel.id)
  await client.logout()
  session.close()
  command = "/usr/bin/sudo /sbin/shutdown now"
  subprocess.call(command.split())
  
async def cTemp(message,params={}):
  if tempx == -69:
    await client.send_message(message.channel, "Something went wrong." )
  await client.send_message(message.channel, f"Current Temperature: {round(tempx,2)}°C" )
  
async def botcommand(message):
  params = {}
  if message.content.startswith("!"):
    smessage = message.content[1:].split()
    for i,msg in enumerate(smessage):
      if i == 0:
        for command in commands:
          if msg in command[0]:
            cmd = command[1]
            if message.author.id in userswaiting:
              return 2
            else:
              userswaiting.append(message.author.id)
              break
        else:
          return 0
      else:
        param = re.search('([a-zA-Z0-9]+)=([a-zA-Z0-9]+)',msg)
        if param:
          params[param.group(1).lower()] = param.group(2) or True
        else:
          params[msg.lower()] = True
    await cmd(message=message,params=params)
    return 1
  return 0

for k,dir in dirs.items():
  if not os.path.exists(dir):
    log(f'Did not find {dir}. Creating...')
    os.mkdir(dir)

    
framefiles = listdir(dirs['frames'])
if len(framefiles) > 0:
  log(f'Frames directory not empty, deleting {len(framefiles)} files...')
  for ffile in framefiles:
      if path.splitext(ffile)[1] == '.jpg' or ffile == 'frames.txt':
        os.remove(path.join(dirs['frames'],ffile))
      else:
        print(f'FRAME DIRECTORY ({dirs["frames"]}) IS NOT EMPTY. REMOVE FILE {ffile}.')
        exit()
    

  
client = discord.Client()
session = aiohttp.ClientSession(loop=client.loop)
me = discord.Object('103294721119494144')
unesco = discord.Object('287618635831443456')
camera = PiCamera()
camera.start_preview()
camera.resolution = (3280, 2464)
if lowpower:
  camera.close()

userswaiting = []
commands = [
  [['effects'],cEffects],
  [['gif','gfy','gfycat'],cGif],
  [['pic'],cPic],
  [['reload','restart'],cReload],
  [['goodnight','shutdown'],cShutdown],
  [['temp','temperature'],cTemp]
]

client.loop.create_task(iPic())

@client.event
async def on_ready():
  log('Logged in as:')
  log(client.user.name)
  log(client.user.id)
  log('Connected to:')
  global unesco
  global me
  for server in client.servers:
    if server.id == unesco.id:     
      unesco = server
      me = server.owner
    log(server.id)
    log(server.name)
    log(server.owner.name)
    
  for privatechannel in client.private_channels:
    async for message in client.logs_from(privatechannel, limit=100):
      if discord.utils.get(message.reactions, me=True) is None and message.author != client.user:
        await olog(message.author.mention+" "+message.content)   
        await client.add_reaction(message, '\U00002705')

  if path.isfile(path.join(dirs['logs'],'reload')):
    async with aiofiles.open(path.join(dirs['logs'],'reload'),('r')) as reloadfile:
      await client.send_message(discord.Object(await reloadfile.read()),"I'm back.")
    os.remove(path.join(dirs['logs'],'reload'))
      
  
  async with session.get("http://icanhazip.com/") as IP:
    IPtext = await IP.read()
    await olog(f"I'm running :) {IPtext}")    
  await client.change_presence(game=discord.Game(name='Live Pictures'))    

  
@client.event 
async def on_message(message):
  res = await botcommand(message)
  if res==0:
    if message.channel.is_private and message.author != client.user and message.author != me:
      await olog(message.author.mention+" "+message.content)   
      await client.add_reaction(message, '\U00002705')
  if res==1:
    asyncio.sleep(1)
    userswaiting.remove(message.author.id)
  if res==2:
    pass
  
         

client.run(token)