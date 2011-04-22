
var auction = function () {
  var 
    channel, 
    socket,
    expiry,
    key,
    timer = null;

  on_opened = function() {
  };
  
  on_message = function(m) {
    var parsed = JSON.parse( m.data );
    update_view( parsed );
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
    key = state.key;
    document.getElementById( "bid" ).innerHTML = state.bid;
    document.getElementById( "bidder" ).innerHTML = state.bidder;
    document.getElementById( "item" ).innerHTML = state.item;
    document.getElementById( "message" ).innerHTML = state.message;
    expiry = new Date(new Date().getTime() + parseInt(state.remaining));
    if ( timer ) {
      clearTimeout( timer );
      timer = null;
    }
    update_remaining();
  }

  update_remaining = function() {
    var remaining = expiry.getTime() - new Date().getTime();
    if ( remaining > 0 ) {
      document.getElementById( "remaining" ).innerHTML = Math.round( remaining / 1000 );
      timer = setTimeout( update_remaining, 1000 );
    }
    else {
      document.getElementById( "remaining" ).innerHTML = "0";
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

    message: function(m) {
      log( "processing message: " + m );
      on_message( { "data": m } );
    }
  }
}

