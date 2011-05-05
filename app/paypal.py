import datetime
import decimal
import logging
import urllib
import urllib2

from google.appengine.api import urlfetch

# hack to enable urllib to work with Python
import os
os.environ['foo_proxy'] = 'bar'

from django.utils import simplejson as json

import settings

class Pay( object ):
  def __init__( self, amount, return_url, cancel_url, remote_address, secondary_receiver=None, ipn_url=None, shipping=False ):
    headers = {
      'X-PAYPAL-SECURITY-USERID': settings.PAYPAL_USERID, 
      'X-PAYPAL-SECURITY-PASSWORD': settings.PAYPAL_PASSWORD, 
      'X-PAYPAL-SECURITY-SIGNATURE': settings.PAYPAL_SIGNATURE, 
      'X-PAYPAL-REQUEST-DATA-FORMAT': 'JSON',
      'X-PAYPAL-RESPONSE-DATA-FORMAT': 'JSON',
      'X-PAYPAL-APPLICATION-ID': settings.PAYPAL_APPLICATION_ID,
      'X-PAYPAL-DEVICE-IPADDRESS': remote_address,
    }

    data = {
      'currencyCode': 'USD',
      'returnUrl': return_url,
      'cancelUrl': cancel_url,
      'requestEnvelope': { 'errorLanguage': 'en_US' },
    } 

    if shipping:
      data['actionType'] = 'CREATE'
    else:
      data['actionType'] = 'PAY'

    if secondary_receiver == None: # simple payment
      data['receiverList'] = { 'receiver': [ { 'email': settings.PAYPAL_EMAIL, 'amount': '%f' % amount } ] }
    else: # chained
      commission = amount * settings.PAYPAL_COMMISSION
      data['receiverList'] = { 'receiver': [ 
          { 'email': settings.PAYPAL_EMAIL, 'amount': '%0.2f' % amount, 'primary': 'true' },
          { 'email': secondary_receiver, 'amount': '%0.2f' % ( amount - commission ), 'primary': 'false' },
        ] 
      }

    if ipn_url != None:
      data['ipnNotificationUrl'] = ipn_url

    self.raw_request = json.dumps(data)
    #request = urllib2.Request( "%s%s" % ( settings.PAYPAL_ENDPOINT, "Pay" ), data=self.raw_request, headers=headers )
    #self.raw_response = urllib2.urlopen( request ).read() 
    self.raw_response = url_request( "%s%s" % ( settings.PAYPAL_ENDPOINT, "Pay" ), data=self.raw_request, headers=headers ).content() 
    logging.debug( "response was: %s" % self.raw_response )
    self.response = json.loads( self.raw_response )

    if shipping:
      # generate setpaymentoptions request
      options_raw_request = json.dumps( { 
        'payKey': self.paykey(),
        'senderOptions': { 'requireShippingAddressSelection': 'true', 'shareAddress': 'true' },
        'requestEnvelope': { 'errorLanguage': 'en_US' }
      } )
      options_raw_response = url_request( "%s%s" % ( settings.PAYPAL_ENDPOINT, "SetPaymentOptions" ), data=options_raw_request, headers=headers ).content() 
      logging.debug( 'SetPaymentOptions response: %s' % options_raw_response )
      # TODO check response was OK
    
  def status( self ):
    if self.response.has_key( 'paymentExecStatus' ):
      return self.response['paymentExecStatus']
    else:
      return None 

  def amount( self ):
    return decimal.Decimal(self.results[ 'payment_gross' ])

  def paykey( self ):
    return self.response['payKey']

  def next_url( self ):
    return '%s?cmd=_ap-payment&paykey=%s' % ( settings.PAYPAL_PAYMENT_HOST, self.response['payKey'] )

class IPN( object ):
  def __init__( self, request ):
    # verify that the request is paypal's
    self.error = None
    #verify_request = urllib2.Request( "%s?cmd=_notify-validate" % settings.PAYPAL_PAYMENT_HOST, data=urllib.urlencode( request.POST.copy() ) )
    #verify_response = urllib2.urlopen( verify_request )
    verify_response = url_request( "%s?cmd=_notify-validate" % settings.PAYPAL_PAYMENT_HOST, data=urllib.urlencode( request.POST.copy() ) )
    # check code
    if verify_response.code() != 200:
      self.error = 'PayPal response code was %i' % verify_response.code()
      return
    # check response
    raw_response = verify_response.content()
    if raw_response != 'VERIFIED':
      self.error = 'PayPal response was "%s"' % raw_response
      return
    # check payment status
    if request.get('status') != 'COMPLETED':
      self.error = 'PayPal status was "%s"' % request.get('status')
      return

    (currency, amount) = request.get( "transaction[0].amount" ).split(' ')
    if currency != 'USD':
      self.error = 'Incorrect currency %s' % currency
      return

    self.amount = decimal.Decimal(amount)

  def success( self ):
    return self.error == None

