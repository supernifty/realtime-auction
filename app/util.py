import logging
import simplejson

from google.appengine.api import channel
from google.appengine.api import users

import model

def notify():
  logging.info( "notifying of new state" )
  for client in model.Client.all():
    logging.info( "notifying of new state for %s" % client.user.email() )
    channel.send_message( client.user.user_id(), simplejson.dumps( model.Item.state() ) )
  logging.info( "notifying of new state: done" )
