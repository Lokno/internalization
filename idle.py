# Author     : Jonathan Decker "Lokno"
# Description: Joins an IRC channel and parses the chat messages for
# percentages. It writes the average percentage from each unique
# user to a file. Idle contributions are removed after a number of 
# seconds, as defined by the variable lifeTime declared on line 29
#
# Reference: https://twitchtv.desk.com/customer/en/portal/articles/1302780-twitch-irc

import socket
import re,os,time,sys
import wave
import configparser
import logging

def writefile(percent):
   with open(filePath,'w') as f:
      f.write("%s: %d%%" % (percentOf,percent))  

def getAvg(sum,count):
   avg = 0
   if count > 0:
      avg = sum/count
   return avg

LOG_FILENAME = 'idle_log.txt'
logging.basicConfig(filename=LOG_FILENAME, level=logging.INFO)

try:
   # Loading configuration file (ini format)
   config = configparser.ConfigParser(inline_comment_prefixes=';',)

   configFile = 'internalization.cfg'
   if not config.read(configFile):
      print('ERROR: could not open file %s' % configFile)
      sys.exit(-1)

   server   = config.get('MAIN','server')
   channel  = '#' + config.get('MAIN','channel')
   botnick  = config.get('MAIN','botnick')
   password = config.get('MAIN','password')
   usePygame = config.get('MAIN','usePygame', fallback=False)
   updateMapInterval = config.getint('TIMING','updateMapInterval')
   lifeTime          = config.getint('TIMING','lifeTime')
   cooldownSoundfile = config.getint('TIMING','cooldownSoundfile')
   percentOf = config.get('FILES','percentOf')
   filePath  = config.get('FILES','filePath')
   soundFilePath = config.get('FILES','goodPlayFilePath')

   percRE = re.compile("(?<![\d\.])(-?\d+\.?\d*)\%")
   nameRE = re.compile("^:([^!]+)!")

   # Attempt to use pygame to load audio file
   if usePygame:
      load_issue = False
      try:
         from pygame import mixer
         from pygame import error as pyerr
         mixer.init()
         try:
            sound = mixer.Sound(soundFilePath)
         except pyerr:
            print("ERROR: Could not load file %s. 32-bit WAVs are not supported." % soundFilePath)
            load_issue = True
      except ModuleNotFoundError:
         print("ERROR: Could not load pygame.mixer. Did you install it? >> python -m pip install pygame")
         load_issue = True

      if load_issue:
         print("Issue loading, defaulting to System.Media.SoundPlayer playback...")
         usePygame = False

   irc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

   print("connecting to:" + server)
   irc.connect((server, 6667))
   print("connected!")
   print("joining channel '%s' as '%s'..." % (channel,botnick))

   irc.send(("PASS " + password + "\n").encode())
   irc.send(("NICK " + botnick  + "\n").encode())
   irc.send(("JOIN " + channel  + "\n").encode())

   initialVal = 0
   lastCheck  = time.time()
   voteMap    = {}
   vsum       = 0
   count      = 0
   changed    = True
   lastCooldownCheck = 0

   writefile(0)

   while 1:
      text     = irc.recv(2040)
      currTime = time.time()

      percM = percRE.search(text.decode())
      nameM = nameRE.search(text.decode())

      if nameM and percM:
         # nonsense numbers from chat are converted
         # to integers in the range [0,100]
         # what does 0.5% internalization even mean?
         # also this can be -inf or inf, which is fun
         val = float(percM.group(1))
         val = int(max(0,min(val,100)))

         currName = nameM.group(1)

         # update sum, count and map
         if currName in voteMap:
            vsum -= voteMap[currName][0]
         else:
            count += 1
         vsum += val
         voteMap[currName] = [val,currTime]

         percent = getAvg(vsum,count)
         writefile(percent)

         if soundFilePath != "":
            # plays a sound file at 100% is it wasn't 100% before this vote and some
            # period of time has past since the last time it played
            if percent == 100 and changed and (currTime-lastCooldownCheck) > cooldownSoundfile:
               if usePygame:
                  that_was_good.play()
               else:
                  os.system('powershell -c (New-Object Media.SoundPlayer "%s").PlaySync();' % soundFilePath)   
               lastCooldownCheck = currTime
            elif percent != 100:
               changed = True

      # refreshes the map to remove votes from idle users
      if (currTime-lastCheck) > updateMapInterval:
         lastCheck = currTime
         for k,v in list(voteMap.items()):
            if (currTime-v[1]) >= lifeTime:
               del voteMap[k]
               vsum  -= v[0]
               count -= 1

         percent = getAvg(vsum,count)
         writefile(percent)

      # sends 'PONG' if 'PING' received to prevent pinging out
      if text.find('PING'.encode()) != -1: 
         irc.send(('PONG ' + text.decode().split() [1] + '\r\n').encode())
         
except Exception as e:
   logging.error(e, exc_info=True)
