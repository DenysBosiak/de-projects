from etls.reddit_etl import connect_reddit
from utils.constants import CLIENT_ID, SECRET


def reddit_pipeline(file_name: str, subreddit: str, time_filter='day', limit=None):
    # Connecting to reddit instance
    instance = connect_reddit(CLIENT_ID, SECRET, 'Airscholar Agent')
    # Exctraction
    # Transformation
    # Loading to csv