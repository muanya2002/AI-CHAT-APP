const { defineConfig } = require("cypress");

module.exports = defineConfig({
  projectId: "9wa6cq",

  e2e: {
    setupNodeEvents(on, config) {
      // implement node event listeners here
    },
  },

  component: {
    devServer: {
      framework: "next",
      bundler: "webpack",
    },
  },
});
