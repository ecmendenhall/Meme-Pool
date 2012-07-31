#!/usr/bin/env python

from __future__ import division

import urllib
import urlparse
import oauth2 as oauth
import json
import random
import flickrapi
import pickle
import csv
from operator import itemgetter

#Store API keys, username & password for xAuth authentication.
CONSUMER_KEY = 'YOUR_TUMBLR_CONSUMER_KEY'
CONSUMER_SECRET = 'YOUR_TUMBLR_CONSUMER_SECRET'
ACCESS_TOKEN_URL = 'https://www.tumblr.com/oauth/access_token'
TUMBLR_USERNAME = 'YOUR_TUMBLR_USERNAME'
TUMBLR_PASSWORD = 'YOUR_TUMBLR_PASSWORD'

#Store Flickr API key
FLICKR_API_KEY = 'YOUR_FLICKR_API_KEY'

#Thanks to John Bunting for the Tumblr xAuth example available here: https://gist.github.com/1298749
def set_up_xauth(consumer_key, consumer_secret, access_token_url, tumblr_username, tumblr_password):
	"""Initializes an xAuth consumer and client, passes in stored credentials, sets signature method to HMAC-SHA1, authenticates and reurns an access token"""
	#Initialize  an xAuth consumer and client, and add the stored credentials.
	consumer = oauth.Consumer(consumer_key, consumer_secret)
	client = oauth.Client(consumer)
	client.add_credentials(tumblr_username, tumblr_password)
	client.authorizations

	params = {}
	params["x_auth_username"] = tumblr_username
	params["x_auth_password"] = tumblr_password
	params["x_auth_mode"] = 'client_auth'

	#Set the signature method to HMAC-SHA1.
	client.set_signature_method = oauth.SignatureMethod_HMAC_SHA1()
	#Authenticate via xAuth. Store the response and access token.
	resp, token = client.request(access_token_url, method="POST", body=urllib.urlencode(params))

	logging.info("xAuth response: %s", resp)

	access_token = dict(urlparse.parse_qsl(token))
	
	logging.info("xAuth access token: %s", access_token) 
	access_token = oauth.Token(access_token['oauth_token'], access_token['oauth_token_secret'])
	client = oauth.Client(consumer, access_token)
	
	return client, access_token

def set_up_flickr(flickr_api_key):
	"""Creates a Flickr API instance."""
	return flickrapi.FlickrAPI(flickr_api_key, format='json')

def get_tagged_image_from_dash(base_hostname):
	"""Randomly selects a tagged image from the dashboard of the given user. Returns its reblog key."""
	params = {'type':'photo'}

	#Get user's dashboard
	resp, dash_json = client.request("http://api.tumblr.com/v2/user/dashboard", method="GET", body=urllib.urlencode(params))
	
	#Get all posts on user's dashboard with tags
	dash_posts_list = json.loads(dash_json)['response']['posts']
	dash_posts_with_tags = sorted(dash_posts_list, key=itemgetter('tags'))
	
	#Remove posts without tags. TK: Empty strings throw this off!
	for post in dash_posts_with_tags:
		if not post['tags']:
			dash_posts_with_tags.remove(post)
	
	#Pick a random post and get its reblog key
	reblog_target = random.choice(dash_posts_with_tags)
	
	#While the selected post has no tags, pick another. Otherwise, return its reblog id.
    i = 0
    reblog_target = None
	while i < len(dash_posts_with_tags) and len(reblog_target['tags']) == 0:	
		reblog_target = random.choice(dash_posts_with_tags)
        i += 1
	else:
		logging.info("Dash reblog target: %s, %s", reblog_target['id'], reblog_target['tags'])
    return reblog_target

def get_all_followers(base_hostname):
	"""Gets all followers of a given user. Returns a list of dicts."""
	resp, users_json = client.request("http://api.tumblr.com/v2/blog/" + base_hostname + ".tumblr.com/followers", method="GET")

	#Get a list of all followers. Returns a list of dicts.
	return json.loads(users_json)['response']['users']

def get_random_follower(base_hostname):
	"""Gets a random follower of the given user. Returns a dict."""
	userslist = get_all_followers(base_hostname)
	
	if not userslist:
		logging.info("No followers!")
		return False
	else:
		#Grab a follower at random
		follower = random.choice(userslist)
        logging.info("Randomly selected follower: %s", follower['name'])
		return follower
	
