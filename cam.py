
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
import netifaces
from sys import exc_info
from os import path
from os import listdir
from time import sleep
from time import time
from picamera import PiCamera
from datetime import datetime
from random import random

from picamera import mmal, mmalobj

from config import token
from config import gfyid
from config import gfysecret
from config import tempid

from zalgo import zalgo

class CommandFound(Exception): pass

lastframe = ''
lowpower = True
dirs = {
  'home':'/home/pi/camera/',
  'live':'live',
  'timelapse':'timelapse',
  'frames':'timelapse/frames',
  'clips':'timelapse/clips',
  'logs':'logs'
}

dirs = {k:path.join(dirs['home'],v) for k, v in dirs.items() if k != 'home'}


async def getTemp():
  try:
    async with aiofiles.open(f'/sys/bus/w1/devices/{tempid}/w1_slave','r') as tempData:
      param = re.search('t=(\d+)',await tempData.read())
      xtemp = int(param.group(1)) / 1000
  except:
    xtemp = -69
  
  try:
    with subprocess.Popen(['/opt/vc/bin/vcgencmd','measure_temp'],stdout=subprocess.PIPE) as pcputemp:
      while pcputemp.poll() is None:
        await asyncio.sleep(0.05)
      xgputemp = float(re.search("temp=(.*?)'C", str(pcputemp.stdout.read()) ).group(1))
  except:
    xgputemp = -69
  
  try:
    fcputemp = await aiofiles.open('/sys/class/thermal/thermal_zone0/temp','r')
    xcputemp = float(await fcputemp.read())/1000
  except:
    xcputemp = -69
    
  return xtemp, xcputemp, xgputemp

async def iPic():  
  while not lowpower:
    print(time())
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC+1')
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
      
      break
      
      print("Deleting frames")
      for ffile in framefiles[:-1]:
        os.remove(path.join(dirs['frames'],ffile))
      os.remove(path.join(dirs['frames'],path.join(dirs['frames'], 'frames.txt')))
      
    print(time())
    await asyncio.sleep(1-(time()-int(time())))
  # await asyncio.sleep(0)

async def olog(message):
  await me.send(message)

def valideffect(effect):
  if str(effect).lower() in PiCamera.IMAGE_EFFECTS:
    return str(effect).lower() 
  else:
    return False

async def cPic(message,params={}):
  '''Takes a live picture from the bot.
Parameters: effectname, eff=effectname shutter=seconds night'''
  if params.get('help'):
    await message.channel.send( f'{message.author.mention} `!pic effect eff=effect`')
    return
  xtemp,_,_ = await getTemp()
  if not lowpower:
    async with message.channel.typing():
      timestamp = f'Picture taken at:{datetime.fromtimestamp(path.getctime(lastframe)).strftime("%Y-%m-%d %H:%M:%S")} UTC+1 \n **Temperature:** {round(xtemp,2)}°C '
      filepath = lastframe 
  else:
    global camera
    while not camera.closed:
      await asyncio.sleep(0.1)
    print(params.get('night'))
    if params.get('night'):
      camera = PiCamera(
      resolution=(3280, 2464),
      framerate=1/6,
      sensor_mode=3)
      
      camera.shutter_speed = 6000000
      camera.iso = 800
      camera.exposure_mode = 'night'
    elif params.get('simple'):
      camera = PiCamera(resolution=(3280, 2464),
      sensor_mode=2)
    else:
      try:
        shutter_speed = max(1/10,min(float(params.get('shutter')),8))
      except TypeError as e:
        shutter_speed = 1/10
      print(shutter_speed)
      camera = PiCamera(
      resolution=(3280, 2464),
      framerate=1/shutter_speed,
      sensor_mode=2)
      if params.get('shutter'):
        camera.shutter_speed = int(shutter_speed * 1000000)
      else:
        camera.shutter_speed = 0
      camera.exposure_mode = 'auto'
    async with message.channel.typing():
      
      camera.start_preview()
      if params.get('fast'):
        await asyncio.sleep(1)   
      elif not params.get('vfast'):
        await asyncio.sleep(2)  
      timestamp = zalgo(f'Picture taken at: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} UTC+1 \n**Temperature:** {round(xtemp,2)}°C ',1)
      timestampshort = datetime.now().strftime('%Y%m%d_%H%M%S')
      shortname = re.sub('[^0-9a-zA-Z]','',message.author.name)
      filepath = path.join(dirs['live'],f'{timestampshort}_{shortname}_{message.author.id}.jpg')
      
      fPic = functools.partial(camera.capture,filepath,'jpeg',use_video_port=params.get('video') or False)
      
      effect = None
      if params.get('eff'):
        effect = valideffect(params.get('eff'))
      else:
        for param in params.keys():
          if valideffect(param):
            effect = valideffect(param)
      
      
      
      
      camera.image_effect = effect or 'none'
      await client.loop.run_in_executor(None, fPic)
      camera.close()
      try:
        await message.channel.send( file=discord.File(filepath) , content=timestamp)
      except discord.errors.HTTPException as e:
        await message.channel.send( f'{message.author.mention} Upload failed with Error: `{str(e)}`')
      except:
        print(exc_info)
        raise

