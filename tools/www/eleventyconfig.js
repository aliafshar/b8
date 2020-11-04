
const CleanCSS = require("clean-css");
const eleventyNavigationPlugin = require("@11ty/eleventy-navigation");
const exec = require('child_process').exec;
const syntaxHighlight = require("@11ty/eleventy-plugin-syntaxhighlight");

module.exports = function(eleventyConfig) {
  eleventyConfig.addFilter("cssmin", function(code) {
    return new CleanCSS({}).minify(code).styles;
  });
  eleventyConfig.setTemplateFormats([
    'md',
    'njk',
  ]);
  eleventyConfig.addNunjucksShortcode('icon', function(name) {
    return `<span class="icon is-medium b8-button"><i class="mdi mdi-light mdi-24px mdi-${name}"></i></span>`;
  });

  eleventyConfig.addNunjucksAsyncFilter('exec', function(command, callback) {
    exec(command, function(error, stdout, stderr){ callback(null, stdout); });
  });

  eleventyConfig.addPlugin(eleventyNavigationPlugin);
  eleventyConfig.addPlugin(syntaxHighlight);

  return {
    dir : {
      input: 'tools/www/src',
      output: 'tools/www/public',
    },
  }
};

