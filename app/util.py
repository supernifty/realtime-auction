import logging
import random
import simplejson
import string

from google.appengine.api import channel
from google.appengine.api import users

import model

def notify_all( user, message ):
  logging.info( "notifying of new state" )
  user_state = simplejson.dumps( model.Item.state( message ) ) 
  default_state = simplejson.dumps( model.Item.state() ) 
  for client in model.Client.all():
    logging.info( "notifying of new state for %s" % client.user.email() )
    if user == client.user:
      channel.send_message( client.user.user_id(), user_state )
    else:
      channel.send_message( client.user.user_id(), default_state )

  logging.info( "notifying of new state: done" )

def notify( user, message='' ):
  channel.send_message( user.user_id(), simplejson.dumps( model.Item.state( message ) ) )

def notify_message( user, state, message ):
  channel.send_message( user.user_id(), simplejson.dumps( { 'state': state, 'message': message } ) )

def random_alnum( count ):
  chars = string.letters + string.digits
  result = ''
  for i in range(count):
    result += random.choice(chars)
  return result

