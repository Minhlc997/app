# Build a webhook endpoint

Build a simple webhook endpoint to listen to events from Stripe. Included are some basic build and run scripts you can use to start up the application.

## Running the sample

1. Build the server

~~~
bundle install
~~~

2. Run the server

~~~
ruby server.rb -o 0.0.0.0
~~~


## Testing the webhook

The easiest way to test your webhook locally is with the Stripe CLI. Download [the CLI](https://github.com/stripe/stripe-cli) and log in with your Stripe account. Alternatively, use a service like ngrok to make your local endpoint publicly accessible.

Set up event forwarding with the CLI to send all Stripe events in test mode to your local webhook endpoint.

~~~
stripe listen --forward-to localhost:4242/webhook
~~~

Use the CLI to simulate specific events that test your webhook application logic by sending a POST request to your webhook endpoint with a mocked Stripe event object.

~~~
stripe trigger payment_intent.succeeded
~~~