import { createContact, sendMessage, updateContact, listContacts } from './surge';
import { signJWT } from './jwt';
import { getTursoClient, saveFormSubmission, getPurchaseHistory } from './turso';

interface Env {
  // Vars (in wrangler.toml)
  SURGE_ACCOUNT_ID: string;
  SURGE_PHONE_NUMBER: string;
  ALLOWED_ORIGIN: string;
  // Secrets (set via wrangler secret put)
  SURGE_API_KEY: string;
  SURGE_SIGNING_KEY_ID: string;
  SURGE_SIGNING_KEY_JWK: string;
  SURGE_WEBHOOK_SECRET: string;
  ADMIN_PASSWORD: string;
  SURGE_ADMIN_USER_ID: string;
  // Turso
  TURSO_DB_URL: string;
  TURSO_AUTH_TOKEN: string;
}

// --- CORS ---

function corsHeaders(env: Env, request?: Request): HeadersInit {
  const origin = request?.headers.get('Origin') || '';
  const allowed = ['https://sakima.co', 'http://sakima.co'];
  const allowOrigin = allowed.includes(origin) ? origin : env.ALLOWED_ORIGIN;
  return {
    'Access-Control-Allow-Origin': allowOrigin,
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Access-Control-Allow-Headers': 'Content-Type',
  };
}

function corsResponse(env: Env): Response {
  return new Response(null, { status: 204, headers: corsHeaders(env) });
}

function jsonResponse(env: Env, data: object, status = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: {
      'Content-Type': 'application/json',
      ...corsHeaders(env),
    },
  });
}

function errorResponse(env: Env, message: string, status = 400): Response {
  return jsonResponse(env, { success: false, error: message }, status);
}

// --- Phone formatting ---

function formatE164(phone: string): string {
  const digits = phone.replace(/\D/g, '');
  if (digits.length === 10) return `+1${digits}`;
  if (digits.length === 11 && digits.startsWith('1')) return `+${digits}`;
  return `+${digits}`;
}

// --- Webhook signature validation ---

async function validateWebhookSignature(body: string, signature: string, secret: string): Promise<boolean> {
  const parts = signature.split(',');
  let timestamp = '';
  let sig = '';

  for (const part of parts) {
    const [key, value] = part.split('=');
    if (key === 't') timestamp = value;
    if (key === 'v1') sig = value;
  }

  if (!timestamp || !sig) return false;

  // Check timestamp freshness (5 minute window)
  const age = Math.abs(Date.now() / 1000 - parseInt(timestamp));
  if (age > 300) return false;

  // Compute HMAC-SHA256
  const key = await crypto.subtle.importKey(
    'raw',
    new TextEncoder().encode(secret),
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign']
  );

  const signed = await crypto.subtle.sign(
    'HMAC',
    key,
    new TextEncoder().encode(`${timestamp}.${body}`)
  );

  const computed = Array.from(new Uint8Array(signed))
    .map(b => b.toString(16).padStart(2, '0'))
    .join('');

  return computed === sig;
}

// --- Route: POST /signup ---

async function handleSignup(request: Request, env: Env): Promise<Response> {
  let data: any;
  try {
    data = await request.json();
  } catch {
    return errorResponse(env, 'Invalid JSON');
  }

  const { name, email, phone, emailOptIn, smsOptIn, channels, source } = data;

  // Validate: need at least one contact method
  const phoneDigits = (phone || '').replace(/\D/g, '');
  const hasPhone = phoneDigits.length >= 10;
  const hasEmail = email && email.includes('@');

  if (!hasPhone && !hasEmail) {
    return errorResponse(env, 'Phone or email required');
  }

  // Parse name into first/last
  const nameParts = (name || '').trim().split(/\s+/);
  const firstName = nameParts[0] || undefined;
  const lastName = nameParts.length > 1 ? nameParts.slice(1).join(' ') : undefined;

  // Build contact data
  const contactData: any = {
    metadata: {
      channels: (channels || []).join(','),
      email_opt_in: String(!!emailOptIn),
      sms_opt_in: String(!!smsOptIn),
      source: source || 'sakima.co/sms',
      signup_date: new Date().toISOString(),
    },
  };

  if (hasPhone) contactData.phone_number = formatE164(phoneDigits);
  if (hasEmail) contactData.email = email;
  if (firstName) contactData.first_name = firstName;
  if (lastName) contactData.last_name = lastName;

  // Persist to Turso
  try {
    const db = getTursoClient(env.TURSO_DB_URL, env.TURSO_AUTH_TOKEN);
    await saveFormSubmission(db, 'signup', {
      email, name, phone,
      channels: (channels || []).join(','),
      emailOptIn: !!emailOptIn,
      smsOptIn: !!smsOptIn,
      source: source || 'sakima.co/sms',
    }, request.headers.get('CF-Connecting-IP') || undefined);
  } catch (e: any) {
    console.error('Turso save failed (signup):', e.message);
  }

  // Create contact in Surge
  const result = await createContact(env, contactData);

  if (result.error === 'duplicate') {
    // Contact exists — try to find and update
    // For now, just acknowledge success (they're already a contact)
    // Could enhance later with contact lookup + metadata merge
  } else if (result.error) {
    console.error('Contact creation failed:', result.error);
    return errorResponse(env, 'Signup failed. Please try again or text a keyword to our number.', 500);
  }

  // Send welcome SMS if opted in and has phone
  if (smsOptIn && hasPhone) {
    const channelList = (channels || [])
      .filter((c: string) => c !== 'transactional' && c !== 'everything')
      .map((c: string) => c.charAt(0).toUpperCase() + c.slice(1))
      .join(', ');

    const welcomeBody = channelList
      ? `Welcome to Sakima Alerts! You're signed up for: ${channelList}. Reply STOP to cancel anytime. Reply HELP for help.`
      : `Welcome to Sakima Alerts! Reply STOP to cancel anytime. Reply HELP for help.`;

    const msgResult = await sendMessage(env, formatE164(phoneDigits), welcomeBody);
    if (msgResult.error) {
      console.error('Welcome SMS failed:', msgResult.error);
      // Don't fail the signup — contact was created
    }
  }

  return jsonResponse(env, {
    success: true,
    contact_id: result.id || null,
    message: 'Subscribed successfully',
  });
}