class ShippingAddress( object ):
  def __init__( self, paykey, remote_address ):
    headers = {
      'X-PAYPAL-SECURITY-USERID': settings.PAYPAL_USERID, 
      'X-PAYPAL-SECURITY-PASSWORD': settings.PAYPAL_PASSWORD, 
      'X-PAYPAL-SECURITY-SIGNATURE': settings.PAYPAL_SIGNATURE, 
      'X-PAYPAL-REQUEST-DATA-FORMAT': 'JSON',
      'X-PAYPAL-RESPONSE-DATA-FORMAT': 'JSON',
      'X-PAYPAL-APPLICATION-ID': settings.PAYPAL_APPLICATION_ID,
      'X-PAYPAL-DEVICE-IPADDRESS': remote_address,
    }

    data = {
      'key': paykey,
      'requestEnvelope': { 'errorLanguage': 'en_US' },
    } 

    self.raw_request = json.dumps(data)
    self.raw_response = url_request( "%s%s" % ( settings.PAYPAL_ENDPOINT, "GetShippingAddresses" ), data=self.raw_request, headers=headers ).content() 
    logging.debug( "response was: %s" % self.raw_response )
    self.response = json.loads( self.raw_response )

class url_request( object ): 
  '''wrapper for urlfetch'''
  def __init__( self, url, data=None, headers={} ):
    # urlfetch - validated
    self.response = urlfetch.fetch( url, payload=data, headers=headers, method=urlfetch.POST, validate_certificate=True )
    # urllib - not validated
    #request = urllib2.Request(url, data=data, headers=headers) 
    #self.response = urllib2.urlopen( https_request )

  def content( self ):
    return self.response.content 

  def code( self ):
    return self.response.status_code

class Preapproval( object ):
  def __init__( self, amount, return_url, cancel_url, remote_address ):
    headers = {
      'X-PAYPAL-SECURITY-USERID': settings.PAYPAL_USERID, 
      'X-PAYPAL-SECURITY-PASSWORD': settings.PAYPAL_PASSWORD, 
      'X-PAYPAL-SECURITY-SIGNATURE': settings.PAYPAL_SIGNATURE, 
      'X-PAYPAL-REQUEST-DATA-FORMAT': 'JSON',
      'X-PAYPAL-RESPONSE-DATA-FORMAT': 'JSON',
      'X-PAYPAL-APPLICATION-ID': settings.PAYPAL_APPLICATION_ID,
      'X-PAYPAL-DEVICE-IPADDRESS': remote_address,
    }

    now = datetime.datetime.utcnow()
    expiry = now + datetime.timedelta( days=settings.PREAPPROVAL_PERIOD )
    data = {
      'endingDate': expiry.isoformat(),
      'startingDate': now.isoformat(),
      'maxTotalAmountOfAllPayments': '%.2f' % amount,
      'currencyCode': 'USD',
      'returnUrl': return_url,
      'cancelUrl': cancel_url,
      'requestEnvelope': { 'errorLanguage': 'en_US' },
    } 

    self.raw_request = json.dumps(data)
    self.raw_response = url_request( "%s%s" % ( settings.PAYPAL_ENDPOINT, "Preapproval" ), data=self.raw_request, headers=headers ).content() 
    logging.debug( "response was: %s" % self.raw_response )
    self.response = json.loads( self.raw_response )

  def key( self ):
    if self.response.has_key( 'preapprovalKey' ):
      return self.response['preapprovalKey']
    else:
      return None

  def next_url( self ):
    return '%s?cmd=_ap-preapproval&preapprovalkey=%s' % ( settings.PAYPAL_PAYMENT_HOST, self.response['preapprovalKey'] )

  def status( self ):
    if self.response.has_key( 'responseEnvelope' ) and self.response['responseEnvelope'].has_key( 'ack' ):
      return self.response['responseEnvelope']['ack']
    else:
      return None 

class PayWithPreapproval( object ):
  def __init__( self, amount, preapproval_key ):
    headers = {
      'X-PAYPAL-SECURITY-USERID': settings.PAYPAL_USERID, 
      'X-PAYPAL-SECURITY-PASSWORD': settings.PAYPAL_PASSWORD, 
      'X-PAYPAL-SECURITY-SIGNATURE': settings.PAYPAL_SIGNATURE, 
      'X-PAYPAL-REQUEST-DATA-FORMAT': 'JSON',
      'X-PAYPAL-RESPONSE-DATA-FORMAT': 'JSON',
      'X-PAYPAL-APPLICATION-ID': settings.PAYPAL_APPLICATION_ID,
      'X-PAYPAL-DEVICE-IPADDRESS': '127.0.0.1', #remote_address,
    }

    data = {
      'actionType': 'PAY',
      'amount': '%.2f' % amount,
      'preapprovalKey': preapproval_key,
      'currencyCode': 'USD',
      'returnUrl': 'http://dummy',
      'cancelUrl': 'http://dummy',
      'requestEnvelope': { 'errorLanguage': 'en_US' },
      'receiverList': { 'receiver': [ { 'email': settings.PAYPAL_EMAIL, 'amount': '%.2f' % amount } ] }
    } 

    self.raw_request = json.dumps(data)
    self.raw_response = url_request( "%s%s" % ( settings.PAYPAL_ENDPOINT, "Pay" ), data=self.raw_request, headers=headers ).content() 
    logging.debug( "response was: %s" % self.raw_response )
    self.response = json.loads( self.raw_response )

  def status( self ):
    if self.response.has_key( 'paymentExecStatus' ):
      return self.response['paymentExecStatus']
    else:
      return None 

  def paykey( self ):
    return self.response['payKey']

