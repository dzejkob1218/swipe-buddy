import datetime
import requests
import math
import statistics as stats
import time
import random
import os
from dotenv import load_dotenv
from datetime import date
import sys

load_dotenv()

# Get the access token from environment
TOKEN = os.environ.get("GENIUS_SECRET")
TINDER_URL = "https://api.gotinder.com"

# Rate every possible interest to judge people by
interest_scores = {
    'Baking': 3,
    'Board Games': 2,
    'Golf': 0,
    'Politics': -1,
    'Netflix': -2,
    'Dancing': 3,
    'Volunteering': 3,
    'Climbing': 3,
    'Dog lover': 3,
    'Working out': 3,
    'Photography': 2,
    'Outdoors': 3,
    'Instagram': -4,
    'Language Exchange': 3,
    'Museum': 2,
    'Grab a drink': 0,
    'Picnicking': 1,
    'Travel': 3,
    'Brunch': 0,
    'Disney': -1,
    'Blogging': 1,
    'Vlogging': 1,
    'Cat lover': 0,
    'Movies': 0,
    'Comedy': 1,
    'Fashion': 0,
    'Karaoke': 1,
    'Shopping': -3,
    'Wine': 1,
    'Art': 1,
    'Soccer': -2,
    'Writer': 3,
    'Reading': 1,
    'Trivia': 0,
    'Coffee': 4,
    'Craft Beer': 3,
    'Yoga': 3,
    'Cooking': 4,
    'Tea': 3,
    'Music': 2,
    'Astrology': -2,
    'Fishing': 0,
    'Environmentalism': 1,
    'Gamer': -1,
    'Walking': 2,
    'Foodie': 0,
    'Sports': 2,
    'DIY': 3,
    'Gardening': 4,
    'Athlete': 3,
    'Hiking': 3,
    'Surfing': 4,
    'Swimming': 3,
    'Running': 3,
    'Cycling': 3,
    'Spirituality': 2}

# Based on this dictionary, profiles can be assigned points for the city entered by their owner
# 'None' is a string literally returned by tinder if no city is entered by user
city_scores = {'None': -1, 'Berlin': 5, 'New York': -5}

points_photos = 3  # Additional points for each photo uploaded
preferred_age = 22  # Preferred age of users
points_age = 5  # This many points are removed from every year away from preferred age
bio_multiplier = 10  # Maximum points to be assigned for length of user's bio
minimum_distance = 10  # Points are removed from profiles with a distance value larger than this
distance_penalty = 0.4  # How many points are removed for each unit of distance away above minimum


def main():
    if not len(sys.argv) == 2:
        print("Enter the number of profiles to like")
        exit()
    _api = tinderAPI(TOKEN)
    goal_likes = sys.argv[1]
    swipe(goal_likes, _api)


class Profile(object):
    """ Represents a user profile received from Tinder """

    def __init__(self, data, _api):
        self._api = _api
        user = data['user']
        self.photos = len(user['photos'])
        self.badges = len(user['badges'])
        self.id = user["_id"]
        self.name = user.get("name", "Unknown")
        self.bio = user.get("bio", "")
        self.distance = data.get("distance_mi", 0)  # / 1.60934 # Uncomment to convert to km
        self.gender = ["Male", "Female", "Unknown"][user.get("gender", 2)]
        self.age = date.today().year - int(user["birth_date"][0:4])

        # Interests
        self.interests = []
        if 'experiment_info' in data:
            self.interests = [i['name'] for i in data['experiment_info']['user_interests']['selected_interests']]

            # City
        self.city = "None"
        if 'city' in user:
            self.city = user['city']['name']

        # Fav. Song
        self.musician = ''
        if 'spotify_theme_track' in data['spotify']:
            self.musician = data['spotify']['spotify_theme_track']['artists'][0]['name']

        self.images = list(map(lambda photo: photo["url"], user.get("photos", [])))
        self.score = self.rate()

    def __repr__(self):
        return f"{self.score} >> {self.name} - Age ({self.age}), Photos ({self.photos}), Ints ({len(self.interests)}), Bio ({len(self.bio)}), Distance ({self.distance})"

    def rate(self):
        """ Assigns a score to a profile based on several criteria """
        score = 0

        # Rate number of photos
        if self.photos == 1:
            score -= 10  # Penalize only one photo (very common)
        else:
            score += self.photos * points_photos

        # Rate interests
        for it in self.interests:
            if it in interest_scores:
                score += interest_scores[it]

        # Rate city:
        if self.city in city_scores:
            score += city_scores[self.city]

        # Removes points for every year away from preferred age
        score -= abs(preferred_age - self.age) * points_age

        # Rate length of bio (medium-length bios are best scored)
        bio_len = len(self.bio)
        if bio_len == 0: score -= 10  # penalize no bio
        if bio_len < 20: score -= 5  # penalize short bio
        score += bio_multiplier * math.sin((bio_len - 40) / 200)

        # Rate distance - Remove points for every distance unit above minimum
        if self.distance > minimum_distance:
            score -= distance_penalty * (self.distance - minimum_distance)

        # I have no idea what 'badges' are, but liking people who have them is a good way to find out
        if self.badges > 0:
            score += 20

        return round(score, 2)

    def like(self):
        return self._api.like(self.id)

    def dislike(self):
        return self._api.dislike(self.id)