def get_tagged_image_from_follower(follower):
	"""Retrieves a randomly selected tagged image from a given follower"""
	
	if not follower:
		logging.info("No followers! Skipping image selection.")
		return False
	
	else:
		#Get a list of follower's image posts
		resp, followerposts_json = client.request("http://api.tumblr.com/v2/blog/" + follower['name'] + ".tumblr.com" + "/posts/photo?api_key=" + consumer_key, method="GET")
		follower_posts = json.loads(followerposts_json)
		follower_posts_list = follower_posts['response']['posts'] 

		#Eliminate untagged posts. TK: Check empty strings!
		follower_posts_with_tags = sorted(follower_posts_list, key=itemgetter('tags'))
	
		for post in follower_posts_with_tags:
			if not post['tags']:
				follower_posts_with_tags.remove(post)	
	
		if all(post['tags'] == 0 for post in follower_posts_with_tags):
			new_follower = get_random_follower('meme-pool')
			get_tagged_image_from_follower(new_follower)

		#Pick a random post and get its reblog key
		reblog_target = random.choice(follower_posts_with_tags)
		
		while follower_posts_with_tags == 'submission':
			reblog_target = random.choice(follower_posts_with_tags)
	
		reblog_target = None
        i = 0
        while i < len(follower_posts_with_tags) and len(reblog_target['tags']) == 0:	
			reblog_target = random.choice(follower_posts_with_tags)
            i += 1
		
		return reblog_target
	
def reblog_to_memepool(reblog_target):
	"""Reblogs a given post to the memepool."""
	
	if not reblog_target:
	    pass
	else:
	
		reblog_target_key = reblog_target['reblog_key']
		reblog_target_id = reblog_target['id']
		print "\nReblog target key:"
		print reblog_target_key
	
		comment = ', '.join(reblog_target['tags'])	
	
		#Reblog post into memepool
		reblog_params = {}
		reblog_params['id'] = reblog_target_id
		reblog_params['reblog_key'] = reblog_target_key
		reblog_params['type'] = u'photo'
		reblog_params['tags'] = comment

		resp_reblog, meta = client.request("http://api.tumblr.com/v2/blog/meme-pool.tumblr.com/post/reblog", method="POST", body=urllib.urlencode(reblog_params))
		logging.info("resp_reblog: %s", resp_reblog)

def sort_memepool_by_fitness():
	"""Sorts the current memepool (the last 20 posts on the user's dashboard) by fitness"""
	#Sort the current memepool by fitness (represented by the parameter 'note_count')
	resp_memepool, memepool_json = client.request("http://api.tumblr.com/v2/blog/meme-pool.tumblr.com/posts/photo?api_key=" + consumer_key + "&notes_info=True")
	
	memepool_posts_list = json.loads(memepool_json)['response']['posts']
	memepool_posts_by_fitness = sorted(memepool_posts_list, key=itemgetter('note_count'))

	return memepool_posts_by_fitness

