var stripeElements = function(publicKey, setupIntent) {
  var stripe = Stripe(publicKey);
  var elements = stripe.elements();

  // Element styles
  var style = {
    base: {
      fontSize: "16px",
      color: "#32325d",
      fontFamily:
        "-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif",
      fontSmoothing: "antialiased",
      "::placeholder": {
        color: "rgba(0,0,0,0.4)"
      }
    }
  };

	/* -- */
	var paymentRequest = stripe.paymentRequest({
  	country: 'US',
  	currency: 'usd',
		displayItems : [
			{
				amount : 9999,
				label: 'Cool stuff',
				pending: true,
			},
			{
				amount : -9999,
				label: 'Cool discount',
				pending: true,
			},
		],
  	total: {
    	label: 'Demo charge ya later',
    	amount: 0,
			pending: true
  	},
  	requestPayerName: true,
  	requestPayerEmail: true,
	});

	var elements = stripe.elements();
	var prButton = elements.create('paymentRequestButton', {
  	paymentRequest: paymentRequest,
	});

	// Check the availability of the Payment Request API first.
	paymentRequest.canMakePayment().then(function(result) {
  	if (result) {
    	prButton.mount('#preq')
  	} else {
    	document.getElementById('preq').style.display = 'none';
  	}
	});
	paymentRequest.on('paymentmethod', function(ev) {
  	// Confirm the PaymentIntent without handling potential next actions (yet).
  	stripe.confirmSetupIntent(
    	setupIntent.client_secret,
    	{payment_method: ev.paymentMethod.id},
    	{handleActions: false}
  	).then(function(confirmResult) {
    	if (confirmResult.error) {
      	// Report to the browser that the payment failed, prompting it to
      	// re-show the payment interface, or show an error message and close
      	// the payment interface.
				console.log("oh no " + error);
      	ev.complete('fail');
    	} else {
      	// Report to the browser that the confirmation was successful, prompting
      	// it to close the browser payment method collection interface.
      	ev.complete('success');
     		});
    	}
  	});
	});
	/* -- */
	

  var card = elements.create("card", { style: style });

  card.mount("#card-element");

  // Element focus ring
  card.on("focus", function() {
    var el = document.getElementById("card-element");
    el.classList.add("focused");
  });

  card.on("blur", function() {
    var el = document.getElementById("card-element");
    el.classList.remove("focused");
  });

  // Handle payment submission when user clicks the pay button.
  var button = document.getElementById("submit");
  button.addEventListener("click", function(event) {
    event.preventDefault();
    changeLoadingState(true);
    var email = document.getElementById("email").value;

    stripe
      .confirmCardSetup(setupIntent.client_secret, {
        payment_method: {
          card: card,
          billing_details: { email: email }
        }
      })
      .then(function(result) {
        if (result.error) {
          changeLoadingState(false);
          var displayError = document.getElementById("card-errors");
          displayError.textContent = result.error.message;
        } else {
          // The PaymentMethod was successfully set up
          orderComplete(stripe, setupIntent.client_secret);
        }
      });
  });
};

var getSetupIntent = function(publicKey) {
  return fetch("/create-setup-intent", {
    method: "post",
    headers: {
      "Content-Type": "application/json"
    }
  })
    .then(function(response) {
      return response.json();
    })
    .then(function(setupIntent) {
      stripeElements(publicKey, setupIntent);
    });
};

var getPublicKey = function() {
  return fetch("/public-key", {
    method: "get",
    headers: {
      "Content-Type": "application/json"
    }
  })
    .then(function(response) {
      return response.json();
    })
    .then(function(response) {
      getSetupIntent(response.publicKey);
    });
};

// Show a spinner on payment submission
var changeLoadingState = function(isLoading) {
  if (isLoading) {
    document.querySelector("button").disabled = true;
    document.querySelector("#spinner").classList.remove("hidden");
    document.querySelector("#button-text").classList.add("hidden");
  } else {
    document.querySelector("button").disabled = false;
    document.querySelector("#spinner").classList.add("hidden");
    document.querySelector("#button-text").classList.remove("hidden");
  }
};

/* Shows a success / error message when the payment is complete */
var orderComplete = function(stripe, clientSecret) {
  stripe.retrieveSetupIntent(clientSecret).then(function(result) {
    var setupIntent = result.setupIntent;
    var setupIntentJson = JSON.stringify(setupIntent, null, 2);

    document.querySelector(".sr-payment-form").classList.add("hidden");
    document.querySelector(".sr-result").classList.remove("hidden");
    document.querySelector("pre").textContent = setupIntentJson;
    setTimeout(function() {
      document.querySelector(".sr-result").classList.add("expand");
    }, 200);

    changeLoadingState(false);
  });
};

getPublicKey();
