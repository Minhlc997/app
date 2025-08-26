require 'sinatra'
require 'json'
require 'stripe'

# This is your test secret API key.
Stripe.api_key = 'sk_test_51QEYtE03hx8I8NwIGayXqBUdXlORbkkUYAQTvCs1EOCDoPwsDgJR7i351e0qrbC6T0s6hfDgmdHazPzrbUFVhCgJ00jOuMGK3i'

# Replace this endpoint secret with your endpoint's unique secret
# If you are testing with the CLI, find the secret by running 'stripe listen'
# If you are using an endpoint defined with the API or dashboard, look in your webhook settings
# at https://dashboard.stripe.com/webhooks
endpoint_secret = 'whsec_...';

set :port, 4242
set :public_folder, File.dirname(__FILE__)

# Your domain (update this for production)
YOUR_DOMAIN = 'http://localhost:4242'

# Serve the main page
get '/' do
  send_file File.join(settings.public_folder, 'index.html')
end

# Create checkout session
post '/create-checkout-session' do
  content_type 'application/json'
  
  begin
    # Get quantity from form data
    quantity = (params[:quantity] || 1).to_i
    quantity = [[quantity, 1].max, 10].min # Ensure quantity is between 1 and 10
    
    session = Stripe::Checkout::Session.create({
      line_items: [{
        price_data: {
          currency: 'usd',
          product_data: {
            name: 'Pasha Original Photo',
            images: ['https://picsum.photos/280/320?random=4']
          },
          unit_amount: 2000, # $20.00 in cents
        },
        quantity: quantity,
      }],
      mode: 'payment',
      success_url: "#{YOUR_DOMAIN}/success.html",
      cancel_url: "#{YOUR_DOMAIN}/cancel.html",
      automatic_tax: {
        enabled: true,
      },
      # Enable Apple Pay and other payment methods
      payment_method_types: ['card', 'apple_pay']
    })
    
    { sessionId: session.id }.to_json
  rescue => e
    puts "Error creating checkout session: #{e.message}"
    status 500
    { error: 'Unable to create checkout session' }.to_json
  end
end

# Apple Pay merchant validation (for future implementation)
post '/validate-merchant' do
  content_type 'application/json'
  
  # In a real implementation, you would validate the merchant with Apple
  # This is a placeholder that would need to be implemented with Apple's merchant validation
  status 501
  { error: 'Merchant validation not implemented' }.to_json
end

# Process Apple Pay payment (for future implementation)
post '/process-apple-pay' do
  content_type 'application/json'
  
  begin
    data = JSON.parse(request.body.read)
    payment_method_id = data['payment_method_id']
    quantity = data['quantity'].to_i
    amount = data['amount'].to_i
    
    # Create payment intent with Apple Pay
    intent = Stripe::PaymentIntent.create({
      amount: amount,
      currency: 'usd',
      payment_method: payment_method_id,
      confirmation_method: 'manual',
      confirm: true,
      metadata: {
        quantity: quantity,
        product: 'Pasha Original Photo'
      }
    })
    
    if intent.status == 'succeeded'
      { success: true }.to_json
    else
      status 400
      { error: 'Payment failed' }.to_json
    end
  rescue => e
    puts "Error processing Apple Pay: #{e.message}"
    status 500
    { error: 'Payment processing failed' }.to_json
  end
end

post '/webhook' do
  payload = request.body.read
  event = nil

  begin
    event = Stripe::Event.construct_from(
      JSON.parse(payload, symbolize_names: true)
    )
  rescue JSON::ParserError => e
    # Invalid payload
    puts "⚠️  Webhook error while parsing basic request. #{e.message}"
    status 400
    return
  end
  # Check if webhook signing is configured.
  if endpoint_secret
    # Retrieve the event by verifying the signature using the raw body and secret.
    signature = request.env['HTTP_STRIPE_SIGNATURE'];
    begin
      event = Stripe::Webhook.construct_event(
        payload, signature, endpoint_secret
      )
    rescue Stripe::SignatureVerificationError => e
      puts "⚠️  Webhook signature verification failed. #{e.message}"
      status 400
    end
  end

  # Handle the event
  case event.type
  when 'payment_intent.succeeded'
    payment_intent = event.data.object # contains a Stripe::PaymentIntent
    puts "Payment for #{payment_intent['amount']} succeeded."
    # Then define and call a method to handle the successful payment intent.
    # handle_payment_intent_succeeded(payment_intent)
  when 'payment_method.attached'
    payment_method = event.data.object # contains a Stripe::PaymentMethod
    # Then define and call a method to handle the successful attachment of a PaymentMethod.
    # handle_payment_method_attached(payment_method)
  else
    puts "Unhandled event type: #{event.type}"
  end
  status 200
end

# Success page
get '/success.html' do
  erb :success
end

# Cancel page  
get '/cancel.html' do
  erb :cancel
end