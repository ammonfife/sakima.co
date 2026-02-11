// Surge API client wrapper

interface Env {
  SURGE_API_KEY: string;
  SURGE_ACCOUNT_ID: string;
  SURGE_PHONE_NUMBER: string;
}

const BASE = 'https://api.surge.app';

async function surgeRequest(env: Env, method: string, path: string, body?: object): Promise<Response> {
  const url = path.startsWith('/accounts/')
    ? `${BASE}${path}`
    : path.startsWith('/')
    ? `${BASE}${path}`
    : `${BASE}/${path}`;

  const res = await fetch(url, {
    method,
    headers: {
      'Authorization': `Bearer ${env.SURGE_API_KEY}`,
      'Content-Type': 'application/json',
    },
    body: body ? JSON.stringify(body) : undefined,
  });

  return res;
}

export interface ContactData {
  phone_number?: string;
  email?: string;
  first_name?: string;
  last_name?: string;
  metadata?: Record<string, string>;
}

export async function createContact(env: Env, data: ContactData): Promise<{ id: string; error?: string }> {
  const res = await surgeRequest(env, 'POST', `/accounts/${env.SURGE_ACCOUNT_ID}/contacts`, data);

  if (res.ok) {
    const contact = await res.json() as { id: string };
    return { id: contact.id };
  }

  const errText = await res.text();

  // If contact already exists, try to find and update
  if (res.status === 409 || res.status === 422) {
    return { id: '', error: 'duplicate' };
  }

  return { id: '', error: `Surge API error ${res.status}: ${errText}` };
}

export async function listContacts(env: Env): Promise<any[]> {
  const res = await surgeRequest(env, 'GET', `/accounts/${env.SURGE_ACCOUNT_ID}/contacts`);
  if (res.ok) {
    const data = await res.json() as { data: any[] };
    return data.data;
  }
  return [];
}

export async function updateContact(env: Env, contactId: string, data: Partial<ContactData>): Promise<boolean> {
  const res = await surgeRequest(env, 'PATCH', `/contacts/${contactId}`, data);
  return res.ok;
}

export async function sendMessage(env: Env, to: string, body: string): Promise<{ id: string; error?: string }> {
  const res = await surgeRequest(env, 'POST', `/accounts/${env.SURGE_ACCOUNT_ID}/messages`, {
    to,
    from: env.SURGE_PHONE_NUMBER,
    body,
  });

  if (res.ok) {
    const msg = await res.json() as { id: string };
    return { id: msg.id };
  }

  const errText = await res.text();
  return { id: '', error: `Message send failed ${res.status}: ${errText}` };
}

export async function createUser(env: Env, firstName: string): Promise<{ id: string; error?: string }> {
  const res = await surgeRequest(env, 'POST', `/accounts/${env.SURGE_ACCOUNT_ID}/users`, {
    first_name: firstName,
  });

  if (res.ok) {
    const user = await res.json() as { id: string };
    return { id: user.id };
  }

  const errText = await res.text();
  return { id: '', error: `User creation failed ${res.status}: ${errText}` };
}

export async function listPhoneNumbers(env: Env): Promise<any[]> {
  const res = await surgeRequest(env, 'GET', `/accounts/${env.SURGE_ACCOUNT_ID}/phone_numbers`);
  if (res.ok) {
    const data = await res.json() as { data: any[] };
    return data.data;
  }
  return [];
}