def mate_posts(sorted_list):
	"""Takes a list of posts in the memepool, mates the given posts, queries the Flickr API for an image, and posts to the memepool."""
	
	#Calculate memepool population
	population = len(sorted_list)
	
	#Pick two mates. Multiplying two random integers between 0 and 1 selects for fitter mates more often.
	mate1 = int(population - (random.random() * random.random() * population))
	mate2 = int(population - (random.random() * random.random() * population))
	
	#If mate1 and mate2 are the same, pick a new mate2
	while mate1 == mate2:
		mate2 = int(population - (random.random() * random.random() * population))
	
	#Choose an allele from each mate
	papa_allele = random.choice(sorted_list[mate1]['tags'])
	mama_allele = random.choice(sorted_list[mate2]['tags'])
	image_tags = papa_allele + ", " + mama_allele
	
	#Search Flickr for photos with both tags. If none are found, search for photos with either tag.
	flickr_json = flickr.photos_search(tags=image_tags, tag_mode='all', license='1,2,3,4,5,6,7', sort='interestingness-desc')[14:-1]
	allele_photos = json.loads(flickr_json)
	
	if allele_photos['photos']['total'] == '0':
		flickr_json = flickr.photos_search(tags=image_tags, license='1,2,3,4,5,6,7', sort='interestingness-desc')[14:-1]
		allele_photos = json.loads(flickr_json)
	
	#Sort returned photos by interestingness and choose more interesting photos more often
	
	number_of_interesting_photos = len(allele_photos['photos']['photo']) - 1
	chosen_photo = int(random.random() * random.random() * number_of_interesting_photos)
	most_interesting_photo = allele_photos['photos']['photo'][chosen_photo]
	
	#Get the chosen photo's id information and generate its source url
	mip_id = str(most_interesting_photo['id'])
	mip_secret = str(most_interesting_photo['secret'])
	
	photo_source_url = "http://farm" + str(most_interesting_photo['farm']) + ".staticflickr.com/" + str(most_interesting_photo['server']) + "/" + mip_id + "_" + mip_secret + ".jpg"
	photo_page_url = "http://www.flickr.com/photos/" + str(most_interesting_photo['owner']) + "/" + mip_id 
	
	photo_info_json = flickr.photos_getinfo(photo_id=mip_id, secret=mip_secret)[14:-1]
	photo_info = json.loads(photo_info_json)
	
	#Check that the photo is freely available
	photo_owner = photo_info['photo']['owner']['username']
	photo_license_id = photo_info['photo']['license']
	photo_license = ""
	
	if photo_license_id == '0':
        logging.info("Warning! This image is copyrighted!")
		
	elif photo_license_id == '1':
		photo_license = "Attribution-NonCommercial-ShareAlike License"
		photo_license_url = "http://creativecommons.org/licenses/by-nc-sa/2.0/"
	
	elif photo_license_id == '2':
		photo_license = "Attribution-NonCommercial License"
		photo_license_url = "http://creativecommons.org/licenses/by-nc/2.0/"
	
	elif photo_license_id == '3':
		photo_license = "Attribution-NonCommercial-NoDerivs License"
		photo_license_url = "http://creativecommons.org/licenses/by-nc-nd/2.0/"
	
	elif photo_license_id == '4':
		photo_license = "Attribution License"
		photo_license_url = "http://creativecommons.org/licenses/by/2.0/"
	
	elif photo_license_id == '5':
		photo_license = "Attribution-ShareAlike License"
		photo_license_url = "http://creativecommons.org/licenses/by-sa/2.0/"
	
	elif photo_license_id == '6':
		photo_license = "Attribution-NoDerivs License"
		photo_license_url = "http://creativecommons.org/licenses/by-nd/2.0/"
	
	elif photo_license_id == '7':
		photo_license = "Public Domain License"
		photo_license_url = "http://flickr.com/commons/usage/"
	
	#Generate a caption including the username and license
	photo_caption = "Photo from Flickr user [" + photo_owner + "](" + photo_page_url + "). [Some rights](" + photo_license_url + ") reserved."
	
	#Add photo information to post parameters and send to Tumblr.
	post_params = {}
	post_params['type'] = 'photo'
	post_params['tags'] = image_tags
	post_params['caption'] = photo_caption
	post_params['link'] = photo_page_url
	post_params['source'] = photo_source_url
	post_params['markdown'] = True
	
	# This is a workaround for markdown formatting, based on the old API. Use at your own risk!
	post_params['format'] = 'markdown'
	
	response = client.request("http://api.tumblr.com/v2/blog/meme-pool.tumblr.com/post", method="POST", body=urllib.urlencode(post_params))
	logging.info("Photo post response: %s", response)

