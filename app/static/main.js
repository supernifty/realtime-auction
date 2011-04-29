
var auction = function () {
  var 
    channel, 
    socket,
    expiry,
    key,
    timer = null,
    stopped = false;

  on_opened = function() {
  };
  
  on_message = function(m) {
    console.log( "got " + m.data );
    if ( stopped ) {
      console.log( "ignored" );
    }
    else {
      var parsed = JSON.parse( m.data );
      update_view( parsed );
    }
  };
  
  on_error = function() {
    log( "An error occurred" );
  };
  
  on_close = function() {
    log( "Connection closed" );
  };

  send = function(path, params) {
    if (params) {
      path += '?' + params;
    }
    var xhr = new XMLHttpRequest();
    xhr.open('POST', path, true);
    xhr.send();
    log( "sent: " + path );
  };

  update_view = function( state ) {
    document.getElementById( "message" ).innerHTML = state.message;
    if ( state.state == 'OK' ) {
      document.getElementById( "auction" ).style.display = 'block';
      key = state.key;
      if ( state.bid == '0.00' ) {
        document.getElementById( "bid" ).innerHTML = 'No bids.';
      }
      else {
        document.getElementById( "bid" ).innerHTML = "Current bid: " + state.bid + " by " + state.bidder;
      }
      document.getElementById( "item_image" ).innerHTML = "<img src='/static/placeholder.png' alt='" + state.item + "'>";
      document.getElementById( "item" ).innerHTML = state.item;
      expiry = new Date(new Date().getTime() + parseInt(state.remaining) * 1000 );
      if ( timer ) {
        clearTimeout( timer );
        timer = null;
      }
      update_remaining();
    }
    else if ( state.state == 'STOP' ) { 
      document.getElementById( "auction" ).style.display = 'none';
      document.getElementById( "confirm" ).style.display = 'block';
      stopped = true;
    }
    else { // something wrong
      document.getElementById( "auction" ).style.display = 'none';
      timer = setTimeout( ping, 30000 );
    }
  }

  ping = function() {
    console.log( "sending ping" );
    send( "/ping" );
  }

  update_remaining = function() {
    var remaining = Math.round( ( expiry.getTime() - new Date().getTime() ) / 1000 );
    if ( remaining > 0 ) {
      document.getElementById( "remaining" ).innerHTML = "This auction will expire in " + Math.round( remaining ) + " second" + ( remaining == 1 ? "" : "s" );
      timer = setTimeout( update_remaining, 1000 );
    }
    else {
      document.getElementById( "remaining" ).innerHTML = "Auction FINISHED";
      timer = setTimeout( ping, 1000 );
    }
  }

  log = function(l) {
    document.getElementById( "log" ).innerHTML = l;
  }
  
  return {
    init: function (token) {
      channel = new goog.appengine.Channel(token);
      socket = channel.open();
      socket.onopen = on_opened;
      socket.onmessage = on_message;
      socket.onerror = on_error;
      socket.onclose = on_close;
    },

    new_bid: function() {
      send( "/bid", "key=" + key + "&amount=" + document.getElementById("new_bid").value );
    },

    confirm_purchase: function() {
      send( "/ping" );
      document.getElementById( "confirm" ).style.display = 'none';
      stopped = false;
    },

    message: function(m) {
      log( "got: " + m );
      on_message( { "data": m } );
    }
  }
}