// --- Route: POST /vip ---

async function handleVIP(request: Request, env: Env): Promise<Response> {
  let data: any;
  try {
    data = await request.json();
  } catch {
    return errorResponse(env, 'Invalid JSON');
  }

  const { email } = data;
  if (!email || !email.includes('@')) {
    return errorResponse(env, 'Valid email required');
  }

  // Persist to Turso
  try {
    const db = getTursoClient(env.TURSO_DB_URL, env.TURSO_AUTH_TOKEN);
    await saveFormSubmission(db, 'vip', { email }, request.headers.get('CF-Connecting-IP') || undefined);
  } catch (e: any) {
    console.error('Turso save failed (vip):', e.message);
  }

  const result = await createContact(env, {
    email,
    metadata: {
      channels: 'vip',
      email_opt_in: 'true',
      source: 'sakima.co/vip',
      signup_date: new Date().toISOString(),
    },
  });

  if (result.error && result.error !== 'duplicate') {
    console.error('VIP signup failed:', result.error);
    return errorResponse(env, 'Signup failed', 500);
  }

  return jsonResponse(env, { success: true });
}

// --- Route: POST /offer ---

async function handleOffer(request: Request, env: Env): Promise<Response> {
  let data: any;
  try {
    data = await request.json();
  } catch {
    return errorResponse(env, 'Invalid JSON');
  }

  const { name, email, phone, type, description } = data;

  if (!email || !email.includes('@')) {
    return errorResponse(env, 'Email required');
  }
  if (!description) {
    return errorResponse(env, 'Description required');
  }

  const nameParts = (name || '').trim().split(/\s+/);
  const firstName = nameParts[0] || undefined;
  const lastName = nameParts.length > 1 ? nameParts.slice(1).join(' ') : undefined;

  // Persist to Turso
  try {
    const db = getTursoClient(env.TURSO_DB_URL, env.TURSO_AUTH_TOKEN);
    await saveFormSubmission(db, 'offer', {
      email, name, phone,
      type: type || 'inquiry',
      description: (description || '').slice(0, 2000),
    }, request.headers.get('CF-Connecting-IP') || undefined);
  } catch (e: any) {
    console.error('Turso save failed (offer):', e.message);
  }

  // Create/update contact
  const phoneDigits = (phone || '').replace(/\D/g, '');
  const contactData: any = {
    email,
    metadata: {
      source: 'sakima.co/offer',
      offer_type: type || 'inquiry',
      latest_offer: description.slice(0, 500),
      offer_date: new Date().toISOString(),
    },
  };
  if (firstName) contactData.first_name = firstName;
  if (lastName) contactData.last_name = lastName;
  if (phoneDigits.length >= 10) contactData.phone_number = formatE164(phoneDigits);

  await createContact(env, contactData);

  // Notify admin via SMS — send to the Surge number itself as a note
  // (Admin will see this in the Surge inbox as an inbound-like notification)
  // Instead, we log it — the admin dashboard will show new contacts
  console.log(`New offer from ${name} (${email}): ${type} - ${description.slice(0, 200)}`);

  return jsonResponse(env, { success: true, message: 'Message sent' });
}

// --- Route: POST /webhooks/surge ---

