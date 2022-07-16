#!/bin/sh

set -e  # exit on any error

# check tools
command -v poetry >/dev/null || (echo 'poetry not installed!'; exit 1)

# check environment
[ -d .venv ] || (echo 'python virtual environment is not set up!'; exit 1)

# .env file is mandatory
[ -f .env ] || (echo '.env file not found!' && exit 1)

# check if .env file is up to date
while read -r line
do
   grep -q "^$line" .env || (echo "$line - param not defined in .env!"; exit 1)
done <<< $(sed 's/#.*//' env.example | sed '/^[[:space:]]*$/d')

poetry run python ./src/main.py
