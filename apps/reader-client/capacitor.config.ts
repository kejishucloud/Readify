import type { CapacitorConfig } from "@capacitor/cli";
const config: CapacitorConfig = {
  appId: "com.kejishucloud.readify",
  appName: "Readify",
  webDir: "dist",
  android: {allowMixedContent: false},
  ios: {contentInset: "automatic"},
};
export default config;
