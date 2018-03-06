import discord
import discordfaby
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
from shlex import split as shsplit
from sys import exc_info
from os import path
from os import listdir
from time import sleep
from time import monotonic as time
from picamera import PiCamera
from datetime import datetime
from random import random
from random import randint

from picamera import mmal, mmalobj

from config import token
from config import gfyid
from config import gfysecret
from config import tempid
import aiogfycat


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


async def getTemp():
  try:
    async with aiofiles.open(f'/sys/bus/w1/devices/{tempid}/w1_slave','r') as tempData:
      param = re.search('t=(-?\d+)',await tempData.read())
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


def valideffect(effect):
  if str(effect).lower() in PiCamera.IMAGE_EFFECTS:
    return str(effect).lower() 
  else:
    return False

async def cPic(client,message,params={}):
  '''Takes a live picture from the bot.
Parameters: effectname, eff=effectname shutter=seconds night'''
  waittime = time()
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
    if params.get('night'):
      camera = PiCamera(
      resolution=(3280, 2464),
      framerate=1/6,
      sensor_mode=3)
      
      camera.exposure_mode = 'sports'
      camera.shutter_speed = 6000000
      camera.iso = 0
    elif params.get('simple'):
      camera = PiCamera(resolution=(3280, 2464),
      sensor_mode=2)
    else:
      try:
        shutter_speed = max(1/10,min(float(params.get('shutter')),8))
      except TypeError as e:
        shutter_speed = 1/10
      camera = PiCamera(
      resolution=(3280, 2464),
      framerate=1/shutter_speed,
      sensor_mode=2)
      try:
        camera.iso = int(params.get('iso'))
      except TypeError:
        pass
      if params.get('shutter'):
        camera.shutter_speed = int(shutter_speed * 1000000)
      else:
        camera.shutter_speed = 0
      # camera.exposure_mode = 'auto'
    async with message.channel.typing():
      
      camera.start_preview()
      if params.get('fast'):
        await asyncio.sleep(1)   
      elif not params.get('vfast'):
        await asyncio.sleep(2)
        
        
      timestamp = f'Picture taken for {message.author.mention}at: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")} UTC+1 \n**Temperature:** {round(xtemp,2)}°C '
      timestampshort = datetime.now().strftime('%Y%m%d_%H%M%S')
      shortname = re.sub('[^0-9a-zA-Z]','',message.author.name)
      filepath = path.join(dirs['live'],f'{timestampshort}_{shortname}_{message.author.id}.jpg')
      

      
      effect = None
      if params.get('eff'):
        effect = valideffect(params.get('eff'))
      else:
        for param in params.keys():
          if valideffect(param):
            effect = valideffect(param)
      
      
      
      
      camera.image_effect = effect or 'none'
      camera.exposure_mode = 'off'
      fPic = functools.partial(camera.capture,filepath,'jpeg')
      await client.loop.run_in_executor(None, fPic)
      camera.close()
      print(time()-waittime)
      try:
        await message.channel.send( file=discord.File(filepath) , content=timestamp)
      except discord.errors.HTTPException as e:
        await message.channel.send( f'{message.author.mention} Upload failed with Error: `{str(e)}`')
      except:
        print(exc_info)
        raise

