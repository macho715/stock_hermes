export default {
  testDir: ".",
  testMatch: /bridge_smoke\.spec\.mjs$/,
  reporter: "line",
  use: {
    channel: "chrome",
  },
};
