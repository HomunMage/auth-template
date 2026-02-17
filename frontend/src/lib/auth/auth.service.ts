// lib/auth/auth.service.ts

import { providers } from './providers';
import { generateRandomString, generateCodeChallenge } from './pkce';
import type { AuthProvider, LoginInfo } from '$lib/types/auth';
import { isWeb } from '$lib/platform';

const BACKEND_URL = import.meta.env.VITE_BACKEND_URL;

interface TokenResponse {
	access_token: string;
	refresh_token?: string;
	id_token?: string;
	expires_in?: number;
	userinfo: {
		sub: string;
		email: string;
		name?: string;
		picture?: string;
	};
}

interface MeResponse {
	sub?: string;
	email: string;
	name?: string;
	picture?: string;
	provider: 'google' | 'authentik';
	role?: string;
}

/**
 * Exchange auth code for tokens via backend.
 */
async function exchangeCodeViaBackend(
	provider: AuthProvider,
	code: string,
	redirectUri: string,
	codeVerifier: string
): Promise<TokenResponse> {
	const response = await fetch(`${BACKEND_URL}/api/login/${provider}/token`, {
		method: 'POST',
		headers: { 'Content-Type': 'application/json' },
		body: JSON.stringify({
			code,
			redirect_uri: redirectUri,
			code_verifier: codeVerifier
		})
	});

	if (!response.ok) {
		const error = await response.json().catch(() => ({ detail: 'Token exchange failed' }));
		throw new Error(error.detail || 'Token exchange failed');
	}

	return response.json();
}

/**
 * Get user info and role from backend /me endpoint.
 */
async function fetchMe(accessToken: string): Promise<MeResponse | null> {
	const response = await fetch(`${BACKEND_URL}/api/login/me`, {
		headers: { Authorization: `Bearer ${accessToken}` }
	});

	if (!response.ok) {
		return null;
	}

	return response.json();
}

export async function startLogin(providerName: AuthProvider) {
	const provider = providers[providerName];

	const codeVerifier = generateRandomString(128);
	const codeChallenge = await generateCodeChallenge(codeVerifier);
	const nonce = generateRandomString(32);

	if (isWeb()) {
		// Web: store PKCE in sessionStorage, state is just the nonce
		sessionStorage.setItem(`pkce_${providerName}`, codeVerifier);
		sessionStorage.setItem(`state_${providerName}`, nonce);
	}

	// Mobile: encode verifier in state so the trampoline page can use it.
	// The trampoline (hosted on our server) does the token exchange, so
	// the app doesn't need to store PKCE state across the browser round-trip.
	const state = isWeb() ? nonce : `${nonce}.${codeVerifier}`;

	const params = new URLSearchParams({
		response_type: 'code',
		client_id: provider.clientId,
		redirect_uri: provider.redirectUri,
		scope: provider.scope,
		state,
		code_challenge: codeChallenge,
		code_challenge_method: 'S256'
	});

	// Google-specific: request offline access for refresh tokens
	if (providerName === 'google') {
		params.set('access_type', 'offline');
		params.set('prompt', 'consent');
	}

	window.location.href = `${provider.authorizeUrl}?${params.toString()}`;
}

export async function handleOAuthCallback(
	providerName: AuthProvider,
	code: string,
	state: string
): Promise<LoginInfo> {
	const provider = providers[providerName];

	const savedState = sessionStorage.getItem(`state_${providerName}`);
	const verifier = sessionStorage.getItem(`pkce_${providerName}`);

	if (!verifier || state !== savedState) {
		throw new Error('Invalid OAuth state');
	}

	// Exchange code via backend (backend has secrets)
	const tokens = await exchangeCodeViaBackend(providerName, code, provider.redirectUri, verifier);

	// Get user info and role from backend
	const me = await fetchMe(tokens.access_token);

	// Clean up PKCE storage
	sessionStorage.removeItem(`pkce_${providerName}`);
	sessionStorage.removeItem(`state_${providerName}`);

	return {
		provider: providerName,
		accessToken: tokens.access_token,
		refreshToken: tokens.refresh_token,
		idToken: tokens.id_token,
		expiresAt: tokens.expires_in ? Math.floor(Date.now() / 1000) + tokens.expires_in : undefined,
		userInfo: {
			sub: tokens.userinfo.sub,
			email: tokens.userinfo.email,
			name: tokens.userinfo.name,
			picture: tokens.userinfo.picture
		},
		role: me?.role
	};
}

/**
 * Handle deep link callback from Android trampoline.
 * The trampoline page already exchanged the code for tokens.
 * Parses authtemplate://auth?data=<json> and returns LoginInfo.
 */
export function handleDeepLinkCallback(url: string): LoginInfo {
	const parsed = new URL(url);
	const dataParam = parsed.searchParams.get('data');

	if (!dataParam) {
		throw new Error('Invalid deep link: missing data');
	}

	const data = JSON.parse(dataParam);

	return {
		provider: data.provider,
		accessToken: data.accessToken,
		refreshToken: data.refreshToken,
		idToken: data.idToken,
		expiresAt: data.expiresAt,
		userInfo: data.userInfo,
		role: data.role
	};
}
