import asyncio
import aiohttp
import aiofiles
from time import monotonic


class GfycatClient:
  def __init__(self,id,secret,loop=None,session=None):
      self._id = id
      self._secret = secret
      self._expiration = 0
      self._loop = loop
      self._session = session or aiohttp.ClientSession(loop=loop)
      self._token = ""
      
  
  
  async def _auth(self):
    data = {  
      "client_id": self._id,
      "client_secret": self._secret,
      "grant_type": "client_credentials"
    }
        
    async with self._session.post('https://api.gfycat.com/v1/oauth/token', data=str(data)) as rt:
      rtjson = await rt.json()
      self._token = f"Bearer {rtjson['access_token']}"
      self._expiration = monotonic() + int(rtjson['expires_in']) + 9999999
    return
    
  async def _auth_reqeust(self,*args, **kwargs):
    if monotonic() > self._expiration:
      await self._auth()
    
    if 'headers' in kwargs:
      kwargs['headers']["Authorization"] = self._token
    else:
      kwargs['headers'] = {"Authorization": self._token}
    async with self._session.request(*args, **kwargs) as r:
      if r.status == 401:
        await self._auth()
        kwargs['headers']["Authorization"] = self._token
        async with self._session.request(*args, **kwargs) as r2:
          return await r2.json()
      return await r.json()

  
    
  async def upload(self,file):
    headers = {'Content-Type': 'application/json'}
    rjson = await self._auth_reqeust('post', 'https://api.gfycat.com/v1/gfycats', headers=headers)
    if rjson['isOk']:  
      async with aiofiles.open(file,mode='rb',loop=self._loop) as f:
        fgfy = await f.read()
        data = aiohttp.FormData()
        data.add_field('key',rjson['gfyname'])
        data.add_field('file',
                       fgfy,
                       filename=rjson['gfyname'],
                       content_type='video/mp4')
        async with self._session.request('post','https://filedrop.gfycat.com', data=data) as r2:
          return rjson['gfyname']
    else:
      print(rjson)
        
    
  async def status(self,name):
    return await self._auth_reqeust('get',f'https://api.gfycat.com/v1/gfycats/fetch/status/{name}')