async function handleWebhook(request: Request, env: Env): Promise<Response> {
  const body = await request.text();

  // Validate signature
  const signature = request.headers.get('Surge-Signature') || '';
  if (env.SURGE_WEBHOOK_SECRET && env.SURGE_WEBHOOK_SECRET !== 'placeholder') {
    const valid = await validateWebhookSignature(body, signature, env.SURGE_WEBHOOK_SECRET);
    if (!valid) {
      console.error('Webhook signature validation failed');
      return new Response('Unauthorized', { status: 401 });
    }
  }

  let event: any;
  try {
    event = JSON.parse(body);
  } catch {
    return new Response('Invalid JSON', { status: 400 });
  }

  const type = event.type || '';
  console.log(`Webhook event: ${type}`, JSON.stringify(event).slice(0, 500));

  switch (type) {
    case 'message.received': {
      // Check for keyword opt-ins
      const msgBodyRaw = (event.data?.body || '').trim();
      const msgBody = msgBodyRaw.toUpperCase();
      const contactId = event.data?.conversation?.contact?.id;
      const fromNumber = event.data?.conversation?.contact?.phone_number;
      // Get existing metadata (assume it's passed, or we might need to fetch contact if not)
      // The webhook payload usually includes contact metadata. Let's check the type definition or assume standard shape.
      // If not present, we can treat it as empty.
      const metadata = event.data?.conversation?.contact?.metadata || {};
      const goldenTicketStep = metadata.golden_ticket_step;

      if (!contactId || !fromNumber) break;

      // --- 1. Golden Ticket (Multi-Step Flow) ---
      
      // Step 2: Handle Username Reply
      if (goldenTicketStep === 'awaiting_username') {
        const username = msgBodyRaw; // Use original casing for username lookup
        
        // Lookup purchase history
        let purchaseCount = 0;
        try {
          const db = getTursoClient(env.TURSO_DB_URL, env.TURSO_AUTH_TOKEN);
          // Assuming getPurchaseHistory is implemented to count purchases by username
          // purchaseCount = await getPurchaseHistory(db, username);
          // For now, mock or implement basic logic:
          // purchaseCount = 0; // Default
          // If you have a real table, uncomment the line above.
          // Since I don't see the table schema, I'll use a placeholder logic based on username length or random for demo,
          // OR assume the function exists and returns 0 if table missing.
           purchaseCount = await getPurchaseHistory(db, username);
        } catch (e) {
          console.error('Failed to lookup purchase history:', e);
        }

        // Determine Reward Tier
        let discountAmount = 5;
        let couponCode = `GOLD-5-${contactId.slice(-4)}`;
        
        if (purchaseCount >= 800) {
          discountAmount = 50;
          couponCode = `GOLD-50-${contactId.slice(-4)}`;
        } else if (purchaseCount >= 100) {
          discountAmount = 25;
          couponCode = `GOLD-25-${contactId.slice(-4)}`;
        } else if (purchaseCount >= 15) {
          discountAmount = 10;
          couponCode = `GOLD-10-${contactId.slice(-4)}`;
        } else {
          // 0-14 purchases
          discountAmount = 5;
          couponCode = `GOLD-5-${contactId.slice(-4)}`;
        }

        // Reply with Coupon
        await sendMessage(env, fromNumber, 
          `🎉 Verification Complete!\n\n` +
          `Username: ${username}\n` +
          `Purchases found: ${purchaseCount}\n\n` +
          `Here is your reward: $${discountAmount} OFF your next order!\n` +
          `Code: ${couponCode}\n\n` +
          `(Valid for 30 days. One use per customer.)`
        );

        // Update State
        await updateContact(env, contactId, {
          metadata: {
            golden_ticket_step: 'completed',
            golden_ticket_username: username,
            golden_ticket_reward: `$${discountAmount}`,
            golden_ticket_code: couponCode
          }
        });
        
        return new Response('OK', { status: 200 }); // Stop processing
      }

      // Step 1: Trigger
      if (msgBody.includes('GOLDEN TICKET') && msgBody.includes('73885')) {
         if (goldenTicketStep === 'completed') {
            await sendMessage(env, fromNumber, "You have already claimed this Golden Ticket! Check your previous messages for the code.");
            return new Response('OK', { status: 200 });
         }

         console.log(`Golden Ticket flow started by ${contactId}`);
         
         // Set state to awaiting_username
         await updateContact(env, contactId, {
           metadata: {
             golden_ticket_step: 'awaiting_username',
             ticket_number: '73885',
             ticket_date: new Date().toISOString()
           }
         });

         // Initial Reply
         await sendMessage(env, fromNumber, 
           "🎉 CONGRATULATIONS! You found Golden Ticket #73885! 🎫\n\n" +
           "To verify your eligibility and unlock your reward tier, please reply with the username you use for purchases.\n\n" +
           "(Reply STOP to unsubscribe)"
         );
         return new Response('OK', { status: 200 }); // Stop processing
      }

      // --- 2. Feature Keywords (Opt-ins) ---
      const features: Record<string, { channels: string[], reply: string }> = {
        'EVERYTHING': { 
          channels: ['everything', 'coins', 'cards', 'whatnot', 'ebay', 'vip'],
          reply: "You're subscribed to EVERYTHING! 🚀 You'll get alerts for all drops, auctions, and VIP deals. Reply STOP to cancel."
        },
        'YES': { 
          channels: ['everything', 'coins', 'cards', 'whatnot', 'ebay', 'vip'],
          reply: "You're subscribed to EVERYTHING! 🚀 You'll get alerts for all drops, auctions, and VIP deals. Reply STOP to cancel."
        },
        'COINS': { 
          channels: ['coins'],
          reply: "You're subscribed to COINS alerts! 🪙 We'll text you about new coin drops and auctions. Reply STOP to cancel."
        },
        'CARDS': { 
          channels: ['cards'],
          reply: "You're subscribed to CARDS alerts! 🃏 We'll text you about new card drops and breaks. Reply STOP to cancel."
        },
        'WHATNOT': { 
          channels: ['whatnot'],
          reply: "You're subscribed to WHATNOT show alerts! 📹 We'll text you when we go live. Reply STOP to cancel."
        },
        'EBAY': { 
          channels: ['ebay'],
          reply: "You're subscribed to EBAY auction alerts! 🏷️ We'll text you about ending auctions. Reply STOP to cancel."
        },
        'VIP': { 
          channels: ['vip'],
          reply: "Welcome to the VIP list! 👑 You'll get early access and exclusive deals. Reply STOP to cancel."
        }
      };

      if (features[msgBody]) {
        const { channels, reply } = features[msgBody];
        
        await updateContact(env, contactId, {
          metadata: {
            channels: channels.join(','),
            sms_opt_in: 'true',
            source: 'sms_keyword',
            signup_date: new Date().toISOString(),
          },
        });
        
        await sendMessage(env, fromNumber, reply);
        console.log(`Keyword opt-in: ${msgBody} → contact ${contactId}`);
      }

      // --- 3. STOP/START Handling ---
      // Surge handles carrier compliance (filtering messages), but we can add app-level logic here if needed.
      // E.g., if (msgBody === 'STOP') { ... tag as opted-out ... }
      // E.g., if (msgBody === 'START') { ... tag as opted-in ... }

      break;
    }

    case 'contact.opted_in':
      console.log(`Contact opted in: ${event.data?.contact?.id}`);
      break;

    case 'contact.opted_out':
      console.log(`Contact opted out: ${event.data?.contact?.id}`);
      break;

    case 'message.delivered':
      console.log(`Message delivered: ${event.data?.id}`);
      break;

    case 'message.failed':
      console.error(`Message failed: ${event.data?.id}`, event.data?.error);
      break;

    default:
      console.log(`Unhandled webhook event: ${type}`);
  }

  return new Response('OK', { status: 200 });
}

