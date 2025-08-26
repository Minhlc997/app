// Stripe Checkout JavaScript with Apple Pay support for Apple TV compatibility

document.addEventListener('DOMContentLoaded', async function() {
  // Initialize Stripe (you'll need to replace with your actual publishable key)
  const stripe = Stripe('pk_test_TYooMQauvdEDq54NiTphI7jx');
  
  // Get DOM elements
  const quantityInput = document.getElementById('quantity-input');
  const subtractBtn = document.getElementById('subtract');
  const addBtn = document.getElementById('add');
  const submitBtn = document.getElementById('submit');
  const errorMessage = document.getElementById('error-message');
  const form = document.querySelector('form');
  
  // Quantity management
  function updateQuantity(delta) {
    const currentQuantity = parseInt(quantityInput.value);
    const newQuantity = Math.max(1, Math.min(10, currentQuantity + delta));
    quantityInput.value = newQuantity;
    
    // Update button states
    subtractBtn.disabled = newQuantity <= 1;
    addBtn.disabled = newQuantity >= 10;
  }
  
  // Event listeners for quantity buttons
  subtractBtn.addEventListener('click', () => updateQuantity(-1));
  addBtn.addEventListener('click', () => updateQuantity(1));
  
  // Handle quantity input changes
  quantityInput.addEventListener('input', function() {
    const quantity = parseInt(this.value) || 1;
    this.value = Math.max(1, Math.min(10, quantity));
    subtractBtn.disabled = this.value <= 1;
    addBtn.disabled = this.value >= 10;
  });
  
  // Apple Pay support check and button creation
  async function initializeApplePay() {
    if (!window.ApplePaySession || !ApplePaySession.canMakePayments()) {
      console.log('Apple Pay not available');
      return;
    }
    
    // Check if Apple Pay is set up
    const canMakePayments = await ApplePaySession.canMakePaymentsWithActiveCard('merchant.your.merchant.id');
    
    if (canMakePayments) {
      createApplePayButton();
    }
  }
  
  function createApplePayButton() {
    const applePayButton = document.createElement('button');
    applePayButton.className = 'apple-pay-button';
    applePayButton.addEventListener('click', handleApplePayClick);
    
    // Create payment methods section
    const paymentMethods = document.createElement('div');
    paymentMethods.className = 'payment-methods';
    
    // Add Apple Pay button
    paymentMethods.appendChild(applePayButton);
    
    // Add divider
    const divider = document.createElement('div');
    divider.className = 'payment-divider';
    divider.innerHTML = '<span>or</span>';
    paymentMethods.appendChild(divider);
    
    // Insert before the regular form
    form.parentNode.insertBefore(paymentMethods, form);
  }
  
  async function handleApplePayClick() {
    const quantity = parseInt(quantityInput.value);
    const amount = 2000 * quantity; // $20.00 per item in cents
    
    const paymentRequest = {
      countryCode: 'US',
      currencyCode: 'USD',
      supportedNetworks: ['visa', 'masterCard', 'amex', 'discover'],
      merchantCapabilities: ['supports3DS'],
      total: {
        label: 'Pasha Original Photo',
        amount: (amount / 100).toFixed(2)
      },
      lineItems: [{
        label: `Photo (x${quantity})`,
        amount: (amount / 100).toFixed(2)
      }]
    };
    
    const session = new ApplePaySession(3, paymentRequest);
    
    session.onvalidatemerchant = async function(event) {
      try {
        // In a real implementation, this would validate with your server
        const merchantSession = await fetch('/validate-merchant', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            validationURL: event.validationURL,
            displayName: 'Pasha Photo Store'
          })
        }).then(res => res.json());
        
        session.completeMerchantValidation(merchantSession);
      } catch (error) {
        console.error('Merchant validation failed:', error);
        session.abort();
      }
    };
    
    session.onpaymentauthorized = async function(event) {
      try {
        // Process payment with Stripe
        const { paymentMethod, error } = await stripe.createPaymentMethod({
          type: 'card',
          card: {
            token: event.payment.token
          }
        });
        
        if (error) {
          session.completePayment(ApplePaySession.STATUS_FAILURE);
          showError(error.message);
          return;
        }
        
        // Send to server for processing
        const response = await fetch('/process-apple-pay', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            payment_method_id: paymentMethod.id,
            quantity: quantity,
            amount: amount
          })
        });
        
        if (response.ok) {
          session.completePayment(ApplePaySession.STATUS_SUCCESS);
          // Handle successful payment
          window.location.href = '/success';
        } else {
          session.completePayment(ApplePaySession.STATUS_FAILURE);
          showError('Payment processing failed');
        }
      } catch (error) {
        console.error('Payment processing error:', error);
        session.completePayment(ApplePaySession.STATUS_FAILURE);
        showError('Payment processing failed');
      }
    };
    
    session.begin();
  }
  
  // Regular form submission
  form.addEventListener('submit', async function(e) {
    e.preventDefault();
    
    setLoading(true);
    clearError();
    
    try {
      const quantity = parseInt(quantityInput.value);
      
      // Create checkout session
      const response = await fetch('/create-checkout-session', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/x-www-form-urlencoded',
        },
        body: `quantity=${quantity}`
      });
      
      if (!response.ok) {
        throw new Error('Network response was not ok');
      }
      
      const { sessionId } = await response.json();
      
      // Redirect to Stripe Checkout
      const { error } = await stripe.redirectToCheckout({
        sessionId: sessionId
      });
      
      if (error) {
        showError(error.message);
      }
    } catch (error) {
      console.error('Error:', error);
      showError('An error occurred. Please try again.');
    } finally {
      setLoading(false);
    }
  });
  
  // Utility functions
  function setLoading(loading) {
    submitBtn.disabled = loading;
    document.body.classList.toggle('loading', loading);
  }
  
  function showError(message) {
    errorMessage.textContent = message;
    errorMessage.style.display = 'block';
  }
  
  function clearError() {
    errorMessage.textContent = '';
    errorMessage.style.display = 'none';
  }
  
  // Apple TV specific enhancements
  function enhanceForAppleTV() {
    // Add focus management for Apple TV remote
    const focusableElements = document.querySelectorAll(
      'button, input, [tabindex]:not([tabindex="-1"])'
    );
    
    // Enhance keyboard navigation
    document.addEventListener('keydown', function(e) {
      if (e.key === 'ArrowUp' || e.key === 'ArrowDown' || 
          e.key === 'ArrowLeft' || e.key === 'ArrowRight') {
        // Handle Apple TV remote navigation
        const currentIndex = Array.from(focusableElements).indexOf(document.activeElement);
        let nextIndex;
        
        switch(e.key) {
          case 'ArrowUp':
          case 'ArrowLeft':
            nextIndex = currentIndex > 0 ? currentIndex - 1 : focusableElements.length - 1;
            break;
          case 'ArrowDown':
          case 'ArrowRight':
            nextIndex = currentIndex < focusableElements.length - 1 ? currentIndex + 1 : 0;
            break;
        }
        
        if (nextIndex !== undefined) {
          e.preventDefault();
          focusableElements[nextIndex].focus();
        }
      }
    });
  }
  
  // Initialize Apple TV enhancements if on Apple TV
  if (navigator.userAgent.includes('AppleTV') || 
      window.screen.width >= 1920 && window.screen.height >= 1080) {
    enhanceForAppleTV();
  }
  
  // Initialize Apple Pay
  await initializeApplePay();
  
  // Initialize quantity buttons state
  updateQuantity(0);
});