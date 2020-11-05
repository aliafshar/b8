
const util = require('util')
const CleanCSS = require("clean-css");
const eleventyNavigationPlugin = require("@11ty/eleventy-navigation");
const exec = require('child_process').exec;
const syntaxHighlight = require("@11ty/eleventy-plugin-syntaxhighlight");
const pluginTOC = require('eleventy-plugin-nesting-toc');
const markdownIt = require('markdown-it')
const markdownItAnchor = require('markdown-it-anchor')
const Parser = require('rss-parser');
const dformat = require('date-format');
const parser = new Parser({
  customFields: {
    item: [
    ]
  }
});

const mdOptions = {
  html: true,
  breaks: false,
  linkify: true,
  typographer: true
}
const mdAnchorOpts = {
  permalink: true,
  permalinkClass: 'anchor-link',
  permalinkSymbol: '',
  level: [1, 2, 3, 4]
}

module.exports = function(eleventyConfig) {

  eleventyConfig.setLibrary(
    'md',
    markdownIt(mdOptions)
      .use(markdownItAnchor, mdAnchorOpts)
  )

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

  eleventyConfig.addNunjucksAsyncFilter('rss', function(url, callback) {
    parser.parseURL(url).then(function(feed) {
      feed.debug = util.inspect(feed);
      callback(null, feed);
    });

    //(command, function(error, stdout, stderr){ callback(null, stdout); });
  });

  eleventyConfig.addNunjucksFilter('date', function(d) {
    return dformat.asString('yyyy MM dd',
      dformat.parse(dformat.ISO8601_WITH_TZ_OFFSET_FORMAT, d));
  });

  eleventyConfig.addPlugin(eleventyNavigationPlugin);
  eleventyConfig.addPlugin(syntaxHighlight);
  eleventyConfig.addPlugin(pluginTOC);

  return {
    dir : {
      input: 'dev/www/src',
      output: 'dev/www/public',
    },
  }
};