async def cGif(message,params={}):
  '''Takes a live gif from the bot.
Parameters: effectname, eff=effectname, s=length_seconds, fps=fps'''
  if not lowpower:
    await message.channel.send( f'Gifs are not available in timelapse mode.')
    return

  
  
  timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC+1 ')
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
  embedm = await message.channel.send(embed=embed)
 
  global camera
  if not camera.closed:
    field1 = embed.set_field_at(index=0,name='Status',value='Waiting for Camera',inline=True)
    await embedm.edit(embed=embed)
    while not camera.closed:
      await asyncio.sleep(0.1)
    
  camera = PiCamera()  
  camera.start_preview()   
  
  try:
    delay = max(1,min(float(params.get('s')),59,))
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


  fGif = functools.partial(camera.start_recording,filepath, format='h264')


  field1 = embed.set_field_at(index=0,name='Status',value='Waiting for Camera',inline=True)
  await embedm.edit(embed=embed)
  while True:
    try:
      camera.image_effect = effect or 'none'
      camera.resolution = (1640,1232)
      camera.framerate = fps
      await client.loop.run_in_executor(None, fGif)
      break
    except Exception as e:
      await asyncio.sleep(1)
      print(e)
  field1 = embed.set_field_at(index=0,name='Status',value='Recording',inline=True)
  embed.colour = discord.Color(0xFFFF00)
  await embedm.edit(embed=embed)
  waituntil = time() + delay
  while waituntil >= time():
    try:
      camera.wait_recording()
      await asyncio.sleep(0.25)
    except Exception as e:
      print(e)
  camera.stop_recording()
  camera.close()

  filepathmp4 = f"{filepath[:-5]}.mp4" 
  command = f"MP4Box -add {filepath} {filepathmp4}"
  try:
    output = subprocess.check_output(command, stderr=subprocess.STDOUT, shell=True)
  except subprocess.CalledProcessError as e:
    print('FAIL:\ncmd:{}\noutput:{}'.format(e.cmd, e.output))
    field1 = embed.set_field_at(index=0,name='Status',value='FAILED',inline=True)
    embed.colour = discord.Color(0xFF0000)
    await embedm.edit(embed=embed)
    return
    

  data = {  
      "client_id": gfyid,
      "client_secret": gfysecret,
      "grant_type": "client_credentials"
  }
  
  field1 = embed.set_field_at(index=0,name='Status',value='Uploading',inline=True)
  embed.colour = discord.Color.green()
  await embedm.edit(embed=embed)
  async with session.post('https://api.gfycat.com/v1/oauth/token', data=str(data)) as rt:
    rtjson = await rt.json()
    token = f"Bearer {rtjson['access_token']}"
    
  headers = {'Content-Type': 'application/json',"Authorization": token}
  headers2 = {"Authorization": token }
    
  gfyname = ""
  
  
  try:
    async with session.post('https://api.gfycat.com/v1/gfycats', headers=headers) as r:
      rjson = await r.json()
      if rjson['isOk']:  
        gfyname = rjson['gfyname']
        async with aiofiles.open(filepathmp4,mode='rb',loop=client.loop) as f:
          fgfy = await f.read()
          data = aiohttp.FormData()
          data.add_field('file',
                         fgfy,
                         filename=rjson['gfyname'],
                         content_type='video/mp4')

          # await session.post(url, data=data)
                    # with aiohttp.MultipartWriter('form-data') as mpwriter:
            
            # print(mpwriter.append((rjson['gfyname'])))
            # part = mpwriter.append((rjson['gfyname']))
            # part.set_content_disposition('form-data', name='key')
            # part2 = mpwriter.append(fgfy,{'CONTENT-TYPE': 'video/mp4'})  
            # part2.set_content_disposition('form-data', name='file', filename=rjson['gfyname'])
            # body = b''.join(mpwriter.serialize())
            
            # print(len(body))
            # mpwriter.headers[aiohttp.hdrs.CONTENT_LENGTH] = str(len(body))
            # async with session.request('post','https://filedrop.gfycat.com', data=body, headers = mpwriter.headers) as r2:
          async with session.request('post','https://filedrop.gfycat.com', data=data) as r2:
            print(r2)
            pass
      else:
        print(rjson)
  except:
    embed.set_field_at(index=0,name='Status',value='FAILED',inline=True)
    embed.add_field(name='Error',value='Failed during upload',inline=True)
    embed.colour = discord.Color(0xFF0000)
    await embedm.edit(embed=embed)
    raise
    return
    
  field1 = embed.set_field_at(index=0,name='Status',value='Waiting for gfycat',inline=True)
  await embedm.edit(embed=embed)
  first = True
  oldprogress = ''
  progress = '0'
  while True:
    async with session.request('get',f'https://api.gfycat.com/v1/gfycats/fetch/status/{gfyname}', headers=headers2) as r3: 
    
      r3json = await r3.json()
      if 'gfyname' in r3json:
        gfyname = r3json['gfyname']
        break
      elif 'errorMessage' in r3json:  
        field1 = embed.set_field_at(index=0,name='Status',value='FAILED',inline=True)
        try:
          embed.set_field_at(index=1,name='Error',value=f'{message.author.mention} Upload failed with Error: `{r3json["errorMessage"]["code"]} : {r3json["errorMessage"]["description"]}`',inline=True)
        except:
          embed.add_field(name='Error',value=f'`{r3json["errorMessage"]["code"]} : {r3json["errorMessage"]["description"]}`',inline=True)
        embed.colour = discord.Color.red()
        await embedm.edit(embed=embed)
        
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
            await embedm.edit(embed=embed)
          await asyncio.sleep(1)
      else:
          await asyncio.sleep(1)
            
  gfylink = f'https://gfycat.com/{gfyname}'
  gfylog = await aiofiles.open(path.join(dirs['logs'],'gfy.log'),'a+',loop=client.loop)
  await gfylog.write(f'\n{gfylink}')
  await gfylog.close()
   
  await embedm.delete()
  xtemp,_,_ = await getTemp()
  await message.channel.send( f'Gfy taken at: {timestamp} \n**Temperature:** {round(xtemp,2)}°C \n{gfylink}')
     
