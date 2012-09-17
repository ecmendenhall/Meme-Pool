#!/usr/bin/env python

from __future__ import division
import urlparse
import oauth2 as oauth
import json
import logging
from urllib import urlencode
from operator import itemgetter
from random import random, choice
from google.appengine.ext import db
from models import Generation

CONSUMER_KEY = 'Fill in your consumer key here'
CONSUMER_SECRET = 'Fill in your consumer secret here'
ACCESS_TOKEN_URL = 'https://www.tumblr.com/oauth/access_token'
TUMBLR_USERNAME = 'Your Tumblr username'
TUMBLR_PASSWORD = 'Your Tumblr password'


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

    logging.info("Response status: ", resp['status'])
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
    return sorted(tagged_posts, key=fitness)


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
                   'meme-pool',
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
    logging.info("Response status: ", meta['status'])
    if meta['status'] not in ['200']:
        logging.info("Meta: ", meta)
        logging.info("Response: ", response)
    return json.loads(response)['response']


def get_current_generation():
    g = Generation.all()
    last_generation = g.order('-saved').get()

    if not last_generation:
        current_generation = 1
    else:
        current_generation = last_generation.generation + 1
    return current_generation


def all_followers(client, blog_name):
    followers = tumblr_request(client,
                               'blog',
                               'followers',
                               'meme-pool')
    return followers['users']


def all_alleles(memepool):
    alleles = []
    for post in memepool:
        for tag in post['tags']:
            if tag.lower() not in ['submission']:
                alleles.append(tag.lower())
    return alleles


def allele_count(alleles):
    ranked_alleles = []
    for allele in alleles:
        ranked_alleles.append((allele, alleles.count(allele)))
    return sorted(ranked_alleles, key=itemgetter(1), reverse=True)


def unique_alleles(alleles):
    return set(alleles)


def get_memepool_post(memepool, index):
    if 'note_count' in memepool[index]:
        fitness = memepool[index]['note_count']
    else:
        fitness = 0
    url = memepool[index]['post_url']
    genome = memepool[index]['tags']
    return fitness, url, genome


def total_fitness(memepool):
    total = 0
    for post in memepool:
        if 'note_count' in post:
            total += int(post['note_count'])
    return total


def generate_stats(client, memepool):
    stats = {}

    stats['generation'] = get_current_generation()
    
    followers = all_followers(client, 'meme-pool')
    stats['contributors'] = len(followers)
    
    alleles = all_alleles(memepool)
    allele_set = unique_alleles(alleles)

    stats['population'] = len(memepool)
    stats['unique alleles'] = list(allele_set)
    stats['n unique alleles'] = len(allele_set)

    leastfit = get_memepool_post(memepool, 0)
    stats['leastfit fitness'] = leastfit[0]
    stats['leastfit url'] = leastfit[1]
    stats['leastfit tags'] = leastfit[2]

    mostfit = get_memepool_post(memepool, -1)
    stats['mostfit fitness'] = mostfit[0]
    stats['mostfit url'] = mostfit[1]
    stats['mostfit tags'] = mostfit[2]
    
    stats['total fitness'] = total_fitness(memepool)
    stats['mean fitness'] = round(total_fitness(memepool) / len(memepool), 3)

    return stats


def save_stats(stats):
    gen = Generation()

    gen.generation = stats['generation']
    gen.population = stats['population']
    
    gen.mean_fitness = stats['mean fitness']
    gen.total_fitness = stats['total fitness']
    
    gen.most_fit_genome = stats['mostfit tags']
    gen.most_fit_post_fitness = stats['mostfit fitness']
    gen.most_fit_post_url = stats['mostfit url']
    
    gen.least_fit_genome = stats['leastfit tags']
    gen.least_fit_post_fitness = stats['leastfit fitness']
    gen.least_fit_post_url = stats['leastfit url']

    gen.unique_alleles = stats['unique alleles']
    gen.n_unique_alleles = stats['n unique alleles']

    gen.contributors = stats['contributors']

    db.put(gen)


def post_stats(client, stats):
    update_title = 'Memepool update: Generation %d' % stats['generation']
    post_strings = ["* __Population:__ %d\n" % 
                    stats['population'],
                    "* __Mean fitness:__ %d\n" % 
                    stats['mean fitness'],
                    "* __Fittest genome:__ [%s](%s) (%d)\n" % 
                    ([s.encode('utf-8') for s in stats['mostfit tags']],
                     stats['mostfit url'],
                     stats['mostfit fitness']),
                    "* __Least fit genome:__ [%s](%s) (%d)\n" % 
                    ([s.encode('utf-8') for s in stats['leastfit tags']],
                     stats['leastfit url'],
                     stats['leastfit fitness']),
                    "* __Unique alleles in population:__ %d\n" % 
                    stats['n unique alleles'],
                    "* __Contributors to memepool:__ %s\n" % 
                    stats['contributors'],
                    "* __Set of unique alleles:__\n%s" % 
                    [s.encode('utf-8') for s in stats['unique alleles']]]

    post_params = {}
    post_params['type'] = 'text'
    post_params['title'] = update_title
    post_params['body'] = ''.join(post_strings)
    post_params['tags'] = 'Memepool Update'
    post_params['markdown'] = True
    post_params['format'] = 'markdown'
 
    tumblr_request(client,
                   'blog',
                   'post',
                   'meme-pool',
                   params=post_params,
                   method='POST')

def post_children(client, n):
    for i in range(n):
        child, genotype = mate_posts(client)
        post_child(client, child, genotype)


def main():
    client = get_client(CONSUMER_KEY,
                        CONSUMER_SECRET,
                        ACCESS_TOKEN_URL,
                        TUMBLR_USERNAME,
                        TUMBLR_PASSWORD)
    
    memepool = get_posts_by_fitness(client, fitness)
    stats = generate_stats(client, memepool)
    save_stats(stats)
    post_stats(client, stats)
    post_children(client, 5)
        

if __name__ == '__main__':
    main()

