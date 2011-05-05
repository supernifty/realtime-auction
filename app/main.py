import cgi
import datetime
import decimal
import logging
import os
import random
import simplejson

from google.appengine.api import channel
from google.appengine.api import users
from google.appengine.ext import db
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import login_required
from google.appengine.ext.webapp.util import run_wsgi_app

import model
import paypal
import settings
import util

class Home(webapp.RequestHandler):
  def get(self):
    '''initialize the main auction page'''
    # ensure logged in
    user = users.get_current_user()
    if not user:
      self.redirect(users.create_login_url(self.request.uri))
      return

    token = channel.create_channel(user.user_id())
    model.Client.add( user )

    data = {
      'token': token,
      'state': simplejson.dumps( model.Item.state() )
    }
    path = os.path.join(os.path.dirname(__file__), 'templates/main.htm')
    self.response.out.write(template.render(path, data))

class Ping(webapp.RequestHandler):
  '''tell server i'm still listening'''
  def post(self):
    user = users.get_current_user()
    model.Client.add( user )
    util.notify( user )

class Bid(webapp.RequestHandler):
  '''make a bid'''
  def post(self):
    user = users.get_current_user()
    item = model.Item.get( self.request.get( "key" ) )
    logging.info( "got item %s" % item.title )
    if item.status == "INPROGRESS":
      # current max
      amount = float( self.request.get( "amount" ) )
      logging.info( "got amount %f" % amount )
      if amount > float( item.bid_info()['bid'] ):
        balance = model.Profile.find( user ).preapproval_amount
        if int(amount*100) <= balance: # TODO check preapproval expiry
          logging.info( "adding bid" )
          model.Bid( bidder=user, amount=int(amount*100), item=item ).save()
          util.notify_all(user, "You bid $%.2f for %s" % ( amount, item.title ) )
        else:
          util.notify( user, "Bid exceeds balance of $%.2f. Update your profile!" % float( balance / 100 ) ) # no good
      else:
        util.notify( user, "Bid must be more than $%.2f" % float( item.bid_info()['bid'] ) ) # no good
    else:
      util.notify( user, "Item '%s' is no longer being auctioned" % item.title ) # no good

class Add(webapp.RequestHandler):
  '''add new items to sell'''
  def get(self):
    path = os.path.join(os.path.dirname(__file__), 'templates/add.htm')
    self.response.out.write(template.render(path, {} ))

  def post(self):
    items = self.request.get( "items" )
    count = 0
    for item in items.split( "\n" ):
      if len(item) > 0:
        model.Item( title=item.strip(), status="READY" ).save()
        count += 1
    path = os.path.join(os.path.dirname(__file__), 'templates/add.htm')
    self.response.out.write(template.render(path, { 'message': "%i items added" % count } ))

class Profile(webapp.RequestHandler):
  '''update user's profile'''
  def get(self):
    user = users.get_current_user()
    if not user:
      self.redirect(users.create_login_url(self.request.uri))
    profile = model.Profile.find( user )
    data = { 'user': user, 'profile': profile }
    path = os.path.join(os.path.dirname(__file__), 'templates/profile.htm')
    self.response.out.write(template.render(path, data))

  def post(self):
    '''start preapproval'''
    user = users.get_current_user()
    if not user:
      self.redirect(users.create_login_url(self.request.uri))

    amount = float(self.request.get( "amount" ))
    item = model.Preapproval( user=user, status="NEW", secret=util.random_alnum(16), amount=int(amount*100) )
    item.put()
    # get key
    preapproval = paypal.Preapproval(
      amount=amount,
      return_url="%s/success/%s/%s/" % ( self.request.uri, item.key(), item.secret ),
      cancel_url=self.request.uri,
      remote_address=self.request.remote_addr )
    
    item.debug_request = preapproval.raw_request
    item.debug_response = preapproval.raw_response
    item.put()

    if preapproval.status() == 'Success':
      item.status = 'CREATED'
      item.preapproval_key = preapproval.key()
      item.put()
      self.redirect( preapproval.next_url() ) # go to paypal
    else:
      item.status = 'ERROR'
      item.status_detail = 'Preapproval status was "%s"' % preapproval.status()
      item.put()

    path = os.path.join(os.path.dirname(__file__), 'templates/profile.htm')
    self.response.out.write(template.render(path, { 'message': 'An error occurred connecting to PayPal', 'user': user, 'profile': model.Profile.find( user ) } ))

class Success (webapp.RequestHandler):
  def get(self, key, secret):
    logging.info( "returned from paypal" )
    
    item = model.Preapproval.get( key )

    # validation
    if item == None: # no key
      self.error(404)
      return

    if item.status != 'CREATED':
      item.status_detail = 'Unexpected status %s' % item.status
      item.status = 'ERROR'
      item.put()
      self.error(501)
      return
      
    if item.secret != secret:
      item.status_detail = 'Incorrect secret %s' % secret
      item.status = 'ERROR'
      item.put()
      self.error(501)
      return

    # looks ok
    profile = model.Profile.find( item.user )
    profile.preapproval_amount = item.amount
    profile.preapproval_expiry = datetime.datetime.utcnow() + datetime.timedelta( days=settings.PREAPPROVAL_PERIOD )
    profile.preapproval_key = item.preapproval_key
    profile.put()
    item.status = 'COMPLETED'
    item.put()
    
    path = os.path.join(os.path.dirname(__file__), 'templates/profile.htm')
    self.response.out.write(template.render(path, { 'message': 'Your preapproved limit was updated.', 'user': item.user, 'profile': profile } ))

class NotFound (webapp.RequestHandler):
  def get(self):
    self.error(404)

application = webapp.WSGIApplication( [
    ('/', Home),
    ('/bid', Bid),
    ('/ping', Ping),
    ('/add', Add),
    ('/profile', Profile),
    ('/profile/success/([^/]*)/([^/]*)/.*', Success),
    ('/.*', NotFound),
  ],
  debug=True)

def main():
  logging.getLogger().setLevel(logging.DEBUG)
  run_wsgi_app(application)

if __name__ == "__main__":
  main()