async def cEffects(message,params={}):
  '''Lists all available image/video effects'''
  effectnames = "```"
  for effectname in PiCamera.IMAGE_EFFECTS:
    effectnames = f"{effectnames}\n{effectname}"
  effectnames = f"{effectnames}```"
  await message.channel.send( effectnames )

async def cReload(message,params={}):
  '''Reloads the bot. `OWNER ONLY`'''
  if message.author != me:
    await message.channel.send( f"I'm sorry {message.author.mention}, I'm afraid I can't do that." )
    return
  await message.add_reaction('\U0000267b')
  async with aiofiles.open(path.join(dirs['logs'],'reload'),('w+')) as reloadfile:
    await reloadfile.write(str(message.channel.id))
  await client.logout()
  session.close()
  exit()

async def cShutdown(message,params={}):  
  '''Turns off the bot hardware. `OWNER ONLY`'''
  if message.author != me:
    await message.channel.send( "I hope you never wake up." )
    return
  await message.add_reaction('\U0000267b')
  async with aiofiles.open(path.join(dirs['logs'],'reload'),('w+')) as reloadfile:
    await reloadfile.write(str(message.channel.id))
  await client.logout()
  session.close()
  command = "/usr/bin/sudo /sbin/shutdown now"
  subprocess.call(command.split())
    
