# Curation-Validation-Bot
A Discord bot that validates curations for [BlueMaxima's Flashpoint](https://bluemaxima.org/flashpoint/). Also does other things.

## Setup and run
- prepare your discord bot shenanigans, it requires the Server Members intent
- copy `example.env` into `.env` and set the variables
- copy `data/example_rolereaction.json` into `data/rolereaction.json` and set the variables
- `pip install -r requirements.txt`
- `python bot.py`

## Running tests
- type `pytest` in the project root directory to run tests

## Running the validator server
`python -m uvicorn validator-server:app --host 127.0.0.1 --port 8000`