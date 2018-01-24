
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
from time import sleep
from time import time
from picamera import PiCamera
from datetime import datetime

from config import token
from config import gfyid
from config import gfysecret

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
  if params.get('help'):
    await client.send_message(message.channel, f'{message.author.mention} `!pic effect eff=effect`')
    return
  if message.channel.is_private:
    await olog(f'{message.author.mention} requested a pic privately')
  else:
    await olog(f'{message.author.mention} requested a pic on \n {message.server.name}\\_{message.server.id}\\_{message.channel.mention}')
  
          
  await client.send_typing(message.channel)
  timestamp = datetime.now().strftime('Picture taken at: %Y-%m-%d %H:%M:%S UTC ')
  timestampshort = datetime.now().strftime('%Y%m%d_%H%M%S')
  shortname = re.sub('[^0-9a-zA-Z]','',message.author.name)
  filepath = f'/home/pi/camera/live/{timestampshort}_{shortname}_{message.author.id}.jpg'
  
  thing = functools.partial(camera.capture,filepath,'jpeg',)
  
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
      await client.loop.run_in_executor(None, thing)
      waiting = False
    except Exception as e:
      print(e)
      await asyncio.sleep(1)
  try:
    await client.send_file(message.channel, filepath , content=timestamp)
  except discord.errors.HTTPException as e:
    await client.send_message(message.channel, f'{message.author.mention} Upload failed with Error: `{str(e)}`')
  except:
    print("Unexpected error:", sys.exc_info()[0])
    raise

async def cGif(message,params={}):
  if params.get('help'):
    await client.send_message(message.channel, f'{message.author.mention} `!gif/gfy/gfycat fps=1-30 s=1-59 eff=effects`')
    return
  if message.channel.is_private:
    await olog(f'{message.author.mention} requested a gif privately')
  else:
    await olog(f'{message.author.mention} requested a gif on \n {message.server.name}\\_{message.server.id}\\_{message.channel.mention}')
  await client.send_typing(message.channel)
  timestamp = datetime.now().strftime('Gfy taken at: %Y-%m-%d %H:%M:%S UTC ')
  timestampshort = datetime.now().strftime('%Y%m%d_%H%M%S')
  shortname = re.sub('[^0-9a-zA-Z]','',message.author.name)
  filepath = f'/home/pi/camera/live/{timestampshort}_{shortname}.h264'
  
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
  waituntil = time() + delay
  while waituntil >= time():
    try:
      camera.wait_recording()
      await asyncio.sleep(0.25)
    except Exception as e:
      print(e)
  camera.stop_recording()
  
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
  async with session.post('https://api.gfycat.com/v1/oauth/token', data=str(data)) as rt:
    rtjson = await rt.json()
    token = f"Bearer {rtjson['access_token']}"
    
  headers = {'Content-Type': 'application/json',"Authorization": token}
  headers2 = {"Authorization": token }
    
  gfyname = ""
  
  await client.send_typing(message.channel)
  
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
          await client.send_typing(message.channel)
          async with session.request('post','https://filedrop.gfycat.com', data=body, headers = mpwriter.headers) as r2:
            pass
    else:
      print(rjson)
  waiting = True
  while waiting:
    async with session.request('get',f'https://api.gfycat.com/v1/gfycats/fetch/status/{gfyname}', headers=headers2) as r3: 
      r3json = await r3.json()
      print(r3json)
      if 'gfyname' in r3json:
        gfyname = r3json['gfyname']
        waiting = False
      elif 'errorMessage' in r3json:
        await client.send_message(message.channel, f'{message.author.mention} Upload failed with Error: `{r3json["errorMessage"]["code"]} : {r3json["errorMessage"]["description"]}`')
        return
      # elif 'asd' in rjson3:
      else:
        await client.send_typing(message.channel)
        await asyncio.sleep(1)
            
  gfylink = f'https://gfycat.com/{gfyname}'
  gfylog = await aiofiles.open('gfy.log','a',loop=client.loop)
  await gfylog.write(f'\n{gfylink}')
  await gfylog.close()
  await client.send_message(message.channel, f'{timestamp} \n {gfylink}')
       
async def cEffects(message,params={}):
    effectnames = "```"
    for effectname in PiCamera.IMAGE_EFFECTS:
      effectnames = f"{effectnames}\n{effectname}"
    effectnames = f"{effectnames}```"
    await client.send_message(message.channel, effectnames )

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

client = discord.Client()
session = aiohttp.ClientSession(loop=client.loop)
me = discord.Object('103294721119494144')
unesco = discord.Object('287618635831443456')
camera = PiCamera()
camera.resolution = (3280, 2464)
userswaiting = []
commands = [
  [['effects'],cEffects],
  [['gif','gfy','gfycat'],cGif],
  [['pic'],cPic],
]

  

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

  await olog("I'm running :)")    
  await client.change_presence(game=discord.Game(name='Live Pictures'))    

  
@client.event 
async def on_message(message):
  res = await botcommand(message)
  if res==0:
    if message.channel.is_private and message.author != client.user and message.author != owner:
      await olog(message.author.mention+" "+message.content)   
      await client.add_reaction(message, '\U00002705')
  if res==1:
    asyncio.sleep(1)
    userswaiting.remove(message.author.id)
  if res==2:
    pass
  
         

client.run(token)