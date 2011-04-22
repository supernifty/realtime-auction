
from google.appengine.ext import db

class Item( db.Model ):
  created = db.DateTimeProperty(auto_now_add=True)
  title = db.StringProperty()
  image = db.BlobProperty()
  status = db.StringProperty( choices=( 'READY', 'INPROGRESS', 'FINISHED', 'DISABLED' ) )

  def bid_info( self ):
    bids = Bid.all().filter( "item =", self ).order( "-amount" ).fetch(1)
    if len(bids) > 0:
      return { 'bid': bids[0].amount_dollars(), 'bidder': bids[0].bidder.email() }
    else:
      return { 'bid': '0.00', 'bidder': 'None' }

  @staticmethod
  def state():
    '''current state'''
    item = Item.current()
    result = {}
    if item == None:
      item = Item.next()
      if item == None:
        result['message'] = 'No item available for sale'
        return result
    else:
      bids = Bid.all().filter( "item =", item ).order( "-amount" ).fetch(1)

    bid_info = item.bid_info()
    result['bid'] = bid_info['bid']
    result['bidder'] = bid_info['bidder']
    result['key'] = str(item.key())
    result['item'] = item.title
    result['message'] = ''
    result['remaining'] = '10000'

    return result

  @staticmethod
  def current():
    '''current auction'''
    return Item.all().filter( "status =", "INPROGRESS" ).get()

  @staticmethod
  def next():
    item = Item.all().filter( "status =", "READY" ).fetch(1)
    if len(item) > 0:
      item[0].status = 'INPROGRESS'
      item[0].save()
      return item[0]

class Bid ( db.Model ):
  bidder = db.UserProperty()
  created = db.DateTimeProperty(auto_now_add=True)
  amount = db.IntegerProperty() # cents
  item = db.ReferenceProperty( Item )

  def amount_dollars( self ):
    return self.amount / 100.0

class Client( db.Model ):
  user = db.UserProperty()
