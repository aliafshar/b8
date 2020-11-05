---
layout: layout.njk
permalink: development.html
eleventyNavigation:
  key: Development
  order: 4
templateEngineOverride: njk,md
---

# Developing Bominade

This information should help you if you want to contribute to Bominade.

## Bugs and feature requests

You can see the open bugs on the [Issue tracker](https://gitlab.com/afshar-oss/b8/-/issues). We
do not use Github's issue tracker.


## Open Issues

{% set bugfeed = 'https://gitlab.com/afshar-oss/b8/-/issues.atom?state=opened' | rss %}

<table class="table is-fullwidth is-striped">
  <thead>
  <tr>
    <th>Bug</th>
    <th>Date</th>
  </tr>
  </thead>
  <tbody>
  {% for item in bugfeed.items %}
  <tr>
    <td><a href="{{ item.url | safe }}">{{ item.title | safe  }}</a></td>
    <td>{{ item.pubDate | date }}</td>
  </tr>
  {% endfor %}
  </tbody>
</table>


## Commit history

{% set commitfeed = 'https://gitlab.com/afshar-oss/b8/-/commits/dev?format=atom&limit=20' | rss  %}

<table class="table is-fullwidth is-striped">
  <thead>
  <tr>
    <th>Bug</th>
    <th>Date</th>
    <th>Author</th>
  </tr>
  </thead>
  <tbody>
  {% for item in commitfeed.items %}
  <tr>
    <td><a href="{{ item.id | safe }}">{{ item.title | safe }}</a></td>
    <td>{{ item.pubDate | date }}</td>
    <td>{{ item.author | safe }}</td>
  </tr>
  {% endfor %}
  </tbody>
</table>



