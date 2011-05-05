# settings for app

PAYPAL_ENDPOINT = 'https://svcs.sandbox.paypal.com/AdaptivePayments/' # sandbox
#PAYPAL_ENDPOINT = 'https://svcs.paypal.com/AdaptivePayments/' # production

PAYPAL_PAYMENT_HOST = 'https://www.sandbox.paypal.com/au/cgi-bin/webscr' # sandbox
#PAYPAL_PAYMENT_HOST = 'https://www.paypal.com/webscr' # production

PAYPAL_USERID = '*** REQUIRED ***'
PAYPAL_PASSWORD = '*** REQUIRED ***'
PAYPAL_SIGNATURE = '*** REQUIRED ***'
PAYPAL_APPLICATION_ID = 'APP-80W284485P519543T' # sandbox only
PAYPAL_EMAIL = '*** REQUIRED ***'

BID_WAIT = 10 # how long to wait before ending the auction (s) 
PREAPPROVAL_PERIOD = 28 # days to ask for in a preapproval
