---
name: greet
description: Greets the user by name in a chosen language. Use when the user asks to be greeted, says hello, or asks for a greeting in a specific language.
---

# Greet Skill

Greet the user warmly by name in the language they request.

## Supported Languages

- English: "Hello, {name}! Welcome!"
- Spanish: "¡Hola, {name}! ¡Bienvenido!"
- French: "Bonjour, {name}! Bienvenue!"
- Japanese: "こんにちは、{name}さん！ようこそ！"

## Instructions

1. Ask for the user's name if not provided.
2. Ask for preferred language, default to English if not specified.
3. Respond using the template above, substituting {name} with their actual name.
4. Add a friendly one-sentence follow-up.
