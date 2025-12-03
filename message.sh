#!/bin/bash

curl -X POST \
  http://localhost:8080/message/sendText/test \
  -H "Content-Type: application/json" \
  -H "apikey: C74709FD0F08-43B5-BA0C-D76E962F33EC" \
  -d '{
        "number": "919650436187",
        "text": "Hi! This is a test message from Evolution API.",
        "delay": 500,
        "linkPreview": false
      }'