async def cGif(client,message,params={}):
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
  
  camera.image_effect = effect or 'none'
  camera.resolution = (1640,1232)
  camera.framerate = fps
  await client.loop.run_in_executor(None, fGif)

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
    
  doembed = not params.get('noembed') and os.path.getsize(filepathmp4) < 8e+6 or params.get('embed') or params.get('nogfy')
    
    
  if not doembed:
    field1 = embed.set_field_at(index=0,name='Status',value='Uploading',inline=True)
    embed.colour = discord.Color.green()
    await embedm.edit(embed=embed)

    gfyname = await GfycatClient.upload(filepathmp4)
    print(gfyname)
      
    # embed.set_field_at(index=0,name='Status',value='FAILED',inline=True)
    # embed.add_field(name='Error',value='Failed during upload',inline=True)
    # embed.colour = discord.Color(0xFF0000)
    # await embedm.edit(embed=embed)
      
    field1 = embed.set_field_at(index=0,name='Status',value='Waiting for gfycat',inline=True)
    await embedm.edit(embed=embed)
    first = True
    oldprogress = ''
    progress = '0'
    while True:
      gfystatus = await GfycatClient.status(gfyname) 
      
      print(gfystatus)
      if 'gfyname' in gfystatus:
        gfylink = f'https://gfycat.com/{gfystatus["gfyname"]}'
        break
      elif 'errorMessage' in gfystatus: 
        field1 = embed.set_field_at(index=0,name='Status',value='FAILED',inline=True)
        embed.set_field_at(index=1,name='Error',value=f'{message.author.mention} Upload failed with Error: `{gfystatus["errorMessage"]["code"]} : {gfystatus["errorMessage"]["description"]}`',inline=True)
        embed.colour = discord.Color.red()
        await embedm.edit(embed=embed)
        return
      elif 'task' in gfystatus and gfystatus['task'] == 'encoding':
          if first:
            field1 = embed.set_field_at(index=0,name='Status',value='Encoding',inline=True)
            field2 = embed.add_field(name='Progress',value='0%',inline=True)
            first = False
          if 'progress' in gfystatus:
            pvalue = round(float(gfystatus['progress']) / 1.17  * 100,2)
            field2 = embed.set_field_at(index=1,name='Progress',value=f'{pvalue}%',inline=True)
            progress = gfystatus['progress']
        
          if oldprogress != progress:
            oldprogress = progress
            await embedm.edit(embed=embed)
          await asyncio.sleep(1)
      else:
          await asyncio.sleep(1)
         
    gfylog = await aiofiles.open(path.join(dirs['logs'],'gfy.log'),'a+',loop=client.loop)
    await gfylog.write(f'\n{gfylink}')
    await gfylog.close()
          
  await embedm.delete()
  xtemp,_,_ = await getTemp()

  
  if doembed:
    await message.channel.send( f'Gif taken for {message.author.mention} at: {timestamp} \n**Temperature:** {round(xtemp,2)}°C',file=discord.File(filepathmp4))
  else:
    await message.channel.send( f'Gfy taken for {message.author.mention} at: {timestamp} \n**Temperature:** {round(xtemp,2)}°C \n{gfylink}')
   
async def cEffects(client,message,params={}):
  '''Lists all available image/video effects'''
  effectnames = "```"
  for effectname in PiCamera.IMAGE_EFFECTS:
    effectnames = f"{effectnames}\n{effectname}"
  effectnames = f"{effectnames}```"
  await message.channel.send( effectnames )

async def cStatus(client,message,params={}):
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
  print(dir(camera.control.params[mmalobj.MMAL_PARAMETER_CAMERA_INFO]))
  await message.channel.send(dir(camera.control.params[mmalobj.MMAL_PARAMETER_CAMERA_INFO]))
  
 

# camera = mmalobj.MMALCamera()
camera = PiCamera()
# encoder = mmalobj.MMALVideoEncoder()
# encoder.format = 'h264'



commands = {
  'effects':[[],cEffects,False],
  'gif':[['gfy','gfycat'],cGif,True],
  'pic':[['picture'],cPic,True],
  'status':[['info'],cStatus,False]
}


camera.close()

client = discordfaby.Client(token=token,commands=commands,dirs=dirs)
client.loop.create_task(iPic())
GfycatClient = aiogfycat.Client(gfyid, gfysecret, loop=client.loop, session=client.session)
@client.event
async def on_ready():
  print('Logged in as:')
  print(client.user.name)
  print(client.user.id)
  print('Connected to:')
  for guild in client.guilds:
    print(guild.id)
    print(guild.name)
    print(guild.owner.name)
 
  await client.change_presence(activity=discord.Game(name='Live Pictures'))    
  await client.process_ready()

  
framefiles = listdir(client.dirs['frames'])
if len(framefiles) > 0:
  print(f'Frames directory not empty, deleting {len(framefiles)} files...')
  for ffile in framefiles:
      if path.splitext(ffile)[1] == '.jpg' or ffile == 'frames.txt':
        os.remove(path.join(client.dirs['frames'],ffile))
      else:
        print(f'FRAME DIRECTORY ({client.dirs["frames"]}) IS NOT EMPTY. REMOVE FILE {ffile}.')
        exit()
    
  
 
client.run(token)