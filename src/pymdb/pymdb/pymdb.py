#!/usr/bin/env python
# -*- coding: utf-8 -*-
# File              : pymdb.py
# Author            : Kaushik S Kalmady
# Date              : 07.11.2015
# Last Modified Date: 07.11.2017
# Last Modified By  : Kaushik S Kalmady

from __future__ import print_function
import json
import string
try:
    from urllib.request import urlopen
    from urllib.parse import urlencode
except:
    from urllib import urlopen
    from urllib import urlencode
import re


def top_250():
    """
    Pulls out IMDb Top 250 movies names.
    :return: dictionary
    """

    url = 'http://www.imdb.com/chart/top'
    try:
        raw_file = urlopen(url).read()
        titles = re.findall('title=".*?dir.*?>(.*?)</a>', raw_file)
        return {i: title for i, title in enumerate(titles, 1)}
    except EnvironmentError:
        print("NetWorkError: [Please make sure you are connected to internet]")
        return {}


def top250_year_count():
    """
    Pulls out number of movies of a particular year in the IMDb Top 250
    :return: dictionary
    """

    year_count = {}

    url = 'http://www.imdb.com/chart/top'
    try:
        raw_file = urlopen(url).read()
        years = re.findall('secondaryInfo">\((.*?)\)</span>', raw_file)
        for year in years:
            year_count[year] = year_count.get(year, 0) + 1
        return year_count
    except EnvironmentError:
        print("NetWorkError: [Please make sure you are connected to internet]")
        return year_count


def years_top250():
    """
    Pulls out IMDb Top 250 movies years
    :return: dictionary
    """

    url = 'http://www.imdb.com/chart/top'
    try:
        raw_file = urlopen(url).read()
        years = re.findall('secondaryInfo">\((.*?)\)</span>', raw_file)
        return {i: year for i, year in enumerate(years, 1)}
    except EnvironmentError:
        print("NetWorkError: [Please make sure you are connected to internet]")
        return {}

def top250_id():
    """Pulls out ImDb Title ID's from the Imdb Top 250 webpage and adds them to a list.
    Returns List"""
    movielist = []
    url2 = 'http://www.imdb.com/chart/top'
    file = urlopen(url2).read()
    links = re.findall('<div class=".*?tconst="(.*?)"></div>', file)

    for link in links:
        movielist.append(link)
    return movielist

class Movie:
    """Movie
    Enter movie title as parameter. Year is an optional argument"""

    def __init__(self, title, year=None, category=''):
        """Fetches JSON for given Movie from omdbapi.com

        Args:
            title (str): title of the movie
            year (None, optional): year of release
            category (str, optional): one of "movie", "series", "episode"

        """
        assert category in ('', "movie", "series", "episode")
        service_url = 'http://www.omdbapi.com/?apikey=eed67065&'
        url = service_url + urlencode({'t': title, 'type': category, 'y': year, 'plot': 'short',
                                       'r': 'json'})
        try:
            self.stuff = json.loads(urlopen(url).read())
        except EnvironmentError:
            print("NetWorkError: [Please make sure you are connected to internet]")
            #exit()

    @classmethod
    def search(self, title, category='', year=None):
        """search for a movie or series by title

        Args:
            title (str): title of the movie
            year (None, optional): year of release
            category (str, optional): one of "movie", "series", "episode"
        """
        assert category in ('', "movie", "series", "episode")
        service_url = 'http://www.omdbapi.com/?apikey=eed67065&'
        url = service_url + urlencode({'s': title, 'type': category, 'y': year,'r': 'json'})
        try:
            results = json.loads(urlopen(url).read())["Search"]
            for item in results:
                print("\t" + item["Title"] + " (" + item["Year"] + ")" + " [" + item["imdbID"] + "]" + " {" + item["Type"] + "}")
            print("Found total {} matching results".format(len(results)))
        except KeyError:
            print("Not found")


    def info(self):
        """Prints basic Info from IMDb"""
        print(self.stuff["Title"])
        print("Year: ", self.stuff["Year"])
        print("Rating: {rating} ({votes} votes)".format(rating=self.stuff["imdbRating"], votes=self.stuff["imdbVotes"]))
        print("Metascore: ", self.stuff["Metascore"])
        print("Language: ", self.stuff["Language"])
        print("Genre: ", self.stuff["Genre"])
        print("Director: ", self.stuff["Director"])
        print("Awards: ", self.stuff["Awards"])


    def getposter(self):
        """Saves poster of movie in current directory or raise exception if anything goes wrong
        To check current directort type 'os.getcwd()'
        To change current directory type 'os.chdir('path you wish')'
        """
        try:
            link = self.stuff["Poster"]
            image = urlopen(link).read()
            filename = self.stuff["Title"].translate(string.punctuation) + ".jpg"
            outfile = open(filename , 'wb')
            outfile.write(image)
            outfile.close()
            print("Poster saved to " + filename)
        except AttributeError:
            print("Error: [ Something went wrong while downloading image, make sure you entered correct name or ID ]")
        except IOError:
            print("IOError: [ No such Image Exist ]")

    def year(self):
        """
        :return: Year of Movie
        """
        return int(self.stuff["Year"])

    def ratings(self):
        """
        :return: IMDb, RT, Metacritic ratings
        """
        data = self.stuff["Ratings"]
        rating = {}
        for entry in data:
            rating[entry["Source"]] = entry["Value"]
        return rating


    def director(self):
        """
        :return: list of Name of Directors of movie
        """
        return list(map(str, self.stuff["Director"].split(",")))

    def actors(self):
        """
        :return: list of Name of Cast in movie
        """
        return list(map(str, self.stuff["Actors"].split(",")))

    def plot(self):
        """Prints Short Plot"""
        print(self.stuff["Plot"])
        print("For more visit:\n ", self.stuff["tomatoURL"])
        print("http://www.imdb.com/title/%s" % self.stuff["imdbID"])

    def awards(self):
        """
        :return: rewards earned by the movie
        """
        return self.stuff["Awards"]

    def reviews(self):
        """Prints Rotten Tomatoes Critics Consensus"""
        print(self.stuff["tomatoConsensus"])
        print("For more visit: ", self.stuff["tomatoeURL"])
        print("http://www.imdb.com/title/%s/reviews?ref_=tt_ov_rt" % self.stuff["imdbID"])


class MovieId(Movie):
    """Takes IMDb ID as parameter instead of title"""

    def __init__(self, movie_id, category=''):
        try:
            assert category in ('', "movie", "series", "episode")
            service_url = 'http://www.omdbapi.com/?apikey=eed67065&'
            url = service_url + urlencode({'i': movie_id, 'type': category, 'plot': 'short',
                                           'r': 'json'})
            self.stuff = json.loads(urlopen(url).read())

        except EnvironmentError:
            print("NetWorkError: [Please make sure you are connected to internet]")
            #exit()

    def title(self):
        """
        :return: Title of movie which has this particular id on IMDb
        """
        return self.stuff["Title"]
