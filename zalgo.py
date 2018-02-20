
from random import choice
from random import random

wsym = []
wsym.append([
'̍','̎','̄','̅','̿','̑','̆','̐','͒','͗',
'͑','̇','̈','̊','͂','̓','̈́','͊','͋','͌',
'̃','̂','̌','͐','̀','́','̋','̏','̒','̓',
'̔','̽','̉','ͣ','ͤ','ͥ','ͦ','ͧ','ͨ','ͩ',
'ͪ','ͫ','ͬ','ͭ','ͮ','ͯ','̾','͛','͆','̚' ])

wsym.append([
'̕','̛','̀','́','͘','̡','̢','̧','̨','̴',
'̵','̶','͏','͜','͝','͞','͟','͠','͢','̸',
'̷','͡','҉'])

wsym.append([
'̖','̗','̘','̙','̜','̝','̞','̟','̠','̤',
'̥','̦','̩','̪','̫','̬','̭','̮','̯','̰',
'̱','̲','̳','̹','̺','̻','̼','ͅ','͇','͈',
'͉','͍','͎','͓','͔','͕','͖','͙','͚'])



def zalgo(text,strength=3, mode=0): 
    
  ntext = ""
  for i, c in enumerate(text):
    nc = c
    trail = min(4,int(len(text)/10))
    if i > trail:
      slen = int(len(text)-trail*2)
      sprob = (i-trail)/slen
      if mode == 1:
        for x in range(int(sprob*strength)):
          for y in range(2):
            if random()<sprob*0.5:
              nc += choice(wsym[y])
      if mode == 2:
        for x in range(int(sprob*strength)):
          for y in range(2):
            if random()>sprob*0.5:
              nc += choice(wsym[y])
      else:
        for x in range(strength):
          for y in range(2):
            if random()<0.15:
              nc += choice(wsym[y])
    ntext += nc
        
  return ntext
  
if __name__ == "__main__":
   
  text = input("Text to fuck up: ")
  # text = "This is a long text that should gradually become more fucked up."
  while len(text) < 5:
    text = input("Too short bro: ")
  tfile = open("output.txt", "bw+")
  tfile.write(zalgo(text).encode("utf-8"))