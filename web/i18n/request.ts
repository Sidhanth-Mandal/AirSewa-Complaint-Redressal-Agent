import { getRequestConfig } from "next-intl/server";
import { cookies } from "next/headers";

export const locales = ["en", "hi"] as const; // add more languages by adding messages/<code>.json and listing the code here

export default getRequestConfig(async () => {
  const c = (await cookies()).get("locale")?.value;
  const locale = (locales as readonly string[]).includes(c || "") ? (c as string) : "en";
  return { locale, messages: (await import(`../messages/${locale}.json`)).default };
});
