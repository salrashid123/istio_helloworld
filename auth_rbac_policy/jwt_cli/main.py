import json
import os
import pprint
import datetime, time, base64

from google.oauth2 import service_account
from google.oauth2 import id_token
import google.auth.transport.requests
import requests

# Sample script to setup self-signed JWTs with custom claims
# TO use, download a service account JSON file from the Google Cloud Console
# and save as 'svc_account.json`.  Running this script will generate two JWTs

cred = None 

def getToken(subject, audience, custom_claims):
  print("Getting custom jwt")

  jwt_header= {
     "alg": "RS256",
     "typ": "JWT"
  }  

  now = int(time.time())
  exptime = now + 3600
  std_claims = {
     "sub": subject,
     "iss": cred.service_account_email, 
     "aud": audience,
     "exp":exptime,
     "iat":now
  }
  payload = std_claims.copy() 
  payload.update(custom_claims)
  jwt = _urlsafe_b64encode(json.dumps(jwt_header)) + '.' +  _urlsafe_b64encode(json.dumps(payload))

  b = cred.sign_bytes(jwt)
  assertion = jwt  +  '.' + _urlsafe_b64encode(b)

  return assertion


def verifyToken(token,audience):
  JWK_URL = 'https://www.googleapis.com/service_accounts/v1/jwk/' + cred.service_account_email
  X509_URL ='https://www.googleapis.com/service_accounts/v1/metadata/x509/' + cred.service_account_email

  request = google.auth.transport.requests.Request()
  id_info = id_token.verify_token(
      token, request, audience, certs_url=X509_URL)

  if id_info['iss'] != cred.service_account_email:
      raise ValueError('Wrong issuer.')
  print id_info['sub']

def _urlsafe_b64encode(raw_bytes):
    return base64.urlsafe_b64encode(raw_bytes).rstrip('=')
   
def _urlsafe_b64decode(b64string):
    # Guard against unicode strings, which base64 can't handle.
    b64string = b64string.encode('ascii')
    padded = b64string + '=' * (4 - len(b64string) % 4)
    return base64.urlsafe_b64decode(padded)
      
if __name__ == '__main__':

    cred = service_account.Credentials.from_service_account_file('service_account.json')
    fbtok = getToken("alice", "https://svc1.example.com", {}) 
    print "TOKEN_ALICE: " + fbtok


    fbtok = getToken("bob", "https://svc2.example.com", {'groups': ['group1','group2']}) 
    print "TOKEN_BOB: " + fbtok

    fbtok = getToken("bob", "https://svc2.example.com", {}) 
    print "TOKEN_BOB NO GROUPS: " + fbtok
     
 
    #verifyToken(fbtok, "https://foo.bar")

