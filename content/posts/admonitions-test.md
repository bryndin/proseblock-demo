---
title: 'Admonitions Test Page'
description: "Testing Hugo's native Markdown alerts (admonitions)."
summary: "A comprehensive test of the five standard Markdown alerts natively parsed by Hugo: Note, Tip, Important, Warning, and Caution."
date: 2026-03-13T10:00:00+00:00
tags: [markdown, admonitions]
categories: [Design]
draft: false
---

This post tests the native Markdown Alerts (Admonitions) supported by Hugo via the GitHub-flavored markdown syntax. 

## Note

```
> [!NOTE]
> This is a **Note** admonition. Useful information that users should know, even when skimming content.
```

> [!NOTE]
> This is a **Note** admonition. Useful information that users should know, even when skimming content.

## Tip

```
> [!TIP]
> This is a **Tip** admonition. Helpful advice for doing things better or more easily.
```

> [!TIP]
> This is a **Tip** admonition. Helpful advice for doing things better or more easily.

## Important

```
> [!IMPORTANT]
> This is an **Important** admonition. Key information users need to know to achieve their goal.
```

> [!IMPORTANT]
> This is an **Important** admonition. Key information users need to know to achieve their goal.

## Warning

```
> [!WARNING]
> This is a **Warning** admonition. Urgent info that needs immediate user attention to avoid problems.
```

> [!WARNING]
> This is a **Warning** admonition. Urgent info that needs immediate user attention to avoid problems.

## Caution

```
> [!CAUTION]
> This is a **Caution** admonition. Advises about risks or negative outcomes of certain actions.
```

> [!CAUTION]
> This is a **Caution** admonition. Advises about risks or negative outcomes of certain actions.

## Nested Content in Alerts
```
> [!TIP]
> You can put block elements inside alerts!
>
> * It supports standard lists.
> * It supports inline `code`.
>
> ```js
> console.log("It even supports full code blocks!");
> ```
```

> [!TIP]
> You can put block elements inside alerts!
>
> * It supports standard lists.
> * It supports inline `code`.
>
> ```js
> console.log("It even supports full code blocks!");
> ```

## Regular Blockquote Comparison

```
> This is a standard blockquote without an alert designator. It should continue to be styled using the standard left-border styling we defined in our `base.css` file, clearly visually distinct from the alerts above.
```

> This is a standard blockquote without an alert designator. It should continue to be styled using the standard left-border styling we defined in our `base.css` file, clearly visually distinct from the alerts above.