class tinderAPI():
    """ Handles requesting and uploading data to Tinder """
    def __init__(self, token):
        self._token = token

    def profile(self):
        """ Get data on token owner's profile """
        data = requests.get(TINDER_URL + "/v2/profile?include=account%2Cuser",
                            headers={"X-Auth-Token": self._token}).json()
        return data

    def matches(self, limit=10):
        """ Get latest matches """
        data = requests.get(TINDER_URL + f"/v2/matches?count={limit}", headers={"X-Auth-Token": self._token}).json()
        return data

    def like(self, user_id):
        """ Votes 'like' on a profile on behalf of the token owner (swipe right), returns True if the profile matched"""
        data = requests.get(TINDER_URL + f"/like/{user_id}", headers={"X-Auth-Token": self._token}).json()
        return data["match"]

    def dislike(self, user_id):
        """ Votes 'pass' on a profile on behalf of the token owner (swipe left) """
        requests.get(TINDER_URL + f"/pass/{user_id}", headers={"X-Auth-Token": self._token}).json()
        return True

    def nearby_persons(self):
        """ Requests a new collection of Tinder profiles """
        data = requests.get(TINDER_URL + "/v2/recs/core", headers={"X-Auth-Token": self._token}).json()
        if data['meta']['status'] == 401:
            print("SESSION INVALID")
            exit()
        if 'results' not in data["data"]:
            print("EMPTY")
            return None
        return list(map(lambda user: Profile(user, self), data["data"]["results"]))


def swipe(goal_likes, _api):
    """
    Votes on profiles until the amount of likes specified is handed out

    Tinder sends user profiles in groups of unspecified length.
    Each group is scored based on criteria specified in Person class and a median score is calculated.
    All profiles above the median score receive a 'like', while those below receive a 'pass'.
    """
    total_likes = 0
    total_median = 0
    groups_received = 0
    while total_likes < goal_likes:
        print(f"Getting new profiles")

        # Get a list of people (sometimes more than one request is necessary)
        profiles = None
        while not profiles:
            profiles = _api.nearby_profiles()
        groups_received += 1
        print(f"Received {len(profiles)} profiles")

        scores = []
        likes = 0

        # Get median of scores
        for profile in profiles:
            scores.append(profile.score)
        median = stats.median(scores)

        print(f"Median is {median}")
        total_median += median

        # Go through the list again and hand out votes, waiting between each vote
        counter = 0
        for person in profiles:
            counter += 1
            complexity = person.photos + (len(person.bio) / 30)  # Measure how long the profile should take to view
            time.sleep(2 + (random.random() * 5) + complexity)  # Wait according to the profile's content
            # Vote 'like' if the profile's score is above media
            if person.score >= median:
                likes += 1
                match = person.like()
                print(f"Liking {person.name}, {person.age}")
                if match:
                    print("Found a match!")
                print(f"({counter}/{len(profiles)})", end="\r")
            else:
                print(f"Disliking {person.name}, {person.age}")
                print(f"({counter}/{len(profiles)})", end="\r")
                person.dislike()

        total_likes += likes
        time.sleep(2 + (random.random() * 3))  # Waits for some time before requesting a new group
        print(f"\n{likes}/{goal_likes} likes, {len(profiles) - likes} passes")

    total_median = total_median / groups_received
    print(f"Average median was {total_median}")
    print("Done")


if __name__ == "__main__":
    main()
