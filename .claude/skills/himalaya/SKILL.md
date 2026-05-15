---
name: himalaya
description: "Compose and send emails from the terminal using the himalaya CLI. Use when the user wants to send a message, draft an email, or do anything email-related from a script or shell."
---

# himalaya

CLI email client. See `references/message-composition.md` for MML body composition details.

## Send a simple email

```bash
echo "From: sakima.lc@gmail.com
To: someone@example.com
Subject: hi

Body content here." | himalaya send
```

## Reply to a message

```bash
himalaya reply <message-id> --body "thanks!"
```

## List inbox

```bash
himalaya list -f INBOX -p 1 -s 20
```

## MML (rich content)

For attachments or HTML bodies, use MML:

```
<#part type="text/html">
  <p>Hello <b>world</b></p>
<#/part>
<#part type="image/png" filename="chart.png"><#/part>
```

See `references/message-composition.md` for header conventions and address formats.