def save_generation_stats(sorted_memepool):
	"""Accepts a population and updates and saves statistics on the current generation, including number of contributors, unique alleles in the current population, and summary fitness statistics. Statistics are saved to the file 'memepool_log.csv,' and data on the previous generation is unpickled from the file 'latest_pickle.txt'."""
	
    #Retrieve last generation from the database
	g = Generation.all()
    last_generation = g.order('-saved').get()

    if not last_generation:
        current_generation = 1
    else:	
	    current_generation = last_generation.generation + 1
	
    all_followers = get_all_followers('meme-pool')
	
	contributors = len(all_followers)
	
	#Get all alleles in the current memepool
	allele_list = []
	for post in sorted_memepool:
		for tag in post['tags']:
			tag.encode('utf-8')
			allele_list.append(tag.lower())
	
	total_alleles = len(allele_list)
			
	allele_dict = {}
	for allele in allele_list:
		allele_dict[allele] = [allele_list.count(allele)]
	
	allele_tuples = sorted(allele_dict.items(), key=itemgetter(1), reverse=True)
	
 	#Get a set of unique alleles in population
	allele_set = set([])
	for post in sorted_memepool:
		for tag in post['tags']:
			allele_set.add(tag.lower())
	
	#Make sure they are encoded as utf-8	
	allele_set_list = list(allele_set)
	allele_set_list_utf8 = []
	for item in allele_set_list:
		utf = item.encode('utf-8')
		allele_set_list_utf8.append(utf)
	
	#Remove the tag 'submission,' which is automatically appended by Tumblr to user-submitted posts.
	if 'submission' in allele_set:
		allele_set_list_utf8.remove('submission')
	
	allele_set_list_utf8.sort()
	
	#Get number of unique alleles
	unique_alleles = len(allele_set)
	
	#Get total population
	population = len(sorted_memepool)
	
	#Calculate post urls and genomes for least and most fit posts.
	leastfit = sorted_memepool[0]['note_count']
	leastfit_url = sorted_memepool[0]['post_url']
	leastfit_genome = sorted_memepool[0]['tags']
	leastfit_genome_utf8 = []
	for item in leastfit_genome:
		utf = item.encode('utf-8')
		leastfit_genome_utf8.append(utf)
		
	mostfit = sorted_memepool[-1]['note_count']
	mostfit_url = sorted_memepool[-1]['post_url']	
	mostfit_genome = sorted_memepool[-1]['tags']
	mostfit_genome_utf8 = []
	for item in mostfit_genome:
		utf = item.encode('utf-8')
		mostfit_genome_utf8.append(utf)
	
	#Calculate total fitness
	memepool_total_fitness = 0
	for post in sorted_memepool:
		memepool_total_fitness = memepool_total_fitness + int(post['note_count'])
		
	#Calculate mean fitness
	mean_fitness = round(memepool_total_fitness / population, 3)
	
    #Store generation statistics in database.
    gen = Generation()
    gen.generation = current_generation
    gen.population = population
    gen. mean_fitness = mean_fitness
    gen.total_fitness = memepool_total_fitness
    gen.most_fit_genome = mostfit_genome_utf8
    gen.most_fit_post_fitness = mostfit
    gen.most_fit_post_url = mostfit_url
    gen.least_fit_genome = leastfit_genome_utf8
    gen.least_fit_post_fitness = leastfit
    gen.least_fit_post_url = leastfit_url
    gen.unique_alleles = allele_set_list_utf8
    gen.n_unique_alleles = unique_alleles
    gen.contributors = contributors
    db.put(gen)
	
	
	#Format the statistics with markdown for a Tumblr post, and submit to Tumblr.
	stats_update_title = 'Memepool update: Generation %d' % current_generation
	stats_update_text = "* __Population:__ %d\n* __Mean fitness:__ %d\n* __Fittest genome:__ [%s](%s) (%d)\n* __Least fit genome:__ [%s](%s) (%d)\n* __Unique alleles in population:__ %d\n* __Contributors to memepool:__ %s\n* __Set of unique alleles:__ \n%s" % (population, mean_fitness, mostfit_genome_utf8, mostfit_url, mostfit, leastfit_genome_utf8, leastfit_url, leastfit, unique_alleles, contributors, allele_set_list_utf8)
	
	post_params = {}
	post_params['type'] = 'text'
	post_params['title'] = stats_update_title
	post_params['body'] = stats_update_text
	post_params['tags'] = 'Memepool Update'
	post_params['markdown'] = True
	post_params['format'] = 'markdown'
	
	response = client.request("http://api.tumblr.com/v2/blog/meme-pool.tumblr.com/post", method="POST", body=urllib.urlencode(post_params))
	logging.info("Stats post response: %s," response)

def main():
    client, access_token = set_up_xauth(consumer_key, consumer_secret, access_token_url, tumblr_username, tumblr_password)
    flickr = set_up_flickr(flickr_api_key)
    sorted_memepool = sort_memepool_by_fitness()
    mate_posts(sorted_memepool)
    mate_posts(sorted_memepool)
    mate_posts(sorted_memepool)
    save_generation_stats(sorted_memepool)

if __name__ == '__main__':
    main()
