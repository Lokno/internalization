# Author     : Jonathan Decker "Lokno"
# Description: Joins an IRC channel and parses the chat messages for
# percentages. It writes the average percentage from each unique
# user to a file. Idle contributions are removed after a number of 
# seconds, as defined by the variable lifeTime declared on line 29

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

def connection(host, port, nick, password, chan):
    global connected
    connected = False
    while connected is False:
        try:
            irc.connect((host, port))
            irc.send(("PASS %s\r\n" % password).encode())
            irc.send(("NICK %s\r\n" % nick).encode())
            #irc.send("USER %s %s bla :%s\r\n" % (ident, host, realname))
            irc.send(("JOIN :%s\r\n" % chan).encode())
            
            connected = True
        except socket.error:
            print("Attempting to connect...")
            time.sleep(5)
            continue
    print("connected!")
    print("joined channel '%s' as '%s'..." % (chan,nick))

LOG_FILENAME = 'idle_log.txt'
logging.basicConfig(filename=LOG_FILENAME, level=logging.DEBUG)

try:
   # Loading configuration file (ini format)
   config = configparser.ConfigParser(inline_comment_prefixes=';',)

   configFile = 'internalization.cfg'
   if not config.read(configFile):
      logging.info('ERROR: could not open file %s' % configFile)
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
            logging.info("ERROR: Could not load file %s. 32-bit WAVs are not supported." % soundFilePath)
            load_issue = True
      except ModuleNotFoundError:
         logging.info("ERROR: Could not load pygame.mixer. Did you install it? >> python -m pip install pygame")
         load_issue = True

      if load_issue:
         logging.info("Issue loading, defaulting to System.Media.SoundPlayer playback...")
         usePygame = False

   irc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

   connection(server, 6667, botnick, password, channel)

   initialVal = 0
   lastCheck  = time.time()
   voteMap    = {}
   vsum       = 0
   count      = 0
   changed    = True
   lastCooldownCheck = 0

   writefile(0)

   #connected = True
   threshold = 3 * 60
   lastPing = time.time()
   while connected:
      text     = irc.recv(2048)
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
         lastPing = time.time()
      
      if (time.time() - lastPing) > threshold:
         print("Ping Timeout")
         connected = False

      if not connected:
         print("Restarting Connection...")
         irc.close()
         irc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
         connection(server, 6667, botnick, password, channel)
         
         # Reset State
         writefile(0)
         initialVal = 0
         lastCheck  = time.time()
         lastPing   = lastCheck
         voteMap    = {}
         vsum       = 0
         count      = 0
         changed    = True
         lastCooldownCheck = 0
except Exception as e:
   logging.error(e, exc_info=True)
