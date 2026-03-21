import { createClient, type Client } from '@libsql/client';

let _client: Client | null = null;

export function getTursoClient(url: string, authToken: string): Client {
  if (!_client) {
    _client = createClient({ url, authToken });
  }
  return _client;
}

export async function saveFormSubmission(
  client: Client,
  formType: string,
  data: {
    email?: string;
    name?: string;
    phone?: string;
    [key: string]: any;
  },
  ip?: string
): Promise<void> {
  const { email, name, phone, ...rest } = data;
  await client.execute({
    sql: `INSERT INTO form_submissions (form_type, email, name, phone, data, ip) VALUES (?, ?, ?, ?, ?, ?)`,
    args: [
      formType,
      email || null,
      name || null,
      phone || null,
      Object.keys(rest).length > 0 ? JSON.stringify(rest) : null,
      ip || null,
    ],
  });
}

export async function getPurchaseHistory(client: Client, username: string): Promise<number> {
  try {
    const result = await client.execute({
      sql: `SELECT COUNT(*) as count FROM purchases WHERE username = ?`,
      args: [username],
    });
    return (result.rows[0] as any).count || 0;
  } catch (e) {
    console.error('Failed to get purchase history:', e);
    return 0; // Default to 0 on error
  }
}
