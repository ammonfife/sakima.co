// Ed25519 JWT signing for Surge embeddable components

function base64urlEncode(data: Uint8Array): string {
  const str = btoa(String.fromCharCode(...data));
  return str.replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}

function textToBase64url(text: string): string {
  return base64urlEncode(new TextEncoder().encode(text));
}

export async function signJWT(
  signingKeyId: string,
  signingKeyJwk: string,
  userId: string,
  durationSeconds: number = 3600
): Promise<string> {
  // Parse the JWK
  const jwk = JSON.parse(signingKeyJwk);

  // Import the Ed25519 private key
  const privateKey = await crypto.subtle.importKey(
    'jwk',
    jwk,
    { name: 'Ed25519' },
    false,
    ['sign']
  );

  // JWT Header
  const header = {
    alg: 'EdDSA',
    kid: signingKeyId,
    typ: 'JWT',
  };

  // JWT Payload
  const now = Math.floor(Date.now() / 1000);
  const payload = {
    sub: userId,
    iat: now,
    exp: now + durationSeconds,
  };

  // Encode header and payload
  const headerB64 = textToBase64url(JSON.stringify(header));
  const payloadB64 = textToBase64url(JSON.stringify(payload));
  const signingInput = `${headerB64}.${payloadB64}`;

  // Sign
  const signature = await crypto.subtle.sign(
    'Ed25519',
    privateKey,
    new TextEncoder().encode(signingInput)
  );

  const signatureB64 = base64urlEncode(new Uint8Array(signature));

  return `${signingInput}.${signatureB64}`;
}
