import logging
import json
import httplib2
import os
import pprint
import sys

import urllib,urllib2
from urllib2 import URLError, HTTPError

import firebase_admin
from firebase_admin import credentials
from firebase_admin import auth

default_app = None 

# Creates a Firebase Secure Token.

# On the Cloud Identity Console, select `Application setup details` link on the top right and note the  `API_KEY` it provides.   
# Create a service account JSON key as described under [Firebase SDK](https://firebase.google.com/docs/admin/setup#initialize_the_sdk).  
# Copy the JSON certificate file into the `auth_rbac_policy/firebase_cli` folder and save it as `svcaccount.json`. 
# Edit `fb_token.py` and add the `API_KEY` into the code.


API_KEY='YOUR_API_KEY'

def verifyIdToken(id_token):
    try:
      decoded_token = auth.verify_id_token(id_token)
      uid = decoded_token['uid']
      print("Verified User " + uid)
      return True
    except auth.AuthError as e:
      logging.error(e.detail)
    except Exception as e:
      logging.error(e)
    return False

def getFBToken(uid, groups):
  print("Getting custom id_token")
  try:
      additionalClaims = {
        'premiumAccount': True,
        'groups': groups
      }
      token = auth.create_custom_token(uid, additionalClaims)
      return token
      
  except auth.AuthError as e:
      print(e.detail)
  except Exception as e:
      print(e)

def getSTSToken(tok):
  print("Getting STS id_token")
  try:

    url = 'https://www.googleapis.com/identitytoolkit/v3/relyingparty/verifyCustomToken?key=' + API_KEY
    data = {'returnSecureToken' : True,
            'token' :tok}
    headers = {"Content-type": "application/x-www-form-urlencoded"}
     
    data = urllib.urlencode(data)
    req = urllib2.Request(url, data, headers)
    resp = urllib2.urlopen(req).read()
    parsed = json.loads(resp)
    idToken = parsed.get('idToken')
    return idToken
  except Exception as e:
      print(e)

if __name__ == '__main__':

    cred = credentials.Certificate('svc_account.json')
    default_app = firebase_admin.initialize_app(cred)   
    
    fbtok = getFBToken('alice',[]) 
    ststok = getSTSToken(fbtok)
    print "STS Token for alice \n"
    print ststok
    print '-----------------------'

    fbtok = getFBToken('bob',['group1','group2']) 
    ststok = getSTSToken(fbtok)
    print "STS Token for bob \n" 
    print ststok
    print '-----------------------'

    #verifyIdToken(ststok)
