import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";
import type { Ref } from "vue";

type Updater<T> = T | ((old: T) => T);

/** 合并 Tailwind CSS 类名 */
export function cn(...inputs: ClassValue[]) {
	return twMerge(clsx(inputs));
}

/** 更新 TanStack Table 的值 */
export function valueUpdater<T>(
	updaterOrValue: Updater<T>,
	ref: Ref<T>,
) {
	ref.value =
		typeof updaterOrValue === "function"
			? (updaterOrValue as (old: T) => T)(ref.value)
			: updaterOrValue;
}
