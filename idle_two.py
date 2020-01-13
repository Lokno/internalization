# Author     : Jonathan Decker "Lokno"
# Description: Joins an IRC channel and parses the chat messages for
# percentages. It writes the average percentage from each unique
# user to a file. Idle contributions are removed after a number of 
# seconds, as defined by the variable lifeTime declared on line 19
# 
# Two Player Variant - type dd%a for Player A and dd%b for Player B
# dd% without a letter will default to Player A.
#
# Reference: https://twitchtv.desk.com/customer/en/portal/articles/1302780-twitch-irc
 
import socket
import string
import re,os,time,sys
import traceback

def writefile(aN, aP, bN, bP):
   with open(filePathA,'w') as f:
      f.write("%s: %d%%" % (aN,aP))
   with open(filePathB,'w') as f:
      f.write("%s: %d%%" % (bN,bP)) 
 
# Return of Ganon Font - https://zeldauniverse.net/media/fonts/
def writeMeterFiles(aN, aP, bN, bP, max_hearts):
   aFull = int(aP) / (100/max_hearts)
   bFull = int(bP) / (100/max_hearts)
   with open(filePathNick,'w') as f:
      f.write(aN + ": " + "#" * aFull + "*" * (max_hearts-aFull))
   with open(filePathJanel,'w') as f:
      f.write(bN + ": " + "#" * bFull + "*" * (max_hearts-bFull))  
 
def getAvg(sum,count):
   avg = 0
   if count > 0:
      avg = sum/count
   return avg

try:
   server   = "irc.chat.twitch.tv"
   channel  = "#CHANNEL"
   botnick  = "ACCOUNTNAME"
   password = "OAUTHTOKEN"
   letterA = 'a'
   letterB = 'b'
   filePathA = "internalization.txt"
   filePathB = "internalization_b.txt"

   updateMapInterval = 60
   lifeTime          = 60*3  # Time before a user's vote expires

   letterA = letterA.lower()
   letterB = letterB.lower()

   if letterA not in string.ascii_lowercase:
      letterA = 'a'
   if letterB not in string.ascii_lowercase:
      letterB = 'b'

   matchSetA = letterA + letterA.upper()
   matchSetB = letterB + letterB.upper()
     
   percA_RE   = re.compile("(?<![\d\.])(-?\d+\.?\d*)\%([" + matchSetA + "]?)(?![jJ])")
   percB_RE   = re.compile("(?<![\d\.])(-?\d+\.?\d*)\%([" + matchSetB + "])")
   nameRE     = re.compile("^:([^!]+)!")
    
   irc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
   print("connecting to:" + server)
   irc.connect((server, 6667))
   print("connected!")
   print("joining channel %s as %s..." % (channel,botnick))
    
   irc.send(("PASS " + password + "\n").encode())
   irc.send(("NICK " + botnick  + "\n").encode())
   irc.send(("JOIN " + channel  + "\n").encode())
    
   lastCheck  = time.time()
    
   voteMapA = {}
   vsumA    = 0
   countA   = 0
    
   voteMapB = {}
   vsumB    = 0
   countB   = 0
    
   writefile('A',0,'B',0)

   while 1:
      text     = irc.recv(2040)
      currTime = time.time()
    
      percAM = percA_RE.search(text.decode())
      percBM = percB_RE.search(text.decode())
      nameM  = nameRE.search(text.decode())
    
      if nameM and (percAM or percBM):
         matches = []
         if percAM:
            matches.append((percAM.group(1),percAM.group(2)))
         if percBM:
            matches.append((percBM.group(1),percBM.group(2)))
    
         for percM in matches:
            # nonsense numbers from chat are converted
            # to integers in the range [0,100]
            # what does 0.5% internalization even mean?
            # also this can be -inf or inf, which is fun
            whoStr = letterA
            if percM[1] != '':
               whoStr = percM[1].lower()
            val = float(percM[0])
            val = int(max(0,min(val,100)))
    
            currName = nameM.group(1)
    
            # update sum, count and map
            if( whoStr == letterA ):
               if currName in voteMapA:
                  vsumA -= voteMapA[currName][0]
               else:
                  countA += 1
               vsumA += val
               voteMapA[currName] = [val,currTime]
            else:
               if currName in voteMapB:
                  vsumB -= voteMapB[currName][0]
               else:
                  countB += 1
               vsumB += val
               voteMapB[currName] = [val,currTime]
    
         writefile(getAvg(vsumA,countA),getAvg(vsumB,countB))
    
      # refreshes the map to remove votes from idle users
      if (currTime-lastCheck) > updateMapInterval:
         lastCheck = currTime
    
         for k,v in list(voteMapA.items()):
            if (currTime-v[1]) >= lifeTime:
               del voteMapA[k]
               vsumA  -= v[0]
               countA -= 1
    
         for k,v in list(voteMapB.items()):
            if (currTime-v[1]) >= lifeTime:
               del voteMapB[k]
               vsumB  -= v[0]
               countB -= 1
    
         writefile(getAvg(vsumA,countA),getAvg(vsumB,countB))
        
      # sends 'PONG' if 'PING' received to prevent pinging out
      if text.find('PING'.encode()) != -1: 
         irc.send(('PONG ' + text.decode().split() [1] + '\r\n').encode())
         
except:
   with open('idle_log.txt','w') as f:
      print("EXCEPTION OCCURRED: Aborting %s. See idle_log.txt" % sys.argv[0])
      traceback.print_exc(file=f)