async def cStatus(message,params={}):
  '''Returns misc bot information'''
  xiface = None
  async with session.get("http://icanhazip.com/") as IP:
    tIP = str(await IP.text())[:-1]
    for iface in netifaces.interfaces():
      for addr in netifaces.ifaddresses(iface).get(netifaces.AF_INET, {}):
        await olog(str(addr))
        if addr.get('addr') == tIP:
          xiface = iface
  pping = subprocess.Popen(['ping','-c 1', '8.8.8.8'],stdout=subprocess.PIPE)
  pcputemp = subprocess.Popen(['/opt/vc/bin/vcgencmd','measure_temp'],stdout=subprocess.PIPE)
  while pping.poll() is None or pcputemp.poll() is None:
    await asyncio.sleep(0.05)
  xping = re.search('time=(.*?) ms', str(pping.stdout.read()) ).group(1)
  if xiface == 'ppp0':
    xiface = "3g"
  elif xiface == 'eth0':
    xiface = "Ethernet"
  else: #may as well at this point assume it's WiFi or we woudln't be online at all. 
    xiface = "WiFi"
  
  xtemp,xcputemp,xgputemp = await getTemp()
  embed=discord.Embed(title="Status", description=f"Requested by {message.author.mention}", color=discord.Color.green())
  embed.add_field(name='Ambient Temperature', value=f'{round(xtemp,1)}°C', inline=True)
  embed.add_field(name='GPU Temperature', value=f'{xgputemp}°C', inline=True)
  embed.add_field(name='CPU Temperature', value=f'{round(xcputemp,1)}°C', inline=True)
  embed.add_field(name='Network Device', value=f'{xiface}', inline=True)
  embed.add_field(name='Ping', value=f'{xping}ms', inline=True)
  embed.add_field(name='Local Time', value=datetime.now().strftime('%H:%M:%S UTC+1'), inline=True)
  await message.channel.send( embed=embed)
  
async def cHelp(message,params={}):
  '''Get help for the bot'''
  hCommands = []
  for command in commands:
    for cmdName in command[0]:
      if params.get(cmdName):
        hCommands.append(command)
        break
  embed = discord.Embed() 
  embed.title = f'Help for TimelapseBot'
  embed.type = 'rich'
  embed.description = 'To use a command mention me with the command name and any parameters. Named parameters are called by name=value' 
  embed.colour = discord.Color.gold()
  for command in hCommands or commands:
    embed.add_field(name='/'.join(command[0]),value=command[1].__doc__,inline=False)
  
  await message.channel.send(embed=embed)
    
async def cPrefix(message,params={}):
  '''mate there is no prefix'''
  message.channel.send( 'No prefix, simply mention me anywhere in your command.')

async def cDebug(message,params={}):
  '''Prints the console output'''
  async with aiofiles.open(path.join(dirs['logs'],'stdout.log'),"r") as logfile:
    logs = await logfile.readlines()
    try:
      lines = max(1,min(20,int(params.get('lines') or params.get('l') or params.get('i')))),
    except TypeError as e:
      lines = 10
    await message.channel.send( f"```{''.join(logs[-lines:])}```" )
      
      
for k,dir in dirs.items():
  if not os.path.exists(dir):
    print(f'Did not find {dir}. Creating...')
    os.mkdir(dir)

  
