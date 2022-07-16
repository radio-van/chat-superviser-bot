import environ
import logging
import pathlib


# set types for env variables
env = environ.FileAwareEnv(
    API_ID=(int, 0),
    API_HASH=(str, ''),
    BOT_TOKEN=(str, ''),

    LOG_LEVEL=(str, 'WARNING'),

    REDIS_HOST=(str, 'redis'),
    REDIS_PORT=(int, 6379),

    CHECK_ONLY_FORWARDED_MESSAGES=(bool, True),
    CHECK_LINKS=(bool, True),
    DUPLICATE_SIMILARITY_THRESHOLD=(float, 0.5),
    MESSAGE_LENGTH_WORDS_THRESHOLD=(int, 10),
    RECENT_MESSAGES_AMOUNT=(int, 50),
    SELF_DESTRUCTION_MULTIPLIER=(int, 10),
)

# read .env file
environ.Env.read_env(pathlib.Path().resolve() / '.env')

API_ID = env('API_ID')
API_HASH = env('API_HASH')
BOT_TOKEN = env('BOT_TOKEN')

REDIS_HOST = env('REDIS_HOST')
REDIS_PORT = env('REDIS_PORT')

if env('LOG_LEVEL') == 'DEBUG':
    LOG_LEVEL = logging.DEBUG
else:
    LOG_LEVEL = logging.INFO

CHECK_ONLY_FORWARDED_MESSAGES = env('CHECK_ONLY_FORWARDED_MESSAGES')
CHECK_LINKS = env('CHECK_LINKS')
DUPLICATE_SIMILARITY_THRESHOLD = env('DUPLICATE_SIMILARITY_THRESHOLD')
MESSAGE_LENGTH_WORDS_THRESHOLD = env('MESSAGE_LENGTH_WORDS_THRESHOLD')
RECENT_MESSAGES_AMOUNT = env('RECENT_MESSAGES_AMOUNT')
SELF_DESTRUCTION_MULTIPLIER = env('SELF_DESTRUCTION_MULTIPLIER')
