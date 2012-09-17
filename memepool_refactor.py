#!/usr/bin/env python

from __future__ import division
#import requests
import urlparse
import oauth2 as oauth
import json
#import logging
from urllib import urlencode
from random import random, choice
#from operator import itemgetter
#from google.appengine.ext import db
#from models import Generation


def get_client(key, secret, token_url, username, password):
    """Initializes an xAuth consumer and client, passes in stored
    credentials, authenticates, and returns an authorized client"""
    #Initialize an xAuth consumer and client and pass in stored credentials
    consumer = oauth.Consumer(key, secret)
    client = oauth.Client(consumer)
    client.add_credentials(username, password)
    client.authorizations

    params = {}
    params['x_auth_username'] = username
    params['x_auth_password'] = password
    params['x_auth_mode'] = 'client_auth'

    client.set_signature_method = oauth.SignatureMethod_HMAC_SHA1()

    #Authenticate via xAuth. Store the returned response and token.
    resp, token = client.request(token_url,
                                 method='POST',
                                 body=urlencode(params))

    print "Response status: ", resp['status']
    access_token = dict(urlparse.parse_qsl(token))
    access_token = oauth.Token(access_token['oauth_token'],
                               access_token['oauth_token_secret'])

    client = oauth.Client(consumer, access_token)
    return client


def fitness(post):
    return post['note_count'] if 'note_count' in post else 0


def get_posts_by_fitness(client, fitness):
    """Gets the last 20 posts on a user's dashboard. Returns a list of
    posts sorted by descending fitness."""
    posts = tumblr_request(client,
                           'blog',
                           'posts/photo',
                           'meme-pool',
                           CONSUMER_KEY,
                           {'notes_info': True})
    tagged_posts = remove_untagged(posts['posts'])
    return sorted(tagged_posts, key=fitness, reverse=True)


def get_alleles(memepool, population):
    mate1 = int(population - (random() * random() * population))
    mate2 = int(population - (random() * random() * population))

    while mate1 == mate2:
        mate2 = int(population - (random() * random() * population))

    try:
        allele1 = choice(memepool[mate1]['tags'])
        allele2 = choice(memepool[mate2]['tags'])
    except IndexError:
        get_alleles(memepool, population)

    return [allele1, allele2]


def remove_untagged(posts):
    return [post for post in posts if post['tags']]


def find_post(client, genotype):
        allele_sets = []
        for allele in genotype:
            tagged = tumblr_request(client,
                                    'tagged',
                                    key=CONSUMER_KEY,
                                    params={'tag': allele})
            reblog_keys = [(post['reblog_key'],
                            post['id'],
                            post['type'])
                            for post in tagged]
            allele_sets.append(set(reblog_keys))
        
        genotype_posts = allele_sets[0].intersection(allele_sets[1])
        
        if len(genotype_posts) == 0:
            dominant_allele = choice(genotype)
            tagged = tumblr_request(client,
                                'tagged',
                                key=CONSUMER_KEY,
                                params={'tag': dominant_allele})
            genotype_posts = [(post['reblog_key'],
                               post['id'],
                               post['type']) 
                               for post in tagged]
        return choice(list(genotype_posts))


def mate_posts(client):
    memepool = get_posts_by_fitness(client, fitness)
    
    #Calculate memepool population
    population = len(memepool)
    
    genotype = get_alleles(memepool, population)
    child_post = find_post(client, genotype)
    return child_post, genotype


def post_child(client, child, genotype):
    post_params = {}
    post_params['reblog_key'] = child[0]
    post_params['id'] = child[1]
    post_params['type'] = child[2]
    post_params['tags'] = ', '.join(genotype)

    tumblr_request(client,
                   'blog',
                   'post/reblog',
                   'meme-pool-dev',
                   params=post_params,
                   method='POST')


def tumblr_request(client, api, 
                   action=None, user=None, key=None, params={}, method='GET'):
    base = 'http://api.tumblr.com/v2/'
    request_url = base + api
    if action:
        request_url = base + api + '/' + action
    if user:
        blog = user + '.tumblr.com/'
        request_url = base + api + '/' + blog + action
    if key:
        params['api_key'] = key
    if urlencode(params) and method == 'GET':
        request_url = request_url + '?' + urlencode(params)
    if method == 'POST':
        meta, response = client.request(request_url,
                                        method=method,
                                        body=urlencode(params))
    else:
        meta, response = client.request(request_url, method=method)
    print "Response status: ", meta['status']
    if meta['status'] not in ['200']:
        print "Meta: ", meta
        print "Response: ", response
    return json.loads(response)['response']


def main():
    client = get_client(CONSUMER_KEY,
                        CONSUMER_SECRET,
                        ACCESS_TOKEN_URL,
                        TUMBLR_USERNAME,
                        TUMBLR_PASSWORD)

    child, genotype = mate_posts(client)
    post_child(client, child, genotype)

if __name__ == '__main__':
    main()