framefiles = listdir(dirs['frames'])
if len(framefiles) > 0:
  print(f'Frames directory not empty, deleting {len(framefiles)} files...')
  for ffile in framefiles:
      if path.splitext(ffile)[1] == '.jpg' or ffile == 'frames.txt':
        os.remove(path.join(dirs['frames'],ffile))
      else:
        print(f'FRAME DIRECTORY ({dirs["frames"]}) IS NOT EMPTY. REMOVE FILE {ffile}.')
        exit()
    
if not lowpower: 
  camera = mmalobj.MMALCamera()
  encoder = mmalobj.MMALVideoEncoder()
  encoder.format = 'h264'
else:
  camera = PiCamera()
camera.close()

client = discord.Client()
session = aiohttp.ClientSession(loop=client.loop)

userswaiting = []
commands = [
  [['effects'],cEffects,False],
  [['gif','gfy','gfycat'],cGif,True],
  [['pic','picture'],cPic,True],
  [['reload','relaod','restart'],cReload,False],
  [['goodnight','shutdown'],cShutdown,False],
  [['status','info'],cStatus,False],
  [['help','commands'],cHelp,False],
  [['prefix'],cPrefix,False],
  [['debug','error'],cDebug,False]
]

client.loop.create_task(iPic())

@client.event
async def on_ready():
  global me
  me = client.get_user(103294721119494144)
  print('Logged in as:')
  print(client.user.name)
  print(client.user.id)
  print('Connected to:')
  for guild in client.guilds:
    print(guild.id)
    print(guild.name)
    print(guild.owner.name)
    
  for privatechannel in client.private_channels:
    async for message in privatechannel.history(limit=100):
      if discord.utils.get(message.reactions, me=True) is None and message.author != client.user:
        await olog(message.author.mention+" "+message.content)   
        await client.add_reaction(message, '\U00002705')
  try:
    if path.isfile(path.join(dirs['logs'],'reload')):
      async with aiofiles.open(path.join(dirs['logs'],'reload'),('r')) as reloadfile:
        async for message in client.get_channel(int(await reloadfile.read())).history(limit=20):
          if discord.utils.get(message.reactions,emoji='\U0000267b', me=True):
            await message.remove_reaction('\U0000267b',client.user)
            await message.add_reaction('\U00002705')
            break
      os.remove(path.join(dirs['logs'],'reload'))
  except Exception as e:
    print(e)
    pass
    
  async with session.get("http://icanhazip.com/") as IP:
    IPtext = await IP.text()
    await olog(f"I'm running :) {IPtext}")    
  await client.change_presence(game=discord.Game(name='Live Pictures'))    

  
@client.event 
async def on_message(message):
  if isinstance(message.channel,discord.abc.PrivateChannel):
    if message.author != message.channel.me:
      await olog(f'{message.author.mention}:{message.content}')
      await client.add_reaction(message, '\U00002705')
      await message.channel.send( "Sorry, no private commands at the moment." )
    return
  cmd = None
  params = {}
  if message.guild.me in message.mentions and message.author != message.guild.me:
    smessage = message.content.split()
    try:
      for pmessage in smessage:
        for command in commands:
          if pmessage.lower() in command[0]:
            if command[2]:
              if message.author.id in userswaiting:
                return
              else:
                userswaiting.append(message.author.id)
            
            cmd = command
            smessage.remove(pmessage)
            if not isinstance(message.channel,discord.abc.PrivateChannel):
              await olog(f'{message.author.mention}\\_{pmessage}\\_{message.guild.name}\\_{message.guild.id}\\_{message.channel.mention}')
            raise CommandFound
    except CommandFound:
      for pmessage in smessage:
        param = re.search('([a-zA-Z0-9]+)=([a-zA-Z0-9\.]+)',pmessage)
        if param:
          params[param.group(1).lower()] = param.group(2) or True
        else:
          params[pmessage.lower()] = True
             
      await cmd[1](message=message,params=params)
      if cmd[2]:
        userswaiting.remove(message.author.id)
      
      
      
      
client.run(token)