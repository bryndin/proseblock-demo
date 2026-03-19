---
title: "Code Blocks and Syntax Highlighting"
date: 2023-02-01T15:23:00+07:00
tags: [code, softwareengineering, post]
categories: [Code, Design]
# toc: true
# hidden: false
weight: 14
draft: false
---

One of the essential features of any blogging theme is code blocks and syntax highlighting. As a blogger, you want to share your code with your audience in a clear and readable format. Maupassant IC has got you covered!<!--more-->

## Supported Languages

Maupassant IC uses Chroma, a popular syntax highlighting engine, to support a wide range of programming languages. You can find the full list of supported languages on the [Hugo documentation website](https://gohugo.io/content-management/syntax-highlighting/#list-of-chroma-highlighting-languages).

## Code Blocks with Copy to Clipboard

In Maupassant IC, code blocks are beautifully formatted with syntax highlighting, and they come with a convenient "copy to clipboard" button. This makes it easy for your readers to copy and paste your code into their own projects.

Here are some sample code blocks in different programming languages:

### Inline code span

`Inline code span`

### Untagged Code Block (no syntax highlighting)

```
This code block has no language specified.
```

### Extra Long Code Block: π

```
3.141592653589793238462643383279502884197169399375105820974944592307816406286208998628034825342117067982148086513282306647093844609550582231725359408128481117450284102701938521105559644622948954930381964428810975665933446128475648233786783165271201909145648566923460348610454326648213393607260249141273724587006606315588174881520920962829254091715364367892590360011330530548820466521384146951941511609433057270365759591953092186117381932611793105118548074462379962749567351885752724891227938183011949129833673362440656643086021394946395224737190702179860943702770539217176293176752384674818467669405132000568127145263560827785771342757789609173637178721468440901224953430146549585371050792279689258923542019956112129021960864034418159813629774771309960518707211349999998372978049951059731732816096318595024459455346908302642522308253344685035261931188171010003137838752886587533208381420617177669147303598253490428755468731159562863882353787593751957781857780532171226806613001927876611195909216420198938095257201065485863278865936153381827968230301952035301852968995773622599413891249721775283479131515574857242454150695950829533116861727855889075098381754637464939319255060400927701671139009848824012858361603563707660104710181942955596198946767837449448255379774726847104047534646208046684259069491293313677028989152104752162056966024058038150193511253382430035587640247496473263914199272604269922796782354781636009341721641219924586315030286182
```

## Examples of syntax highlighting

### Go  

```go
package main

import "fmt"

func main() {
    fmt.Println("Hello, World!")
}
```

### Python (snippet with line numbers)

```python {linenos=true}
print("Hello, World!")
```

### JavaScript (snippet with table line numbers)

```javascript {linenos=table}
console.log("Hello, World!");
```

### Java (snippet with line numbers, highlighting lines 2-4)

```java {linenos=true,hl_lines=["2-4"]}
public class HelloWorld {
    public static void main(String[] args) {
        System.out.println("Hello, World!");
    }
}
```

### Bash (snippet with inline line numbers and anchor lines)

```bash {linenos=inline,anchorlinenos=true}
#!/bin/bash
echo "Hello, World!"
```

As you can see, the code blocks are nicely formatted with syntax highlighting, and the "copy to clipboard" button makes it easy to copy the code.

## Conclusion

Maupassant IC makes it easy to share your code with your audience in a clear and readable format. With support for a wide range of programming languages and a convenient "copy to clipboard" button, you can focus on sharing your knowledge and expertise with the world.

Stay tuned for more updates and features from the Maupassant IC demo blog!
