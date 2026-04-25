---
title: "Lecture 1. Feature Showcase"
author: ""
date: "2026-04-25"
subject: "Tutorial"
creator: "md2pdf"
---

# LECTURE 1

# Feature Showcase

## CHECKBOXES

## NESTED LISTS

## ESCAPING

## PYTHON HIGHLIGHTING

## JAVASCRIPT HIGHLIGHTING

## SQL HIGHLIGHTING

## BASH HIGHLIGHTING

## Tutorial

# Table of Contents

## 1. Checkboxes

## 2. Nested lists

## 3. Escaping

## 4. Python highlighting

## 5. JavaScript highlighting

## 6. SQL highlighting

## 7. Bash highlighting

## 8. Common elements

## 9. Conclusion

# 1. Checkboxes

- [x] Done: parser extended
- [x] Done: syntax highlighting
- [ ] Not done yet
- [ ] Also pending

# 2. Nested lists

- Level 0
  - Level 1
    - Level 2
      - Level 3
- Another Level 0
  - And Level 1

# 3. Escaping

This is not italic, and \# is not a heading.

Backslash: \\, inline code: `not code` rendered as code.

# 4. Python highlighting

```python
def hello(name):
    """Greet a user by name."""
    if name is None:
        return "Hello, World!"
    count = 42
    return f"Hello, {name}!"


class MyClass:
    pass
```

# 5. JavaScript highlighting

```javascript
const greet = (name) => {
   // This is a comment
   let message = `Hello, ${name}!`;
   return message;
};

async function fetchData(url) {
   const response = await fetch(url);
   return response.json();
}
```

# 6. SQL highlighting

```sql
SELECT u.name, COUNT(*) AS total
FROM users u
LEFT JOIN orders o ON u.id = o.user_id
WHERE u.active = 1
GROUP BY u.name
HAVING total > 5
ORDER BY total DESC
LIMIT 10;
```

# 7. Bash highlighting

```bash
#!/bin/bash
for file in *.md; do
   echo "Processing $file"
   if [ -f "$file" ]; then
       local count=$(wc -l < "$file")
       echo "Lines: $count"
   fi
done
```

# 8. Common elements

| Header 1 | Header 2 | Header 3 |
| --- | --- | --- |
| Cell 1 | Cell 2 | Cell 3 |
| Cell 4 | Cell 5 | Cell 6 |

> A blockquote to verify the block style.

# 9. Conclusion

All 12 polish items work as expected.

Regular text with **bold**, *italic*, and `inline code`.