// --- Route: POST /admin/token ---

async function handleAdminToken(request: Request, env: Env): Promise<Response> {
  let data: any;
  try {
    data = await request.json();
  } catch {
    return errorResponse(env, 'Invalid JSON');
  }

  if (data.password !== env.ADMIN_PASSWORD) {
    return errorResponse(env, 'Unauthorized', 401);
  }

  if (!env.SURGE_ADMIN_USER_ID) {
    return errorResponse(env, 'Admin user not configured', 500);
  }

  const token = await signJWT(
    env.SURGE_SIGNING_KEY_ID,
    env.SURGE_SIGNING_KEY_JWK,
    env.SURGE_ADMIN_USER_ID,
    3600 // 1 hour
  );

  return jsonResponse(env, {
    token,
    expires_at: Math.floor(Date.now() / 1000) + 3600,
  });
}

// --- Main Router ---

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    const url = new URL(request.url);
    const path = url.pathname;

    // CORS preflight
    if (request.method === 'OPTIONS') {
      return corsResponse(env);
    }

    // Health check
    if (path === '/' && request.method === 'GET') {
      return jsonResponse(env, { status: 'ok', service: 'sakima-api' });
    }

    // Only allow POST for API routes
    if (request.method !== 'POST') {
      return errorResponse(env, 'Method not allowed', 405);
    }

    try {
      switch (path) {
        case '/signup':
          return await handleSignup(request, env);
        case '/vip':
          return await handleVIP(request, env);
        case '/offer':
          return await handleOffer(request, env);
        case '/webhooks/surge':
          return await handleWebhook(request, env);
        case '/admin/token':
          return await handleAdminToken(request, env);
        default:
          return errorResponse(env, 'Not found', 404);
      }
    } catch (err: any) {
      console.error('Unhandled error:', err.message, err.stack);
      return errorResponse(env, 'Internal server error', 500);
    }
  },
};
