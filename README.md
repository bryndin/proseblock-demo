## Setting up Core Pages (Search, Archives, Authors)

Theme X uses Hugo's native routing to generate custom functional pages. Because a theme should never force content onto your site, you must opt-in to these pages by creating a simple `_index.md` file in your site's `content` folder.

### 1. Enable the Search Page

Create a file at `content/search/_index.md` with the following front matter:

```yaml
---
title: "Search"
type: "search"
layout: "list"
---
```

_Note: Make sure your `hugo.toml` has `JSON` output enabled for the home page so the search engine can index your articles._

### 2. Enable the Archives Page

Create a file at `content/archives/_index.md` with the following front matter:

```yaml
---
title: "Archives"
type: "archives"
layout: "list"
---
A complete chronological record of our publications.
```

_Note: Any text you place below the front matter dashes will automatically be used as the Hero subtitle._
