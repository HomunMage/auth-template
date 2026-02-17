// lib/platform/detect.ts

import type { Platform } from './types';

const isMobile = import.meta.env.VITE_PLATFORM === 'mobile';

/** Get the current platform */
export async function getPlatform(): Promise<Platform> {
	if (!isMobile) {
		return 'web';
	}

	try {
		const { Capacitor } = await import('@capacitor/core');
		const platform = Capacitor.getPlatform();
		if (platform === 'android') return 'android';
		if (platform === 'ios') return 'ios';
		return 'web';
	} catch {
		return 'web';
	}
}

/** Check if running on a native mobile platform */
export async function isNativePlatform(): Promise<boolean> {
	if (!isMobile) return false;

	try {
		const { Capacitor } = await import('@capacitor/core');
		return Capacitor.isNativePlatform();
	} catch {
		return false;
	}
}

/** Check if running on web */
export function isWeb(): boolean {
	return !isMobile;
}
